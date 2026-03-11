"""Settings router — get/update user preferences."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.repository import Setting

router = APIRouter(prefix="/api", tags=["settings"])

# Default settings
DEFAULT_SETTINGS = {
    "github_username": "",
    "auto_summarize": "true",
    "include_readmes": "true",
    "first_name": "",
    "last_name": "",
    "email": "",
}


class SettingsResponse(BaseModel):
    github_username: str = ""
    auto_summarize: bool = True
    include_readmes: bool = True
    first_name: str = ""
    last_name: str = ""
    email: str = ""


class SettingsUpdate(BaseModel):
    github_username: str | None = None
    auto_summarize: bool | None = None
    include_readmes: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


async def _get_setting(db: AsyncSession, key: str) -> str:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        return setting.value
    return DEFAULT_SETTINGS.get(key, "")


async def _set_setting(db: AsyncSession, key: str, value: str):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        db.add(Setting(key=key, value=value))


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get user settings."""
    return SettingsResponse(
        github_username=await _get_setting(db, "github_username"),
        auto_summarize=(await _get_setting(db, "auto_summarize")) == "true",
        include_readmes=(await _get_setting(db, "include_readmes")) == "true",
        first_name=await _get_setting(db, "first_name"),
        last_name=await _get_setting(db, "last_name"),
        email=await _get_setting(db, "email"),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate, db: AsyncSession = Depends(get_db)
):
    """Update user settings."""
    if updates.github_username is not None:
        await _set_setting(db, "github_username", updates.github_username)
    if updates.auto_summarize is not None:
        await _set_setting(db, "auto_summarize", str(updates.auto_summarize).lower())
    if updates.include_readmes is not None:
        await _set_setting(db, "include_readmes", str(updates.include_readmes).lower())
    if updates.first_name is not None:
        await _set_setting(db, "first_name", updates.first_name)
    if updates.last_name is not None:
        await _set_setting(db, "last_name", updates.last_name)
    if updates.email is not None:
        await _set_setting(db, "email", updates.email)

    await db.commit()

    return await get_settings(db)
