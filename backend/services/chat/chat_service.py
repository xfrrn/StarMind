from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.llm import LLMClient
from core.retrieval import EmbeddingService
from services.chat.context_builder import ContextBuilder
from services.chat.intent_router import IntentRouter
from services.chat.models import (
    BuiltContext,
    ChatRequestModel,
    ChatResponsePayload,
    ChatTurn,
    RetrievalTelemetry,
)
from services.chat.policies import ChatPolicy
from services.chat.query_parser import QueryParser
from services.chat.query_rewriter import QueryRewriter
from services.chat.response_generator import ResponseGenerator
from services.chat.retrieval_planner import RetrievalPlanner
from services.chat.retrieval_service import RetrievalService
from services.chat.reranker import Reranker

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        llm_client: LLMClient,
        embedding_service: EmbeddingService,
        policy: ChatPolicy | None = None,
    ):
        self.policy = policy or ChatPolicy()
        self.intent_router = IntentRouter()
        self.query_parser = QueryParser()
        self.query_rewriter = QueryRewriter()
        self.retrieval_planner = RetrievalPlanner(self.policy)
        self.retrieval_service = RetrievalService(
            settings=settings,
            embedding_service=embedding_service,
            policy=self.policy,
        )
        self.reranker = Reranker()
        self.context_builder = ContextBuilder(self.policy)
        self.response_generator = ResponseGenerator(
            llm_client,
            timeout_seconds=float(self.policy.response_timeout_seconds),
        )

    async def chat(
        self,
        db: AsyncSession,
        user_message: str,
        session_id: str | None = None,
        history: list | None = None,
    ) -> ChatResponsePayload:
        started_at = perf_counter()
        request = ChatRequestModel(
            user_message=user_message,
            session_id=session_id,
            history=history or [],
        )
        telemetry = RetrievalTelemetry()
        intent = self.intent_router.route(request.user_message)
        parsed_query = self.query_parser.parse(request.user_message, intent.intent_type)
        plan = self.retrieval_planner.build_plan(intent, parsed_query)

        rewrite_queries: list[str] = []
        if self.policy.enable_query_rewrite:
            rewrite_queries = self.query_rewriter.rewrite(parsed_query)

        ranked = []
        if intent.needs_retrieval:
            try:
                candidates, used_paths = await self.retrieval_service.hybrid_search(
                    db,
                    parsed_query=parsed_query,
                    plan=plan,
                    rewrite_queries=rewrite_queries,
                )
                telemetry.used_paths = used_paths
                telemetry.retrieval_count = len(candidates)
                ranked = self.reranker.rank(
                    candidates,
                    parsed_query=parsed_query,
                    top_k=self.policy.max_reranked_candidates,
                )
                telemetry.reranked_count = len(ranked)
            except Exception as e:
                logger.error("Retrieval degraded in chat pipeline: %s", e)
                telemetry.degraded = True
                telemetry.notes.append(f"retrieval degraded: {e}")
                ranked = []

        built_context = self.context_builder.build(intent.intent_type, ranked)
        answer = ""
        try:
            answer = await self.response_generator.generate(
                user_message=request.user_message,
                built_context=built_context,
                history=request.history,
            )
        except Exception as e:
            telemetry.degraded = True
            telemetry.notes.append(f"generation fallback: {e}")
            answer = self.response_generator.build_structured_fallback(built_context)

        repositories = [self._to_api_repository(repo) for repo in built_context.repositories]
        payload = ChatResponsePayload(
            answer=answer,
            repositories=repositories,
            intent=intent.intent_type,
            telemetry=telemetry,
        )
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        self._log_chat_telemetry(
            session_id=request.session_id,
            query=request.user_message,
            payload=payload,
            elapsed_ms=elapsed_ms,
        )
        return payload

    async def chat_stream(
        self,
        db: AsyncSession,
        user_message: str,
        session_id: str | None = None,
        history: list | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat response with SSE format.

        Yields SSE events:
        - event: status, data: {"stage": str, "message": str}
        - event: repositories, data: JSON array of repositories
        - event: token, data: text chunk
        - event: done, data: empty
        - event: error, data: error message (on failure)
        """
        started_at = perf_counter()
        request = ChatRequestModel(
            user_message=user_message,
            session_id=session_id,
            history=history or [],
        )
        telemetry = RetrievalTelemetry()

        # Helper to format status events
        def status_event(stage: str, message: str) -> str:
            return f'event: status\ndata: {{"stage": "{stage}", "message": "{message}"}}\n\n'

        # 1. Intent routing
        yield status_event("analyzing", "正在分析查询意图...")
        intent = self.intent_router.route(request.user_message)

        # 2. Query parsing
        parsed_query = self.query_parser.parse(request.user_message, intent.intent_type)

        # 3. Retrieval planning
        plan = self.retrieval_planner.build_plan(intent, parsed_query)

        # 4. Query rewriting
        rewrite_queries: list[str] = []
        if self.policy.enable_query_rewrite:
            rewrite_queries = self.query_rewriter.rewrite(parsed_query)

        # 5. Retrieval
        yield status_event("retrieving", "正在搜索相关仓库...")
        ranked = []
        if intent.needs_retrieval:
            try:
                candidates, used_paths = await self.retrieval_service.hybrid_search(
                    db,
                    parsed_query=parsed_query,
                    plan=plan,
                    rewrite_queries=rewrite_queries,
                )
                telemetry.used_paths = used_paths
                telemetry.retrieval_count = len(candidates)
                ranked = self.reranker.rank(
                    candidates,
                    parsed_query=parsed_query,
                    top_k=self.policy.max_reranked_candidates,
                )
                telemetry.reranked_count = len(ranked)
            except Exception as e:
                logger.error("Retrieval degraded in chat stream pipeline: %s", e)
                telemetry.degraded = True
                telemetry.notes.append(f"retrieval degraded: {e}")
                ranked = []

        # 6. Context building
        built_context = self.context_builder.build(intent.intent_type, ranked)

        # 7. Send repositories first
        repositories = [self._to_api_repository(repo) for repo in built_context.repositories]
        yield f"event: repositories\ndata: {json.dumps(repositories, ensure_ascii=False)}\n\n"

        # 8. Stream response tokens
        yield status_event("generating", "正在生成回答...")
        try:
            async for token in self.response_generator.generate_stream(
                user_message=request.user_message,
                built_context=built_context,
                history=request.history,
            ):
                # Escape newlines in SSE data
                escaped_token = token.replace("\n", "\\n")
                yield f"event: token\ndata: {escaped_token}\n\n"
        except Exception as e:
            logger.error("Stream generation failed: %s", e)
            telemetry.degraded = True
            telemetry.notes.append(f"generation error: {e}")
            fallback = self.response_generator.build_structured_fallback(built_context)
            for line in fallback.split("\n"):
                yield f"event: token\ndata: {line}\\n\n\n"

        # 9. Send done event
        yield "event: done\ndata: \n\n"

        # Log telemetry
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        self._log_chat_telemetry(
            session_id=request.session_id,
            query=request.user_message,
            payload=ChatResponsePayload(
                answer="[streamed]",
                repositories=repositories,
                intent=intent.intent_type,
                telemetry=telemetry,
            ),
            elapsed_ms=elapsed_ms,
        )

    async def ask_repositories(self, db: AsyncSession, query: str, top_k: int = 5) -> dict:
        payload = await self.chat(db, query)
        return {
            "answer": payload.answer,
            "repositories": payload.repositories[:top_k],
        }

    @staticmethod
    def _to_api_repository(repo) -> dict:
        return {
            "id": str(repo.repo_id),
            "name": repo.full_name,
            "description": repo.description or "",
            "stars": repo.stars,
            "language": repo.language or "",
            "tags": repo.tags or [],
            "category": repo.category or "",
            "aiReason": repo.analysis_summary or "",
            "hasUI": bool(repo.has_ui),
            "hasAPI": bool(repo.has_api),
            "activityLevel": repo.activity_level or "Medium",
            "lastUpdated": repo.last_updated or "",
            "readme": (repo.cleaned_readme_snippet or "")[:800],
            "url": repo.url or "",
        }

    @staticmethod
    def _log_chat_telemetry(
        *,
        session_id: str | None,
        query: str,
        payload: ChatResponsePayload,
        elapsed_ms: int,
    ) -> None:
        logger.info(
            "chat.pipeline session=%s intent=%s degraded=%s paths=%s retrieval=%s reranked=%s repos=%s latency_ms=%s query=%s notes=%s",
            session_id or "-",
            payload.intent,
            payload.telemetry.degraded,
            ",".join(payload.telemetry.used_paths) or "-",
            payload.telemetry.retrieval_count,
            payload.telemetry.reranked_count,
            len(payload.repositories),
            max(0, elapsed_ms),
            (query or "")[:120].replace("\n", " "),
            " | ".join(payload.telemetry.notes)[:200] if payload.telemetry.notes else "-",
        )
