"""Collection model for organizing repositories into groups."""

import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from models.database import Base


class Collection(Base):
    """A collection/folder for organizing starred repositories."""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    tags = Column(Text, default="[]")  # JSON array of tags
    color = Column(String(20), default="#3B82F6")  # Hex color for UI
    icon = Column(String(50), default="folder")  # Icon name
    repo_count = Column(Integer, default=0)
    ai_introduction = Column(Text, default="")  # AI-generated or manual overview in Markdown
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    repositories = relationship(
        "Repository",
        secondary="collection_repos",
        back_populates="collections",
    )
    user = relationship("User", back_populates="collections")


class CollectionRepo(Base):
    """Association table for collections and repositories."""
    __tablename__ = "collection_repos"

    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, default="")  # Optional notes for this repo in this collection
    tags = Column(Text, default="[]")  # JSON array of tags for this repo in this collection
