"""SharedCollection model for public sharing of collections."""

import datetime
import secrets

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models.database import Base


def generate_share_id() -> str:
    """Generate a random 8-character share ID."""
    return secrets.token_urlsafe(6)[:8]


class SharedCollection(Base):
    """A publicly shared collection."""
    __tablename__ = "shared_collections"

    share_id = Column(String(12), primary_key=True, default=generate_share_id)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    view_count = Column(Integer, default=0)

    # Relationship to collection
    collection = relationship("Collection", backref="share")
