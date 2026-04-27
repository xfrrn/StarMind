"""Integration tests for health check endpoint."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_health_check_healthy_status(client: AsyncClient):
    """Test health check returns healthy status when all dependencies are up."""
    from routers import health

    # Mock external API checks to return healthy
    async def mock_check_github_healthy(token):
        return {"status": "healthy"}

    async def mock_check_openai_healthy(api_key):
        return {"status": "healthy"}

    with patch.object(health, "_check_github_api", mock_check_github_healthy), \
         patch.object(health, "_check_openai_api", mock_check_openai_healthy):
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptimeSeconds" in data
        assert "timestamp" in data
        assert "checks" in data


@pytest.mark.asyncio
async def test_health_check_response_structure(client: AsyncClient):
    """Test that health check response has correct structure."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Verify top-level fields
    assert "status" in data
    assert "version" in data
    assert "uptimeSeconds" in data
    assert "timestamp" in data
    assert "checks" in data

    # Verify checks structure
    checks = data["checks"]
    assert "database" in checks
    assert "github_api" in checks
    assert "openai_api" in checks

    # Each check should have a status
    for check_name, check_data in checks.items():
        assert "status" in check_data
        assert check_data["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.mark.asyncio
async def test_health_check_version_field(client: AsyncClient):
    """Test that version field is present and valid."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_health_check_uptime_field(client: AsyncClient):
    """Test that uptime field is present and valid."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert "uptimeSeconds" in data
    assert isinstance(data["uptimeSeconds"], int)
    assert data["uptimeSeconds"] >= 0


@pytest.mark.asyncio
async def test_health_check_timestamp_field(client: AsyncClient):
    """Test that timestamp field is present and valid ISO format."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)
    # Verify ISO format (basic check)
    assert "T" in data["timestamp"]
    assert data["timestamp"].endswith("Z") or "+" in data["timestamp"]


@pytest.mark.asyncio
async def test_health_check_database_healthy(client: AsyncClient):
    """Test database check returns healthy when database is accessible."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Database should be healthy (using in-memory SQLite in tests)
    assert data["checks"]["database"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_database_unhealthy(client: AsyncClient):
    """Test database check returns unhealthy when database fails."""
    from routers import health

    # Mock database check to fail
    async def mock_check_db_fail(db):
        return {"status": "unhealthy", "error": "Connection failed"}

    with patch.object(health, "_check_database", mock_check_db_fail):
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "unhealthy"
        assert "error" in data["checks"]["database"]


@pytest.mark.asyncio
async def test_health_check_degraded_status(client: AsyncClient):
    """Test health check returns degraded when some dependencies are down."""
    from routers import health

    # Mock GitHub API check to be degraded, others healthy
    async def mock_check_github_degraded(token):
        return {"status": "degraded", "error": "HTTP 401"}

    async def mock_check_openai_healthy(api_key):
        return {"status": "healthy"}

    with patch.object(health, "_check_github_api", mock_check_github_degraded), \
         patch.object(health, "_check_openai_api", mock_check_openai_healthy):
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Overall status should be degraded
        assert data["status"] == "degraded"
        assert data["checks"]["github_api"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_unhealthy_status(client: AsyncClient):
    """Test health check returns unhealthy when critical dependency is down."""
    from routers import health

    # Mock database check to fail
    async def mock_check_db_fail(db):
        return {"status": "unhealthy", "error": "Connection timeout"}

    with patch.object(health, "_check_database", mock_check_db_fail):
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Overall status should be unhealthy
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_check_external_api_checks(client: AsyncClient):
    """Test that external API checks are included."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Verify external API checks exist
    assert "github_api" in data["checks"]
    assert "openai_api" in data["checks"]

    # Each should have a status
    assert "status" in data["checks"]["github_api"]
    assert "status" in data["checks"]["openai_api"]


@pytest.mark.asyncio
async def test_health_check_correlation_id_header(client: AsyncClient):
    """Test that health check includes correlation ID in response."""
    response = await client.get("/api/health")

    assert response.status_code == 200
    # Health endpoint is excluded from logging but should still have correlation ID
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_health_check_multiple_calls_increment_uptime(client: AsyncClient):
    """Test that uptime increases between calls."""
    import asyncio

    # First call
    response1 = await client.get("/api/health")
    uptime1 = response1.json()["uptimeSeconds"]

    # Wait a bit
    await asyncio.sleep(0.1)

    # Second call
    response2 = await client.get("/api/health")
    uptime2 = response2.json()["uptimeSeconds"]

    # Uptime should be same or slightly higher (depends on timing)
    assert uptime2 >= uptime1
