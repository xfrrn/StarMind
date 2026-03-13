from pydantic import BaseModel


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


class SyncTriggerResponse(BaseModel):
    message: str
    status: str
