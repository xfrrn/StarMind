"""Chat router - AI-powered semantic search endpoint."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from routers.schemas import ChatRequest, ChatResponse, RepoChatRequest, RepoChatResponse
from routers.mappers.chat import to_repository_response
from services.service_registry import get_chat_service, get_repo_chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI-powered semantic search across starred repositories."""
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
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI-powered semantic search with streaming response via SSE."""
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


@router.post("/chat/repo/{repo_id}", response_model=RepoChatResponse)
async def chat_repo(
    repo_id: int,
    request: RepoChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Chat about a specific repository.

    Args:
        repo_id: Repository ID
        request: Chat request with message and optional history
        db: Database session

    Returns:
        RepoChatResponse with answer and repo info
    """
    service = get_repo_chat_service()
    result = await service.chat(
        db,
        repo_id=repo_id,
        message=request.message,
        history=[turn.model_dump() for turn in request.history],
    )
    return {
        "answer": result.answer,
        "repo": to_repository_response(result.repo),
    }
