"""Data migration script to migrate existing data to default user.

Usage:
    uv run python scripts/migrate_to_default_user.py
"""

import asyncio
import logging
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.database import async_session
from models.user import User
from models.repository import Repository
from models.conversation import Conversation
from models.collection import Collection

logger = logging.getLogger(__name__)


async def get_or_create_default_user(db: AsyncSession) -> User | None:
    """Get or create the default user for data migration."""
    result = await db.execute(
        select(User).where(User.email == "default@starmind.local")
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        return existing_user

    # Create default user with a placeholder password (OAuth-only account)
    user = User(
        email="default@starmind.local",
        password_hash=None,  # No password - should use OAuth
        github_token=get_settings().github_token,  # Use system token as fallback
        display_name="Default User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Created default user: {user.email}")
    return user


async def migrate_data(db: AsyncSession) -> None:
    """Migrate existing data to the default user."""
    # Get or create default user
    default_user = await get_or_create_default_user(db)
    if not default_user:
        logger.error("Failed to create default user")
        return

    default_user_id = default_user.id
    logger.info(f"Using default user ID: {default_user_id}")

    # Migrate repositories
    result = await db.execute(select(Repository))
    repos = result.scalars().all()

    for repo in repos:
        if repo.user_id is None:
            repo.user_id = default_user_id

    await db.commit()
    logger.info(f"Updated {len(repos)} repositories")

    # Migrate conversations
    result = await db.execute(select(Conversation))
    conversations = result.scalars().all()

    for conv in conversations:
        if conv.user_id is None:
            conv.user_id = default_user_id

    await db.commit()
    logger.info(f"Updated {len(conversations)} conversations")

    # Migrate collections
    result = await db.execute(select(Collection))
    collections = result.scalars().all()

    for col in collections:
        if col.user_id is None:
            col.user_id = default_user_id

    await db.commit()
    logger.info(f"Updated {len(collections)} collections")

    logger.info("Data migration completed!")


async def main():
    """Run migration script."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting data migration...")

    async with async_session() as db:
        await migrate_data(db)

    logger.info("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
