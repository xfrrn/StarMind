"""Conversation service for managing chat sessions and messages."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.conversation import Conversation, Message, to_conversation_dict, to_message_dict

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversations and messages."""

    async def create_conversation(
        self,
        db: AsyncSession,
        title: str = "",
    ) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(title=title or "新对话")
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        logger.info("Created conversation %s", conv.id)
        return conv

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        """Get a conversation by ID."""
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations ordered by last updated."""
        result = await db.execute(
            select(Conversation)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        tool_calls: list | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
        )
        db.add(msg)

        # Update conversation stats
        await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = await self.get_conversation(db, conversation_id)
        if conv:
            conv.message_count = (conv.message_count or 0) + 1
            conv.last_message = content[:500]
            conv.updated_at = datetime.utcnow()
            # Auto-generate title from first user message
            if not conv.title or conv.title == "新对话":
                conv.title = content[:50] + ("..." if len(content) > 50 else "")

        await db.commit()
        await db.refresh(msg)
        return msg

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Message]:
        """Get messages for a conversation, ordered by creation time."""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> bool:
        """Delete a conversation and all its messages."""
        conv = await self.get_conversation(db, conversation_id)
        if not conv:
            return False
        await db.delete(conv)
        await db.commit()
        logger.info("Deleted conversation %s", conversation_id)
        return True

    async def get_conversation_count(self, db: AsyncSession) -> int:
        """Get total conversation count."""
        result = await db.execute(select(func.count(Conversation.id)))
        return result.scalar() or 0

    @staticmethod
    def to_history_format(messages: list[Message]) -> list[dict]:
        """Convert messages to format expected by chat service."""
        return [
            {"role": msg.role, "message": msg.content}
            for msg in messages
            if msg.role in ("user", "assistant")
        ]


# Global instance
_conversation_service: ConversationService | None = None


def get_conversation_service() -> ConversationService:
    """Get or create the global conversation service."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
