"""Collection service for managing repository collections."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select, delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.collection import Collection, CollectionRepo
from models.repository import Repository

logger = logging.getLogger(__name__)


class CollectionService:
    """Service for managing collections of repositories."""

    async def list_collections(
        self,
        db: AsyncSession,
        include_repos: bool = False,
    ) -> list[dict[str, Any]]:
        """List all collections with optional repo info.

        Args:
            db: Database session
            include_repos: Whether to include repository details

        Returns:
            List of collection dictionaries
        """
        query = select(Collection).order_by(Collection.updated_at.desc())
        result = await db.execute(query)
        collections = result.scalars().all()

        output = []
        for col in collections:
                col_dict = self._collection_to_dict(col)

                if include_repos:
                    # Get repositories in this collection
                    repos_query = (
                        select(Repository)
                        .join(CollectionRepo, Repository.id == CollectionRepo.repo_id)
                        .where(CollectionRepo.collection_id == col.id)
                        .limit(10)
                    )
                    repos_result = await db.execute(repos_query)
                    repos = repos_result.scalars().all()
                    col_dict["repositories"] = [
                        {
                            "id": str(r.id),
                            "name": r.name,
                            "description": r.description,
                            "language": r.language,
                            "stars": r.stars,
                        }
                        for r in repos
                    ]

                output.append(col_dict)

        return output

    async def get_collection(
        self,
        db: AsyncSession,
        collection_id: int,
    ) -> dict[str, Any] | None:
        """Get a single collection by ID.

        Args:
            db: Database session
            collection_id: Collection ID

        Returns:
            Collection dictionary or None
        """
        result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        col = result.scalar_one_or_none()
        if not col:
                return None

        return self._collection_to_dict(col)

    async def create_collection(
        self,
        db: AsyncSession,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
        color: str = "#3B82F6",
        icon: str = "folder",
    ) -> dict[str, Any]:
        """Create a new collection.

        Args:
            db: Database session
            name: Collection name
            description: Collection description
            tags: List of tags
            color: Hex color for UI
            icon: Icon name

        Returns:
            Created collection dictionary
        """
        col = Collection(
            name=name,
            description=description,
            tags=json.dumps(tags or []),
            color=color,
            icon=icon,
            repo_count=0,
        )
        db.add(col)
        await db.commit()
        await db.refresh(col)

        logger.info(f"Created collection: {name}")
        return self._collection_to_dict(col)

    async def update_collection(
        self,
        db: AsyncSession,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        color: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a collection.

        Args:
            db: Database session
            collection_id: Collection ID
            name: New name
            description: New description
            tags: New tags
            color: New color
            icon: New icon

        Returns:
            Updated collection dictionary or None
        """
        result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        col = result.scalar_one_or_none()
        if not col:
            return None

        if name is not None:
            col.name = name
        if description is not None:
            col.description = description
        if tags is not None:
            col.tags = json.dumps(tags)
        if color is not None:
            col.color = color
        if icon is not None:
            col.icon = icon

        await db.commit()
        await db.refresh(col)

        logger.info(f"Updated collection: {col.name}")
        return self._collection_to_dict(col)

    async def delete_collection(
        self,
        db: AsyncSession,
        collection_id: int,
    ) -> bool:
        """Delete a collection.

        Args:
            db: Database session
            collection_id: Collection ID

        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        col = result.scalar_one_or_none()
        if not col:
            return False

        # Delete associated share record first (if any)
        from models.shared_collection import SharedCollection
        await db.execute(
            delete(SharedCollection).where(SharedCollection.collection_id == collection_id)
        )

        await db.delete(col)
        await db.commit()

        logger.info(f"Deleted collection: {col.name}")
        return True

    async def add_repo_to_collection(
        self,
        db: AsyncSession,
        collection_id: int,
        repo_id: int,
        notes: str = "",
    ) -> bool:
        """Add a repository to a collection.

        Args:
            db: Database session
            collection_id: Collection ID
            repo_id: Repository ID
            notes: Optional notes

        Returns:
            True if added, False if already exists
        """
        # Check if already exists
        existing = await db.execute(
            select(CollectionRepo).where(
                CollectionRepo.collection_id == collection_id,
                CollectionRepo.repo_id == repo_id,
            )
        )
        if existing.scalar_one_or_none():
            return False

        # Add association
        col_repo = CollectionRepo(
            collection_id=collection_id,
            repo_id=repo_id,
            notes=notes,
        )
        db.add(col_repo)

        # Update repo count
        await self._update_repo_count(db, collection_id)

        await db.commit()
        logger.info(f"Added repo {repo_id} to collection {collection_id}")
        return True

    async def remove_repo_from_collection(
        self,
        db: AsyncSession,
        collection_id: int,
        repo_id: int,
    ) -> bool:
        """Remove a repository from a collection.

        Args:
            db: Database session
            collection_id: Collection ID
            repo_id: Repository ID

        Returns:
            True if removed, False if not found
        """
        result = await db.execute(
            select(CollectionRepo).where(
                CollectionRepo.collection_id == collection_id,
                CollectionRepo.repo_id == repo_id,
            )
        )
        col_repo = result.scalar_one_or_none()
        if not col_repo:
            return False

        await db.delete(col_repo)

        # Update repo count
        await self._update_repo_count(db, collection_id)

        await db.commit()
        logger.info(f"Removed repo {repo_id} from collection {collection_id}")
        return True

    async def get_collection_repos(
        self,
        db: AsyncSession,
        collection_id: int,
        page: int = 1,
        limit: int = 20,
        filter_tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get repositories in a collection with pagination.

        Args:
            db: Database session
            collection_id: Collection ID
            page: Page number
            limit: Items per page
            filter_tags: Optional list of tags to filter by

        Returns:
            Dictionary with repositories and pagination info
        """
        # Count total
        count_result = await db.execute(
            select(func.count())
            .select_from(CollectionRepo)
            .where(CollectionRepo.collection_id == collection_id)
        )
        total = count_result.scalar() or 0

        # Get repos with pagination
        offset = (page - 1) * limit
        query = (
            select(Repository, CollectionRepo.notes, CollectionRepo.tags)
            .join(CollectionRepo, Repository.id == CollectionRepo.repo_id)
            .where(CollectionRepo.collection_id == collection_id)
            .order_by(CollectionRepo.added_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        rows = result.all()

        repos = []
        for repo, notes, repo_tags_json in rows:
            # Parse repo_tags from JSON
            repo_tags = []
            if repo_tags_json:
                try:
                    repo_tags = json.loads(repo_tags_json) if isinstance(repo_tags_json, str) else repo_tags_json
                except (json.JSONDecodeError, TypeError):
                    repo_tags = []

            # Filter by tags if specified
            if filter_tags:
                # Check if any of the filter_tags are in repo_tags
                if not any(tag in repo_tags for tag in filter_tags):
                    continue

            repo_dict = {
                "id": str(repo.id),
                "name": repo.name,
                "description": repo.description or "",
                "language": repo.language or "",
                "stars": repo.stars,
                "tags": repo.tags or [],
                "repo_tags": repo_tags,
                "category": repo.category or "",
                "url": repo.url or "",
                "notes": notes or "",
            }
            repos.append(repo_dict)

        return {
            "repositories": repos,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": offset + limit < total,
        }

    async def get_repo_collections(
        self,
        db: AsyncSession,
        repo_id: int,
    ) -> list[dict[str, Any]]:
        """Get all collections that contain a repository.

        Args:
            db: Database session
            repo_id: Repository ID

        Returns:
            List of collection dictionaries
        """
        query = (
            select(Collection)
            .join(CollectionRepo, Collection.id == CollectionRepo.collection_id)
            .where(CollectionRepo.repo_id == repo_id)
            .order_by(Collection.name)
        )
        result = await db.execute(query)
        collections = result.scalars().all()

        return [self._collection_to_dict(col) for col in collections]

    async def get_all_tags(
        self,
        db: AsyncSession,
    ) -> list[str]:
        """Get all unique tags from all collections.

        Args:
            db: Database session

        Returns:
            List of unique tags
        """
        result = await db.execute(select(Collection.tags))
        all_tags = set()

        for row in result.scalars().all():
            try:
                tags = json.loads(row) if isinstance(row, str) else row
                if isinstance(tags, list):
                    all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass

        return sorted(list(all_tags))

    async def update_overview(
        self,
        db: AsyncSession,
        collection_id: int,
        content: str,
    ) -> dict[str, Any] | None:
        """Update the AI introduction/overview for a collection.

        Args:
            db: Database session
            collection_id: Collection ID
            content: New overview content (Markdown)

        Returns:
            Updated collection dictionary or None
        """
        result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        col = result.scalar_one_or_none()
        if not col:
            return None

        col.ai_introduction = content
        await db.commit()
        await db.refresh(col)

        logger.info(f"Updated overview for collection: {col.name}")
        return self._collection_to_dict(col)

    async def update_repo_tags(
        self,
        db: AsyncSession,
        collection_id: int,
        repo_id: int,
        tags: list[str],
    ) -> bool:
        """Update tags for a repository in a collection.

        Args:
            db: Database session
            collection_id: Collection ID
            repo_id: Repository ID
            tags: New list of tags

        Returns:
            True if updated, False if not found
        """
        result = await db.execute(
            select(CollectionRepo).where(
                CollectionRepo.collection_id == collection_id,
                CollectionRepo.repo_id == repo_id,
            )
        )
        col_repo = result.scalar_one_or_none()
        if not col_repo:
            return False

        col_repo.tags = json.dumps(tags)
        await db.commit()

        logger.info(f"Updated tags for repo {repo_id} in collection {collection_id}")
        return True

    async def get_collection_repos_for_overview(
        self,
        db: AsyncSession,
        collection_id: int,
    ) -> list[dict[str, Any]]:
        """Get all repositories in a collection for AI overview generation.

        Args:
            db: Database session
            collection_id: Collection ID

        Returns:
            List of repository dictionaries with relevant info
        """
        query = (
            select(Repository, CollectionRepo.notes, CollectionRepo.tags)
            .join(CollectionRepo, Repository.id == CollectionRepo.repo_id)
            .where(CollectionRepo.collection_id == collection_id)
            .order_by(Repository.stars.desc())
        )
        result = await db.execute(query)
        rows = result.all()

        repos = []
        for repo, notes, repo_tags_json in rows:
            # Parse repo_tags from JSON
            repo_tags = []
            if repo_tags_json:
                try:
                    repo_tags = json.loads(repo_tags_json) if isinstance(repo_tags_json, str) else repo_tags_json
                except (json.JSONDecodeError, TypeError):
                    repo_tags = []

            repos.append({
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "",
                "language": repo.language or "",
                "stars": repo.stars,
                "tags": repo.tags or [],
                "repo_tags": repo_tags,
                "category": repo.category or "",
                "ai_reason": repo.ai_reason or "",
                "summary": repo.summary or "",
                "notes": notes or "",
            })

        return repos

    async def get_all_repo_tags_in_collection(
        self,
        db: AsyncSession,
        collection_id: int,
    ) -> list[str]:
        """Get all unique repo tags from a collection.

        Args:
            db: Database session
            collection_id: Collection ID

        Returns:
            List of unique tags
        """
        result = await db.execute(
            select(CollectionRepo.tags).where(CollectionRepo.collection_id == collection_id)
        )
        all_tags = set()

        for row in result.scalars().all():
            try:
                tags = json.loads(row) if isinstance(row, str) else row
                if isinstance(tags, list):
                    all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass

        return sorted(list(all_tags))

    async def _update_repo_count(self, db: AsyncSession, collection_id: int) -> None:
        """Update the repo count for a collection."""
        count_result = await db.execute(
            select(func.count())
            .select_from(CollectionRepo)
            .where(CollectionRepo.collection_id == collection_id)
        )
        count = count_result.scalar() or 0

        # Update the repo_count field in the collection
        await db.execute(
            update(Collection).where(Collection.id == collection_id).values(repo_count=count)
        )

    def _collection_to_dict(self, col: Collection) -> dict[str, Any]:
        """Convert Collection model to dictionary."""
        tags = []
        if col.tags:
            try:
                tags = json.loads(col.tags) if isinstance(col.tags, str) else col.tags
            except (json.JSONDecodeError, TypeError):
                tags = []

        return {
            "id": str(col.id),
            "name": col.name,
            "description": col.description or "",
            "tags": tags,
            "color": col.color or "#3B82F6",
            "icon": col.icon or "folder",
            "repo_count": col.repo_count or 0,
            "ai_introduction": col.ai_introduction or "",
            "created_at": col.created_at.isoformat() if col.created_at else None,
            "updated_at": col.updated_at.isoformat() if col.updated_at else None,
        }
