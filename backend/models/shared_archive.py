"""SharedArchive model for public sharing of archived repositories."""

import datetime
import secrets

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from models.database import Base


def generate_share_id() -> str:
    """Generate a random 8-character share ID."""
    return secrets.token_urlsafe(6)[:8]


class SharedArchive(Base):
    """A publicly shared archive."""
    __tablename__ = "shared_archives"

    share_id = Column(String(12), primary_key=True, default=generate_share_id)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    view_count = Column(Integer, default=0)

    # Relationship to repository
    repository = relationship("Repository", backref="archive_share")
