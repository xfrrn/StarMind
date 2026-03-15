"""Public cleaner entrypoint with compatibility methods."""

from __future__ import annotations

from services.readme_cleaning.models import CleaningResult
from services.readme_cleaning.pipeline import run_cleaning_pipeline


class ReadmeCleaner:
    """README cleaner with dual-path cleaning for analysis and embedding."""

    def clean(
        self,
        raw_readme: str,
        *,
        mode: str,
        max_tokens: int,
        debug: bool = False,
    ) -> str | CleaningResult:
        final_text, debug_info = run_cleaning_pipeline(
            raw_readme,
            mode=mode,  # type: ignore[arg-type]
            max_tokens=max_tokens,
        )
        if not debug:
            return final_text
        return CleaningResult(
            final_text=final_text,
            selected_sections=debug_info.selected_sections,
            skipped_sections=debug_info.removed_sections,
            section_scores=debug_info.section_scores,
            kept_code_blocks=debug_info.kept_code_blocks,
            removed_code_blocks=debug_info.removed_code_blocks,
        )

    def clean_for_analysis(
        self,
        raw_readme: str,
        max_tokens: int = 1200,
        debug: bool = False,
    ) -> str | CleaningResult:
        return self.clean(
            raw_readme,
            mode="analysis",
            max_tokens=max_tokens,
            debug=debug,
        )

    def clean_for_embedding(
        self,
        raw_readme: str,
        max_tokens: int = 1800,
        debug: bool = False,
    ) -> str | CleaningResult:
        return self.clean(
            raw_readme,
            mode="embedding",
            max_tokens=max_tokens,
            debug=debug,
        )
