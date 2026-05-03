"""RepoNote model for personal notes on repositories."""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import relationship

from models.database import Base


class RepoNote(Base):
    """Personal notes for a repository."""
    __tablename__ = "repo_notes"

    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    repository = relationship("Repository", backref="personal_note")
    user = relationship("User", back_populates="notes")

    __table_args__ = (
        Index("ix_repo_notes_user_id", "user_id"),
    )
