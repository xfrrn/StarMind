from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any

from sqlalchemy import String, and_, cast, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.retrieval import EmbeddingService
from models.repository import Repository
from services.chat.models import RepoCandidate, RepoQuery, RetrievalPlan
from services.chat.policies import ChatPolicy

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        policy: ChatPolicy,
    ):
        self.settings = settings
        self.embedding_service = embedding_service
        self.policy = policy
        self._embedding_cache: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()

    def _get_cached_embedding(self, query_text: str) -> list[float] | None:
        cached = self._embedding_cache.get(query_text)
        if not cached:
            return None
        expire_at, vector = cached
        if time.time() > expire_at:
            self._embedding_cache.pop(query_text, None)
            return None
        self._embedding_cache.move_to_end(query_text)
        return vector

    def _save_cached_embedding(self, query_text: str, vector: list[float]) -> None:
        ttl = max(1, int(self.policy.query_embedding_cache_ttl_seconds))
        self._embedding_cache[query_text] = (time.time() + ttl, vector)
        self._embedding_cache.move_to_end(query_text)
        max_size = max(16, int(self.policy.query_embedding_cache_size))
        while len(self._embedding_cache) > max_size:
            self._embedding_cache.popitem(last=False)

    @staticmethod
    def _to_candidate(repo: Repository, *, matched_by: str, score: float | None = None) -> RepoCandidate:
        full_name = repo.name or ""
        owner = full_name.split("/", 1)[0] if "/" in full_name else ""
        short_name = full_name.split("/", 1)[1] if "/" in full_name else full_name
        return RepoCandidate(
            repo_id=repo.id,
            github_id=repo.github_id,
            full_name=full_name,
            name=short_name,
            owner=owner,
            description=repo.description or "",
            language=repo.language or "",
            topics=repo.topics or [],
            stars=repo.stars or 0,
            tags=repo.tags or [],
            category=repo.category or "",
            analysis_summary=repo.ai_summary or "",
            cleaned_readme_snippet=(repo.readme_for_embedding or repo.readme or "")[:800],
            has_ui=bool(repo.has_ui),
            has_api=bool(repo.has_api),
            activity_level=repo.activity_level or "Medium",
            last_updated=repo.last_updated or "",
            url=repo.url or "",
            score=score,
            matched_by=[matched_by],
        )

    async def search_exact_repo(self, db: AsyncSession, parsed_query: RepoQuery, limit: int) -> list[RepoCandidate]:
        if not (parsed_query.owner and parsed_query.repo_name):
            return []
        full_name = f"{parsed_query.owner}/{parsed_query.repo_name}"
        stmt = select(Repository).where(
            or_(Repository.name == full_name, Repository.name.ilike(f"%/{parsed_query.repo_name}"))
        ).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [self._to_candidate(repo, matched_by="exact") for repo in rows]

    async def search_by_metadata(self, db: AsyncSession, parsed_query: RepoQuery, limit: int) -> list[RepoCandidate]:
        conditions = []
        if parsed_query.language:
            conditions.append(Repository.language == parsed_query.language)
        if parsed_query.owner:
            conditions.append(Repository.name.ilike(f"{parsed_query.owner}/%"))
        if parsed_query.topics:
            for topic in parsed_query.topics[:3]:
                conditions.append(cast(Repository.topics, String).ilike(f"%{topic}%"))

        if not conditions:
            return []
        stmt = select(Repository).where(and_(*conditions)).order_by(Repository.stars.desc()).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [self._to_candidate(repo, matched_by="metadata") for repo in rows]

    async def search_by_keywords(self, db: AsyncSession, parsed_query: RepoQuery, limit: int) -> list[RepoCandidate]:
        terms = (parsed_query.keywords + parsed_query.capabilities)[:10]
        if not terms:
            return []
        keyword_conditions = []
        for term in terms:
            like = f"%{term}%"
            keyword_conditions.append(
                or_(
                    Repository.name.ilike(like),
                    Repository.description.ilike(like),
                    Repository.ai_summary.ilike(like),
                    Repository.readme_for_embedding.ilike(like),
                )
            )
        stmt = select(Repository).where(or_(*keyword_conditions)).order_by(Repository.stars.desc()).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [self._to_candidate(repo, matched_by="keyword") for repo in rows]

    async def search_by_vector(
        self,
        db: AsyncSession,
        parsed_query: RepoQuery,
        rewrite_queries: list[str],
        limit: int,
    ) -> list[RepoCandidate]:
        query_text = rewrite_queries[0] if rewrite_queries else parsed_query.raw_query
        if not query_text.strip():
            return []
        try:
            query_embedding = self._get_cached_embedding(query_text)
            if query_embedding is None:
                query_embedding = await asyncio.wait_for(
                    self.embedding_service.generate_embedding_vector(query_text),
                    timeout=float(self.policy.embedding_timeout_seconds),
                )
                self._save_cached_embedding(query_text, query_embedding)
            else:
                logger.debug("Chat query embedding cache hit")
        except Exception as e:
            logger.warning("Vector embedding generation failed for chat query: %s", e)
            return []

        metadata_weight = float(self.settings.embedding_metadata_weight)
        readme_weight = float(self.settings.embedding_readme_weight)
        sql = text(
            """
            SELECT id, github_id, name, description, stars, language,
                   tags, category, ai_summary, has_ui, has_api, activity_level,
                   last_updated, readme_for_embedding, readme, url, topics,
                   (:metadata_weight * COALESCE(repo_metadata_embedding <=> :query_embedding, 2.0) +
                    :readme_weight * COALESCE(readme_embedding <=> :query_embedding, 2.0)) AS distance
            FROM repositories
            WHERE repo_metadata_embedding IS NOT NULL OR readme_embedding IS NOT NULL
            ORDER BY distance
            LIMIT :limit
            """
        )
        rows = (await db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "metadata_weight": metadata_weight,
                "readme_weight": readme_weight,
                "limit": limit,
            },
        )).mappings().all()

        result: list[RepoCandidate] = []
        for row in rows:
            full_name = row["name"] or ""
            owner = full_name.split("/", 1)[0] if "/" in full_name else ""
            short_name = full_name.split("/", 1)[1] if "/" in full_name else full_name
            distance = float(row["distance"]) if row["distance"] is not None else 2.0
            result.append(
                RepoCandidate(
                    repo_id=row["id"],
                    github_id=row["github_id"],
                    full_name=full_name,
                    name=short_name,
                    owner=owner,
                    description=row["description"] or "",
                    language=row["language"] or "",
                    topics=row["topics"] or [],
                    stars=row["stars"] or 0,
                    tags=row["tags"] or [],
                    category=row["category"] or "",
                    analysis_summary=row["ai_summary"] or "",
                    cleaned_readme_snippet=((row["readme_for_embedding"] or row["readme"] or "")[:800]),
                    has_ui=bool(row["has_ui"]),
                    has_api=bool(row["has_api"]),
                    activity_level=row["activity_level"] or "Medium",
                    last_updated=row["last_updated"] or "",
                    url=row["url"] or "",
                    score=max(0.0, 1.0 - distance),
                    matched_by=["vector"],
                )
            )
        return result

    @staticmethod
    def _merge_candidates(candidates_groups: list[list[RepoCandidate]], limit: int) -> list[RepoCandidate]:
        merged: OrderedDict[int, RepoCandidate] = OrderedDict()
        for group in candidates_groups:
            for candidate in group:
                existing = merged.get(candidate.repo_id)
                if not existing:
                    merged[candidate.repo_id] = candidate
                    continue
                for source in candidate.matched_by:
                    if source not in existing.matched_by:
                        existing.matched_by.append(source)
                if existing.score is None and candidate.score is not None:
                    existing.score = candidate.score
                elif candidate.score is not None and existing.score is not None:
                    existing.score = max(existing.score, candidate.score)
        return list(merged.values())[:limit]

    async def hybrid_search(
        self,
        db: AsyncSession,
        parsed_query: RepoQuery,
        plan: RetrievalPlan,
        rewrite_queries: list[str],
    ) -> tuple[list[RepoCandidate], list[str]]:
        groups: list[list[RepoCandidate]] = []
        used_paths: list[str] = []
        if plan.use_exact_lookup:
            groups.append(await self.search_exact_repo(db, parsed_query, limit=plan.limit))
            used_paths.append("exact")
        if plan.use_metadata_filter:
            groups.append(await self.search_by_metadata(db, parsed_query, limit=plan.limit))
            used_paths.append("metadata")
        if plan.use_keyword_search:
            groups.append(await self.search_by_keywords(db, parsed_query, limit=plan.limit))
            used_paths.append("keyword")
        if plan.use_vector_search:
            groups.append(await self.search_by_vector(db, parsed_query, rewrite_queries, limit=plan.limit))
            used_paths.append("vector")
        return self._merge_candidates(groups, limit=plan.limit), used_paths
