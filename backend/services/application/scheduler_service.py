"""Scheduler service for auto-sync functionality."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import all_timezones
from sqlalchemy import select

from models.database import async_session
from models.user import User, UserSetting
from services.service_registry import get_sync_service, get_settings_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled tasks like auto-sync for multiple users."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

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

    def _get_user_job_id(self, user_id: int) -> str:
        """Get the job ID for a specific user."""
        return f"auto_sync_user_{user_id}"

    async def schedule_user_auto_sync(
        self,
        user_id: int,
        enabled: bool,
        time_str: str,
        timezone: str,
    ) -> None:
        """Schedule or update the auto-sync job for a specific user.

        Args:
            user_id: User ID
            enabled: Whether auto-sync is enabled
            time_str: Time in HH:MM format (e.g., "00:00")
            timezone: Timezone string (e.g., "Asia/Shanghai")
        """
        job_id = self._get_user_job_id(user_id)

        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info("Removed existing auto-sync job for user %s", user_id)

        if not enabled:
            logger.info("Auto-sync is disabled for user %s", user_id)
            return

        # Parse time string
        try:
            hour, minute = map(int, time_str.split(":"))
        except (ValueError, AttributeError):
            logger.warning("Invalid time format: %s for user %s, using default 00:00", time_str, user_id)
            hour, minute = 0, 0

        # Validate timezone
        if timezone not in all_timezones:
            logger.warning("Invalid timezone: %s for user %s, using UTC", timezone, user_id)
            timezone = "UTC"

        # Create cron trigger
        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)

        # Add job with user_id as argument
        self.scheduler.add_job(
            self._run_user_auto_sync,
            trigger,
            id=job_id,
            args=[user_id],
            replace_existing=True,
            misfire_grace_time=3600,  # Allow 1 hour grace period for missed runs
        )

        logger.info("Scheduled auto-sync for user %s at %s %s", user_id, time_str, timezone)

    async def _run_user_auto_sync(self, user_id: int) -> None:
        """Execute the auto-sync task for a specific user."""
        logger.info("Starting auto-sync for user %s...", user_id)

        try:
            async with async_session() as db:
                # Get GitHub token for user (decrypted)
                settings_service = get_settings_service()
                github_token = await settings_service.get_github_token(db, user_id)

                if not github_token:
                    logger.warning("Auto-sync skipped for user %s: GitHub token not configured", user_id)
                    return

                # Check if sync is already running
                sync_service = get_sync_service()
                status = sync_service.runtime_state.get_sync_status()
                if status["is_syncing"]:
                    logger.info("Auto-sync skipped for user %s: sync already in progress", user_id)
                    return

                # Run incremental sync
                await sync_service.run_sync(db, github_token, full_sync=False, user_id=user_id)
                logger.info("Auto-sync completed successfully for user %s", user_id)

        except Exception as e:
            logger.error("Auto-sync failed for user %s: %s", user_id, e, exc_info=True)

    def remove_user_job(self, user_id: int) -> None:
        """Remove the auto-sync job for a specific user."""
        job_id = self._get_user_job_id(user_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info("Removed auto-sync job for user %s", user_id)


# Global scheduler instance
_scheduler: SchedulerService | None = None


def get_scheduler() -> SchedulerService:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


async def init_scheduler() -> None:
    """Initialize and start the scheduler with settings for all users."""
    scheduler = get_scheduler()
    scheduler.start()

    # Load settings for all users with auto_sync_enabled
    async with async_session() as db:
        result = await db.execute(
            select(User, UserSetting)
            .join(UserSetting, User.id == UserSetting.user_id)
            .where(User.github_token.isnot(None))
            .where(UserSetting.auto_sync_enabled == True)
        )
        user_settings = result.all()

        if not user_settings:
            logger.info("No users with auto-sync enabled found")
            return

        for user, settings in user_settings:
            await scheduler.schedule_user_auto_sync(
                user_id=user.id,
                enabled=settings.auto_sync_enabled,
                time_str=settings.auto_sync_time or "00:00",
                timezone=settings.timezone or "Asia/Shanghai",
            )

        logger.info("Initialized scheduler for %d users", len(user_settings))


async def update_user_scheduler_job(user_id: int, enabled: bool, time_str: str, timezone: str) -> None:
    """Update the scheduler job for a specific user."""
    scheduler = get_scheduler()
    await scheduler.schedule_user_auto_sync(user_id, enabled, time_str, timezone)


async def remove_user_scheduler_job(user_id: int) -> None:
    """Remove the scheduler job for a specific user."""
    scheduler = get_scheduler()
    scheduler.remove_user_job(user_id)
