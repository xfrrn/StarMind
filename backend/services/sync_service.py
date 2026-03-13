"""Sync service — orchestrates the full GitHub → AI → DB sync pipeline."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.repository import Repository, SyncLog
from services.github_service import GitHubService
from services import ai_service

logger = logging.getLogger(__name__)
settings = get_settings()

# 全局同步状态
_sync_status = {
    "is_syncing": False,
    "progress": 0,
    "total": 0,
    "current_repo": "",
}


def get_sync_status() -> dict:
    return {**_sync_status}


def _relative_time(dt: datetime | None) -> str:
    """Convert a datetime to a human-readable relative time string."""
    if not dt:
        return "Unknown"
    
    # dt might be offset-aware (e.g. from GitHub API) or offset-naive (e.g. from DB)
    if dt.tzinfo:
        from datetime import timezone
        now = datetime.now(timezone.utc)
    else:
        now = datetime.utcnow()
        
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds} seconds ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} mins ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hours ago"
    days = hours // 24
    if days < 30:
        return f"{days} days ago"
    return dt.strftime("%Y-%m-%d")


async def run_sync(db: AsyncSession, github_token: str) -> SyncLog:
    """Execute a full sync: GitHub → AI analysis → Database."""
    global _sync_status

    if _sync_status["is_syncing"]:
        raise RuntimeError("A sync is already in progress")

    _sync_status = {
        "is_syncing": True,
        "progress": 0,
        "total": 0,
        "current_repo": "",
    }

    log = SyncLog(status="success", started_at=datetime.utcnow(), details="")
    new_count = 0
    updated_count = 0

    try:
        # 1) Fetch starred repos from GitHub
        github = GitHubService(github_token)

        # 获取最新同步时间用于增量同步
        last_sync = await db.execute(
            select(func.max(Repository.synced_at))
        )
        last_sync_time = last_sync.scalar()

        starred_repos = await github.fetch_starred_repos(
            since=last_sync_time,
            concurrency=settings.github_sync_page_concurrency,
        )
        _sync_status["total"] = len(starred_repos)

        if not starred_repos:
            log.details = "No new starred repositories found."
            log.finished_at = datetime.utcnow()
            db.add(log)
            await db.commit()
            return log

        # 2) Fetch README in parallel first (network-bound)
        repo_names = [repo["name"] for repo in starred_repos]
        readme_map = await github.fetch_readmes(
            repo_names, concurrency=settings.github_readme_concurrency
        )

        # 3) Upsert each repo into DB (DB-bound, single session for safety)
        for i, repo_data in enumerate(starred_repos):
            _sync_status["progress"] = i + 1
            _sync_status["current_repo"] = repo_data["name"]

            # Check if repo already exists
            existing = await db.execute(
                select(Repository).where(
                    Repository.github_id == repo_data["github_id"]
                )
            )
            existing_repo = existing.scalar_one_or_none()

            readme = readme_map.get(repo_data["name"], "")
            repo_data["readme"] = readme

            # Parse updated_at
            updated_at = None
            if repo_data.get("updated_at"):
                try:
                    # Parse and convert to offset-naive UTC to match DB schema
                    dt = datetime.fromisoformat(repo_data["updated_at"].replace("Z", "+00:00"))
                    updated_at = dt.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    pass

            # Parse starred_at
            starred_at = None
            if repo_data.get("starred_at"):
                try:
                    dt = datetime.fromisoformat(repo_data["starred_at"].replace("Z", "+00:00"))
                    starred_at = dt.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    pass

            if existing_repo:
                # Update existing
                existing_repo.name = repo_data["name"]
                existing_repo.description = repo_data["description"]
                existing_repo.stars = repo_data["stars"]
                existing_repo.language = repo_data["language"]
                existing_repo.topics = repo_data.get("topics", [])
                existing_repo.url = repo_data["url"]
                existing_repo.homepage = repo_data.get("homepage", "")
                existing_repo.readme = readme
                existing_repo.updated_at = updated_at
                existing_repo.last_updated = _relative_time(updated_at)
                existing_repo.synced_at = datetime.utcnow()
                updated_count += 1
            else:
                # Insert new (without AI data initially)
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
                    last_updated=_relative_time(updated_at),
                    updated_at=updated_at,
                    readme=readme,
                    url=repo_data["url"],
                    homepage=repo_data.get("homepage", ""),
                    starred_at=starred_at,
                    synced_at=datetime.utcnow(),
                    embedding=None,
                )
                db.add(new_repo)
                new_count += 1

            # 每 100 个仓库 commit 一次避免长事务
            if (i + 1) % 100 == 0:
                await db.commit()

        await db.commit()

        log.new_repos = new_count
        log.updated_repos = updated_count
        log.details = (
            f"Synced {new_count} new starred repositories. "
            f"Updated {updated_count} existing records. "
            f"GitHub page concurrency={max(1, settings.github_sync_page_concurrency)}, "
            f"README concurrency={max(1, settings.github_readme_concurrency)}."
        )
        log.finished_at = datetime.utcnow()

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        log.status = "error"
        log.details = f"Sync failed: {str(e)}"
        log.finished_at = datetime.utcnow()

    finally:
        _sync_status["is_syncing"] = False
        db.add(log)
        await db.commit()

    return log


async def run_ai_analysis(db: AsyncSession) -> dict:
    """Run AI analysis only on repositories that need it (Pending Analysis)."""
    global _sync_status

    if _sync_status["is_syncing"]:
        raise RuntimeError("A sync or analysis is already in progress")

    # Count how many need analysis
    result = await db.execute(
        select(Repository).where(Repository.category == "Pending Analysis")
    )
    pending_repos = result.scalars().all()
    
    total_pending = len(pending_repos)
    if total_pending == 0:
        return {"message": "No repositories pending AI analysis", "processed": 0}

    _sync_status = {
        "is_syncing": True,
        "progress": 0,
        "total": total_pending,
        "current_repo": "",
    }

    processed_count = 0
    failed_count = 0
    analysis_log = SyncLog(
        status="success",
        started_at=datetime.utcnow(),
        details="",
    )
    concurrency = max(1, settings.ai_analysis_concurrency)
    delay_seconds = max(0.0, settings.ai_analysis_request_delay_seconds)

    try:
        # 1) Prepare serializable input from ORM objects
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
                    "language": repo.language,
                    "topics": repo.topics,
                    "stars": repo.stars,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else "",
                }
            )

        # 2) Run AI analysis + embedding in concurrent workers (network-bound)
        semaphore = asyncio.Semaphore(concurrency)
        status_lock = asyncio.Lock()
        completed_count = 0

        async def analyze_one(repo_data: dict[str, Any]) -> dict[str, Any]:
            nonlocal completed_count
            async with semaphore:
                async with status_lock:
                    _sync_status["current_repo"] = repo_data["name"]

                try:
                    analysis = await ai_service.analyze_repository(repo_data)
                    combined_data = {**repo_data, **analysis}
                    embedding = await ai_service.generate_repo_embedding(combined_data)
                    return {
                        "id": repo_data["id"],
                        "ok": True,
                        "analysis": analysis,
                        "embedding": embedding,
                    }
                except Exception as e:
                    logger.error(f"Failed AI analysis for {repo_data['name']}: {e}")
                    return {"id": repo_data["id"], "ok": False}
                finally:
                    if delay_seconds > 0:
                        await asyncio.sleep(delay_seconds)
                    async with status_lock:
                        completed_count += 1
                        _sync_status["progress"] = completed_count

        results = await asyncio.gather(*(analyze_one(item) for item in pending_inputs))

        # 3) Apply results to DB in current session (DB-bound, single session)
        for result_item in results:
            if not result_item["ok"]:
                failed_count += 1
                continue

            repo = repos_by_id.get(result_item["id"])
            if not repo:
                failed_count += 1
                continue

            analysis = result_item["analysis"]
            repo.tags = analysis.get("tags", [])
            repo.category = analysis.get("category", "Other")
            repo.ai_summary = analysis.get("ai_summary", "")
            repo.has_ui = analysis.get("has_ui", False)
            repo.has_api = analysis.get("has_api", False)
            repo.activity_level = analysis.get("activity_level", "Medium")
            repo.embedding = result_item["embedding"]
            processed_count += 1

        await db.commit()
        analysis_log.status = "warning" if failed_count > 0 else "success"
        analysis_log.details = (
            f"AI analysis completed. Processed {processed_count}/{total_pending}, "
            f"failed {failed_count}, concurrency {concurrency}."
        )
        analysis_log.finished_at = datetime.utcnow()
    except Exception as e:
        logger.error(f"AI analysis batch failed: {e}", exc_info=True)
        analysis_log.status = "error"
        analysis_log.details = f"AI analysis batch failed: {str(e)}"
        analysis_log.finished_at = datetime.utcnow()
    
    finally:
        _sync_status["is_syncing"] = False
        db.add(analysis_log)
        await db.commit()

    return {
        "message": f"Successfully analyzed {processed_count} out of {total_pending} pending repositories.",
        "processed": processed_count,
        "total_pending": total_pending,
        "failed": failed_count,
        "concurrency": concurrency,
    }
