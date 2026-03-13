"""Embedding generation and embedding-text construction."""

import hashlib
import logging
from typing import Any

from config import get_settings
from core.llm.client import create_embedding
from utils.text import clean_readme_markdown, truncate_by_tokens

logger = logging.getLogger(__name__)
settings = get_settings()


def build_repository_metadata_text(repo: dict[str, Any]) -> str:
    summary = truncate_by_tokens(
        str(repo.get("ai_summary", "")),
        int(settings.embedding_summary_max_tokens),
    )
    parts = [
        str(repo.get("name", "")),
        str(repo.get("description", "")),
        " ".join(repo.get("topics", []) or []),
        " ".join(repo.get("tags", []) or []),
        summary,
    ]
    merged = " ".join(part for part in parts if part).strip()
    return truncate_by_tokens(merged, int(settings.embedding_readme_max_tokens))


def build_repository_readme_text(repo: dict[str, Any]) -> str:
    cleaned = clean_readme_markdown(repo.get("readme", ""))
    return truncate_by_tokens(cleaned, int(settings.embedding_readme_max_tokens))


def build_legacy_embedding_text(repo: dict[str, Any]) -> str:
    metadata_text = build_repository_metadata_text(repo)
    readme_text = build_repository_readme_text(repo)
    return " ".join(part for part in [metadata_text, readme_text] if part)


def hash_embedding_source(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


async def generate_embedding_vector(text_content: str) -> list[float]:
    try:
        embedding = await create_embedding(text_content)
        expected_dim = int(settings.embedding_dimension)
        if len(embedding) != expected_dim:
            logger.error(
                "Embedding dimension mismatch: expected %s, got %s (model=%s).",
                expected_dim,
                len(embedding),
                settings.openai_embedding_model,
            )
            return [0.0] * expected_dim
        return embedding
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        return [0.0] * int(settings.embedding_dimension)


async def generate_dual_repository_embeddings(repo: dict[str, Any]) -> dict[str, Any]:
    metadata_text = build_repository_metadata_text(repo)
    readme_text = build_repository_readme_text(repo)

    metadata_embedding = None
    readme_embedding = None
    if metadata_text:
        metadata_embedding = await generate_embedding_vector(metadata_text)
    if readme_text:
        readme_embedding = await generate_embedding_vector(readme_text)

    return {
        "metadata_text": metadata_text,
        "readme_text": readme_text,
        "metadata_hash": hash_embedding_source(metadata_text),
        "readme_hash": hash_embedding_source(readme_text),
        "repo_metadata_embedding": metadata_embedding,
        "readme_embedding": readme_embedding,
    }
