"""Sync router - trigger sync and view status/history."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import async_session, get_db
from routers.schemas import SyncStatusResponse, SyncTriggerResponse
from services.sync_service import (
    get_configured_github_token,
    get_sync_status_overview,
    run_ai_analysis,
    run_sync,
    validate_analysis_trigger,
    validate_sync_trigger,
)

router = APIRouter(prefix="/api", tags=["sync"])


async def _run_sync_background(github_token: str):
    async with async_session() as db:
        await run_sync(db, github_token)


async def _run_analysis_background():
    async with async_session() as db:
        await run_ai_analysis(db)


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a sync of starred repositories."""
    validation = validate_sync_trigger()
    if validation:
        return validation

    background_tasks.add_task(_run_sync_background, get_configured_github_token())
    return {"message": "Sync started successfully.", "status": "started"}


@router.post("/sync/analyze", response_model=SyncTriggerResponse)
async def trigger_analysis(background_tasks: BackgroundTasks):
    """Trigger AI analysis for pending repositories."""
    validation = validate_analysis_trigger()
    if validation:
        return validation

    background_tasks.add_task(_run_analysis_background)
    return {"message": "AI Analysis started successfully.", "status": "started"}


@router.get("/sync/status", response_model=SyncStatusResponse)
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Get current sync status and history."""
    return await get_sync_status_overview(db)
