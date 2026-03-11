"""Repositories router — list and detail endpoints."""

from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.repository import Repository

router = APIRouter(prefix="/api", tags=["repositories"])


class RepoOut(BaseModel):
    id: str
    name: str
    description: str
    stars: int
    language: str
    tags: list[str]
    category: str
    aiReason: str | None = None
    hasUI: bool = False
    hasAPI: bool = False
    activityLevel: str = "Medium"
    lastUpdated: str = ""
    readme: str = ""
    url: str = ""

    class Config:
        from_attributes = True


class RepoListResponse(BaseModel):
    repositories: list[RepoOut]
    total: int
    page: int
    limit: int


class StatsResponse(BaseModel):
    total: int
    languages: dict[str, int]
    categories: dict[str, int]


@router.get("/repositories", response_model=RepoListResponse)
async def list_repositories(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    has_ui: Optional[bool] = Query(None),
    has_api: Optional[bool] = Query(None),
    activity_level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List repositories with filtering and pagination."""
    query = select(Repository)

    # Filters
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

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(Repository.stars.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    repos = result.scalars().all()

    return RepoListResponse(
        repositories=[
            RepoOut(
                id=str(r.id),
                name=r.name,
                description=r.description or "",
                stars=r.stars,
                language=r.language or "",
                tags=r.tags or [],
                category=r.category or "",
                aiReason=r.ai_summary or "",
                hasUI=r.has_ui,
                hasAPI=r.has_api,
                activityLevel=r.activity_level or "Medium",
                lastUpdated=r.last_updated or "",
                readme=r.readme or "",
                url=r.url or "",
            )
            for r in repos
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/repositories/{repo_id}", response_model=RepoOut)
async def get_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single repository by ID."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return RepoOut(
        id=str(repo.id),
        name=repo.name,
        description=repo.description or "",
        stars=repo.stars,
        language=repo.language or "",
        tags=repo.tags or [],
        category=repo.category or "",
        aiReason=repo.ai_summary or "",
        hasUI=repo.has_ui,
        hasAPI=repo.has_api,
        activityLevel=repo.activity_level or "Medium",
        lastUpdated=repo.last_updated or "",
        readme=repo.readme or "",
        url=repo.url or "",
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get statistics about synced repositories."""
    # Total count
    total_result = await db.execute(select(func.count(Repository.id)))
    total = total_result.scalar() or 0

    # Language distribution
    lang_result = await db.execute(
        select(Repository.language, func.count(Repository.id))
        .where(Repository.language != "")
        .group_by(Repository.language)
        .order_by(func.count(Repository.id).desc())
    )
    languages = {row[0]: row[1] for row in lang_result.all()}

    # Category distribution
    cat_result = await db.execute(
        select(Repository.category, func.count(Repository.id))
        .where(Repository.category != "")
        .group_by(Repository.category)
        .order_by(func.count(Repository.id).desc())
    )
    categories = {row[0]: row[1] for row in cat_result.all()}

    return StatsResponse(total=total, languages=languages, categories=categories)
