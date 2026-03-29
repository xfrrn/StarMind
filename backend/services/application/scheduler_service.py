"""Scheduler service for auto-sync functionality."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import all_timezones
from sqlalchemy import select

from models.database import async_session
from services.service_registry import get_sync_service, get_settings_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled tasks like auto-sync."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._job_id = "auto_sync_job"

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")

    async def schedule_auto_sync(self, enabled: bool, time_str: str, timezone: str) -> None:
        """Schedule or update the auto-sync job.

        Args:
            enabled: Whether auto-sync is enabled
            time_str: Time in HH:MM format (e.g., "00:00")
            timezone: Timezone string (e.g., "Asia/Shanghai")
        """
        # Remove existing job if any
        if self.scheduler.get_job(self._job_id):
            self.scheduler.remove_job(self._job_id)
            logger.info("Removed existing auto-sync job")

        if not enabled:
            logger.info("Auto-sync is disabled")
            return

        # Parse time string
        try:
            hour, minute = map(int, time_str.split(":"))
        except (ValueError, AttributeError):
            logger.warning("Invalid time format: %s, using default 00:00", time_str)
            hour, minute = 0, 0

        # Validate timezone
        if timezone not in all_timezones:
            logger.warning("Invalid timezone: %s, using UTC", timezone)
            timezone = "UTC"

        # Create cron trigger
        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)

        # Add job
        self.scheduler.add_job(
            self._run_auto_sync,
            trigger,
            id=self._job_id,
            replace_existing=True,
            misfire_grace_time=3600,  # Allow 1 hour grace period for missed runs
        )

        logger.info("Scheduled auto-sync at %s %s", time_str, timezone)

    async def _run_auto_sync(self) -> None:
        """Execute the auto-sync task."""
        logger.info("Starting auto-sync...")

        try:
            async with async_session() as db:
                # Get the first user (default user or the only user)
                from sqlalchemy import text
                result = await db.execute(text("SELECT id FROM users WHERE github_token IS NOT NULL LIMIT 1"))
                user_row = result.scalar_one_or_none()

                if not user_row:
                    logger.warning("Auto-sync skipped: No user with GitHub token found")
                    return

                # Get GitHub token from user
                from models.user import User
                user_result = await db.execute(select(User).where(User.id == user_row))
                user = user_result.scalar_one_or_none()

                if not user or not user.github_token:
                    logger.warning("Auto-sync skipped: GitHub token not configured")
                    return

                github_token = user.github_token

                # Check if sync is already running
                sync_service = get_sync_service()
                status = sync_service.runtime_state.get_sync_status()
                if status["is_syncing"]:
                    logger.info("Auto-sync skipped: sync already in progress")
                    return

                # Run incremental sync
                await sync_service.run_sync(db, github_token, full_sync=False, user_id=user_row)
                logger.info("Auto-sync completed successfully")

        except Exception as e:
            logger.error("Auto-sync failed: %s", e, exc_info=True)


# Global scheduler instance
_scheduler: SchedulerService | None = None


def get_scheduler() -> SchedulerService:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


async def init_scheduler() -> None:
    """Initialize and start the scheduler with current settings."""
    scheduler = get_scheduler()
    scheduler.start()

    # Load settings for default user (id=1) and schedule job
    async with async_session() as db:
        from sqlalchemy import text
        result = await db.execute(text("SELECT id FROM users LIMIT 1"))
        user_row = result.scalar_one_or_none()

        if not user_row:
            logger.info("No users found, skipping scheduler initialization")
            return

        settings_service = get_settings_service()
        settings = await settings_service.get_user_settings(db, user_row)

        await scheduler.schedule_auto_sync(
            enabled=settings.get("auto_sync_enabled", False),
            time_str=settings.get("auto_sync_time", "00:00"),
            timezone=settings.get("timezone", "Asia/Shanghai"),
        )


async def update_scheduler_job(enabled: bool, time_str: str, timezone: str) -> None:
    """Update the scheduler job with new settings."""
    scheduler = get_scheduler()
    await scheduler.schedule_auto_sync(enabled, time_str, timezone)
