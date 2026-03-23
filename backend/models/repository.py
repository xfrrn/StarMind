import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship

from config import get_settings
from models.database import Base

EMBEDDING_DIM = int(get_settings().embedding_dimension)


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(Text, nullable=False)  # owner/repo
    description = Column(Text, default="")
    stars = Column(Integer, default=0)
    language = Column(String(100), default="")
    topics = Column(JSONB, default=list)
    tags = Column(JSONB, default=list)
    category = Column(String(50), default="")
    ai_summary = Column(Text, default="")
    has_ui = Column(Boolean, default=False)
    has_api = Column(Boolean, default=False)
    activity_level = Column(String(20), default="Medium")
    last_updated = Column(Text, default="")
    updated_at = Column(DateTime, default=None)
    readme = Column(Text, default="")
    readme_for_analysis = Column(Text, default="")
    readme_for_embedding = Column(Text, default="")
    cleaning_version = Column(String(20), default="v1")
    process_status = Column(String(20), default="fetched")
    analyze_status = Column(String(20), default="pending")
    embedding_status = Column(String(20), default="pending")
    last_run_id = Column(String(64), default="")
    last_error_code = Column(String(100), default="")
    last_error_detail = Column(Text, default="")
    url = Column(Text, default="")
    homepage = Column(Text, default="")
    starred_at = Column(DateTime, default=None)
    synced_at = Column(DateTime, default=datetime.datetime.utcnow)
    # Legacy single embedding kept for backward compatibility.
    embedding = Column(Vector(EMBEDDING_DIM))
    repo_metadata_embedding = Column(Vector(EMBEDDING_DIM), default=None)
    readme_embedding = Column(Vector(EMBEDDING_DIM), default=None)
    metadata_hash = Column(String(64), default="")
    readme_hash = Column(String(64), default="")
    embedding_version = Column(String(20), default="")
    embedding_updated_at = Column(DateTime, default=None)

    # Relationship to collections
    collections = relationship(
        "Collection",
        secondary="collection_repos",
        back_populates="repositories",
    )

    __table_args__ = (
        Index("ix_repositories_language", "language"),
        Index("ix_repositories_category", "category"),
    )


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False)  # success, warning, error
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, default=None)
    new_repos = Column(Integer, default=0)
    updated_repos = Column(Integer, default=0)
    details = Column(Text, default="")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, default="")


class RepoProcessEvent(Base):
    __tablename__ = "repo_process_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(Integer, nullable=False, index=True)
    run_id = Column(String(64), default="", index=True)
    stage = Column(String(30), nullable=False)  # sync, clean, analyze, embed
    action = Column(String(30), nullable=False)  # start, success, fail, retry
    status_field = Column(String(30), nullable=False)  # process/analyze/embedding
    from_status = Column(String(30), default="")
    to_status = Column(String(30), default="")
    reason = Column(Text, default="")
    error_code = Column(String(100), default="")
    error_detail = Column(Text, default="")
    attempt = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
