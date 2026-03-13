"""Repositories router - list and detail endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from routers.schemas import RepoListResponse, RepoOut, StatsResponse
from services.repository_service import (
    get_repository_detail,
    get_repository_stats,
    list_repositories as list_repositories_service,
)

router = APIRouter(prefix="/api", tags=["repositories"])


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
    return await list_repositories_service(
        db,
        page=page,
        limit=limit,
        search=search,
        language=language,
        category=category,
        has_ui=has_ui,
        has_api=has_api,
        activity_level=activity_level,
    )


@router.get("/repositories/{repo_id}", response_model=RepoOut)
async def get_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single repository by ID."""
    repo = await get_repository_detail(db, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get statistics about synced repositories."""
    return await get_repository_stats(db)
