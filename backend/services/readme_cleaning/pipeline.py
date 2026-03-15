"""README cleaning pipeline orchestration."""

from __future__ import annotations

from services.readme_cleaning.code_handler import filter_code_blocks
from services.readme_cleaning.config import get_mode_config
from services.readme_cleaning.dedup import deduplicate_sections
from services.readme_cleaning.html_normalizer import normalize_html_fragments
from services.readme_cleaning.markdown_parser import parse_readme_sections
from services.readme_cleaning.models import CleaningDebugInfo, ReadmeDocument, ReadmeSection
from services.readme_cleaning.noise_filter import filter_noisy_lines
from services.readme_cleaning.section_classifier import classify_and_score_section
from services.readme_cleaning.section_selector import (
    select_sections_for_analysis,
    select_sections_for_embedding,
)
from services.readme_cleaning.text_normalizer import squeeze_blank_lines
from services.readme_cleaning.truncation import apply_token_limit
from services.readme_cleaning.types import CleanupMode


def _join_sections(sections: list[ReadmeSection]) -> str:
    parts: list[str] = []
    for sec in sections:
        heading = sec.heading.strip() if sec.heading else ""
        body = sec.body.strip()
        if heading:
            parts.append(heading)
        if body:
            parts.append(body)
    return "\n\n".join(part for part in parts if part).strip()


def run_cleaning_pipeline(
    raw_readme: str,
    *,
    mode: CleanupMode,
    max_tokens: int,
) -> tuple[str, CleaningDebugInfo]:
    config = get_mode_config(mode)
    debug = CleaningDebugInfo()

    doc = ReadmeDocument(raw_text=raw_readme or "")
    normalized = normalize_html_fragments(doc.raw_text)
    normalized = filter_noisy_lines(normalized, config)
    doc.normalized_text = normalized
    sections = parse_readme_sections(normalized)

    classified = [classify_and_score_section(section, config) for section in sections]
    debug.section_scores = [(section.heading, section.score) for section in classified]

    deduped, removed_duplicates = deduplicate_sections(classified)
    for item in removed_duplicates:
        item.flags.add("removed_duplicate")

    if mode == "analysis":
        selected, removed = select_sections_for_analysis(deduped, config)
    else:
        selected, removed = select_sections_for_embedding(deduped)

    removed.extend(removed_duplicates)
    debug.selected_sections = [sec.heading for sec in selected]
    debug.removed_sections = [sec.heading for sec in removed]

    text = _join_sections(selected)
    text, kept_code, removed_code = filter_code_blocks(text, mode, config)
    text = squeeze_blank_lines(text)
    text = apply_token_limit(text, max_tokens)
    debug.kept_code_blocks = kept_code
    debug.removed_code_blocks = removed_code
    return text, debug
