import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, Text, Boolean, DateTime, String, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from models.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(Text, nullable=False)  # owner/repo
    description = Column(Text, default="")
    stars = Column(Integer, default=0)
    language = Column(String(100), default="")
    topics = Column(JSONB, default=list)  # GitHub 原始 topics
    tags = Column(JSONB, default=list)  # AI 生成的标签
    category = Column(String(50), default="")  # AI 分类: Frontend, Backend, AI, DevOps, etc.
    ai_summary = Column(Text, default="")  # AI 生成的项目摘要
    has_ui = Column(Boolean, default=False)
    has_api = Column(Boolean, default=False)
    activity_level = Column(String(20), default="Medium")  # High, Medium, Low
    last_updated = Column(Text, default="")  # 人类可读的更新时间
    updated_at = Column(DateTime, default=None)  # 仓库最后推送时间
    readme = Column(Text, default="")
    url = Column(Text, default="")
    homepage = Column(Text, default="")
    starred_at = Column(DateTime, default=None)
    synced_at = Column(DateTime, default=datetime.datetime.utcnow)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small 维度

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
