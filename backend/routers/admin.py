"""Admin router for administrative tasks."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.user import User
from models.repository import Repository
from models.conversation import Conversation
from models.collection import Collection
from models.repo_note import RepoNote
from routers.deps import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.post("/migrate-all-data")
async def migrate_all_data_to_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Migrate all data in the database to the current user.

    This is useful when you have orphaned data from previous versions
    or from a default user that needs to be claimed.
    """
    target_user_id = current_user.id
    stats = {}

    try:
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

        await db.commit()

        logger.info(f"Migration completed for user {current_user.email}: {stats}")

        return {
            "success": True,
            "message": f"All data migrated to user {current_user.email}",
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
