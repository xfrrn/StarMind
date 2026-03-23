"""Repository-specific chat service for deep conversations about a single repo."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.llm import LLMClient
from models.repository import Repository
from services.chat.prompts import REPO_CHAT_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class RepoChatResponse:
    """Response for repository chat."""

    answer: str
    repo_id: int
    repo_name: str
    repo: Repository | None = None


class RepoChatService:
    """Service for having conversations about a specific repository."""

    def __init__(self, *, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client

    async def chat(
        self,
        db: AsyncSession,
        repo_id: int,
        message: str,
        history: list | None = None,
    ) -> RepoChatResponse:
        """Chat about a specific repository.

        Args:
            db: Database session
            repo_id: Repository ID
            message: User message
            history: Conversation history

        Returns:
            RepoChatResponse with answer and repo info
        """
        # 1. Get repository
        repo = await self._get_repo(db, repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        # 2. Build context
        context = self._build_context(repo)

        # 3. Generate response
        answer = await self._generate(message, context, history or [])

        return RepoChatResponse(
            answer=answer,
            repo_id=repo_id,
            repo_name=repo.name,
            repo=repo,
        )

    async def _get_repo(self, db: AsyncSession, repo_id: int) -> Repository | None:
        """Fetch repository by ID."""
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        return result.scalar_one_or_none()

    def _build_context(self, repo: Repository) -> str:
        """Build context string from repository data."""
        parts = [
            f"## Repository: {repo.name}",
            "",
        ]

        if repo.description:
            parts.append(f"**Description:** {repo.description}")
            parts.append("")

        if repo.language:
            parts.append(f"**Language:** {repo.language}")
            parts.append("")

        if repo.tags:
            parts.append(f"**Tags:** {', '.join(repo.tags)}")
            parts.append("")

        if repo.category:
            parts.append(f"**Category:** {repo.category}")
            parts.append("")

        if repo.ai_summary:
            parts.append("## AI Summary")
            parts.append(repo.ai_summary)
            parts.append("")

        # Add README content (truncate to avoid token limits)
        readme_content = repo.readme or ""
        if readme_content:
            # Limit README to ~6000 chars to stay within token budget
            if len(readme_content) > 6000:
                readme_content = readme_content[:6000] + "\n\n... (truncated)"
            parts.append("## README Content")
            parts.append(readme_content)

        return "\n".join(parts)

    async def _generate(
        self,
        message: str,
        context: str,
        history: list,
    ) -> str:
        """Generate response using LLM."""
        # Build messages
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions about GitHub repositories. Answer in the same language as the user's question. Be concise but thorough.",
            }
        ]

        # Add conversation history
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("message", "")
            if role == "user":
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "assistant", "content": content})

        # Add current message with context
        prompt = REPO_CHAT_PROMPT.format(context=context, user_message=message)
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.llm_client.create_chat_completion(
                messages=messages,
                temperature=0.35,
                max_tokens=1000,
                enforce_json=False,
            )
            return response
        except Exception as e:
            logger.error("Repo chat generation failed: %s", e)
            raise
