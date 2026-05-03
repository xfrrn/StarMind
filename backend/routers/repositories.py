"""Repositories router - list and detail endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.repo_note import RepoNote
from models.user import User
from routers.deps import get_current_user
from routers.schemas import RepoListResponse, RepoOut, StatsResponse
from services.service_registry import get_repository_service

router = APIRouter(prefix="/api", tags=["repositories"])


class NoteUpdate(BaseModel):
    note: str


class NoteResponse(BaseModel):
    repo_id: int
    note: str


class NoteOut(BaseModel):
    note: str


@router.get("/repositories", response_model=RepoListResponse)
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    has_ui: Optional[bool] = Query(None),
    has_api: Optional[bool] = Query(None),
    activity_level: Optional[str] = Query(None),
    stars_min: Optional[int] = Query(None, ge=0, description="Minimum stars count"),
    stars_max: Optional[int] = Query(None, ge=0, description="Maximum stars count"),
    sort_by: Optional[str] = Query(
        None,
        description="Sort field: 'stars', 'stars_asc', 'name', 'updated'",
        pattern="^(stars|stars_asc|name|updated)$",
    ),
):
    """List repositories with filtering and pagination."""
    service = get_repository_service()
    return await service.list_repositories(
        db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        search=search,
        language=language,
        category=category,
        has_ui=has_ui,
        has_api=has_api,
        activity_level=activity_level,
        stars_min=stars_min,
        stars_max=stars_max,
        sort_by=sort_by,
    )


@router.get("/repositories/{repo_id}", response_model=RepoOut)
async def get_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single repository by ID."""
    service = get_repository_service()
    repo = await service.get_repository_detail(db, repo_id, user_id=current_user.id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics about synced repositories."""
    service = get_repository_service()
    return await service.get_repository_stats(db, user_id=current_user.id)


@router.get("/repositories/{repo_id}/note", response_model=NoteOut)
async def get_repo_note(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get personal note for a repository."""
    result = await db.execute(
        select(RepoNote).where(
            RepoNote.repo_id == repo_id,
            RepoNote.user_id == current_user.id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return NoteOut(note="")
    return NoteOut(note=note.note)


@router.put("/repositories/{repo_id}/note", response_model=NoteOut)
async def update_repo_note(
    repo_id: int,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update personal note for a repository."""
    result = await db.execute(
        select(RepoNote).where(
            RepoNote.repo_id == repo_id,
            RepoNote.user_id == current_user.id,
        )
    )
    note = result.scalar_one_or_none()

    if note:
        note.note = data.note
    else:
        note = RepoNote(repo_id=repo_id, user_id=current_user.id, note=data.note)
        db.add(note)

    await db.commit()
    return NoteOut(note=note.note)


@router.delete("/repositories/{repo_id}/note")
async def delete_repo_note(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete personal note for a repository."""
    result = await db.execute(
        select(RepoNote).where(
            RepoNote.repo_id == repo_id,
            RepoNote.user_id == current_user.id,
        )
    )
    note = result.scalar_one_or_none()

    if note:
        await db.delete(note)
        await db.commit()

    return {"message": "Note deleted"}
