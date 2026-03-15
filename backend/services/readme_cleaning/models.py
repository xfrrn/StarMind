"""Datamodels used in README cleaning pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReadmeSection:
    heading: str
    level: int | None
    body: str
    text: str
    source_kind: str
    score: float = 0.0
    flags: set[str] = field(default_factory=set)


@dataclass
class ReadmeDocument:
    raw_text: str
    normalized_text: str | None = None
    sections: list[ReadmeSection] = field(default_factory=list)


@dataclass
class CleaningDebugInfo:
    selected_sections: list[str] = field(default_factory=list)
    removed_sections: list[str] = field(default_factory=list)
    section_scores: list[tuple[str, float]] = field(default_factory=list)
    kept_code_blocks: int = 0
    removed_code_blocks: int = 0


@dataclass
class CleaningResult:
    final_text: str
    selected_sections: list[str]
    skipped_sections: list[str]
    section_scores: list[tuple[str, float]]
    kept_code_blocks: int
    removed_code_blocks: int
