"""Sync router - trigger sync and view status/history."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter

from models.database import async_session, get_db
from routers.schemas import SyncStatusResponse, SyncTriggerResponse
from services.service_registry import get_sync_service

router = APIRouter(prefix="/api", tags=["sync"])


async def _run_sync_background(github_token: str):
    async with async_session() as db:
        await get_sync_service().run_sync(db, github_token)


async def _run_analysis_background():
    async with async_session() as db:
        await get_sync_service().run_ai_analysis(db)


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_sync(request: Request, background_tasks: BackgroundTasks):
    """Trigger a sync of starred repositories."""
    limiter: Limiter = request.app.state.limiter
    await limiter.limit("5/hour")(request)

    service = get_sync_service()
    validation = service.validate_sync_trigger()
    if validation:
        return validation

    background_tasks.add_task(_run_sync_background, service.get_configured_github_token())
    return {"message": "Sync started successfully.", "status": "started"}


@router.post("/sync/analyze", response_model=SyncTriggerResponse)
async def trigger_analysis(background_tasks: BackgroundTasks):
    """Trigger AI analysis for pending repositories."""
    service = get_sync_service()
    validation = service.validate_analysis_trigger()
    if validation:
        return validation

    background_tasks.add_task(_run_analysis_background)
    return {"message": "AI Analysis started successfully.", "status": "started"}


@router.get("/sync/status", response_model=SyncStatusResponse)
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Get current sync status and history."""
    service = get_sync_service()
    return await service.get_sync_status_overview(db)
