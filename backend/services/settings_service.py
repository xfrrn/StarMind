"""Settings service object: persistence for user preferences."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Setting


class SettingsService:
    DEFAULT_SETTINGS = {
        "github_username": "",
        "auto_summarize": "true",
        "include_readmes": "true",
        "first_name": "",
        "last_name": "",
        "email": "",
    }

    async def _get_setting(self, db: AsyncSession, key: str) -> str:
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return self.DEFAULT_SETTINGS.get(key, "")

    async def _set_setting(self, db: AsyncSession, key: str, value: str) -> None:
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))

    async def get_user_settings(self, db: AsyncSession) -> dict:
        return {
            "github_username": await self._get_setting(db, "github_username"),
            "auto_summarize": (await self._get_setting(db, "auto_summarize")) == "true",
            "include_readmes": (await self._get_setting(db, "include_readmes")) == "true",
            "first_name": await self._get_setting(db, "first_name"),
            "last_name": await self._get_setting(db, "last_name"),
            "email": await self._get_setting(db, "email"),
        }

    async def update_user_settings(self, db: AsyncSession, updates: dict) -> dict:
        if updates.get("github_username") is not None:
            await self._set_setting(db, "github_username", updates["github_username"])
        if updates.get("auto_summarize") is not None:
            await self._set_setting(db, "auto_summarize", str(updates["auto_summarize"]).lower())
        if updates.get("include_readmes") is not None:
            await self._set_setting(db, "include_readmes", str(updates["include_readmes"]).lower())
        if updates.get("first_name") is not None:
            await self._set_setting(db, "first_name", updates["first_name"])
        if updates.get("last_name") is not None:
            await self._set_setting(db, "last_name", updates["last_name"])
        if updates.get("email") is not None:
            await self._set_setting(db, "email", updates["email"])

        await db.commit()
        return await self.get_user_settings(db)
