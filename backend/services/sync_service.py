"""Sync service — orchestrates the full GitHub → AI → DB sync pipeline."""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository, SyncLog
from services.github_service import GitHubService
from services import ai_service

logger = logging.getLogger(__name__)

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

        starred_repos = await github.fetch_starred_repos(since=last_sync_time)
        _sync_status["total"] = len(starred_repos)

        if not starred_repos:
            log.details = "No new starred repositories found."
            log.finished_at = datetime.utcnow()
            db.add(log)
            await db.commit()
            return log

        # 2) Process each repo
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

            # Fetch README
            readme = await github.fetch_readme(repo_data["name"])
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
            f"Updated {updated_count} existing records."
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

    try:
        for i, repo in enumerate(pending_repos):
            _sync_status["progress"] = i + 1
            _sync_status["current_repo"] = repo.name

            # Build data dict for AI service
            repo_data = {
                "name": repo.name,
                "description": repo.description,
                "readme": repo.readme,
                "language": repo.language,
                "topics": repo.topics,
            }

            try:
                # 1) Analyze repo (tags, category, summary, etc.)
                analysis = await ai_service.analyze_repository(repo_data)

                # 2) Generate embedding
                combined_data = {**repo_data, **analysis}
                embedding = await ai_service.generate_repo_embedding(combined_data)

                # 3) Update DB object
                repo.tags = analysis.get("tags", [])
                repo.category = analysis.get("category", "Other")
                repo.ai_summary = analysis.get("ai_summary", "")
                repo.has_ui = analysis.get("has_ui", False)
                repo.has_api = analysis.get("has_api", False)
                repo.activity_level = analysis.get("activity_level", "Medium")
                repo.embedding = embedding

                processed_count += 1

                # Commit every 5 repos
                if processed_count % 5 == 0:
                    await db.commit()

            except Exception as e:
                logger.error(f"Failed AI analysis for {repo.name}: {e}")
                # Continue with next so one bad repo doesn't stop the whole batch
                
            # Rate limiting sleep
            await asyncio.sleep(0.5)

        await db.commit()
    
    finally:
        _sync_status["is_syncing"] = False

    return {
        "message": f"Successfully analyzed {processed_count} out of {total_pending} pending repositories.",
        "processed": processed_count,
        "total_pending": total_pending
    }
