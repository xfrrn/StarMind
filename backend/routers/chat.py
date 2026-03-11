"""Chat router — AI-powered semantic search endpoint."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from services import ai_service

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    query: str


class RepositoryResponse(BaseModel):
    id: str
    name: str
    description: str
    stars: int
    language: str
    tags: list[str]
    category: str
    aiReason: str | None = None
    has_ui: bool = False  # noqa: N815
    hasUI: bool = False  # noqa: N815
    has_api: bool = False  # noqa: N815
    hasAPI: bool = False  # noqa: N815
    activityLevel: str = "Medium"
    lastUpdated: str = ""
    readme: str = ""
    url: str = ""


class ChatResponse(BaseModel):
    answer: str
    repositories: list[RepositoryResponse]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI-powered semantic search across starred repositories."""
    # 1. Semantic search
    matched_repos = await ai_service.semantic_search(db, request.query, top_k=5)

    # 2. Generate natural language answer
    answer = await ai_service.chat_with_repos(request.query, matched_repos)

    # 3. Format response for frontend
    repositories = [
        RepositoryResponse(
            id=repo["id"],
            name=repo["name"],
            description=repo["description"],
            stars=repo["stars"],
            language=repo["language"],
            tags=repo.get("tags", []),
            category=repo.get("category", ""),
            aiReason=repo.get("ai_summary", ""),
            hasUI=repo.get("has_ui", False),
            hasAPI=repo.get("has_api", False),
            activityLevel=repo.get("activity_level", "Medium"),
            lastUpdated=repo.get("last_updated", ""),
            readme=repo.get("readme", ""),
            url=repo.get("url", ""),
        )
        for repo in matched_repos
    ]

    return ChatResponse(answer=answer, repositories=repositories)
