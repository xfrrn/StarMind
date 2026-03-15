"""Repository service object: listing, detail and stats workflows."""

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.github import GitHubSyncer
from models.repository import Repository
from utils.response_utils import to_repo_out


class RepositoryService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def list_repositories(
        self,
        db: AsyncSession,
        *,
        page: int,
        limit: int,
        search: Optional[str],
        language: Optional[str],
        category: Optional[str],
        has_ui: Optional[bool],
        has_api: Optional[bool],
        activity_level: Optional[str],
    ) -> dict:
        query = select(Repository)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Repository.name.ilike(search_pattern),
                    Repository.description.ilike(search_pattern),
                    Repository.ai_summary.ilike(search_pattern),
                )
            )
        if language:
            query = query.where(Repository.language == language)
        if category:
            query = query.where(Repository.category == category)
        if has_ui is not None:
            query = query.where(Repository.has_ui == has_ui)
        if has_api is not None:
            query = query.where(Repository.has_api == has_api)
        if activity_level:
            query = query.where(Repository.activity_level == activity_level)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Repository.stars.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        result = await db.execute(query)
        repos = result.scalars().all()

        return {
            "repositories": [to_repo_out(r) for r in repos],
            "total": total,
            "page": page,
            "limit": limit,
        }

    async def get_repository_by_id(self, db: AsyncSession, repo_id: int):
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        return result.scalar_one_or_none()

    async def backfill_truncated_readme_if_needed(self, db: AsyncSession, repo: Repository) -> None:
        if not repo.readme or not repo.readme.endswith("\n\n...(truncated)"):
            return

        if not self.settings.github_token:
            return

        syncer = GitHubSyncer(self.settings.github_token)
        fresh_readme = await syncer.fetch_readme(repo.name)
        if fresh_readme:
            repo.readme = fresh_readme
            await db.commit()

    async def get_repository_detail(self, db: AsyncSession, repo_id: int):
        repo = await self.get_repository_by_id(db, repo_id)
        if not repo:
            return None
        await self.backfill_truncated_readme_if_needed(db, repo)
        return to_repo_out(repo)

    async def get_repository_stats(self, db: AsyncSession) -> dict:
        total_result = await db.execute(select(func.count(Repository.id)))
        total = total_result.scalar() or 0

        lang_result = await db.execute(
            select(Repository.language, func.count(Repository.id))
            .where(Repository.language != "")
            .group_by(Repository.language)
            .order_by(func.count(Repository.id).desc())
        )
        languages = {row[0]: row[1] for row in lang_result.all()}

        cat_result = await db.execute(
            select(Repository.category, func.count(Repository.id))
            .where(Repository.category != "")
            .group_by(Repository.category)
            .order_by(func.count(Repository.id).desc())
        )
        categories = {row[0]: row[1] for row in cat_result.all()}

        return {"total": total, "languages": languages, "categories": categories}
