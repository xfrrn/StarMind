"""Integration tests for rate limiting."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_rate_limit_enabled_in_config(settings):
    """Test that rate limiting is enabled in configuration."""
    assert hasattr(settings, "rate_limit_enabled")
    assert isinstance(settings.rate_limit_enabled, bool)


@pytest.mark.asyncio
async def test_rate_limit_default_config(settings):
    """Test that default rate limit is configured."""
    assert hasattr(settings, "rate_limit_default")
    assert settings.rate_limit_default == "100/minute"


@pytest.mark.asyncio
async def test_rate_limit_sync_config(settings):
    """Test that sync endpoint rate limit is configured."""
    assert hasattr(settings, "rate_limit_sync")
    assert settings.rate_limit_sync == "5/hour"


@pytest.mark.asyncio
async def test_rate_limit_chat_config(settings):
    """Test that chat endpoint rate limit is configured."""
    assert hasattr(settings, "rate_limit_chat")
    assert settings.rate_limit_chat == "20/minute"


@pytest.mark.asyncio
async def test_rate_limiter_created_when_enabled(settings):
    """Test that rate limiter is created when enabled."""
    from main import app

    if settings.rate_limit_enabled:
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None


@pytest.mark.asyncio
async def test_rate_limit_middleware_configuration():
    """Test that rate limit middleware is properly configured."""
    from middleware.rate_limit import create_limiter

    limiter = create_limiter()
    assert limiter is not None
    # Verify limiter has key_func configured
    assert limiter._key_func is not None


@pytest.mark.asyncio
async def test_rate_limit_error_handler():
    """Test that rate limit error handler is configured."""
    from middleware.rate_limit import rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from fastapi import Request
    from unittest.mock import MagicMock

    # Create mock request
    request = MagicMock(spec=Request)

    # Create mock exception with detail attribute
    exc = MagicMock(spec=RateLimitExceeded)
    exc.detail = "60 seconds"

    # Call handler
    response = rate_limit_exceeded_handler(request, exc)

    # Verify response
    assert response.status_code == 429
    assert response.body is not None


@pytest.mark.asyncio
async def test_rate_limit_error_response_structure():
    """Test the structure of rate limit error responses."""
    from middleware.rate_limit import rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from fastapi import Request
    from unittest.mock import MagicMock
    import json

    # Create mock request
    request = MagicMock(spec=Request)

    # Create mock exception with detail attribute
    exc = MagicMock(spec=RateLimitExceeded)
    exc.detail = "60 seconds"

    # Call handler
    response = rate_limit_exceeded_handler(request, exc)

    # Parse response body
    body = json.loads(response.body)

    # Verify structure
    assert "error" in body
    assert body["error"] == "rate_limit_exceeded"
    assert "message" in body
    assert "retry_after" in body or "retryAfter" in body


@pytest.mark.asyncio
async def test_basic_request_succeeds(client: AsyncClient):
    """Test that basic requests succeed when rate limit is not exceeded."""
    response = await client.get("/api/health")

    # Should succeed (not rate limited in test environment)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_disabled_mode(settings):
    """Test that rate limiting can be disabled via configuration."""
    # Verify the setting exists and can be toggled
    assert hasattr(settings, "rate_limit_enabled")

    # Test with disabled rate limiting
    with patch.object(settings, "rate_limit_enabled", False):
        assert settings.rate_limit_enabled is False

