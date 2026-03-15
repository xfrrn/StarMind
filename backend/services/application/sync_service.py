"""Sync service object: sync orchestration, status and trigger helpers."""

import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.github import GitHubSyncer
from models.repository import Repository, SyncLog
from services.domain import ReadmeCleaner, StateTransitionService
from services.application.analysis_service import AnalysisService
from services.application.runtime import SyncRuntimeState
from utils.response_utils import to_sync_log_item
from utils.time_utils import format_last_sync_time, format_relative_time, parse_iso_to_naive_utc

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(
        self,
        settings: Settings,
        runtime_state: SyncRuntimeState,
        analysis_service: AnalysisService,
        readme_cleaner: ReadmeCleaner | None = None,
        state_transition_service: StateTransitionService | None = None,
    ):
        self.settings = settings
        self.runtime_state = runtime_state
        self.analysis_service = analysis_service
        self.readme_cleaner = readme_cleaner or ReadmeCleaner()
        self.state_transition_service = state_transition_service or StateTransitionService()

    async def run_sync(self, db: AsyncSession, github_token: str) -> SyncLog:
        if self.runtime_state.get_sync_status()["is_syncing"]:
            raise RuntimeError("A sync is already in progress")

        self.runtime_state.start_sync(total=0)

        log = SyncLog(status="success", started_at=datetime.utcnow(), details="")
        new_count = 0
        updated_count = 0
        run_id = f"sync-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"

        try:
            syncer = GitHubSyncer(github_token)

            last_sync = await db.execute(select(func.max(Repository.synced_at)))
            last_sync_time = last_sync.scalar()

            starred_repos = await syncer.fetch_starred_repos(
                since=last_sync_time,
                concurrency=self.settings.github_sync_page_concurrency,
            )
            self.runtime_state.set_total(len(starred_repos))

            if not starred_repos:
                log.details = "No new starred repositories found."
                log.finished_at = datetime.utcnow()
                db.add(log)
                await db.commit()
                return log

            repo_names = [repo["name"] for repo in starred_repos]
            readme_map = await syncer.fetch_readmes(
                repo_names,
                concurrency=self.settings.github_readme_concurrency,
            )

            for i, repo_data in enumerate(starred_repos):
                self.runtime_state.set_progress(i + 1)
                self.runtime_state.set_current_repo(repo_data["name"])

                existing = await db.execute(
                    select(Repository).where(Repository.github_id == repo_data["github_id"])
                )
                existing_repo = existing.scalar_one_or_none()

                readme = readme_map.get(repo_data["name"], "")
                readme_for_analysis = self.readme_cleaner.clean_for_analysis(readme, max_tokens=1200)
                readme_for_embedding = self.readme_cleaner.clean_for_embedding(
                    readme,
                    max_tokens=int(self.settings.embedding_readme_max_tokens),
                )
                updated_at = parse_iso_to_naive_utc(repo_data.get("updated_at"))
                starred_at = parse_iso_to_naive_utc(repo_data.get("starred_at"))

                if existing_repo:
                    self.state_transition_service.ensure_defaults(existing_repo)
                    existing_repo.name = repo_data["name"]
                    existing_repo.description = repo_data["description"]
                    existing_repo.stars = repo_data["stars"]
                    existing_repo.language = repo_data["language"]
                    existing_repo.topics = repo_data.get("topics", [])
                    existing_repo.url = repo_data["url"]
                    existing_repo.homepage = repo_data.get("homepage", "")
                    existing_repo.readme = readme
                    existing_repo.readme_for_analysis = readme_for_analysis
                    existing_repo.readme_for_embedding = readme_for_embedding
                    existing_repo.cleaning_version = "v1"
                    existing_repo.updated_at = updated_at
                    existing_repo.last_updated = format_relative_time(updated_at)
                    existing_repo.synced_at = datetime.utcnow()
                    existing_repo.category = "Pending Analysis"
                    existing_repo.tags = []
                    existing_repo.ai_summary = ""
                    existing_repo.has_ui = False
                    existing_repo.has_api = False
                    existing_repo.activity_level = "Medium"
                    existing_repo.embedding = None
                    existing_repo.repo_metadata_embedding = None
                    existing_repo.readme_embedding = None
                    existing_repo.metadata_hash = ""
                    existing_repo.readme_hash = ""
                    existing_repo.embedding_version = ""
                    existing_repo.embedding_updated_at = None
                    existing_repo.analyze_status = "pending"
                    existing_repo.embedding_status = "pending"
                    existing_repo.last_error_code = ""
                    existing_repo.last_error_detail = ""
                    try:
                        db.add(
                            self.state_transition_service.transition(
                                repo=existing_repo,
                                status_field="process",
                                to_status="cleaned",
                                stage="clean",
                                action="success",
                                run_id=run_id,
                            )
                        )
                    except ValueError:
                        logger.warning(
                            "Invalid process transition during sync update for repo=%s",
                            existing_repo.id,
                        )
                    updated_count += 1
                else:
                    new_repo = Repository(
                        github_id=repo_data["github_id"],
                        name=repo_data["name"],
                        description=repo_data["description"],
                        stars=repo_data["stars"],
                        language=repo_data["language"],
                        topics=repo_data.get("topics", []),
                        tags=[],
                        category="Pending Analysis",
                        ai_summary="",
                        has_ui=False,
                        has_api=False,
                        activity_level="Medium",
                        last_updated=format_relative_time(updated_at),
                        updated_at=updated_at,
                        readme=readme,
                        readme_for_analysis=readme_for_analysis,
                        readme_for_embedding=readme_for_embedding,
                        cleaning_version="v1",
                        process_status="cleaned",
                        analyze_status="pending",
                        embedding_status="pending",
                        last_run_id=run_id,
                        url=repo_data["url"],
                        homepage=repo_data.get("homepage", ""),
                        starred_at=starred_at,
                        synced_at=datetime.utcnow(),
                        embedding=None,
                    )
                    db.add(new_repo)
                    await db.flush()
                    db.add(
                        self.state_transition_service.transition(
                            repo=new_repo,
                            status_field="process",
                            to_status="cleaned",
                            stage="clean",
                            action="success",
                            run_id=run_id,
                        )
                    )
                    new_count += 1

                if (i + 1) % 100 == 0:
                    await db.commit()

            await db.commit()

            log.new_repos = new_count
            log.updated_repos = updated_count
            log.details = (
                f"Synced {new_count} new starred repositories. "
                f"Updated {updated_count} existing records. "
                f"GitHub page concurrency={max(1, self.settings.github_sync_page_concurrency)}, "
                f"README concurrency={max(1, self.settings.github_readme_concurrency)}."
            )
            log.finished_at = datetime.utcnow()

        except Exception as e:
            logger.error("Sync failed: %s", e, exc_info=True)
            log.status = "error"
            log.details = f"Sync failed: {str(e)}"
            log.finished_at = datetime.utcnow()

        finally:
            self.runtime_state.stop_sync()
            db.add(log)
            await db.commit()

        return log

    async def run_ai_analysis(self, db: AsyncSession) -> dict:
        return await self.analysis_service.run_pending_repository_analysis(db)

    async def get_sync_status_overview(self, db: AsyncSession) -> dict:
        status = self.runtime_state.get_sync_status()

        total_result = await db.execute(select(func.count(Repository.id)))
        total_stars = total_result.scalar() or 0

        indexed_result = await db.execute(
            select(func.count(Repository.id)).where(
                or_(
                    Repository.embedding_status == "success",
                    Repository.repo_metadata_embedding.isnot(None),
                    Repository.readme_embedding.isnot(None),
                    Repository.embedding.isnot(None),
                )
            )
        )
        indexed_repos = indexed_result.scalar() or 0

        pending_result = await db.execute(
            select(func.count(Repository.id)).where(
                or_(
                    Repository.process_status.in_(["cleaned", "failed"]),
                    Repository.analyze_status.in_(["pending", "failed", "running"]),
                    Repository.repo_metadata_embedding.is_(None),
                    Repository.readme_embedding.is_(None),
                    Repository.embedding_version != self.settings.embedding_version,
                )
            )
        )
        pending_repos = pending_result.scalar() or 0

        last_sync_result = await db.execute(
            select(SyncLog.finished_at)
            .where(SyncLog.status == "success")
            .order_by(SyncLog.finished_at.desc())
            .limit(1)
        )
        last_sync = format_last_sync_time(last_sync_result.scalar())

        logs_result = await db.execute(
            select(SyncLog).order_by(SyncLog.started_at.desc()).limit(10)
        )
        logs = logs_result.scalars().all()
        log_list = [to_sync_log_item(log.status, log.started_at, log.details or "") for log in logs]

        process_rows = await db.execute(
            select(Repository.process_status, func.count(Repository.id)).group_by(Repository.process_status)
        )
        analyze_rows = await db.execute(
            select(Repository.analyze_status, func.count(Repository.id)).group_by(Repository.analyze_status)
        )
        embedding_rows = await db.execute(
            select(Repository.embedding_status, func.count(Repository.id)).group_by(Repository.embedding_status)
        )
        process_breakdown = {
            (row[0] or "unknown"): row[1]
            for row in process_rows.all()
        }
        analyze_breakdown = {
            (row[0] or "unknown"): row[1]
            for row in analyze_rows.all()
        }
        embedding_breakdown = {
            (row[0] or "unknown"): row[1]
            for row in embedding_rows.all()
        }

        return {
            "is_syncing": status["is_syncing"],
            "progress": status["progress"],
            "total": status["total"],
            "current_repo": status["current_repo"],
            "total_stars": total_stars,
            "indexed_repos": indexed_repos,
            "pending_repos": pending_repos,
            "last_sync": last_sync,
            "logs": log_list,
            "process_breakdown": process_breakdown,
            "analyze_breakdown": analyze_breakdown,
            "embedding_breakdown": embedding_breakdown,
        }

    def validate_sync_trigger(self) -> dict | None:
        status = self.runtime_state.get_sync_status()
        if status["is_syncing"]:
            return {
                "message": "A sync or analysis is already in progress.",
                "status": "already_running",
            }

        if not self.settings.github_token:
            return {
                "message": "GitHub token not configured. Please set GITHUB_TOKEN in settings.",
                "status": "error",
            }

        return None

    def validate_analysis_trigger(self) -> dict | None:
        status = self.runtime_state.get_sync_status()
        if status["is_syncing"]:
            return {
                "message": "A sync or analysis is already in progress.",
                "status": "already_running",
            }

        if not self.settings.openai_api_key:
            return {
                "message": "OpenAI API key not configured. Please set OPENAI_API_KEY in settings.",
                "status": "error",
            }

        return None

    def get_configured_github_token(self) -> str:
        return self.settings.github_token
