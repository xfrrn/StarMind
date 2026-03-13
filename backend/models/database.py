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


async def _ensure_repository_columns_and_embedding_dimension():
    expected_dim = int(settings.embedding_dimension)
    expected_type = f"vector({expected_dim})"
    vector_columns = [
        "embedding",
        "repo_metadata_embedding",
        "readme_embedding",
    ]

    async with engine.begin() as conn:
        # Ensure evolving columns exist for analysis/embedding pipeline.
        await conn.execute(
            text(
                f"""
                ALTER TABLE repositories
                ADD COLUMN IF NOT EXISTS readme_for_analysis text DEFAULT '',
                ADD COLUMN IF NOT EXISTS readme_for_embedding text DEFAULT '',
                ADD COLUMN IF NOT EXISTS cleaning_version varchar(20) DEFAULT 'v1',
                ADD COLUMN IF NOT EXISTS repo_metadata_embedding vector({expected_dim}),
                ADD COLUMN IF NOT EXISTS readme_embedding vector({expected_dim}),
                ADD COLUMN IF NOT EXISTS metadata_hash varchar(64) DEFAULT '',
                ADD COLUMN IF NOT EXISTS readme_hash varchar(64) DEFAULT '',
                ADD COLUMN IF NOT EXISTS embedding_version varchar(20) DEFAULT '',
                ADD COLUMN IF NOT EXISTS embedding_updated_at timestamp
                """
            )
        )

        for column in vector_columns:
            result = await conn.execute(
                text(
                    """
                    SELECT pg_catalog.format_type(a.atttypid, a.atttypmod) AS type_str
                    FROM pg_attribute a
                    JOIN pg_class c ON c.oid = a.attrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'repositories'
                      AND n.nspname = 'public'
                      AND a.attname = :column
                      AND a.attnum > 0
                      AND NOT a.attisdropped
                    """
                ),
                {"column": column},
            )
            current_type = result.scalar()
            if not current_type or current_type == expected_type:
                continue

            logger.warning(
                "Column %s type mismatch (%s). Migrating to %s and clearing vectors.",
                column,
                current_type,
                expected_type,
            )
            await conn.execute(text(f"UPDATE repositories SET {column} = NULL"))
            await conn.execute(
                text(
                    f"ALTER TABLE repositories ALTER COLUMN {column} TYPE vector({expected_dim})"
                )
            )
            logger.info("Column %s migrated to %s", column, expected_type)


async def init_db():
    """Initialize DB, extension, schema, and embedding dimension alignment."""
    await _ensure_database_exists()

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    await _ensure_repository_columns_and_embedding_dimension()
    logger.info("Database tables verified/created")
