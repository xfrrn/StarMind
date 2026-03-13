"""Sync router — trigger sync and view status/history."""

import asyncio
from datetime import datetime

from pydantic import BaseModel
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db, async_session
from models.repository import Repository, SyncLog
from services.sync_service import run_sync, get_sync_status, run_ai_analysis
from config import get_settings

router = APIRouter(prefix="/api", tags=["sync"])


class SyncStatusResponse(BaseModel):
    is_syncing: bool
    progress: int
    total: int
    current_repo: str
    total_stars: int
    indexed_repos: int
    pending_repos: int
    last_sync: str | None
    logs: list[dict]


class SyncTriggerResponse(BaseModel):
    message: str
    status: str


async def _run_sync_background(github_token: str):
    """Run sync in background using a fresh database session."""
    async with async_session() as db:
        await run_sync(db, github_token)


async def _run_analysis_background():
    """Run AI analysis in background using a fresh database session."""
    async with async_session() as db:
        await run_ai_analysis(db)


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a sync of starred repositories."""
    settings = get_settings()
    status = get_sync_status()

    if status["is_syncing"]:
        return SyncTriggerResponse(
            message="A sync or analysis is already in progress.",
            status="already_running",
        )

    if not settings.github_token:
        return SyncTriggerResponse(
            message="GitHub token not configured. Please set GITHUB_TOKEN in settings.",
            status="error",
        )

    background_tasks.add_task(_run_sync_background, settings.github_token)

    return SyncTriggerResponse(
        message="Sync started successfully.",
        status="started",
    )


@router.post("/sync/analyze", response_model=SyncTriggerResponse)
async def trigger_analysis(background_tasks: BackgroundTasks):
    """Trigger AI analysis for pending repositories."""
    settings = get_settings()
    status = get_sync_status()

    if status["is_syncing"]:
        return SyncTriggerResponse(
            message="A sync or analysis is already in progress.",
            status="already_running",
        )

    if not settings.openai_api_key:
        return SyncTriggerResponse(
            message="OpenAI API key not configured. Please set OPENAI_API_KEY in settings.",
            status="error",
        )

    background_tasks.add_task(_run_analysis_background)

    return SyncTriggerResponse(
        message="AI Analysis started successfully.",
        status="started",
    )


@router.get("/sync/status", response_model=SyncStatusResponse)
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Get current sync status and history."""
    status = get_sync_status()

    # Get total stars count
    total_result = await db.execute(select(func.count(Repository.id)))
    total_stars = total_result.scalar() or 0

    # Get indexed repos count (those with embeddings)
    indexed_result = await db.execute(
        select(func.count(Repository.id)).where(Repository.embedding.isnot(None))
    )
    indexed_repos = indexed_result.scalar() or 0

    # Get pending repos count
    pending_result = await db.execute(
        select(func.count(Repository.id)).where(Repository.category == "Pending Analysis")
    )
    pending_repos = pending_result.scalar() or 0

    # Get last sync time
    last_sync_result = await db.execute(
        select(SyncLog.finished_at)
        .where(SyncLog.status == "success")
        .order_by(SyncLog.finished_at.desc())
        .limit(1)
    )
    last_sync_row = last_sync_result.scalar()
    last_sync = None
    if last_sync_row:
        diff = datetime.utcnow() - last_sync_row
        hours = int(diff.total_seconds() / 3600)
        if hours < 1:
            minutes = int(diff.total_seconds() / 60)
            last_sync = f"{minutes}m ago"
        elif hours < 24:
            last_sync = f"{hours}h ago"
        else:
            last_sync = last_sync_row.strftime("%Y-%m-%d %H:%M")

    # Get sync logs
    logs_result = await db.execute(
        select(SyncLog).order_by(SyncLog.started_at.desc()).limit(10)
    )
    logs = logs_result.scalars().all()

    log_list = []
    for log in logs:
        log_time = log.started_at.strftime("%b %d, %I:%M %p") if log.started_at else ""
        log_list.append(
            {
                "status": log.status,
                "time": log_time,
                "details": log.details or "",
            }
        )

    return SyncStatusResponse(
        is_syncing=status["is_syncing"],
        progress=status["progress"],
        total=status["total"],
        current_repo=status["current_repo"],
        total_stars=total_stars,
        indexed_repos=indexed_repos,
        pending_repos=pending_repos,
        last_sync=last_sync,
        logs=log_list,
    )
