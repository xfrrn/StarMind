"""Dedup helpers for README sections."""

from __future__ import annotations

import re

from services.readme_cleaning.models import ReadmeSection


def _signature(section: ReadmeSection) -> str:
    heading = (section.heading or "").strip().lower()
    body = (section.body or "").strip().lower()
    normalized = re.sub(r"\s+", " ", body)
    if len(normalized) > 350:
        normalized = normalized[:350]
    return f"{heading}|{normalized}"


def deduplicate_sections(sections: list[ReadmeSection]) -> tuple[list[ReadmeSection], list[ReadmeSection]]:
    seen: set[str] = set()
    kept: list[ReadmeSection] = []
    removed: list[ReadmeSection] = []
    for section in sections:
        sign = _signature(section)
        if sign in seen:
            section.flags.add("duplicate")
            removed.append(section)
            continue
        seen.add(sign)
        kept.append(section)
    return kept, removed
