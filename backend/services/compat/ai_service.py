"""Backward-compatible AI service facade.

Existing import path `services.ai_service` is preserved while
implementation now delegates to object-based services/core components.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from services.service_registry import (
    get_chat_service,
    get_repository_service,
    search_service,
    embedding_service,
    repository_analyzer,
)
from services.domain import ReadmeCleaner

_readme_cleaner = ReadmeCleaner()


async def analyze_repository(repo_data: dict) -> dict:
    return await repository_analyzer.analyze_repository(repo_data)


def build_metadata_text(repo: dict) -> str:
    return embedding_service.build_repository_metadata_text(repo)


def _build_embedding_text(repo: dict) -> str:
    return embedding_service.build_legacy_embedding_text(repo)


async def generate_embedding(text_content: str) -> list[float]:
    return await embedding_service.generate_embedding_vector(text_content)


async def generate_repo_embedding(repo: dict) -> list[float]:
    return await generate_embedding(_build_embedding_text(repo))


async def generate_dual_embeddings(repo: dict) -> dict:
    return await embedding_service.generate_dual_repository_embeddings(repo)


async def semantic_search(db: AsyncSession, query: str, top_k: int = 5) -> list[dict]:
    return await search_service.semantic_repository_search(db, query, top_k=top_k)


async def chat_with_repos(query: str, repos: list[dict]) -> str:
    return await get_chat_service().chat_responder.generate_chat_answer(query, repos)


def clean_readme_for_embedding(raw_readme: str) -> str:
    return _readme_cleaner.clean_for_embedding(
        raw_readme,
        max_tokens=int(get_repository_service().settings.embedding_readme_max_tokens),
    )


__all__ = [
    "analyze_repository",
    "build_metadata_text",
    "chat_with_repos",
    "clean_readme_for_embedding",
    "generate_dual_embeddings",
    "generate_embedding",
    "generate_repo_embedding",
    "semantic_search",
    "_build_embedding_text",
]
