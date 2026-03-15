"""Config and heuristics for README cleaning."""

from __future__ import annotations

from dataclasses import dataclass, field

from services.readme_cleaning.types import CleanupMode


@dataclass(frozen=True)
class ReadmeCleaningConfig:
    mode: CleanupMode
    top_k_sections_analysis: int = 8
    min_section_chars: int = 48
    skip_heading_keywords: tuple[str, ...] = field(default_factory=tuple)
    priority_heading_keywords: tuple[str, ...] = field(default_factory=tuple)
    body_signal_keywords: tuple[str, ...] = field(default_factory=tuple)
    bad_body_keywords: tuple[str, ...] = field(default_factory=tuple)
    toc_heading_keywords: tuple[str, ...] = field(default_factory=tuple)
    preferred_code_languages: tuple[str, ...] = field(default_factory=tuple)
    analysis_max_code_lines: int = 14
    embedding_max_code_lines: int = 44
    noisy_line_patterns: tuple[str, ...] = field(default_factory=tuple)


_COMMON_PRIORITY = (
    "overview",
    "introduction",
    "what is",
    "about",
    "feature",
    "usage",
    "quick start",
    "api",
    "sdk",
    "cli",
    "architecture",
    "concept",
    "core",
    "component",
    "概览",
    "介绍",
    "特性",
    "功能",
    "使用",
    "快速开始",
    "接口",
    "架构",
)

_COMMON_SKIP = (
    "license",
    "contributing",
    "acknowledg",
    "changelog",
    "release note",
    "roadmap",
    "sponsor",
    "donate",
    "citation",
    "致谢",
    "贡献",
    "许可证",
    "更新日志",
)

_COMMON_BODY_SIGNAL = (
    "usage",
    "example",
    "api",
    "sdk",
    "cli",
    "command",
    "config",
    "endpoint",
    "request",
    "response",
    "feature",
    "supports",
    "支持",
    "示例",
    "参数",
    "配置",
    "命令",
    "接口",
)


def get_mode_config(mode: CleanupMode) -> ReadmeCleaningConfig:
    if mode == "analysis":
        return ReadmeCleaningConfig(
            mode=mode,
            top_k_sections_analysis=7,
            min_section_chars=64,
            skip_heading_keywords=_COMMON_SKIP + ("installation", "install", "how to install"),
            priority_heading_keywords=_COMMON_PRIORITY,
            body_signal_keywords=_COMMON_BODY_SIGNAL,
            bad_body_keywords=("copyright", "all rights reserved"),
            toc_heading_keywords=("table of contents", "contents", "目录"),
            preferred_code_languages=("bash", "shell", "sh", "json", "yaml", "yml", "http"),
            analysis_max_code_lines=12,
            embedding_max_code_lines=44,
            noisy_line_patterns=("shields.io", "img.shields.io", "star history", "badge"),
        )
    return ReadmeCleaningConfig(
        mode=mode,
        top_k_sections_analysis=10,
        min_section_chars=24,
        skip_heading_keywords=_COMMON_SKIP,
        priority_heading_keywords=_COMMON_PRIORITY + ("install", "configuration"),
        body_signal_keywords=_COMMON_BODY_SIGNAL + ("install", "setup"),
        bad_body_keywords=("all rights reserved",),
        toc_heading_keywords=("table of contents", "contents", "目录"),
        preferred_code_languages=("bash", "shell", "sh", "json", "yaml", "yml", "http", "toml", "ini"),
        analysis_max_code_lines=12,
        embedding_max_code_lines=48,
        noisy_line_patterns=("shields.io", "img.shields.io", "star history", "badge"),
    )
