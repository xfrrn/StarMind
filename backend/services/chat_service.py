"""Chat service: orchestrates retrieval + LLM answering."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.analysis import generate_chat_answer
from core.retrieval import semantic_repository_search
from utils.response_utils import to_chat_repository_response


async def ask_repositories(db: AsyncSession, query: str, top_k: int = 5) -> dict:
    matched_repos = await semantic_repository_search(db, query, top_k=top_k)
    answer = await generate_chat_answer(query, matched_repos)
    repositories = [to_chat_repository_response(repo) for repo in matched_repos]
    return {
        "answer": answer,
        "repositories": repositories,
    }
