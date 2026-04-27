"""Chat router - AI-powered semantic search endpoint."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter

from models.database import get_db
from routers.schemas import ChatRequest, ChatResponse
from services.service_registry import get_chat_service
from config import get_settings

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request, db: AsyncSession = Depends(get_db)):
    """AI-powered semantic search across starred repositories."""
    # Apply rate limiting if enabled
    if hasattr(req.app.state, 'limiter'):
        limiter: Limiter = req.app.state.limiter
        await limiter.limit(get_settings().rate_limit_chat)(req)
    service = get_chat_service()
    payload = await service.chat(
        db,
        user_message=request.query,
        session_id=request.session_id,
        history=[turn.model_dump() for turn in request.history],
    )
    return {
        "answer": payload.answer,
        "repositories": payload.repositories,
    }


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request, db: AsyncSession = Depends(get_db)):
    """AI-powered semantic search with streaming response via SSE."""
    # Apply rate limiting if enabled
    if hasattr(req.app.state, 'limiter'):
        limiter: Limiter = req.app.state.limiter
        await limiter.limit(get_settings().rate_limit_chat)(req)
    service = get_chat_service()

    async def event_generator():
        async for event in service.chat_stream(
            db,
            user_message=request.query,
            session_id=request.session_id,
            history=[turn.model_dump() for turn in request.history],
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
