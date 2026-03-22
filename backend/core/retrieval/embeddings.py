"""Embedding generation and embedding-text construction."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from config import Settings
from core.llm.client import LLMClient
from core.retrieval.chunking import chunk_text
from utils.text import clean_readme_markdown, truncate_by_tokens

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client

    def build_repository_metadata_text(self, repo: dict[str, Any]) -> str:
        summary = truncate_by_tokens(
            str(repo.get("ai_summary", "")),
            int(self.settings.embedding_summary_max_tokens),
        )
        parts = [
            str(repo.get("name", "")),
            str(repo.get("description", "")),
            " ".join(repo.get("topics", []) or []),
            " ".join(repo.get("tags", []) or []),
            summary,
        ]
        merged = " ".join(part for part in parts if part).strip()
        return truncate_by_tokens(merged, int(self.settings.embedding_readme_max_tokens))

    def build_repository_readme_text(self, repo: dict[str, Any]) -> str:
        """Build README text for embedding using smart chunking.

        Instead of simple truncation, this method:
        1. Cleans and normalizes the README
        2. Chunks it into semantic units
        3. Selects the most important chunks (first + keyword-rich)
        4. Concatenates them within token limits
        """
        cleaned = repo.get("readme_for_embedding", "")
        if not cleaned:
            cleaned = clean_readme_markdown(repo.get("readme", ""))

        if not cleaned:
            return ""

        max_tokens = int(self.settings.embedding_readme_max_tokens)
        # Approximate chars per token (conservative for mixed content)
        max_chars = max_tokens * 3

        if len(cleaned) <= max_chars:
            return cleaned

        # Use recursive chunking for better semantic preservation
        chunks = chunk_text(cleaned, chunk_size=512, chunk_overlap=50)

        if not chunks:
            return truncate_by_tokens(cleaned, max_tokens)

        # Strategy: Select important chunks
        # 1. Always include first chunk (project intro)
        # 2. Score remaining chunks by keyword density
        # 3. Fill remaining budget with high-scoring chunks

        selected = [chunks[0]]  # First chunk always included
        remaining_budget = max_chars - len(chunks[0])

        if len(chunks) > 1:
            # Score chunks by information density (simple heuristic)
            scored_chunks = []
            for i, chunk in enumerate(chunks[1:], start=1):
                score = self._score_chunk_importance(chunk, repo)
                scored_chunks.append((score, i, chunk))

            # Sort by score (descending)
            scored_chunks.sort(key=lambda x: x[0], reverse=True)

            # Add chunks by score until budget exhausted
            for score, idx, chunk in scored_chunks:
                chunk_len = len(chunk) + 2  # +2 for separator
                if chunk_len <= remaining_budget:
                    selected.append(chunk)
                    remaining_budget -= chunk_len
                if remaining_budget < 100:
                    break

        result = "\n\n".join(selected)
        return truncate_by_tokens(result, max_tokens)

    def _score_chunk_importance(self, chunk: str, repo: dict[str, Any]) -> float:
        """Score a chunk's importance for embedding.

        Higher scores indicate more valuable content.
        """
        score = 0.0
        chunk_lower = chunk.lower()

        # Boost for containing repo name
        name = repo.get("name", "")
        if name and name.lower() in chunk_lower:
            score += 10.0

        # Boost for installation/usage sections
        important_keywords = [
            "install", "usage", "example", "quick start", "getting started",
            "安装", "使用", "示例", "快速开始",
            "feature", "特性", "功能",
            "api", "配置", "config",
        ]
        for kw in important_keywords:
            if kw in chunk_lower:
                score += 2.0

        # Boost for code blocks (indicate examples)
        code_block_count = chunk.count("```")
        score += code_block_count * 1.5

        # Penalize very short chunks
        if len(chunk) < 50:
            score -= 5.0

        # Boost for reasonable length (100-500 chars is ideal)
        if 100 <= len(chunk) <= 500:
            score += 3.0

        return score

    def build_legacy_embedding_text(self, repo: dict[str, Any]) -> str:
        metadata_text = self.build_repository_metadata_text(repo)
        readme_text = self.build_repository_readme_text(repo)
        return " ".join(part for part in [metadata_text, readme_text] if part)

    def hash_embedding_source(self, text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    async def generate_embedding_vector(self, text_content: str) -> list[float]:
        try:
            embedding = await self.llm_client.create_embedding(text_content)
            expected_dim = int(self.settings.embedding_dimension)
            if len(embedding) != expected_dim:
                logger.error(
                    "Embedding dimension mismatch: expected %s, got %s (model=%s).",
                    expected_dim,
                    len(embedding),
                    self.settings.openai_embedding_model,
                )
                return [0.0] * expected_dim
            return embedding
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            return [0.0] * int(self.settings.embedding_dimension)

    async def generate_dual_repository_embeddings(self, repo: dict[str, Any]) -> dict[str, Any]:
        metadata_text = self.build_repository_metadata_text(repo)
        readme_text = self.build_repository_readme_text(repo)

        metadata_embedding = None
        readme_embedding = None
        if metadata_text:
            metadata_embedding = await self.generate_embedding_vector(metadata_text)
        if readme_text:
            readme_embedding = await self.generate_embedding_vector(readme_text)

        return {
            "metadata_text": metadata_text,
            "readme_text": readme_text,
            "metadata_hash": self.hash_embedding_source(metadata_text),
            "readme_hash": self.hash_embedding_source(readme_text),
            "repo_metadata_embedding": metadata_embedding,
            "readme_embedding": readme_embedding,
        }
