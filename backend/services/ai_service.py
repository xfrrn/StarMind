"""Backward-compatible AI service facade.

Existing import path `services.ai_service` is preserved while
implementation lives in `core` and `services` layers.
"""

from core.analysis import analyze_repository, generate_chat_answer
from core.retrieval import (
    build_legacy_embedding_text as _build_embedding_text,
    build_repository_metadata_text as build_metadata_text,
    generate_dual_repository_embeddings as generate_dual_embeddings,
    generate_embedding_vector as generate_embedding,
    semantic_repository_search as semantic_search,
)
from config import get_settings
from utils.text import clean_readme_markdown, truncate_by_tokens


async def generate_repo_embedding(repo: dict) -> list[float]:
    return await generate_embedding(_build_embedding_text(repo))


async def chat_with_repos(query: str, repos: list[dict]) -> str:
    return await generate_chat_answer(query, repos)


def clean_readme_for_embedding(raw_readme: str) -> str:
    settings = get_settings()
    cleaned = clean_readme_markdown(raw_readme)
    return truncate_by_tokens(cleaned, int(settings.embedding_readme_max_tokens))


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
