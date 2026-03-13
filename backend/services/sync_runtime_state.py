"""In-memory runtime state for sync/analysis progress."""

_sync_status = {
    "is_syncing": False,
    "progress": 0,
    "total": 0,
    "current_repo": "",
}


def get_sync_status() -> dict:
    return {**_sync_status}


def start_sync(total: int = 0) -> None:
    _sync_status["is_syncing"] = True
    _sync_status["progress"] = 0
    _sync_status["total"] = total
    _sync_status["current_repo"] = ""


def stop_sync() -> None:
    _sync_status["is_syncing"] = False


def set_total(total: int) -> None:
    _sync_status["total"] = total


def set_progress(progress: int) -> None:
    _sync_status["progress"] = progress


def set_current_repo(current_repo: str) -> None:
    _sync_status["current_repo"] = current_repo
