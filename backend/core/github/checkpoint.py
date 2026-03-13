"""Checkpoint helpers for batched async workflows."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def commit_when_reach_checkpoint(
    *,
    db: AsyncSession,
    completed_since_commit: int,
    checkpoint_every: int,
) -> int:
    if completed_since_commit < checkpoint_every:
        return completed_since_commit
    try:
        await db.commit()
        return 0
    except Exception as e:
        logger.error("Checkpoint commit failed: %s", e, exc_info=True)
        await db.rollback()
        raise
