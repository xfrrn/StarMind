"""Conversation API endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from services.conversation_service import get_conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# Request/Response schemas
class CreateConversationRequest(BaseModel):
    title: str = ""


class AddMessageRequest(BaseModel):
    role: str
    content: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    messageCount: int = 0
    lastMessage: str = ""


class MessageResponse(BaseModel):
    id: int
    conversationId: str
    role: str
    content: str
    createdAt: Optional[str] = None


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all conversations."""
    service = get_conversation_service()
    conversations = await service.list_conversations(db, limit=limit, offset=offset)
    from models.conversation import to_conversation_dict
    return [to_conversation_dict(c) for c in conversations]


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    service = get_conversation_service()
    conv = await service.create_conversation(db, title=request.title)
    from models.conversation import to_conversation_dict
    return to_conversation_dict(conv)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all messages."""
    service = get_conversation_service()
    conv = await service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    from models.conversation import to_conversation_dict
    return to_conversation_dict(conv, conv.messages)


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    service = get_conversation_service()
    success = await service.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: uuid.UUID,
    request: AddMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a message to a conversation."""
    service = get_conversation_service()
    conv = await service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = await service.add_message(
        db,
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
    )
    from models.conversation import to_message_dict
    return to_message_dict(msg)
