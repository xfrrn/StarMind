"""Analysis service object: orchestrates AI analysis for pending repositories."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.analysis import RepositoryAnalyzer
from core.github.checkpoint import commit_when_reach_checkpoint
from core.retrieval import EmbeddingService
from models.repository import Repository, SyncLog
from services.readme_cleaner import ReadmeCleaner
from services.sync_runtime_state import SyncRuntimeState

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(
        self,
        settings: Settings,
        runtime_state: SyncRuntimeState,
        repository_analyzer: RepositoryAnalyzer,
        embedding_service: EmbeddingService,
        readme_cleaner: ReadmeCleaner | None = None,
    ):
        self.settings = settings
        self.runtime_state = runtime_state
        self.repository_analyzer = repository_analyzer
        self.embedding_service = embedding_service
        self.readme_cleaner = readme_cleaner or ReadmeCleaner()
        self.expected_embedding_dim = int(settings.embedding_dimension)

    async def run_pending_repository_analysis(self, db: AsyncSession) -> dict:
        if self.runtime_state.get_sync_status()["is_syncing"]:
            raise RuntimeError("A sync or analysis is already in progress")

        result = await db.execute(
            select(Repository).where(
                or_(
                    Repository.category == "Pending Analysis",
                    Repository.repo_metadata_embedding.is_(None),
                    Repository.readme_embedding.is_(None),
                    Repository.embedding_version != self.settings.embedding_version,
                )
            )
        )
        pending_repos = result.scalars().all()

        total_pending = len(pending_repos)
        if total_pending == 0:
            return {"message": "No repositories pending AI analysis", "processed": 0}

        self.runtime_state.start_sync(total=total_pending)

        processed_count = 0
        failed_count = 0
        analysis_log = SyncLog(status="success", started_at=datetime.utcnow(), details="")
        concurrency = max(1, self.settings.ai_analysis_concurrency)
        delay_seconds = max(0.0, self.settings.ai_analysis_request_delay_seconds)
        checkpoint_every = max(1, self.settings.ai_analysis_checkpoint_every)
        tasks: list[asyncio.Task] = []

        try:
            pending_inputs: list[dict[str, Any]] = []
            repos_by_id: dict[int, Repository] = {}
            for repo in pending_repos:
                repos_by_id[repo.id] = repo
                pending_inputs.append(
                    {
                        "id": repo.id,
                        "name": repo.name,
                        "description": repo.description,
                        "readme": repo.readme,
                        "readme_for_analysis": self.readme_cleaner.clean_for_analysis(
                            repo.readme or "",
                            max_tokens=1200,
                        ),
                        "readme_for_embedding": self.readme_cleaner.clean_for_embedding(
                            repo.readme or "",
                            max_tokens=int(self.settings.embedding_readme_max_tokens),
                        ),
                        "language": repo.language,
                        "topics": repo.topics,
                        "stars": repo.stars,
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else "",
                    }
                )

            semaphore = asyncio.Semaphore(concurrency)
            status_lock = asyncio.Lock()
            completed_count = 0

            async def analyze_one(repo_data: dict[str, Any]) -> dict[str, Any]:
                nonlocal completed_count
                async with semaphore:
                    async with status_lock:
                        self.runtime_state.set_current_repo(repo_data["name"])

                    try:
                        analysis = await self.repository_analyzer.analyze_repository(repo_data)
                        combined_data = {**repo_data, **analysis}
                        dual_embeddings = await self.embedding_service.generate_dual_repository_embeddings(
                            combined_data
                        )
                        return {
                            "id": repo_data["id"],
                            "ok": True,
                            "analysis": analysis,
                            "dual_embeddings": dual_embeddings,
                        }
                    except Exception as e:
                        logger.error("Failed AI analysis for %s: %s", repo_data["name"], e)
                        return {"id": repo_data["id"], "ok": False}
                    finally:
                        if delay_seconds > 0:
                            await asyncio.sleep(delay_seconds)
                        async with status_lock:
                            completed_count += 1
                            self.runtime_state.set_progress(completed_count)

            tasks = [asyncio.create_task(analyze_one(item)) for item in pending_inputs]
            completed_since_commit = 0

            for done in asyncio.as_completed(tasks):
                result_item = await done
                if not result_item["ok"]:
                    failed_count += 1
                    completed_since_commit += 1
                    completed_since_commit = await commit_when_reach_checkpoint(
                        db=db,
                        completed_since_commit=completed_since_commit,
                        checkpoint_every=checkpoint_every,
                    )
                    continue

                repo = repos_by_id.get(result_item["id"])
                if not repo:
                    failed_count += 1
                    completed_since_commit += 1
                    completed_since_commit = await commit_when_reach_checkpoint(
                        db=db,
                        completed_since_commit=completed_since_commit,
                        checkpoint_every=checkpoint_every,
                    )
                    continue

                analysis = result_item["analysis"]
                dual_embeddings = result_item["dual_embeddings"]
                metadata_embedding = dual_embeddings.get("repo_metadata_embedding")
                readme_embedding = dual_embeddings.get("readme_embedding")

                if metadata_embedding is not None and len(metadata_embedding) != self.expected_embedding_dim:
                    logger.error(
                        "Skip repository %s due to metadata embedding dimension mismatch (expected %s, got %s).",
                        repo.name,
                        self.expected_embedding_dim,
                        len(metadata_embedding),
                    )
                    failed_count += 1
                    completed_since_commit += 1
                    completed_since_commit = await commit_when_reach_checkpoint(
                        db=db,
                        completed_since_commit=completed_since_commit,
                        checkpoint_every=checkpoint_every,
                    )
                    continue

                if readme_embedding is not None and len(readme_embedding) != self.expected_embedding_dim:
                    logger.error(
                        "Skip repository %s due to readme embedding dimension mismatch (expected %s, got %s).",
                        repo.name,
                        self.expected_embedding_dim,
                        len(readme_embedding),
                    )
                    failed_count += 1
                    completed_since_commit += 1
                    completed_since_commit = await commit_when_reach_checkpoint(
                        db=db,
                        completed_since_commit=completed_since_commit,
                        checkpoint_every=checkpoint_every,
                    )
                    continue

                repo.tags = analysis.get("tags", [])
                repo.category = analysis.get("category", "Other")
                repo.ai_summary = analysis.get("ai_summary", "")
                repo.has_ui = analysis.get("has_ui", False)
                repo.has_api = analysis.get("has_api", False)
                repo.activity_level = analysis.get("activity_level", "Medium")
                repo.embedding = metadata_embedding
                repo.repo_metadata_embedding = metadata_embedding
                repo.readme_embedding = readme_embedding
                repo.metadata_hash = dual_embeddings.get("metadata_hash", "")
                repo.readme_hash = dual_embeddings.get("readme_hash", "")
                repo.embedding_version = self.settings.embedding_version
                repo.embedding_updated_at = datetime.utcnow()
                processed_count += 1
                completed_since_commit += 1

                completed_since_commit = await commit_when_reach_checkpoint(
                    db=db,
                    completed_since_commit=completed_since_commit,
                    checkpoint_every=checkpoint_every,
                )

            await db.commit()

            analysis_log.status = "warning" if failed_count > 0 else "success"
            analysis_log.details = (
                f"AI analysis completed. Processed {processed_count}/{total_pending}, "
                f"failed {failed_count}, concurrency {concurrency}, "
                f"checkpoint every {checkpoint_every}."
            )
            analysis_log.finished_at = datetime.utcnow()

        except Exception as e:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await db.rollback()
            logger.error("AI analysis batch failed: %s", e, exc_info=True)
            analysis_log.status = "error"
            analysis_log.details = f"AI analysis batch failed: {str(e)}"
            analysis_log.finished_at = datetime.utcnow()

        finally:
            self.runtime_state.stop_sync()
            try:
                db.add(analysis_log)
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error("Failed to persist analysis log: %s", e, exc_info=True)

        return {
            "message": f"Successfully analyzed {processed_count} out of {total_pending} pending repositories.",
            "processed": processed_count,
            "total_pending": total_pending,
            "failed": failed_count,
            "concurrency": concurrency,
            "checkpoint_every": checkpoint_every,
        }
