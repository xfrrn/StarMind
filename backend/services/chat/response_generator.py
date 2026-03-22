from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

from core.llm import LLMClient
from services.chat.exceptions import GenerationError
from services.chat.models import BuiltContext
from services.chat.prompts import (
    GENERAL_CHAT_PROMPT,
    REPO_ANALYSIS_PROMPT,
    REPO_COMPARE_PROMPT,
    REPO_RECOMMEND_PROMPT,
    REPO_SEARCH_PROMPT,
)
from services.chat.types import IntentType

logger = logging.getLogger(__name__)


class ResponseGenerator:
    def __init__(self, llm_client: LLMClient, timeout_seconds: float = 8.0):
        self.llm_client = llm_client
        self.timeout_seconds = max(1.0, timeout_seconds)

    @staticmethod
    def _pick_prompt(intent_type: IntentType) -> str:
        if intent_type == "repo_analysis":
            return REPO_ANALYSIS_PROMPT
        if intent_type == "repo_compare":
            return REPO_COMPARE_PROMPT
        if intent_type == "repo_recommend":
            return REPO_RECOMMEND_PROMPT
        if intent_type == "repo_search":
            return REPO_SEARCH_PROMPT
        return GENERAL_CHAT_PROMPT

    async def generate(self, *, user_message: str, built_context: BuiltContext) -> str:
        prompt = self._pick_prompt(built_context.intent_type).format(
            user_message=user_message,
            context=built_context.prompt_context or "No repository context provided.",
        )
        try:
            return await asyncio.wait_for(
                self.llm_client.create_chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.35,
                    max_tokens=900,
                    enforce_json=False,
                ),
                timeout=self.timeout_seconds,
            )
        except Exception as e:
            logger.error("Chat response generation failed: %s", e)
            raise GenerationError(str(e)) from e

    async def generate_stream(
        self, *, user_message: str, built_context: BuiltContext
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens one by one."""
        prompt = self._pick_prompt(built_context.intent_type).format(
            user_message=user_message,
            context=built_context.prompt_context or "No repository context provided.",
        )
        try:
            async for token in self.llm_client.create_chat_completion_stream(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.35,
                max_tokens=900,
            ):
                yield token
        except Exception as e:
            logger.error("Chat response streaming failed: %s", e)
            raise GenerationError(str(e)) from e

    @staticmethod
    def build_fallback(user_message: str, built_context: BuiltContext) -> str:
        if not built_context.repositories:
            return (
                "我没有在你已同步的仓库里找到明显匹配。"
                "你可以尝试补充语言、技术关键词或仓库名称来缩小范围。"
            )
        names = ", ".join(repo.full_name for repo in built_context.repositories[:3])
        return f"我先给你候选仓库：{names}。如果你愿意，我可以继续按用途做更细的对比。"

    @staticmethod
    def build_structured_fallback(built_context: BuiltContext) -> str:
        if not built_context.repositories:
            return (
                "这次生成超时了，而且我没有足够候选仓库。"
                "你可以补充更具体的关键词（语言、功能、仓库名）后重试。"
            )
        lines = [
            "这次模型生成超时了，我先给你结构化结果：",
        ]
        for idx, repo in enumerate(built_context.repositories[:5], 1):
            lines.append(
                f"{idx}. {repo.full_name} | {repo.language or 'N/A'} | "
                f"matched_by={','.join(repo.matched_by)} | reason={repo.why_relevant or 'N/A'}"
            )
        lines.append("如果你愿意，我可以基于这几个仓库继续做更细的对比或推荐。")
        return "\n".join(lines)
