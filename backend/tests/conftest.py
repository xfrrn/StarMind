"""Shared pytest fixtures for all tests."""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from main import app
from models.database import get_db
from config import get_settings


@pytest_asyncio.fixture
async def mock_db_session():
    """Create a mock database session for testing."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    yield session


@pytest_asyncio.fixture
async def client(mock_db_session):
    """Create an async HTTP client for testing."""
    # Override the database dependency with mock
    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()
