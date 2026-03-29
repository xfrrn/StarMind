"""Sync router - trigger sync and view status/history."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import async_session, get_db
from models.user import User
from routers.deps import get_current_user
from routers.schemas import SyncStatusResponse, SyncTriggerResponse
from services.service_registry import get_sync_service

router = APIRouter(prefix="/api", tags=["sync"])


async def _run_sync_background(user_id: int, github_token: str, full_sync: bool = False):
    async with async_session() as db:
        await get_sync_service().run_sync(db, github_token, user_id=user_id, full_sync=full_sync)


async def _run_analysis_background(user_id: int):
    async with async_session() as db:
        await get_sync_service().run_ai_analysis(db, user_id=user_id)


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    full_sync: bool = Query(False, description="Force full sync instead of incremental"),
):
    """Trigger a sync of starred repositories."""
    service = get_sync_service()

    # Use user's GitHub token if available, otherwise fall back to system token
    github_token = current_user.github_token or service.get_configured_github_token()
    if not github_token:
        return {"message": "No GitHub token configured.", "status": "error"}

    validation = service.validate_sync_trigger()
    if validation:
        return validation

    background_tasks.add_task(
        _run_sync_background,
        current_user.id,
        github_token,
        full_sync,
    )
    return {"message": "Sync started successfully.", "status": "started"}


@router.post("/sync/analyze", response_model=SyncTriggerResponse)
async def trigger_analysis(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Trigger AI analysis for pending repositories."""
    service = get_sync_service()
    validation = service.validate_analysis_trigger()
    if validation:
        return validation

    background_tasks.add_task(_run_analysis_background, current_user.id)
    return {"message": "AI Analysis started successfully.", "status": "started"}


@router.get("/sync/status", response_model=SyncStatusResponse)
async def sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current sync status and history."""
    service = get_sync_service()
    return await service.get_sync_status_overview(db, user_id=current_user.id)
