"""Archive router - manage repository snapshots."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.database import get_db
from models.shared_archive import SharedArchive, generate_share_id
from services.application.archive_service import ArchiveService

router = APIRouter(prefix="/api", tags=["archives"])


def get_archive_service() -> ArchiveService:
    return ArchiveService()


class ShareCreate(BaseModel):
    expires_in_hours: int = 24  # Default 24 hours


class ShareStatus(BaseModel):
    is_shared: bool
    share_id: Optional[str] = None
    share_url: Optional[str] = None
    expires_at: Optional[str] = None
    view_count: int = 0


@router.post("/repositories/{repo_id}/archive")
async def create_archive(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    service: ArchiveService = Depends(get_archive_service),
):
    """Create or update archive for a repository."""
    try:
        result = await service.create_archive(db, repo_id)
        return {"message": "Archive created successfully", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create archive: {str(e)}")


@router.get("/repositories/{repo_id}/archive")
async def get_archive_status(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    service: ArchiveService = Depends(get_archive_service),
):
    """Get archive status for a repository."""
    try:
        return await service.get_archive_status(db, repo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/repositories/{repo_id}/archive")
async def delete_archive(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    service: ArchiveService = Depends(get_archive_service),
):
    """Delete archive for a repository."""
    try:
        await service.delete_archive(db, repo_id)
        return {"message": "Archive deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/repositories/{repo_id}/archive/download")
async def download_archive(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    service: ArchiveService = Depends(get_archive_service),
):
    """Download archive file for a repository."""
    # Check if archived
    status = await service.get_archive_status(db, repo_id)
    if not status["is_archived"]:
        raise HTTPException(status_code=404, detail="Archive not found")

    # Get file path
    file_path = service.get_archive_file_path(repo_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Archive file not found")

    return FileResponse(
        path=file_path,
        filename=f"archive_{repo_id}.zip",
        media_type="application/zip",
    )


@router.get("/archives")
async def list_archives(
    db: AsyncSession = Depends(get_db),
    service: ArchiveService = Depends(get_archive_service),
):
    """List all archived repositories."""
    repos = await service.list_archived_repos(db)
    return {"repositories": repos, "total": len(repos)}


# ---- Share APIs ----

@router.post("/repositories/{repo_id}/share")
async def create_share(
    repo_id: int,
    data: ShareCreate,
    db: AsyncSession = Depends(get_db),
    service: ArchiveService = Depends(get_archive_service),
):
    """Create or update share link for an archived repository."""
    # Check if repo is archived
    status = await service.get_archive_status(db, repo_id)
    if not status["is_archived"]:
        raise HTTPException(status_code=400, detail="Repository must be archived first")

    # Check existing share
    result = await db.execute(select(SharedArchive).where(SharedArchive.repo_id == repo_id))
    existing = result.scalar_one_or_none()

    expires_at = datetime.utcnow() + timedelta(hours=data.expires_in_hours)

    if existing:
        existing.expires_at = expires_at
        await db.commit()
        share = existing
    else:
        share = SharedArchive(repo_id=repo_id, expires_at=expires_at)
        db.add(share)
        await db.commit()

    settings = get_settings()
    if settings.frontend_base_url:
        base_url = settings.frontend_base_url
    else:
        # Fallback to first cors origin
        base_url = settings.cors_origins.split(",")[0] if settings.cors_origins else "http://localhost:5173"
    share_url = f"{base_url}/share/{share.share_id}"

    return {
        "share_id": share.share_id,
        "share_url": share_url,
        "expires_at": share.expires_at.isoformat() + "Z",
    }


@router.get("/repositories/{repo_id}/share", response_model=ShareStatus)
async def get_share_status(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get share status for a repository."""
    result = await db.execute(select(SharedArchive).where(SharedArchive.repo_id == repo_id))
    share = result.scalar_one_or_none()

    if not share:
        return ShareStatus(is_shared=False, view_count=0)

    settings = get_settings()
    if settings.frontend_base_url:
        base_url = settings.frontend_base_url
    else:
        base_url = settings.cors_origins.split(",")[0] if settings.cors_origins else "http://localhost:5173"
    share_url = f"{base_url}/share/{share.share_id}"

    return ShareStatus(
        is_shared=True,
        share_id=share.share_id,
        share_url=share_url,
        expires_at=share.expires_at.isoformat() + "Z",
        view_count=share.view_count,
    )


@router.delete("/repositories/{repo_id}/share")
async def delete_share(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete share link for a repository."""
    result = await db.execute(select(SharedArchive).where(SharedArchive.repo_id == repo_id))
    share = result.scalar_one_or_none()

    if share:
        await db.delete(share)
        await db.commit()

    return {"message": "Share deleted"}
