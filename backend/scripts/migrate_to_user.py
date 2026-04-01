"""Data migration script to migrate all data to a specific user.

Usage:
    uv run python scripts/migrate_to_user.py <target_email>
    Example: uv run python scripts/migrate_to_user.py myemail@example.com
"""
import asyncio
import logging
import sys
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.database import async_session, async_engine
from models.user import User
from models.repository import Repository
from models.conversation import Conversation
from models.collection import Collection
from models.repo_note import RepoNote

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_all_users(db: AsyncSession) -> list[User]:
    """Get all users."""
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


async def migrate_data_to_user(db: AsyncSession, target_user_id: int) -> dict:
    """Migrate all data to the target user."""
    stats = {}

    # Migrate repositories
    result = await db.execute(
        update(Repository).values(user_id=target_user_id)
    )
    stats['repositories'] = result.rowcount

    # Migrate conversations
    result = await db.execute(
        update(Conversation).values(user_id=target_user_id)
    )
    stats['conversations'] = result.rowcount

    # Migrate collections
    result = await db.execute(
        update(Collection).values(user_id=target_user_id)
    )
    stats['collections'] = result.rowcount

    # Migrate repo notes
    result = await db.execute(
        update(RepoNote).values(user_id=target_user_id)
    )
    stats['repo_notes'] = result.rowcount

    # Migrate user_settings (handle separately - update existing or create)
    await db.execute(text("""
        INSERT INTO user_settings (user_id, github_token, openai_api_key, created_at, updated_at)
        VALUES (:user_id, NULL, NULL, NOW(), NOW())
        ON CONFLICT (user_id) DO NOTHING
    """), {"user_id": target_user_id})

    await db.commit()

    return stats


async def main():
    """Run migration script."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Get target email from command line
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/migrate_to_user.py <target_email>")
        print("Example: uv run python scripts/migrate_to_user.py myemail@example.com")
        sys.exit(1)

    target_email = sys.argv[1]
    logger.info(f"Starting data migration to user: {target_email}")

    async with async_session() as db:
        # Show all users first
        users = await get_all_users(db)
        logger.info(f"Found {len(users)} users in database:")
        for u in users:
            logger.info(f"  - ID: {u.id}, Email: {u.email}, GitHub: {u.github_username}")

        # Find target user
        target_user = await get_user_by_email(db, target_email)
        if not target_user:
            logger.error(f"User with email '{target_email}' not found!")
            logger.info("Please register first or use one of the emails above.")
            sys.exit(1)

        logger.info(f"Target user found: ID={target_user.id}, Email={target_user.email}")

        # Perform migration
        logger.info("Migrating data...")
        stats = await migrate_data_to_user(db, target_user.id)

        logger.info("Migration completed!")
        logger.info("Stats:")
        for table, count in stats.items():
            logger.info(f"  - {table}: {count} records")

        # Clean up old users without data (optional)
        logger.info("\nYou may want to delete old unused users manually if needed.")


if __name__ == "__main__":
    asyncio.run(main())
