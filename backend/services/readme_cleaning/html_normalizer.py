"""Normalize embedded HTML fragments inside README markdown."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from services.readme_cleaning.text_normalizer import normalize_newlines


def normalize_html_fragments(raw_readme: str) -> str:
    """Normalize HTML tags while preserving textual meaning as much as possible."""
    text = normalize_newlines(raw_readme)
    if not text:
        return ""

    # Remove HTML comments first.
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)

    # Keep line-break intent.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Expand details/summary blocks as plain text while dropping tags.
    def _details_repl(match: re.Match[str]) -> str:
        soup = BeautifulSoup(match.group(0), "html.parser")
        for img in soup.find_all("img"):
            img.decompose()
        extracted = soup.get_text("\n", strip=True)
        return f"\n{extracted}\n" if extracted else "\n"

    text = re.sub(
        r"<details[\s\S]*?</details>",
        _details_repl,
        text,
        flags=re.IGNORECASE,
    )

    # Drop standalone img tags.
    text = re.sub(r"<img\b[^>]*>", " ", text, flags=re.IGNORECASE)
    return text


def html_token_to_text(html_snippet: str) -> str:
    if not html_snippet:
        return ""
    soup = BeautifulSoup(html_snippet, "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    return soup.get_text("\n", strip=True)
