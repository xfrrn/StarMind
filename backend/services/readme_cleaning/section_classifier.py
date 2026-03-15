"""Section scoring/classification logic for analysis and embedding paths."""

from __future__ import annotations

import re

from services.readme_cleaning.config import ReadmeCleaningConfig
from services.readme_cleaning.models import ReadmeSection
from services.readme_cleaning.noise_filter import is_pure_link_section, is_toc_section


def classify_and_score_section(section: ReadmeSection, config: ReadmeCleaningConfig) -> ReadmeSection:
    heading = (section.heading or "").lower()
    body = (section.body or "").lower()
    combined = f"{heading}\n{body}"
    score = 0.0
    flags = set(section.flags)

    if any(k in heading for k in config.priority_heading_keywords):
        score += 2.5
        flags.add("priority_heading")
    if any(k in heading for k in config.skip_heading_keywords):
        score -= 3.0
        flags.add("skip_heading")
    if any(k in combined for k in config.body_signal_keywords):
        score += 1.5
        flags.add("signal_body")
    if any(k in combined for k in config.bad_body_keywords):
        score -= 2.0
        flags.add("bad_body")

    if len(section.body.strip()) < config.min_section_chars:
        score -= 1.0
        flags.add("too_short")

    if is_toc_section(section, config):
        score -= 3.5
        flags.add("toc")

    if is_pure_link_section(section):
        score -= 2.0
        flags.add("pure_links")

    bullet_count = len(re.findall(r"^\s*[-*+]\s+", section.body, flags=re.MULTILINE))
    if bullet_count >= 3:
        score += 0.5
        flags.add("feature_list")

    section.score = score
    section.flags = flags
    return section
