from __future__ import annotations

from services.chat.models import BuiltContext, RankedRepoCandidate
from services.chat.policies import ChatPolicy
from services.chat.types import IntentType
from utils.text import truncate_by_tokens


class ContextBuilder:
    def __init__(self, policy: ChatPolicy):
        self.policy = policy

    def build(self, intent_type: IntentType, candidates: list[RankedRepoCandidate]) -> BuiltContext:
        repos = candidates[: self.policy.max_context_repos]
        lines: list[str] = []
        for idx, repo in enumerate(repos, 1):
            snippet = (repo.cleaned_readme_snippet or "").strip()
            snippet = snippet[: self.policy.max_readme_snippet_chars]
            lines.append(
                "\n".join(
                    [
                        f"{idx}. {repo.full_name}",
                        f"   Description: {repo.description or 'N/A'}",
                        f"   Language: {repo.language or 'N/A'}",
                        f"   Topics: {', '.join(repo.topics[:8])}",
                        f"   Tags: {', '.join(repo.tags[:8])}",
                        f"   Category: {repo.category or 'N/A'}",
                        f"   Summary: {repo.analysis_summary or 'N/A'}",
                        f"   Matched By: {', '.join(repo.matched_by)}",
                        f"   Why Relevant: {repo.why_relevant}",
                        f"   Snippet: {snippet or 'N/A'}",
                    ]
                )
            )
        context = truncate_by_tokens("\n\n".join(lines), self.policy.max_prompt_context_tokens)
        return BuiltContext(intent_type=intent_type, prompt_context=context, repositories=repos)
