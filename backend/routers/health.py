"""Health check endpoint with dependency status monitoring."""

import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx
from models.database import get_db
from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Track startup time
_startup_time = datetime.now(timezone.utc)

# Shared HTTP client for health checks
_http_client = httpx.AsyncClient(timeout=5.0)


@router.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Enhanced health check with dependency status."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    uptime_seconds = (now - _startup_time).total_seconds()

    checks = {
        "database": await _check_database(db),
        "github_api": await _check_github_api(settings.github_token),
        "openai_api": await _check_openai_api(settings.openai_api_key),
    }

    # Determine overall status
    if all(c["status"] == "healthy" for c in checks.values()):
        overall_status = "healthy"
    elif any(c["status"] == "unhealthy" for c in checks.values()):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": settings.app_version,
        "uptimeSeconds": int(uptime_seconds),
        "timestamp": now.isoformat(),
        "checks": checks,
    }


async def _check_database(db: AsyncSession) -> dict[str, str]:
    """Check database connectivity."""
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=5.0)
        return {"status": "healthy"}
    except Exception as e:
        logger.debug(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def _check_github_api(token: str) -> dict[str, str]:
    """Check GitHub API connectivity."""
    try:
        response = await _http_client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"}
        )
        if response.status_code == 200:
            return {"status": "healthy"}
        else:
            return {"status": "degraded", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.debug(f"GitHub API health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def _check_openai_api(api_key: str) -> dict[str, str]:
    """Check OpenAI API connectivity."""
    try:
        response = await _http_client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        if response.status_code == 200:
            return {"status": "healthy"}
        else:
            return {"status": "degraded", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.debug(f"OpenAI API health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
