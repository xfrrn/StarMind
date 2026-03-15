"""Backward-compatible import shim for ReadmeCleaner."""

from services.domain.readme_cleaner import CleaningResult, ReadmeCleaner

__all__ = ["ReadmeCleaner", "CleaningResult"]
