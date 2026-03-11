import logging
from urllib.parse import urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def _ensure_database_exists():
    """Connect to the default 'postgres' database and create the target DB if it doesn't exist."""
    parsed = urlparse(settings.database_url)
    db_name = parsed.path.lstrip("/")  # e.g. "starmind"

    if not db_name:
        return

    # Build a connection URL pointing to the default 'postgres' database
    default_url = urlunparse(parsed._replace(path="/postgres"))

    try:
        tmp_engine = create_async_engine(default_url, isolation_level="AUTOCOMMIT")
        async with tmp_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not result.scalar():
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info(f"✅ Created database '{db_name}'")
            else:
                logger.info(f"Database '{db_name}' already exists")
        await tmp_engine.dispose()
    except Exception as e:
        logger.warning(f"Could not auto-create database: {e}")


async def init_db():
    """Auto-create the database if needed, enable pgvector, and create all tables."""
    # Step 1: Ensure database exists
    await _ensure_database_exists()

    # Step 2: Enable pgvector extension and create tables
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ Database tables verified/created")
