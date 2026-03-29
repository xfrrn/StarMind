"""GitHub OAuth service for user authentication via GitHub."""

import datetime
import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings

logger = logging.getLogger(__name__)


async def generate_oauth_state(db: AsyncSession) -> str:
    """Generate a random state for OAuth CSRF protection and store in database."""
    state = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    await db.execute(
        text("INSERT INTO oauth_states (state, expires_at) VALUES (:state, :expires_at)"),
        {"state": state, "expires_at": expires_at}
    )
    await db.commit()

    return state


async def validate_oauth_state(db: AsyncSession, state: str) -> bool:
    """Validate OAuth state and remove it after use."""
    # Delete expired states first
    await db.execute(
        text("DELETE FROM oauth_states WHERE expires_at < :now"),
        {"now": datetime.datetime.utcnow()}
    )

    # Check if state exists and is valid
    result = await db.execute(
        text("SELECT id FROM oauth_states WHERE state = :state AND expires_at > :now"),
        {"state": state, "now": datetime.datetime.utcnow()}
    )
    row = result.scalar_one_or_none()

    if row is None:
        return False

    # Delete the used state
    await db.execute(
        text("DELETE FROM oauth_states WHERE id = :id"),
        {"id": row}
    )
    await db.commit()

    return True


def get_github_oauth_url(state: str) -> str:
    """Generate GitHub OAuth authorization URL."""
    settings = get_settings()

    params = {
        "client_id": settings.github_oauth_client_id,
        "redirect_uri": settings.github_oauth_redirect_uri,
        "scope": "read:user repo",  # Access to user info and repos
        "state": state,
        "response_type": "code",
    }

    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Exchange OAuth code for access token."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": settings.github_oauth_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if response.status_code != 200:
            logger.error("GitHub OAuth token exchange failed: %s", response.text)
            raise ValueError("Failed to exchange code for token")

        data = response.json()

        if "error" in data:
            logger.error("GitHub OAuth error: %s", data)
            raise ValueError(data.get("error_description", data["error"]))

        return data


async def get_github_user_info(access_token: str) -> dict[str, Any]:
    """Get GitHub user info using access token."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if response.status_code != 200:
            logger.error("Failed to get GitHub user info: %s", response.text)
            raise ValueError("Failed to get GitHub user info")

        return response.json()


async def get_github_user_emails(access_token: str) -> list[dict[str, Any]]:
    """Get GitHub user emails using access token."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if response.status_code != 200:
            logger.warning("Failed to get GitHub user emails: %s", response.text)
            return []

        return response.json()
