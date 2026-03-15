"""Chat service object: orchestrates retrieval + LLM answering."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.analysis import ChatResponder
from core.retrieval import RepositorySearchService
from utils.response_utils import to_chat_repository_response


class ChatService:
    def __init__(self, search_service: RepositorySearchService, chat_responder: ChatResponder):
        self.search_service = search_service
        self.chat_responder = chat_responder

    async def ask_repositories(self, db: AsyncSession, query: str, top_k: int = 5) -> dict:
        matched_repos = await self.search_service.semantic_repository_search(
            db,
            query,
            top_k=top_k,
        )
        answer = await self.chat_responder.generate_chat_answer(query, matched_repos)
        repositories = [to_chat_repository_response(repo) for repo in matched_repos]
        return {
            "answer": answer,
            "repositories": repositories,
        }
