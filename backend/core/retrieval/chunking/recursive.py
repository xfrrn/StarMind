"""Recursive character text chunker with multi-level separators.

Borrowed from SurveyAgent's RAG design - splits text recursively using
priority separators to maintain semantic integrity.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk with metadata."""

    content: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)


class RecursiveChunker:
    """Recursive character text splitter.

    Splits text using a hierarchy of separators, trying larger semantic
    units first (paragraphs) before falling back to smaller units (sentences, words).

    Default separators are optimized for mixed Chinese/English content.
    """

    # Default separator hierarchy (from largest to smallest semantic unit)
    DEFAULT_SEPARATORS: list[str] = [
        "\n\n",       # Paragraphs
        "\n",         # Lines
        "。",         # Chinese period
        "！",         # Chinese exclamation
        "？",         # Chinese question mark
        "；",         # Chinese semicolon
        ".",          # English period
        "!",          # English exclamation
        "?",          # English question mark
        ";",          # English semicolon
        "，",         # Chinese comma
        ",",          # English comma
        " ",          # Space
        "",           # Character-level fallback
    ]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
        keep_separator: bool = True,
    ):
        """Initialize the chunker.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            separators: Custom separator hierarchy (uses defaults if None)
            keep_separator: Whether to keep the separator at the end of chunks
        """
        self.chunk_size = max(64, chunk_size)  # Minimum 64 chars
        self.chunk_overlap = min(chunk_overlap, chunk_size // 4)
        self.separators = separators or self.DEFAULT_SEPARATORS
        self.keep_separator = keep_separator

    def split_text(self, text: str) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: Input text to split

        Returns:
            List of Chunk objects with metadata
        """
        if not text or not text.strip():
            return []

        # Normalize whitespace but preserve structure
        text = self._normalize_text(text)

        # If text is small enough, return as single chunk
        if len(text) <= self.chunk_size:
            return [Chunk(content=text, index=0, start_char=0, end_char=len(text))]

        # Split recursively
        chunks = self._split_recursive(text, self.separators)

        # Add index and position metadata
        result = []
        current_pos = 0
        for i, chunk_content in enumerate(chunks):
            start = text.find(chunk_content, current_pos)
            if start == -1:
                start = current_pos
            end = start + len(chunk_content)
            current_pos = end

            result.append(Chunk(
                content=chunk_content,
                index=i,
                start_char=start,
                end_char=end,
            ))

        return result

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using the separator hierarchy."""
        if not separators:
            return self._split_by_characters(text)

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator:
            # Split by current separator
            if self.keep_separator:
                # Keep separator with preceding text
                splits = re.split(f"({re.escape(separator)})", text)
                parts = []
                for i in range(0, len(splits) - 1, 2):
                    if splits[i] or (i + 1 < len(splits) and splits[i + 1]):
                        parts.append(splits[i] + (splits[i + 1] if i + 1 < len(splits) else ""))
                if len(splits) % 2 == 1 and splits[-1]:
                    parts.append(splits[-1])
            else:
                parts = text.split(separator)
                parts = [p for p in parts if p]
        else:
            # Character-level split
            parts = list(text)

        # Merge parts into chunks of appropriate size
        chunks = self._merge_splits(parts, separator, remaining_separators)
        return chunks

    def _merge_splits(
        self,
        splits: list[str],
        separator: str,
        remaining_separators: list[str],
    ) -> list[str]:
        """Merge splits into chunks of target size."""
        chunks = []
        current_chunk: list[str] = []
        current_length = 0

        for split in splits:
            split_len = len(split)

            # If single split is too large, recursively split it
            if split_len > self.chunk_size:
                # First, save current chunk if not empty
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Recursively split this large piece
                sub_chunks = self._split_recursive(split, remaining_separators)
                chunks.extend(sub_chunks)
                continue

            # Check if adding this split would exceed chunk size
            new_length = current_length + split_len + (len(separator) if current_chunk else 0)

            if new_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(separator.join(current_chunk))

                # Start new chunk with overlap from previous
                overlap_text = self._get_overlap_text(current_chunk, separator)
                if overlap_text:
                    current_chunk = [overlap_text]
                    current_length = len(overlap_text)
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(split)
            current_length += split_len + (len(separator) if len(current_chunk) > 1 else 0)

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return chunks

    def _get_overlap_text(self, chunk_parts: list[str], separator: str) -> str:
        """Get overlap text from the end of current chunk."""
        if self.chunk_overlap == 0:
            return ""

        # Take last portion that fits within overlap
        overlap_parts: list[str] = []
        overlap_length = 0

        for part in reversed(chunk_parts):
            part_len = len(part) + (len(separator) if overlap_parts else 0)
            if overlap_length + part_len > self.chunk_overlap:
                break
            overlap_parts.insert(0, part)
            overlap_length += part_len

        return separator.join(overlap_parts) if overlap_parts else ""

    def _split_by_characters(self, text: str) -> list[str]:
        """Character-level fallback split."""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks

    def _normalize_text(self, text: str) -> str:
        """Normalize text while preserving structure."""
        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Replace multiple spaces with single space (but preserve indentation)
        text = re.sub(r"[^\S\n]{2,}", " ", text)
        # Remove trailing whitespace from lines
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[str]:
    """Convenience function to chunk text.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk strings
    """
    chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [c.content for c in chunker.split_text(text)]


def chunk_repository_readme(
    readme: str,
    name: str,
    description: str | None = None,
    chunk_size: int = 512,
) -> list[dict[str, Any]]:
    """Chunk a repository README for embedding.

    Args:
        readme: README content
        name: Repository full name (owner/repo)
        description: Repository description
        chunk_size: Target chunk size

    Returns:
        List of chunk dicts with content and metadata
    """
    if not readme or not readme.strip():
        return []

    chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=50)
    chunks = chunker.split_text(readme)

    result = []
    for chunk in chunks:
        # Build chunk with metadata
        chunk_content = chunk.content
        if chunk.index == 0 and description:
            # Prepend description to first chunk
            chunk_content = f"{description}\n\n{chunk_content}"

        result.append({
            "content": chunk_content,
            "metadata": {
                "repo_name": name,
                "chunk_index": chunk.index,
                "total_chunks": len(chunks),
                "is_first": chunk.index == 0,
                "is_last": chunk.index == len(chunks) - 1,
            },
        })

    logger.debug("Chunked %s: %d chars -> %d chunks", name, len(readme), len(result))
    return result
