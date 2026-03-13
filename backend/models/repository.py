import datetime

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
    url = Column(Text, default="")
    homepage = Column(Text, default="")
    starred_at = Column(DateTime, default=None)
    synced_at = Column(DateTime, default=datetime.datetime.utcnow)
    embedding = Column(Vector(EMBEDDING_DIM))

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
