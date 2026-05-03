"""Repository service object: listing, detail and stats workflows."""

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
        user_id: int | None = None,
        page: int,
        limit: int,
        search: str | None,
        language: str | None,
        category: str | None,
        has_ui: bool | None,
        has_api: bool | None,
        activity_level: str | None,
        stars_min: int | None = None,
        stars_max: int | None = None,
        sort_by: str | None = None,
    ) -> dict:
        query = select(Repository)

        # Filter by user_id if provided
        if user_id is not None:
            query = query.where(Repository.user_id == user_id)

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
        if stars_min is not None:
            query = query.where(Repository.stars >= stars_min)
        if stars_max is not None:
            query = query.where(Repository.stars <= stars_max)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_field = Repository.stars
        sort_desc = True
        if sort_by == "name":
            sort_field = Repository.name
            sort_desc = False
        elif sort_by == "updated":
            sort_field = Repository.updated_at
            sort_desc = True
        elif sort_by == "stars_asc":
            sort_field = Repository.stars
            sort_desc = False
        elif sort_by == "stars":
            sort_field = Repository.stars
            sort_desc = True

        if sort_desc:
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())

        query = query.offset((page - 1) * limit).limit(limit)
        result = await db.execute(query)
        repos = result.scalars().all()

        return {
            "repositories": [to_repo_out(r) for r in repos],
            "total": total,
            "page": page,
            "limit": limit,
        }

    async def get_repository_by_id(self, db: AsyncSession, repo_id: int, user_id: int | None = None):
        query = select(Repository).where(Repository.id == repo_id)
        if user_id is not None:
            query = query.where(Repository.user_id == user_id)
        result = await db.execute(query)
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

    async def get_repository_detail(self, db: AsyncSession, repo_id: int, user_id: int | None = None):
        repo = await self.get_repository_by_id(db, repo_id, user_id)
        if not repo:
            return None
        await self.backfill_truncated_readme_if_needed(db, repo)
        return to_repo_out(repo)

    async def get_repository_stats(self, db: AsyncSession, user_id: int | None = None) -> dict:
        base_query = select(Repository)
        if user_id is not None:
            base_query = base_query.where(Repository.user_id == user_id)

        total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
        total = total_result.scalar() or 0

        lang_query = (
            select(Repository.language, func.count(Repository.id))
            .where(Repository.language != "")
        )
        if user_id is not None:
            lang_query = lang_query.where(Repository.user_id == user_id)
        lang_query = lang_query.group_by(Repository.language).order_by(func.count(Repository.id).desc())
        lang_result = await db.execute(lang_query)
        languages = {row[0]: row[1] for row in lang_result.all()}

        cat_query = (
            select(Repository.category, func.count(Repository.id))
            .where(Repository.category != "")
        )
        if user_id is not None:
            cat_query = cat_query.where(Repository.user_id == user_id)
        cat_query = cat_query.group_by(Repository.category).order_by(func.count(Repository.id).desc())
        cat_result = await db.execute(cat_query)
        categories = {row[0]: row[1] for row in cat_result.all()}

        return {"total": total, "languages": languages, "categories": categories}
