"""In-memory runtime state object for sync/analysis progress."""


class SyncRuntimeState:
    def __init__(self):
        self._sync_status = {
            "is_syncing": False,
            "progress": 0,
            "total": 0,
            "current_repo": "",
        }

    def get_sync_status(self) -> dict:
        return {**self._sync_status}

    def start_sync(self, total: int = 0) -> None:
        self._sync_status["is_syncing"] = True
        self._sync_status["progress"] = 0
        self._sync_status["total"] = total
        self._sync_status["current_repo"] = ""

    def stop_sync(self) -> None:
        self._sync_status["is_syncing"] = False

    def set_total(self, total: int) -> None:
        self._sync_status["total"] = total

    def set_progress(self, progress: int) -> None:
        self._sync_status["progress"] = progress

    def set_current_repo(self, current_repo: str) -> None:
        self._sync_status["current_repo"] = current_repo
