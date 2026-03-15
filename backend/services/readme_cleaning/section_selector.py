"""Section selection policies."""

from __future__ import annotations

from services.readme_cleaning.config import ReadmeCleaningConfig
from services.readme_cleaning.models import ReadmeSection


def select_sections_for_analysis(
    sections: list[ReadmeSection],
    config: ReadmeCleaningConfig,
) -> tuple[list[ReadmeSection], list[ReadmeSection]]:
    if not sections:
        return [], []

    ranked = sorted(enumerate(sections), key=lambda item: item[1].score, reverse=True)
    selected_idx = {
        idx
        for idx, sec in ranked[: config.top_k_sections_analysis]
        if sec.score > -1.5 and "toc" not in sec.flags and "skip_heading" not in sec.flags
    }
    if not selected_idx:
        for idx, sec in enumerate(sections[:6]):
            if "toc" in sec.flags or "skip_heading" in sec.flags:
                continue
            selected_idx.add(idx)

    selected = [sec for idx, sec in enumerate(sections) if idx in selected_idx]
    removed = [sec for idx, sec in enumerate(sections) if idx not in selected_idx]
    return selected, removed


def select_sections_for_embedding(
    sections: list[ReadmeSection],
) -> tuple[list[ReadmeSection], list[ReadmeSection]]:
    selected: list[ReadmeSection] = []
    removed: list[ReadmeSection] = []
    for sec in sections:
        if "toc" in sec.flags or ("skip_heading" in sec.flags and sec.score < -1.5):
            removed.append(sec)
            continue
        selected.append(sec)
    return selected, removed
