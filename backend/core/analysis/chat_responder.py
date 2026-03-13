"""Generate chat answers from retrieved repositories."""

import logging
from typing import Any

from core.llm.client import LLMClient
from core.llm.prompts import CHAT_RESPONSE_PROMPT

logger = logging.getLogger(__name__)


class ChatResponder:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    @staticmethod
    def build_repositories_context(repos: list[dict[str, Any]]) -> str:
        if not repos:
            return "No relevant repositories were found."

        parts = []
        for i, repo in enumerate(repos, 1):
            parts.append(
                f"{i}. **{repo['name']}** ({repo['stars']:,} stars)\n"
                f"   Language: {repo['language']}\n"
                f"   Description: {repo['description']}\n"
                f"   AI Summary: {repo.get('ai_summary', 'N/A')}\n"
                f"   Tags: {', '.join(repo.get('tags', []))}\n"
            )
        return "\n".join(parts)

    async def generate_chat_answer(self, query: str, repos: list[dict[str, Any]]) -> str:
        prompt = CHAT_RESPONSE_PROMPT.format(
            query=query,
            repos_context=self.build_repositories_context(repos),
        )
        try:
            return await self.llm_client.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1500,
                enforce_json=False,
            )
        except Exception as e:
            logger.error("Chat generation failed: %s", e)
            return "I'm sorry, I encountered an error while generating a response. Please try again later."
