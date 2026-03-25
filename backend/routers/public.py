"""Public router - public access to shared collections."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from models.database import get_db
from models.shared_collection import SharedCollection
from models.collection import Collection, CollectionRepo
from models.repository import Repository


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
