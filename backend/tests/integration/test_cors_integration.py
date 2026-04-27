"""Integration tests for CORS configuration."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_allowed_origin(client: AsyncClient):
    """Test that allowed origins receive proper CORS headers."""
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.asyncio
async def test_cors_blocked_origin(client: AsyncClient):
    """Test that blocked origins do not receive CORS headers."""
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    # FastAPI CORS middleware returns 400 for disallowed origins on preflight
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cors_preflight_options(client: AsyncClient):
    """Test preflight OPTIONS request handling."""
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers


@pytest.mark.asyncio
async def test_cors_allowed_methods(client: AsyncClient):
    """Test that only allowed methods are permitted."""
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    allowed_methods = response.headers.get("access-control-allow-methods", "")

    # Check that configured methods are allowed
    assert "GET" in allowed_methods
    assert "POST" in allowed_methods
    assert "DELETE" in allowed_methods
    assert "OPTIONS" in allowed_methods


@pytest.mark.asyncio
async def test_cors_allowed_headers(client: AsyncClient):
    """Test that only allowed headers are permitted."""
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        },
    )

    assert response.status_code == 200
    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()

    # Check that configured headers are allowed
    assert "content-type" in allowed_headers
    assert "authorization" in allowed_headers
    assert "x-correlation-id" in allowed_headers


@pytest.mark.asyncio
async def test_cors_credentials(client: AsyncClient):
    """Test that credentials are allowed when configured."""
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-credentials" in response.headers
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_cors_actual_request(client: AsyncClient):
    """Test CORS headers on actual request (not preflight)."""
    response = await client.get(
        "/api/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
