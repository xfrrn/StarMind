"""Settings router - get/update user preferences."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from routers.schemas import SettingsResponse, SettingsUpdate
from services.service_registry import get_settings_service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get user settings."""
    service = get_settings_service()
    return await service.get_user_settings(db)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    service = get_settings_service()
    return await service.update_user_settings(db, updates.model_dump())
