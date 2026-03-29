"""Collections router - manage repository collections."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.llm import LLMClient
from models.database import get_db
from models.shared_collection import SharedCollection
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
    include_repos: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all collections.

    Args:
        include_repos: Whether to include first 10 repos in each collection
        db: Database session

    Returns:
        List of collections
    """
    service = get_collection_service()
    collections = await service.list_collections(db, include_repos=include_repos)
    return {"collections": collections}


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single collection by ID.

    Args:
        collection_id: Collection ID
        db: Database session

    Returns:
        Collection details
    """
    service = get_collection_service()
    collection = await service.get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/collections", response_model=CollectionResponse, status_code=201)
async def create_collection(
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new collection.

    Args:
        data: Collection data
        db: Database session

    Returns:
        Created collection
    """
    service = get_collection_service()
    collection = await service.create_collection(
        db,
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
    db: AsyncSession = Depends(get_db),
):
    """Update a collection.

    Args:
        collection_id: Collection ID
        data: Update data
        db: Database session

    Returns:
        Updated collection
    """
    service = get_collection_service()
    collection = await service.update_collection(
        db,
        collection_id=collection_id,
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
    db: AsyncSession = Depends(get_db),
):
    """Delete a collection.

    Args:
        collection_id: Collection ID
        db: Database session
    """
    service = get_collection_service()
    success = await service.delete_collection(db, collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")


@router.post("/collections/{collection_id}/repos", status_code=201)
async def add_repo_to_collection(
    collection_id: int,
    data: AddRepoToCollectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a repository to a collection.

    Args:
        collection_id: Collection ID
        data: Request with repo_id and optional notes
        db: Database session
    """
    service = get_collection_service()
    success = await service.add_repo_to_collection(
        db,
        collection_id=collection_id,
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
    db: AsyncSession = Depends(get_db),
):
    """Remove a repository from a collection.

    Args:
        collection_id: Collection ID
        repo_id: Repository ID
        db: Database session
    """
    service = get_collection_service()
    success = await service.remove_repo_from_collection(
        db,
        collection_id=collection_id,
        repo_id=repo_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Repository not in collection")


@router.get("/collections/{collection_id}/repos", response_model=CollectionReposResponse)
async def get_collection_repos(
    collection_id: int,
    page: int = 1,
    limit: int = 20,
    tags: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Get repositories in a collection with pagination.

    Args:
        collection_id: Collection ID
        page: Page number
        limit: Items per page
        tags: Comma-separated list of tags to filter by
        db: Database session

    Returns:
        Paginated list of repositories
    """
    # Parse tags filter
    filter_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    service = get_collection_service()
    result = await service.get_collection_repos(
        db,
        collection_id=collection_id,
        page=page,
        limit=limit,
        filter_tags=filter_tags,
    )
    return result


@router.get("/repositories/{repo_id}/collections", response_model=CollectionListResponse)
async def get_repo_collections(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all collections containing a repository.

    Args:
        repo_id: Repository ID
        db: Database session

    Returns:
        List of collections
    """
    service = get_collection_service()
    collections = await service.get_repo_collections(db, repo_id=repo_id)
    return {"collections": collections}


@router.get("/collections/tags")
async def get_all_tags(
    db: AsyncSession = Depends(get_db),
):
    """Get all unique tags from collections.

    Args:
        db: Database session

    Returns:
        List of unique tags
    """
    service = get_collection_service()
    tags = await service.get_all_tags(db)
    return {"tags": tags}


# ---- Share endpoints ----

@router.get("/collections/{collection_id}/share", response_model=ShareStatusResponse)
async def get_share_status(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get share status for a collection."""
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
    db: AsyncSession = Depends(get_db),
):
    """Create a share link for a collection."""
    # Check if collection exists
    service = get_collection_service()
    collection = await service.get_collection(db, collection_id)
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
    db: AsyncSession = Depends(get_db),
):
    """Delete share link for a collection."""
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
    db: AsyncSession = Depends(get_db),
):
    """Update the AI introduction/overview for a collection.

    Args:
        collection_id: Collection ID
        data: Overview content
        db: Database session

    Returns:
        Updated collection
    """
    service = get_collection_service()
    collection = await service.update_overview(
        db,
        collection_id=collection_id,
        content=data.content,
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/collections/{collection_id}/overview/generate", response_model=GenerateOverviewResponse)
async def generate_collection_overview(
    collection_id: int,
    data: GenerateOverviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI overview for a collection.

    Args:
        collection_id: Collection ID
        data: Optional prompt to guide generation
        db: Database session

    Returns:
        Generated Markdown content
    """
    overview_service = get_overview_service()
    try:
        content = await overview_service.generate_overview(
            db,
            collection_id=collection_id,
            prompt=data.prompt,
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
    db: AsyncSession = Depends(get_db),
):
    """Update tags for a repository in a collection.

    Args:
        collection_id: Collection ID
        repo_id: Repository ID
        data: New tags
        db: Database session

    Returns:
        Success status
    """
    service = get_collection_service()
    success = await service.update_repo_tags(
        db,
        collection_id=collection_id,
        repo_id=repo_id,
        tags=data.tags,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Repository not in collection")
    return {"success": True}


@router.get("/collections/{collection_id}/repo-tags")
async def get_collection_repo_tags(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all unique repo tags in a collection.

    Args:
        collection_id: Collection ID
        db: Database session

    Returns:
        List of unique tags
    """
    service = get_collection_service()
    tags = await service.get_all_repo_tags_in_collection(db, collection_id)
    return {"tags": tags}
