"""Section and line-level noise filtering."""

from __future__ import annotations

import re

from services.readme_cleaning.config import ReadmeCleaningConfig
from services.readme_cleaning.models import ReadmeSection


def is_badge_like_line(line: str, config: ReadmeCleaningConfig) -> bool:
    low = line.lower()
    return any(marker in low for marker in config.noisy_line_patterns)


def filter_noisy_lines(text: str, config: ReadmeCleaningConfig) -> str:
    lines = text.splitlines()
    kept = [line for line in lines if not is_badge_like_line(line, config)]
    return "\n".join(kept).strip()


def is_toc_section(section: ReadmeSection, config: ReadmeCleaningConfig) -> bool:
    heading = section.heading.lower()
    if any(k in heading for k in config.toc_heading_keywords):
        return True
    lines = [line.strip() for line in section.body.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    anchor_lines = sum(
        1
        for line in lines
        if re.search(r"\[[^\]]+\]\(#", line.lower()) or re.search(r"^-+\s*\[[^\]]+\]\(#", line.lower())
    )
    return anchor_lines >= max(3, int(len(lines) * 0.6))


def is_pure_link_section(section: ReadmeSection) -> bool:
    lines = [line.strip() for line in section.body.splitlines() if line.strip()]
    if not lines:
        return False
    linkish = 0
    for line in lines:
        if re.search(r"^[-*]?\s*\[[^\]]+\]\([^)]+\)\s*$", line):
            linkish += 1
    return linkish >= max(3, int(len(lines) * 0.7))
