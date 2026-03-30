"""User model for authentication and data isolation."""

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from models.database import Base

if TYPE_CHECKING:
    from models.repository import Repository
    from models.conversation import Conversation
    from models.collection import Collection
    from models.repo_note import RepoNote


class User(Base):
    """User model for authentication and data isolation."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # OAuth users may not have password
    github_id = Column(String(50), unique=True, nullable=True)
    github_token = Column(Text, nullable=True)  # Encrypted storage
    github_username = Column(String(100), nullable=True)
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("RepoNote", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserSetting(Base):
    """User-specific settings (each user has their own OpenAI key, sync config, etc.)."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # OpenAI settings
    openai_api_key = Column(Text, nullable=True)  # Encrypted storage
    openai_base_url = Column(String(255), default="https://api.openai.com/v1")
    openai_model = Column(String(100), default="gpt-4o-mini")

    # Chat settings
    chat_similarity_threshold = Column(Integer, default=50)  # 0-100, mapped to 0.0-1.0
    chat_llm_filter_enabled = Column(Boolean, default=True)

    # Sync settings
    github_sync_page_concurrency = Column(Integer, default=4)
    github_readme_concurrency = Column(Integer, default=8)
    ai_analysis_concurrency = Column(Integer, default=1)
    auto_summarize = Column(Boolean, default=True)
    include_readmes = Column(Boolean, default=True)

    # Auto sync settings
    auto_sync_enabled = Column(Boolean, default=False)
    auto_sync_time = Column(String(10), default="00:00")  # HH:MM format
    timezone = Column(String(50), default="UTC")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSetting user_id={self.user_id}>"
