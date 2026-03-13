"""Chat router - AI-powered semantic search endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from routers.schemas import ChatRequest, ChatResponse
from services.service_registry import get_chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI-powered semantic search across starred repositories."""
    service = get_chat_service()
    return await service.ask_repositories(db, request.query, top_k=5)
