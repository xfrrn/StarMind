"""README cleaning service.

This module provides two different cleaning strategies:
- clean_for_analysis: optimized for LLM repository analysis.
- clean_for_embedding: optimized for semantic retrieval embedding.
"""

from __future__ import annotations

import re

from utils.text import truncate_by_tokens


class ReadmeCleaner:
    """Dual-path README cleaner used by analysis and embedding pipelines."""

    _SKIP_SECTION_KEYWORDS = (
        "installation",
        "install",
        "contributing",
        "license",
        "acknowledgement",
        "acknowledgment",
        "changelog",
        "release notes",
        "roadmap",
        "faq",
        "credits",
        "donate",
        "sponsor",
    )

    _PRIORITY_SECTION_KEYWORDS = (
        "overview",
        "introduction",
        "what is",
        "about",
        "feature",
        "usage",
        "quick start",
        "api",
        "sdk",
        "cli",
        "ui",
    )

    def clean_for_analysis(self, raw_readme: str, max_tokens: int = 1200) -> str:
        """Return concise, high-signal text for LLM analysis.

        TODO:
        - Add language-aware heading classification.
        - Add optional keyword boosting based on repository metadata.
        """
        text = self._base_cleanup(raw_readme, keep_short_code=False)
        if not text:
            return ""

        sections = self._split_sections(text)
        if not sections:
            return truncate_by_tokens(text, max_tokens)

        selected: list[str] = []
        for heading, body in sections:
            heading_lower = heading.lower()
            if any(key in heading_lower for key in self._SKIP_SECTION_KEYWORDS):
                continue
            if any(key in heading_lower for key in self._PRIORITY_SECTION_KEYWORDS):
                selected.append(f"{heading}\n{body}".strip())

        if not selected:
            # Fallback: keep first useful sections except explicitly noisy ones.
            for heading, body in sections[:6]:
                heading_lower = heading.lower()
                if any(key in heading_lower for key in self._SKIP_SECTION_KEYWORDS):
                    continue
                selected.append(f"{heading}\n{body}".strip())

        merged = "\n\n".join(part for part in selected if part).strip()
        return truncate_by_tokens(merged or text, max_tokens)

    def clean_for_embedding(self, raw_readme: str, max_tokens: int = 1800) -> str:
        """Return retrieval-oriented text for embedding.

        Keeps technical keywords, feature lists, usage/API/CLI information,
        and short code snippets.

        TODO:
        - Add structured extraction for commands/options/API routes.
        - Add optional deduplication across repeated README sections.
        """
        text = self._base_cleanup(raw_readme, keep_short_code=True)
        if not text:
            return ""

        lines = text.splitlines()
        kept: list[str] = []
        for line in lines:
            low = line.lower()
            if self._is_badge_line(low):
                continue
            if self._is_noisy_line(low):
                continue
            kept.append(line)

        merged = "\n".join(kept).strip()
        merged = re.sub(r"\n{3,}", "\n\n", merged)
        return truncate_by_tokens(merged, max_tokens)

    def _base_cleanup(self, raw_readme: str, *, keep_short_code: bool) -> str:
        text = raw_readme or ""
        if not text:
            return ""

        text = text.replace("\r\n", "\n")
        text = re.sub(r"<!--[\s\S]*?-->", " ", text)
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
        text = re.sub(r"<img[^>]*>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)

        text = self._handle_code_fences(text, keep_short_code=keep_short_code)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"https?://\S+", " ", text)

        normalized_lines: list[str] = []
        for line in text.splitlines():
            if self._is_badge_line(line.lower()):
                continue
            normalized_lines.append(line.rstrip())

        text = "\n".join(normalized_lines)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    @staticmethod
    def _handle_code_fences(text: str, *, keep_short_code: bool) -> str:
        fence_pattern = re.compile(r"```[\s\S]*?```")

        def _replace(match: re.Match[str]) -> str:
            content = match.group(0)
            if not keep_short_code:
                return " "

            code_body = re.sub(r"^```[\w+-]*\n?", "", content)
            code_body = re.sub(r"\n?```$", "", code_body)
            if code_body.count("\n") > 18:
                return " "
            return f"\n{content.strip()}\n"

        return fence_pattern.sub(_replace, text)

    @staticmethod
    def _split_sections(text: str) -> list[tuple[str, str]]:
        lines = text.splitlines()
        sections: list[tuple[str, list[str]]] = []
        current_heading = "Overview"
        current_body: list[str] = []

        for line in lines:
            heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
            if heading_match:
                sections.append((current_heading, current_body))
                current_heading = heading_match.group(1).strip()
                current_body = []
                continue
            current_body.append(line)

        sections.append((current_heading, current_body))
        return [
            (heading, "\n".join(body).strip())
            for heading, body in sections
            if heading or any(item.strip() for item in body)
        ]

    @staticmethod
    def _is_badge_line(line: str) -> bool:
        markers = ("shields.io", "badge", "img.shields", "![", "<img", "travis-ci", "github/actions")
        return any(marker in line for marker in markers)

    @staticmethod
    def _is_noisy_line(line: str) -> bool:
        return bool(
            re.search(
                r"\b(contributing|license|copyright|acknowledg(e)?ment|sponsor|donate)\b",
                line,
            )
        )
