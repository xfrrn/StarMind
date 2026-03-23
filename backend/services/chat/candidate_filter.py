"""Candidate filtering: threshold + LLM verification."""

from __future__ import annotations

import json
import logging
from typing import Any

from config import Settings
from core.llm import LLMClient
from services.chat.models import RankedRepoCandidate, RepoQuery

logger = logging.getLogger(__name__)

FILTER_PROMPT = """You are a precise repository matcher. Given a user query and a list of repositories, determine which ones TRULY match the user's needs.

User query: "{query}"

Repositories:
{repos_list}

For each repository, determine if it genuinely matches what the user is looking for. Consider:
1. Does it solve the user's stated problem?
2. Is it relevant to the user's intent (not just tangentially related)?
3. Would you recommend it to someone with this exact request?

Return ONLY a JSON object with repository indices as keys and boolean match status as values.
Example: {{"0": true, "1": false, "2": true}}

Be strict: only mark as true if the repository clearly addresses the user's need."""


class CandidateFilter:
    def __init__(
        self,
        settings: Settings,
        llm_client: LLMClient,
        similarity_threshold: float | None = None,
        llm_filter_enabled: bool | None = None,
    ):
        self.settings = settings
        self.llm_client = llm_client
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else settings.chat_similarity_threshold
        self.llm_filter_enabled = llm_filter_enabled if llm_filter_enabled is not None else settings.chat_llm_filter_enabled

    def filter_by_threshold(
        self,
        candidates: list[RankedRepoCandidate],
    ) -> list[RankedRepoCandidate]:
        """Filter candidates by similarity score threshold."""
        if self.similarity_threshold <= 0:
            return candidates

        filtered = [c for c in candidates if c.final_score >= self.similarity_threshold]
        logger.info(
            "Threshold filter: %d -> %d candidates (threshold=%.2f)",
            len(candidates),
            len(filtered),
            self.similarity_threshold,
        )
        return filtered

    async def verify_with_llm(
        self,
        query: str,
        candidates: list[RankedRepoCandidate],
    ) -> list[RankedRepoCandidate]:
        """Use LLM to verify which candidates truly match the query."""
        if not self.llm_filter_enabled or len(candidates) == 0:
            return candidates

        # Build repository list for prompt
        repos_list = []
        for i, c in enumerate(candidates):
            repo_info = f"[{i}] {c.full_name}\n"
            repo_info += f"    Description: {c.description or 'N/A'}\n"
            repo_info += f"    Category: {c.category}\n"
            if c.analysis_summary:
                repo_info += f"    AI Summary: {c.analysis_summary[:200]}\n"
            if c.tags:
                repo_info += f"    Tags: {', '.join(c.tags[:5])}\n"
            repos_list.append(repo_info)

        prompt = FILTER_PROMPT.format(
            query=query,
            repos_list="\n".join(repos_list),
        )

        try:
            response = await self.llm_client.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
                enforce_json=True,
            )

            # Parse LLM response
            match_results = self._parse_filter_response(response, len(candidates))

            # Filter candidates based on LLM judgment
            verified = [c for i, c in enumerate(candidates) if match_results.get(i, True)]

            logger.info(
                "LLM verification: %d -> %d candidates verified",
                len(candidates),
                len(verified),
            )
            return verified

        except Exception as e:
            logger.warning("LLM verification failed, returning threshold-filtered results: %s", e)
            return candidates

    def _parse_filter_response(self, response: str, num_candidates: int) -> dict[int, bool]:
        """Parse LLM filter response into a dict of index -> match status."""
        try:
            # Try to extract JSON from response
            data = json.loads(response)
            if isinstance(data, dict):
                return {int(k): bool(v) for k, v in data.items() if str(k).isdigit()}
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse LLM filter response: %s", e)

        # Default: all candidates pass
        return {i: True for i in range(num_candidates)}

    async def filter_candidates(
        self,
        query: str,
        candidates: list[RankedRepoCandidate],
    ) -> list[RankedRepoCandidate]:
        """Full filtering pipeline: threshold + LLM verification."""
        # Step 1: Threshold filtering
        threshold_passed = self.filter_by_threshold(candidates)

        if len(threshold_passed) == 0:
            return []

        # Step 2: LLM verification
        verified = await self.verify_with_llm(query, threshold_passed)

        return verified
