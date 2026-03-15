"""Code block selection policy."""

from __future__ import annotations

import re

from services.readme_cleaning.config import ReadmeCleaningConfig
from services.readme_cleaning.types import CleanupMode

FENCE_PATTERN = re.compile(r"```([^\n`]*)\n([\s\S]*?)\n```")


def _looks_like_log_block(code: str) -> bool:
    low = code.lower()
    log_tokens = ("traceback", "exception", "error:", "error ", "info:", "info ", "warn:", "warn ", "stack", " at ")
    hit = sum(1 for t in log_tokens if t in low)
    return hit >= 2 or "traceback" in low


def _looks_command_like(code: str) -> bool:
    low = code.lower()
    command_tokens = (
        "pip install",
        "npm ",
        "yarn ",
        "pnpm ",
        "docker ",
        "curl ",
        "http ",
        "python ",
        "uvicorn ",
        "pytest",
        "--help",
    )
    return any(token in low for token in command_tokens)


def _looks_like_large_source(lang: str, code: str) -> bool:
    source_langs = {
        "python",
        "typescript",
        "javascript",
        "java",
        "go",
        "rust",
        "c",
        "cpp",
        "csharp",
    }
    lines = [line for line in code.splitlines() if line.strip()]
    if lang not in source_langs:
        return False
    if len(lines) <= 30:
        return False
    symbol_rich = sum(1 for line in lines if any(sym in line for sym in ("{", "}", "=>", "def ", "class ")))
    return symbol_rich >= 8


def filter_code_blocks(text: str, mode: CleanupMode, config: ReadmeCleaningConfig) -> tuple[str, int, int]:
    kept_count = 0
    removed_count = 0
    if not text:
        return "", kept_count, removed_count

    def _replace(match: re.Match[str]) -> str:
        nonlocal kept_count, removed_count
        lang = (match.group(1) or "").strip().lower()
        code = (match.group(2) or "").strip("\n")
        lines = [line for line in code.splitlines() if line.strip()]
        line_count = len(lines)

        if not lines:
            removed_count += 1
            return "\n"

        is_log = _looks_like_log_block(code)
        is_command = _looks_command_like(code)
        is_large_source = _looks_like_large_source(lang, code)
        preferred_lang = lang in config.preferred_code_languages

        keep = False
        if mode == "analysis":
            keep = (line_count <= config.analysis_max_code_lines and (preferred_lang or is_command)) and not is_log
        else:
            if is_log or is_large_source:
                keep = False
            elif line_count <= config.embedding_max_code_lines and (preferred_lang or is_command or line_count <= 10):
                keep = True

        if keep:
            kept_count += 1
            return f"\n```{lang}\n{code}\n```\n"
        removed_count += 1
        return "\n"

    cleaned = FENCE_PATTERN.sub(_replace, text)
    return cleaned, kept_count, removed_count
