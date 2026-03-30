"""Settings service object: persistence for user preferences."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.user import UserSetting
from utils.crypto import encrypt_value, decrypt_value, mask_token

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing user-specific settings."""

    async def _get_or_create_user_settings(self, db: AsyncSession, user_id: int) -> UserSetting:
        """Get or create user settings for a given user."""
        result = await db.execute(
            select(UserSetting).where(UserSetting.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            settings = UserSetting(user_id=user_id)
            db.add(settings)
            await db.flush()
        return settings

    def _parse_bool(self, value: bool) -> bool:
        """Return boolean value as-is."""
        return bool(value)

    def _parse_float(self, value: int, default: float = 0.0) -> float:
        """Parse integer (0-100) to float (0.0-1.0)."""
        try:
            return float(value) / 100.0 if value is not None else default
        except (ValueError, TypeError):
            return default

    def _float_to_int(self, value: float) -> int:
        """Convert float (0.0-1.0) to integer (0-100)."""
        return int(value * 100)

    async def get_user_settings(self, db: AsyncSession, user_id: int) -> dict[str, Any]:
        """Get all user settings with masked sensitive values."""
        settings = await self._get_or_create_user_settings(db, user_id)

        # Get user's GitHub token from User model (handled by auth)
        # For now, we check if the user has set a token
        from models.user import User
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        github_token_set = bool(user and user.github_token)
        openai_key = settings.openai_api_key
        if openai_key:
            openai_key = decrypt_value(openai_key)

        return {
            # === User Info (from User model) ===
            "github_username": user.github_username if user else "",
            "first_name": "",
            "last_name": "",
            "email": user.email if user else "",
            # === API Keys (masked) ===
            "github_token_set": github_token_set,
            "github_token_masked": mask_token(user.github_token) if user and user.github_token else "",
            "openai_api_key_set": bool(openai_key),
            "openai_api_key_masked": mask_token(openai_key) if openai_key else "",
            "openai_base_url": settings.openai_base_url or "https://api.openai.com/v1",
            "openai_model": settings.openai_model or "gpt-4o-mini",
            # === Chat Retrieval ===
            "chat_similarity_threshold": self._parse_float(settings.chat_similarity_threshold, 0.5),
            "chat_llm_filter_enabled": settings.chat_llm_filter_enabled,
            # === Sync Configuration ===
            "github_sync_page_concurrency": settings.github_sync_page_concurrency or 4,
            "github_readme_concurrency": settings.github_readme_concurrency or 8,
            "ai_analysis_concurrency": settings.ai_analysis_concurrency or 1,
            # === Feature Toggles ===
            "auto_summarize": settings.auto_summarize,
            "include_readmes": settings.include_readmes,
            # === Auto Sync ===
            "auto_sync_enabled": settings.auto_sync_enabled,
            "auto_sync_time": settings.auto_sync_time or "00:00",
            "timezone": settings.timezone or "UTC",
            "last_sync_at": None,  # Could be added to UserSetting if needed
        }

    async def update_user_settings(
        self, db: AsyncSession, user_id: int, updates: dict
    ) -> dict[str, Any]:
        """Update user settings with proper encryption for sensitive fields."""
        settings = await self._get_or_create_user_settings(db, user_id)

        # === OpenAI Config ===
        if updates.get("openai_api_key") is not None:
            settings.openai_api_key = encrypt_value(updates["openai_api_key"])
        if updates.get("openai_base_url") is not None:
            settings.openai_base_url = updates["openai_base_url"]
        if updates.get("openai_model") is not None:
            settings.openai_model = updates["openai_model"]

        # === Chat Retrieval ===
        if updates.get("chat_similarity_threshold") is not None:
            settings.chat_similarity_threshold = self._float_to_int(updates["chat_similarity_threshold"])
        if updates.get("chat_llm_filter_enabled") is not None:
            settings.chat_llm_filter_enabled = updates["chat_llm_filter_enabled"]

        # === Sync Configuration ===
        if updates.get("github_sync_page_concurrency") is not None:
            settings.github_sync_page_concurrency = updates["github_sync_page_concurrency"]
        if updates.get("github_readme_concurrency") is not None:
            settings.github_readme_concurrency = updates["github_readme_concurrency"]
        if updates.get("ai_analysis_concurrency") is not None:
            settings.ai_analysis_concurrency = updates["ai_analysis_concurrency"]

        # === Feature Toggles ===
        if updates.get("auto_summarize") is not None:
            settings.auto_summarize = updates["auto_summarize"]
        if updates.get("include_readmes") is not None:
            settings.include_readmes = updates["include_readmes"]

        # === Auto Sync ===
        if updates.get("auto_sync_enabled") is not None:
            settings.auto_sync_enabled = updates["auto_sync_enabled"]
        if updates.get("auto_sync_time") is not None:
            settings.auto_sync_time = updates["auto_sync_time"]
        if updates.get("timezone") is not None:
            settings.timezone = updates["timezone"]

        await db.commit()
        return await self.get_user_settings(db, user_id)

    async def get_github_token(self, db: AsyncSession, user_id: int) -> str:
        """Get decrypted GitHub token for a user."""
        from models.user import User
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user and user.github_token:
            # Decrypt if it looks like encrypted data (Fernet tokens start with 'gAAAAA')
            token = user.github_token
            if token.startswith('gAAAAA') or token.startswith('gAAAA'):
                decrypted = decrypt_value(token)
                if decrypted:
                    return decrypted
            return token
        # Fallback to system token
        return get_settings().github_token

    async def get_openai_api_key(self, db: AsyncSession, user_id: int) -> str:
        """Get decrypted OpenAI API key for a user."""
        settings = await self._get_or_create_user_settings(db, user_id)

        if settings.openai_api_key:
            return decrypt_value(settings.openai_api_key)
        # Fallback to system key
        return get_settings().openai_api_key

    async def _get_user_setting(
        self, db: AsyncSession, user_id: int, key: str, decrypt: bool = False
    ) -> str:
        """Get a specific setting value by key (for compatibility)."""
        settings = await self._get_or_create_user_settings(db, user_id)

        # Map old key names to new model attributes
        key_map = {
            "openai_base_url": settings.openai_base_url,
            "openai_model": settings.openai_model,
            "chat_similarity_threshold": str(settings.chat_similarity_threshold),
            "chat_llm_filter_enabled": str(settings.chat_llm_filter_enabled).lower(),
            "github_sync_page_concurrency": str(settings.github_sync_page_concurrency),
            "github_readme_concurrency": str(settings.github_readme_concurrency),
            "ai_analysis_concurrency": str(settings.ai_analysis_concurrency),
            "auto_summarize": str(settings.auto_summarize).lower(),
            "include_readmes": str(settings.include_readmes).lower(),
            "auto_sync_enabled": str(settings.auto_sync_enabled).lower(),
            "auto_sync_time": settings.auto_sync_time,
            "timezone": settings.timezone,
        }

        value = key_map.get(key, "")
        if decrypt and value:
            return decrypt_value(value)
        return str(value) if value else ""
