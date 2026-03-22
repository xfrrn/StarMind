"""Conversation and Message models for chat persistence."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from models.database import Base


class Conversation(Base):
    """A conversation session with multiple messages."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0)
    last_message = Column(Text, default="")

    # Relationship
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id}>"


class Message(Base):
    """A single message in a conversation."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)  # user, assistant, tool
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # For tool calls
    tool_calls = Column(JSONB, default=None)
    tool_call_id = Column(String(100), default=None)

    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} role={self.role}>"


def to_conversation_dict(conv: Conversation, messages: list[Message] | None = None) -> dict:
    """Convert Conversation to API response dict."""
    result = {
        "id": str(conv.id),
        "title": conv.title,
        "createdAt": conv.created_at.isoformat() if conv.created_at else None,
        "updatedAt": conv.updated_at.isoformat() if conv.updated_at else None,
        "messageCount": conv.message_count,
        "lastMessage": conv.last_message[:100] if conv.last_message else "",
    }
    if messages is not None:
        result["messages"] = [to_message_dict(m) for m in messages]
    return result


def to_message_dict(msg: Message) -> dict:
    """Convert Message to API response dict."""
    return {
        "id": msg.id,
        "conversationId": str(msg.conversation_id),
        "role": msg.role,
        "content": msg.content,
        "createdAt": msg.created_at.isoformat() if msg.created_at else None,
        "toolCalls": msg.tool_calls,
    }
