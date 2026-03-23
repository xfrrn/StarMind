"""Collections router - manage repository collections."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from routers.schemas import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse,
    AddRepoToCollectionRequest,
    CollectionReposResponse,
)
from services.application.collection_service import CollectionService

router = APIRouter(prefix="/api", tags=["collections"])

# Service instance
_collection_service = CollectionService()


def get_collection_service() -> CollectionService:
    return _collection_service


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
    db: AsyncSession = Depends(get_db),
):
    """Get repositories in a collection with pagination.

    Args:
        collection_id: Collection ID
        page: Page number
        limit: Items per page
        db: Database session

    Returns:
        Paginated list of repositories
    """
    service = get_collection_service()
    result = await service.get_collection_repos(
        db,
        collection_id=collection_id,
        page=page,
        limit=limit,
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
