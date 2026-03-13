"""Settings router - get/update user preferences."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from routers.schemas import SettingsResponse, SettingsUpdate
from services.settings_service import get_user_settings, update_user_settings

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get user settings."""
    return await get_user_settings(db)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    return await update_user_settings(db, updates.model_dump())
