"""Collections router - manage repository collections."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.llm import LLMClient
from models.database import get_db
from models.shared_collection import SharedCollection
from models.user import User
from routers.deps import get_current_user
from routers.schemas import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse,
    AddRepoToCollectionRequest,
    CollectionReposResponse,
    UpdateCollectionOverview,
    UpdateRepoTagsRequest,
    GenerateOverviewRequest,
    GenerateOverviewResponse,
)
from services.application.collection_service import CollectionService
from services.application.collection_overview_service import CollectionOverviewService

router = APIRouter(prefix="/api", tags=["collections"])

logger = logging.getLogger(__name__)


class ShareResponse(BaseModel):
    share_id: str
    share_url: str


class ShareStatusResponse(BaseModel):
    is_shared: bool
    share_id: str | None = None
    share_url: str | None = None
    view_count: int = 0

# Service instance
_collection_service = CollectionService()


def get_collection_service() -> CollectionService:
    return _collection_service


def get_overview_service() -> CollectionOverviewService:
    """Get collection overview service instance."""
    settings = get_settings()
    llm_client = LLMClient(settings)
    return CollectionOverviewService(settings, llm_client)


@router.get("/collections", response_model=CollectionListResponse)
async def list_collections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_repos: bool = False,
):
    """List all collections for the current user."""
    service = get_collection_service()
    collections = await service.list_collections(db, user_id=current_user.id, include_repos=include_repos)
    return {"collections": collections}


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single collection by ID."""
    service = get_collection_service()
    collection = await service.get_collection(db, collection_id, user_id=current_user.id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/collections", response_model=CollectionResponse, status_code=201)
async def create_collection(
    data: CollectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new collection."""
    service = get_collection_service()
    collection = await service.create_collection(
        db,
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        tags=data.tags,
        color=data.color,
        icon=data.icon,
    )
    return collection


@router.put("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a collection."""
    service = get_collection_service()
    collection = await service.update_collection(
        db,
        collection_id=collection_id,
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        tags=data.tags,
        color=data.color,
        icon=data.icon,
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a collection."""
    service = get_collection_service()
    success = await service.delete_collection(db, collection_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")


@router.post("/collections/{collection_id}/repos", status_code=201)
async def add_repo_to_collection(
    collection_id: int,
    data: AddRepoToCollectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a repository to a collection."""
    service = get_collection_service()
    success = await service.add_repo_to_collection(
        db,
        collection_id=collection_id,
        user_id=current_user.id,
        repo_id=data.repo_id,
        notes=data.notes,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Repository already in collection")
    return {"success": True}


@router.delete("/collections/{collection_id}/repos/{repo_id}", status_code=204)
async def remove_repo_from_collection(
    collection_id: int,
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a repository from a collection."""
    service = get_collection_service()
    success = await service.remove_repo_from_collection(
        db,
        collection_id=collection_id,
        user_id=current_user.id,
        repo_id=repo_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Repository not in collection")


@router.get("/collections/{collection_id}/repos", response_model=CollectionReposResponse)
async def get_collection_repos(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    limit: int = 20,
    tags: str = "",
):
    """Get repositories in a collection with pagination.

    Args:
        collection_id: Collection ID
        page: Page number
        limit: Items per page
        tags: Comma-separated list of tags to filter by

    Returns:
        Paginated list of repositories
    """
    # Parse tags filter
    filter_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    service = get_collection_service()
    result = await service.get_collection_repos(
        db,
        collection_id=collection_id,
        user_id=current_user.id,
        page=page,
        limit=limit,
        filter_tags=filter_tags,
    )
    return result


@router.get("/repositories/{repo_id}/collections", response_model=CollectionListResponse)
async def get_repo_collections(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all collections containing a repository."""
    service = get_collection_service()
    collections = await service.get_repo_collections(db, repo_id=repo_id, user_id=current_user.id)
    return {"collections": collections}


@router.get("/collections/tags")
async def get_all_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all unique tags from collections."""
    service = get_collection_service()
    tags = await service.get_all_tags(db, user_id=current_user.id)
    return {"tags": tags}


# ---- Share endpoints ----

@router.get("/collections/{collection_id}/share", response_model=ShareStatusResponse)
async def get_share_status(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get share status for a collection."""
    # Verify ownership
    service = get_collection_service()
    collection = await service.get_collection(db, collection_id, user_id=current_user.id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    result = await db.execute(
        select(SharedCollection).where(SharedCollection.collection_id == collection_id)
    )
    share = result.scalar_one_or_none()

    if not share:
        return ShareStatusResponse(is_shared=False, view_count=0)

    return ShareStatusResponse(
        is_shared=True,
        share_id=share.share_id,
        share_url=f"/shared/{share.share_id}",
        view_count=share.view_count,
    )


@router.post("/collections/{collection_id}/share", response_model=ShareResponse)
async def create_share(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a share link for a collection."""
    # Verify ownership
    service = get_collection_service()
    collection = await service.get_collection(db, collection_id, user_id=current_user.id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Check if already shared
    result = await db.execute(
        select(SharedCollection).where(SharedCollection.collection_id == collection_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        return ShareResponse(
            share_id=existing.share_id,
            share_url=f"/shared/{existing.share_id}",
        )

    # Create new share
    share = SharedCollection(collection_id=collection_id)
    db.add(share)
    await db.commit()
    await db.refresh(share)

    return ShareResponse(
        share_id=share.share_id,
        share_url=f"/shared/{share.share_id}",
    )


@router.delete("/collections/{collection_id}/share", status_code=204)
async def delete_share(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete share link for a collection."""
    # Verify ownership
    service = get_collection_service()
    collection = await service.get_collection(db, collection_id, user_id=current_user.id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    result = await db.execute(
        select(SharedCollection).where(SharedCollection.collection_id == collection_id)
    )
    share = result.scalar_one_or_none()

    if share:
        await db.delete(share)
        await db.commit()


# ---- Overview endpoints ----

@router.put("/collections/{collection_id}/overview", response_model=CollectionResponse)
async def update_collection_overview(
    collection_id: int,
    data: UpdateCollectionOverview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the AI introduction/overview for a collection."""
    service = get_collection_service()
    collection = await service.update_overview(
        db,
        collection_id=collection_id,
        content=data.content,
        user_id=current_user.id,
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/collections/{collection_id}/overview/generate", response_model=GenerateOverviewResponse)
async def generate_collection_overview(
    collection_id: int,
    data: GenerateOverviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI overview for a collection."""
    overview_service = get_overview_service()
    try:
        content = await overview_service.generate_overview(
            db,
            collection_id=collection_id,
            prompt=data.prompt,
            user_id=current_user.id,
        )
        return GenerateOverviewResponse(content=content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Failed to generate overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---- Repo tags endpoints ----

@router.put("/collections/{collection_id}/repos/{repo_id}/tags")
async def update_repo_tags(
    collection_id: int,
    repo_id: int,
    data: UpdateRepoTagsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tags for a repository in a collection."""
    service = get_collection_service()
    success = await service.update_repo_tags(
        db,
        collection_id=collection_id,
        repo_id=repo_id,
        tags=data.tags,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Repository not in collection")
    return {"success": True}


@router.get("/collections/{collection_id}/repo-tags")
async def get_collection_repo_tags(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all unique repo tags in a collection."""
    service = get_collection_service()
    tags = await service.get_all_repo_tags_in_collection(db, collection_id, user_id=current_user.id)
    return {"tags": tags}
