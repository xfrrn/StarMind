"""GitHub OAuth service for user authentication via GitHub."""

import datetime
import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

# State storage for OAuth flow (in production, use Redis or similar)
_oauth_states: dict[str, float] = {}


def generate_oauth_state() -> str:
    """Generate a random state for OAuth CSRF protection."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = datetime.datetime.utcnow().timestamp()
    return state


def validate_oauth_state(state: str, max_age_seconds: int = 600) -> bool:
    """Validate OAuth state and remove it after use."""
    if state not in _oauth_states:
        return False

    created_at = _oauth_states.pop(state)
    age = datetime.datetime.utcnow().timestamp() - created_at
    return age < max_age_seconds


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
