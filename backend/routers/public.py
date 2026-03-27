"""Public router - public access to shared collections."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from models.database import get_db
from models.shared_collection import SharedCollection
from models.shared_archive import SharedArchive
from models.collection import Collection, CollectionRepo
from models.repository import Repository
from services.application.archive_service import ArchiveService


router = APIRouter(prefix="/api/public", tags=["public"])


class PublicCollectionRepo(BaseModel):
    id: int
    name: str
    description: str
    language: str
    stars: int
    url: str
    notes: str


class PublicCollectionResponse(BaseModel):
    name: str
    description: str
    tags: list[str]
    color: str
    icon: str
    repo_count: int
    repositories: list[PublicCollectionRepo]


@router.get("/shared/{share_id}", response_model=PublicCollectionResponse)
async def get_shared_collection(
    share_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a publicly shared collection by share ID."""
    # Find the share
    result = await db.execute(
        select(SharedCollection).where(SharedCollection.share_id == share_id)
    )
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Shared collection not found")

    # Increment view count
    share.view_count += 1
    await db.commit()

    # Get the collection
    collection_result = await db.execute(
        select(Collection).where(Collection.id == share.collection_id)
    )
    collection = collection_result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Get repos in collection
    repos_result = await db.execute(
        select(Repository, CollectionRepo.notes)
        .join(CollectionRepo, Repository.id == CollectionRepo.repo_id)
        .where(CollectionRepo.collection_id == collection.id)
        .order_by(Repository.stars.desc())
        .limit(100)
    )
    repos_data = repos_result.all()

    repositories = [
        PublicCollectionRepo(
            id=repo.id,
            name=repo.name,
            description=repo.description or "",
            language=repo.language or "",
            stars=repo.stars,
            url=repo.url,
            notes=notes or "",
        )
        for repo, notes in repos_data
    ]

    # Parse tags from JSON string
    import json
    try:
        tags = json.loads(collection.tags) if collection.tags else []
    except:
        tags = []

    return PublicCollectionResponse(
        name=collection.name,
        description=collection.description or "",
        tags=tags,
        color=collection.color or "#3B82F6",
        icon=collection.icon or "folder",
        repo_count=collection.repo_count,
        repositories=repositories,
    )


# ---- Shared Archive ----

class SharedArchiveInfo(BaseModel):
    repo_name: str
    repo_description: str
    archive_size: int
    expires_at: str
    view_count: int


@router.get("/archive/{share_id}", response_model=SharedArchiveInfo)
async def get_shared_archive_info(
    share_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get info about a shared archive."""
    result = await db.execute(
        select(SharedArchive).where(SharedArchive.share_id == share_id)
    )
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    # Check expiration
    if share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share has expired")

    # Increment view count
    share.view_count += 1
    await db.commit()

    # Get repository info
    repo_result = await db.execute(
        select(Repository).where(Repository.id == share.repo_id)
    )
    repo = repo_result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return SharedArchiveInfo(
        repo_name=repo.name,
        repo_description=repo.description or "",
        archive_size=repo.archive_size or 0,
        expires_at=share.expires_at.isoformat() + "Z",
        view_count=share.view_count,
    )


@router.get("/archive/{share_id}/download")
async def download_shared_archive(
    share_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a shared archive file."""
    result = await db.execute(
        select(SharedArchive).where(SharedArchive.share_id == share_id)
    )
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    # Check expiration
    if share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share has expired")

    # Get archive service
    service = ArchiveService()
    file_path = service.get_archive_file_path(share.repo_id)

    if not file_path:
        raise HTTPException(status_code=404, detail="Archive file not found")

    # Get repo name for filename
    repo_result = await db.execute(
        select(Repository).where(Repository.id == share.repo_id)
    )
    repo = repo_result.scalar_one_or_none()
    filename = f"{repo.name.replace('/', '_')}.zip" if repo else f"archive_{share.repo_id}.zip"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/zip",
    )
