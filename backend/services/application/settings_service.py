"""Settings service object: persistence for user preferences."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.repository import Setting
from utils.crypto import encrypt_value, decrypt_value, mask_token

logger = logging.getLogger(__name__)


class SettingsService:
    # Keys that should be encrypted when stored
    SENSITIVE_KEYS = {
        "github_token",
        "openai_api_key",
    }

    DEFAULT_SETTINGS: dict[str, str] = {
        # User info
        "github_username": "",
        "first_name": "",
        "last_name": "",
        "email": "",
        # Feature toggles
        "auto_summarize": "true",
        "include_readmes": "true",
        # OpenAI config
        "openai_base_url": "https://api.openai.com/v1",
        "openai_model": "gpt-4o-mini",
        # Chat retrieval
        "chat_similarity_threshold": "0.5",
        "chat_llm_filter_enabled": "true",
        # Sync config
        "github_sync_page_concurrency": "4",
        "github_readme_concurrency": "8",
        "ai_analysis_concurrency": "1",
    }

    async def _get_setting(self, db: AsyncSession, key: str, decrypt: bool = False) -> str:
        """Get a setting value by key.

        Args:
            db: Database session
            key: Setting key
            decrypt: Whether to decrypt the value (for sensitive keys)
        """
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            value = setting.value
            if decrypt and value:
                return decrypt_value(value)
            return value
        return self.DEFAULT_SETTINGS.get(key, "")

    async def _set_setting(
        self, db: AsyncSession, key: str, value: str, encrypt: bool = False
    ) -> None:
        """Set a setting value by key.

        Args:
            db: Database session
            key: Setting key
            value: Setting value
            encrypt: Whether to encrypt the value (for sensitive keys)
        """
        if encrypt and value:
            value = encrypt_value(value)

        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))

    def _parse_bool(self, value: str) -> bool:
        """Parse a string value to boolean."""
        return value.lower() == "true" if value else False

    def _parse_float(self, value: str, default: float = 0.0) -> float:
        """Parse a string value to float."""
        try:
            return float(value) if value else default
        except ValueError:
            return default

    def _parse_int(self, value: str, default: int = 0) -> int:
        """Parse a string value to int."""
        try:
            return int(value) if value else default
        except ValueError:
            return default

    async def get_user_settings(self, db: AsyncSession) -> dict[str, Any]:
        """Get all user settings with masked sensitive values."""
        # Get sensitive values (decrypted for masking)
        github_token = await self._get_setting(db, "github_token", decrypt=True)
        openai_api_key = await self._get_setting(db, "openai_api_key", decrypt=True)

        return {
            # === User Info ===
            "github_username": await self._get_setting(db, "github_username"),
            "first_name": await self._get_setting(db, "first_name"),
            "last_name": await self._get_setting(db, "last_name"),
            "email": await self._get_setting(db, "email"),
            # === API Keys (masked) ===
            "github_token_set": bool(github_token),
            "github_token_masked": mask_token(github_token) if github_token else "",
            "openai_api_key_set": bool(openai_api_key),
            "openai_api_key_masked": mask_token(openai_api_key) if openai_api_key else "",
            "openai_base_url": await self._get_setting(db, "openai_base_url"),
            "openai_model": await self._get_setting(db, "openai_model"),
            # === Chat Retrieval ===
            "chat_similarity_threshold": self._parse_float(
                await self._get_setting(db, "chat_similarity_threshold"), 0.5
            ),
            "chat_llm_filter_enabled": self._parse_bool(
                await self._get_setting(db, "chat_llm_filter_enabled")
            ),
            # === Sync Configuration ===
            "github_sync_page_concurrency": self._parse_int(
                await self._get_setting(db, "github_sync_page_concurrency"), 4
            ),
            "github_readme_concurrency": self._parse_int(
                await self._get_setting(db, "github_readme_concurrency"), 8
            ),
            "ai_analysis_concurrency": self._parse_int(
                await self._get_setting(db, "ai_analysis_concurrency"), 1
            ),
            # === Feature Toggles ===
            "auto_summarize": self._parse_bool(
                await self._get_setting(db, "auto_summarize")
            ),
            "include_readmes": self._parse_bool(
                await self._get_setting(db, "include_readmes")
            ),
        }

    async def update_user_settings(self, db: AsyncSession, updates: dict) -> dict:
        """Update user settings with proper encryption for sensitive fields."""
        # === User Info ===
        if updates.get("github_username") is not None:
            await self._set_setting(db, "github_username", updates["github_username"])
        if updates.get("first_name") is not None:
            await self._set_setting(db, "first_name", updates["first_name"])
        if updates.get("last_name") is not None:
            await self._set_setting(db, "last_name", updates["last_name"])
        if updates.get("email") is not None:
            await self._set_setting(db, "email", updates["email"])

        # === API Keys (encrypt sensitive values) ===
        if updates.get("github_token") is not None:
            await self._set_setting(
                db, "github_token", updates["github_token"], encrypt=True
            )
        if updates.get("openai_api_key") is not None:
            await self._set_setting(
                db, "openai_api_key", updates["openai_api_key"], encrypt=True
            )

        # === OpenAI Config ===
        if updates.get("openai_base_url") is not None:
            await self._set_setting(db, "openai_base_url", updates["openai_base_url"])
        if updates.get("openai_model") is not None:
            await self._set_setting(db, "openai_model", updates["openai_model"])

        # === Chat Retrieval ===
        if updates.get("chat_similarity_threshold") is not None:
            await self._set_setting(
                db, "chat_similarity_threshold", str(updates["chat_similarity_threshold"])
            )
        if updates.get("chat_llm_filter_enabled") is not None:
            await self._set_setting(
                db,
                "chat_llm_filter_enabled",
                str(updates["chat_llm_filter_enabled"]).lower(),
            )

        # === Sync Configuration ===
        if updates.get("github_sync_page_concurrency") is not None:
            await self._set_setting(
                db, "github_sync_page_concurrency", str(updates["github_sync_page_concurrency"])
            )
        if updates.get("github_readme_concurrency") is not None:
            await self._set_setting(
                db, "github_readme_concurrency", str(updates["github_readme_concurrency"])
            )
        if updates.get("ai_analysis_concurrency") is not None:
            await self._set_setting(
                db, "ai_analysis_concurrency", str(updates["ai_analysis_concurrency"])
            )

        # === Feature Toggles ===
        if updates.get("auto_summarize") is not None:
            await self._set_setting(
                db, "auto_summarize", str(updates["auto_summarize"]).lower()
            )
        if updates.get("include_readmes") is not None:
            await self._set_setting(
                db, "include_readmes", str(updates["include_readmes"]).lower()
            )

        await db.commit()
        return await self.get_user_settings(db)

    async def get_github_token(self, db: AsyncSession) -> str:
        """Get decrypted GitHub token."""
        # First check database, then fallback to env
        token = await self._get_setting(db, "github_token", decrypt=True)
        if token:
            return token
        return get_settings().github_token

    async def get_openai_api_key(self, db: AsyncSession) -> str:
        """Get decrypted OpenAI API key."""
        # First check database, then fallback to env
        key = await self._get_setting(db, "openai_api_key", decrypt=True)
        if key:
            return key
        return get_settings().openai_api_key
