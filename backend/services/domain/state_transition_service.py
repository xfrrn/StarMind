"""State machine service for repository processing lifecycle."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from models.repository import RepoProcessEvent, Repository

logger = logging.getLogger(__name__)


PROCESS_TRANSITIONS: dict[str, set[str]] = {
    "fetched": {"cleaned", "failed"},
    "cleaned": {"analyzed", "failed"},
    "analyzed": {"embedded", "failed"},
    "embedded": {"completed", "failed"},
    "completed": {"cleaned", "analyzed", "embedded", "failed"},
    "failed": {"cleaned", "fetched"},
}

ANALYZE_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running"},
    "running": {"success", "failed"},
    "success": {"running"},
    "failed": {"running"},
}

EMBEDDING_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running"},
    "running": {"success", "failed"},
    "success": {"running"},
    "failed": {"running"},
}


class StateTransitionService:
    """Centralized transition validator + event writer."""

    def _normalize_current(self, status_field: str, value: str | None) -> str:
        current = (value or "").strip().lower()
        if current:
            return current
        if status_field == "process":
            return "fetched"
        return "pending"

    @staticmethod
    def _set_field(repo: Repository, status_field: str, status_value: str) -> None:
        if status_field == "process":
            repo.process_status = status_value
            return
        if status_field == "analyze":
            repo.analyze_status = status_value
            return
        if status_field == "embedding":
            repo.embedding_status = status_value
            return
        raise ValueError(f"Unknown status field: {status_field}")

    @staticmethod
    def _get_field(repo: Repository, status_field: str) -> str | None:
        if status_field == "process":
            return repo.process_status
        if status_field == "analyze":
            return repo.analyze_status
        if status_field == "embedding":
            return repo.embedding_status
        raise ValueError(f"Unknown status field: {status_field}")

    def _transition_rules(self, status_field: str) -> dict[str, set[str]]:
        if status_field == "process":
            return PROCESS_TRANSITIONS
        if status_field == "analyze":
            return ANALYZE_TRANSITIONS
        if status_field == "embedding":
            return EMBEDDING_TRANSITIONS
        raise ValueError(f"Unknown status field: {status_field}")

    def ensure_defaults(self, repo: Repository) -> None:
        if not repo.process_status:
            repo.process_status = "fetched"
        if not repo.analyze_status:
            repo.analyze_status = "pending"
        if not repo.embedding_status:
            repo.embedding_status = "pending"

    def transition(
        self,
        *,
        repo: Repository,
        status_field: str,
        to_status: str,
        stage: str,
        action: str,
        run_id: str = "",
        reason: str = "",
        error_code: str = "",
        error_detail: str = "",
        attempt: int = 1,
    ) -> RepoProcessEvent:
        self.ensure_defaults(repo)
        to_status = to_status.strip().lower()
        from_status = self._normalize_current(status_field, self._get_field(repo, status_field))
        rules = self._transition_rules(status_field)
        allowed = rules.get(from_status, set())

        if to_status != from_status and to_status not in allowed:
            raise ValueError(
                f"Invalid {status_field} transition for repo={repo.id}: {from_status} -> {to_status}"
            )

        self._set_field(repo, status_field, to_status)
        if run_id:
            repo.last_run_id = run_id
        if error_code:
            repo.last_error_code = error_code
        if error_detail:
            repo.last_error_detail = error_detail

        return RepoProcessEvent(
            repo_id=repo.id,
            run_id=run_id,
            stage=stage,
            action=action,
            status_field=status_field,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            error_code=error_code,
            error_detail=error_detail,
            attempt=attempt,
        )

    def transition_many(
        self,
        *,
        repos: Iterable[Repository],
        status_field: str,
        to_status: str,
        stage: str,
        action: str,
        run_id: str = "",
    ) -> list[RepoProcessEvent]:
        events: list[RepoProcessEvent] = []
        for repo in repos:
            try:
                events.append(
                    self.transition(
                        repo=repo,
                        status_field=status_field,
                        to_status=to_status,
                        stage=stage,
                        action=action,
                        run_id=run_id,
                    )
                )
            except ValueError as e:
                logger.warning("Skipping invalid transition: %s", e)
        return events
