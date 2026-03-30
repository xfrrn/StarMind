"""Settings router - get/update user preferences."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.user import User
from routers.deps import get_current_user
from routers.schemas import SettingsResponse, SettingsUpdate, TestConnectionResponse
from services.service_registry import get_settings_service
from services.application.scheduler_service import update_user_scheduler_job

router = APIRouter(prefix="/api", tags=["settings"])
logger = logging.getLogger(__name__)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user settings."""
    service = get_settings_service()
    return await service.get_user_settings(db, user_id=current_user.id)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    service = get_settings_service()
    result = await service.update_user_settings(db, current_user.id, updates.model_dump())

    # Update scheduler if auto-sync settings changed
    if any(k in updates.model_dump(exclude_none=True) for k in
           ["auto_sync_enabled", "auto_sync_time", "timezone"]):
        try:
            await update_user_scheduler_job(
                user_id=current_user.id,
                enabled=result.get("auto_sync_enabled", False),
                time_str=result.get("auto_sync_time", "00:00"),
                timezone=result.get("timezone", "Asia/Shanghai"),
            )
        except Exception as e:
            logger.warning("Failed to update scheduler: %s", e)

    return result


@router.post("/settings/test-github", response_model=TestConnectionResponse)
async def test_github_connection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test GitHub token validity by fetching user info."""
    service = get_settings_service()
    token = await service.get_github_token(db, user_id=current_user.id)

    if not token:
        return TestConnectionResponse(
            success=False, message="GitHub token not configured"
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

        if response.status_code == 200:
            user_data = response.json()
            username = user_data.get("login", "Unknown")
            return TestConnectionResponse(
                success=True, message=f"Connected as @{username}"
            )
        elif response.status_code == 401:
            return TestConnectionResponse(
                success=False, message="Invalid token or token expired"
            )
        else:
            return TestConnectionResponse(
                success=False,
                message=f"GitHub API error: {response.status_code}",
            )
    except httpx.TimeoutException:
        return TestConnectionResponse(success=False, message="Connection timeout")
    except Exception as e:
        logger.error("GitHub connection test failed: %s", e)
        return TestConnectionResponse(
            success=False, message=f"Connection failed: {str(e)}"
        )


@router.post("/settings/test-openai", response_model=TestConnectionResponse)
async def test_openai_connection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test OpenAI API key validity by listing models."""
    service = get_settings_service()
    api_key = await service.get_openai_api_key(db, user_id=current_user.id)
    base_url = await service._get_user_setting(db, current_user.id, "openai_base_url")

    if not api_key:
        return TestConnectionResponse(
            success=False, message="OpenAI API key not configured"
        )

    # Ensure base_url doesn't have trailing slash
    base_url = base_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )

        if response.status_code == 200:
            data = response.json()
            model_count = len(data.get("data", []))
            return TestConnectionResponse(
                success=True, message=f"Connected successfully ({model_count} models available)"
            )
        elif response.status_code == 401:
            return TestConnectionResponse(
                success=False, message="Invalid API key"
            )
        else:
            return TestConnectionResponse(
                success=False,
                message=f"OpenAI API error: {response.status_code}",
            )
    except httpx.TimeoutException:
        return TestConnectionResponse(success=False, message="Connection timeout")
    except Exception as e:
        logger.error("OpenAI connection test failed: %s", e)
        return TestConnectionResponse(
            success=False, message=f"Connection failed: {str(e)}"
        )
