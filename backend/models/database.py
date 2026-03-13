import logging
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

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
    """Create target database if missing."""
    parsed = urlparse(settings.database_url)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        return

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
                logger.info("Created database '%s'", db_name)
            else:
                logger.info("Database '%s' already exists", db_name)
        await tmp_engine.dispose()
    except Exception as e:
        logger.warning("Could not auto-create database: %s", e)


async def _ensure_embedding_dimension():
    expected_dim = int(settings.embedding_dimension)
    expected_type = f"vector({expected_dim})"

    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                SELECT pg_catalog.format_type(a.atttypid, a.atttypmod) AS type_str
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = 'repositories'
                  AND n.nspname = 'public'
                  AND a.attname = 'embedding'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """
            )
        )
        current_type = result.scalar()
        if not current_type or current_type == expected_type:
            return

        logger.warning(
            "Embedding type mismatch (%s). Migrating to %s and clearing old vectors.",
            current_type,
            expected_type,
        )
        await conn.execute(text("UPDATE repositories SET embedding = NULL"))
        await conn.execute(
            text(f"ALTER TABLE repositories ALTER COLUMN embedding TYPE vector({expected_dim})")
        )
        logger.info("Embedding column migrated to %s", expected_type)


async def init_db():
    """Initialize DB, extension, schema, and embedding dimension alignment."""
    await _ensure_database_exists()

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    await _ensure_embedding_dimension()
    logger.info("Database tables verified/created")
