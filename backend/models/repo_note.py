"""RepoNote model for personal notes on repositories."""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from models.database import Base


class RepoNote(Base):
    """Personal notes for a repository."""
    __tablename__ = "repo_notes"

    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationship to repository
    repository = relationship("Repository", backref="personal_note")
