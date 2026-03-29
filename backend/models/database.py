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
                ADD COLUMN IF NOT EXISTS process_status varchar(20) DEFAULT 'fetched',
                ADD COLUMN IF NOT EXISTS analyze_status varchar(20) DEFAULT 'pending',
                ADD COLUMN IF NOT EXISTS embedding_status varchar(20) DEFAULT 'pending',
                ADD COLUMN IF NOT EXISTS last_run_id varchar(64) DEFAULT '',
                ADD COLUMN IF NOT EXISTS last_error_code varchar(100) DEFAULT '',
                ADD COLUMN IF NOT EXISTS last_error_detail text DEFAULT '',
                ADD COLUMN IF NOT EXISTS repo_metadata_embedding vector({expected_dim}),
                ADD COLUMN IF NOT EXISTS readme_embedding vector({expected_dim}),
                ADD COLUMN IF NOT EXISTS metadata_hash varchar(64) DEFAULT '',
                ADD COLUMN IF NOT EXISTS readme_hash varchar(64) DEFAULT '',
                ADD COLUMN IF NOT EXISTS embedding_version varchar(20) DEFAULT '',
                ADD COLUMN IF NOT EXISTS embedding_updated_at timestamp,
                ADD COLUMN IF NOT EXISTS is_archived boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS archive_path text DEFAULT '',
                ADD COLUMN IF NOT EXISTS archive_size bigint DEFAULT 0,
                ADD COLUMN IF NOT EXISTS archive_sha varchar(64) DEFAULT '',
                ADD COLUMN IF NOT EXISTS archived_at timestamp
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS repo_process_events (
                    id varchar(36) PRIMARY KEY,
                    repo_id integer NOT NULL,
                    run_id varchar(64) DEFAULT '',
                    stage varchar(30) NOT NULL,
                    action varchar(30) NOT NULL,
                    status_field varchar(30) NOT NULL,
                    from_status varchar(30) DEFAULT '',
                    to_status varchar(30) DEFAULT '',
                    reason text DEFAULT '',
                    error_code varchar(100) DEFAULT '',
                    error_detail text DEFAULT '',
                    attempt integer DEFAULT 1,
                    created_at timestamp NOT NULL DEFAULT now()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS shared_archives (
                    share_id varchar(12) PRIMARY KEY,
                    repo_id integer NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    expires_at timestamp NOT NULL,
                    created_at timestamp NOT NULL DEFAULT now(),
                    view_count integer DEFAULT 0,
                    UNIQUE(repo_id)
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_repo_process_events_repo_id
                ON repo_process_events(repo_id)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_repo_process_events_run_id
                ON repo_process_events(run_id)
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
    await _ensure_user_system_tables()
    logger.info("Database tables verified/created")


async def _ensure_user_system_tables():
    """Ensure user system tables and columns exist for multi-tenant support."""
    async with engine.begin() as conn:
        # Create users table if not exists (for migration from older versions)
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id serial PRIMARY KEY,
                    email varchar(255) UNIQUE NOT NULL,
                    password_hash varchar(255),
                    github_id varchar(50) UNIQUE,
                    github_token text,
                    github_username varchar(100),
                    display_name varchar(100),
                    avatar_url text,
                    is_active boolean DEFAULT true,
                    created_at timestamp DEFAULT now(),
                    updated_at timestamp DEFAULT now()
                )
                """
            )
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)")
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_users_github_id ON users(github_id)")
        )

        # Create user_settings table if not exists
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    id serial PRIMARY KEY,
                    user_id integer UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    openai_api_key text,
                    openai_base_url varchar(255) DEFAULT 'https://api.openai.com/v1',
                    openai_model varchar(100) DEFAULT 'gpt-4o-mini',
                    chat_similarity_threshold integer DEFAULT 50,
                    chat_llm_filter_enabled boolean DEFAULT true,
                    github_sync_page_concurrency integer DEFAULT 4,
                    github_readme_concurrency integer DEFAULT 8,
                    ai_analysis_concurrency integer DEFAULT 1,
                    auto_summarize boolean DEFAULT true,
                    include_readmes boolean DEFAULT true,
                    auto_sync_enabled boolean DEFAULT false,
                    auto_sync_time varchar(10) DEFAULT '00:00',
                    timezone varchar(50) DEFAULT 'UTC',
                    created_at timestamp DEFAULT now(),
                    updated_at timestamp DEFAULT now()
                )
                """
            )
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_user_settings_user_id ON user_settings(user_id)")
        )

        # Add user_id columns to existing tables (nullable for migration)
        for table in ["repositories", "conversations", "collections", "repo_notes", "sync_logs"]:
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_id integer REFERENCES users(id)")
            )

        logger.info("User system tables verified/created")
