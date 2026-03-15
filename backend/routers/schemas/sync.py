from pydantic import BaseModel, Field


class SyncStatusResponse(BaseModel):
    is_syncing: bool
    progress: int
    total: int
    current_repo: str
    total_stars: int
    indexed_repos: int
    pending_repos: int
    last_sync: str | None
    logs: list[dict]
    process_breakdown: dict[str, int] = Field(default_factory=dict)
    analyze_breakdown: dict[str, int] = Field(default_factory=dict)
    embedding_breakdown: dict[str, int] = Field(default_factory=dict)


class SyncTriggerResponse(BaseModel):
    message: str
    status: str
