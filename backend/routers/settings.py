"""Settings router - get/update user preferences."""

import logging

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from routers.schemas import SettingsResponse, SettingsUpdate, TestConnectionResponse
from services.service_registry import get_settings_service

router = APIRouter(prefix="/api", tags=["settings"])
logger = logging.getLogger(__name__)


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


@router.post("/settings/test-github", response_model=TestConnectionResponse)
async def test_github_connection(db: AsyncSession = Depends(get_db)):
    """Test GitHub token validity by fetching user info."""
    service = get_settings_service()
    token = await service.get_github_token(db)

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
async def test_openai_connection(db: AsyncSession = Depends(get_db)):
    """Test OpenAI API key validity by listing models."""
    service = get_settings_service()
    api_key = await service.get_openai_api_key(db)
    base_url = await service._get_setting(db, "openai_base_url")

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
