"""Collection overview service for AI-generated collection summaries."""

from __future__ import annotations

import logging
from typing import Any

from config import Settings
from core.llm import LLMClient
from services.application.collection_service import CollectionService

logger = logging.getLogger(__name__)

OVERVIEW_SYSTEM_PROMPT = """你是一个帮助用户管理 GitHub Star 仓库的智能助手。
你的任务是根据用户提供的收藏夹信息，生成一个结构化的 Markdown 总览。

总览应该包含：
1. 收藏夹的主题总结（一句话概括）
2. 仓库分类和亮点（按功能/技术栈分组）
3. 推荐的阅读顺序或使用建议（可选）

请使用中文输出，格式清晰，适合在网页上展示。"""

OVERVIEW_USER_PROMPT_TEMPLATE = """请为以下收藏夹生成一个 Markdown 总览。

收藏夹名称：{collection_name}
收藏夹描述：{collection_description}
用户提示：{user_prompt}

收藏夹内的仓库列表（共 {repo_count} 个）：

{repos_info}

请生成一个结构化的 Markdown 总览。"""


class CollectionOverviewService:
    """Service for generating AI-powered collection overviews."""

    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client
        self.collection_service = CollectionService()

    def _format_repo_info(self, repos: list[dict[str, Any]]) -> str:
        """Format repository information for the prompt."""
        lines = []
        for i, repo in enumerate(repos, 1):
            tags_str = ", ".join(repo.get("repo_tags", []) or repo.get("tags", []))
            info_parts = [
                f"{i}. **{repo.get('full_name') or repo.get('name')}**",
                f"   - Stars: {repo.get('stars', 'N/A')}",
                f"   - Language: {repo.get('language') or 'N/A'}",
                f"   - Category: {repo.get('category') or 'N/A'}",
            ]
            if tags_str:
                info_parts.append(f"   - Tags: {tags_str}")
            if repo.get("description"):
                # Truncate long descriptions
                desc = repo["description"][:200] + "..." if len(repo["description"]) > 200 else repo["description"]
                info_parts.append(f"   - Description: {desc}")
            if repo.get("summary"):
                # Truncate long summaries
                summary = repo["summary"][:150] + "..." if len(repo["summary"]) > 150 else repo["summary"]
                info_parts.append(f"   - Summary: {summary}")
            lines.append("\n".join(info_parts))
        return "\n\n".join(lines)

    async def generate_overview(
        self,
        db,
        collection_id: int,
        prompt: str = "",
    ) -> str:
        """Generate an AI overview for a collection.

        Args:
            db: Database session
            collection_id: Collection ID
            prompt: Optional user prompt to guide generation

        Returns:
            Generated Markdown content
        """
        # Get collection info
        collection = await self.collection_service.get_collection(db, collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        # Get repositories in the collection
        repos = await self.collection_service.get_collection_repos_for_overview(db, collection_id)
        if not repos:
            return "该收藏夹暂无仓库，无法生成总览。"

        # Format repository info
        repos_info = self._format_repo_info(repos)

        # Build the prompt
        user_prompt = OVERVIEW_USER_PROMPT_TEMPLATE.format(
            collection_name=collection["name"],
            collection_description=collection.get("description") or "无",
            user_prompt=prompt or "请根据仓库信息自动生成总览",
            repo_count=len(repos),
            repos_info=repos_info,
        )

        messages = [
            {"role": "system", "content": OVERVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.llm_client.create_chat_completion(
                messages=messages,
                temperature=0.5,
                max_tokens=1500,
                enforce_json=False,
            )
            logger.info(f"Generated overview for collection {collection_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to generate overview: {e}")
            raise RuntimeError(f"Failed to generate overview: {e}") from e
