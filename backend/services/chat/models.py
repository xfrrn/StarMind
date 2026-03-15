from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.chat.types import IntentType


@dataclass
class ChatTurn:
    role: str
    message: str


@dataclass
class ChatRequestModel:
    user_message: str
    session_id: str | None = None
    history: list[ChatTurn] = field(default_factory=list)


@dataclass
class IntentResult:
    intent_type: IntentType
    confidence: float
    needs_retrieval: bool
    reason: str | None = None


@dataclass
class RepoQuery:
    raw_query: str
    intent_type: IntentType
    repo_name: str | None = None
    owner: str | None = None
    language: str | None = None
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    scope: str | None = "starred"
    filters: dict[str, Any] = field(default_factory=dict)
    compare_targets: list[str] = field(default_factory=list)


@dataclass
class RetrievalPlan:
    use_exact_lookup: bool = False
    use_metadata_filter: bool = False
    use_keyword_search: bool = False
    use_vector_search: bool = False
    limit: int = 20


@dataclass
class RepoCandidate:
    repo_id: int
    github_id: int | None
    full_name: str
    name: str
    owner: str
    description: str | None
    language: str | None
    topics: list[str]
    stars: int
    tags: list[str] = field(default_factory=list)
    category: str = ""
    analysis_summary: str | None = None
    cleaned_readme_snippet: str | None = None
    has_ui: bool = False
    has_api: bool = False
    activity_level: str = "Medium"
    last_updated: str = ""
    url: str = ""
    score: float | None = None
    matched_by: list[str] = field(default_factory=list)


@dataclass
class RankedRepoCandidate(RepoCandidate):
    final_score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    why_relevant: str = ""


@dataclass
class RetrievalTelemetry:
    used_paths: list[str] = field(default_factory=list)
    retrieval_count: int = 0
    reranked_count: int = 0
    degraded: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class BuiltContext:
    intent_type: IntentType
    prompt_context: str
    repositories: list[RankedRepoCandidate]


@dataclass
class ChatResponsePayload:
    answer: str
    repositories: list[dict[str, Any]]
    intent: IntentType
    telemetry: RetrievalTelemetry
