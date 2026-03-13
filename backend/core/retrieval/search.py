"""Vector similarity retrieval over repositories."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.retrieval.embeddings import EmbeddingService


class RepositorySearchService:
    def __init__(self, settings: Settings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedding_service = embedding_service

    async def semantic_repository_search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        query_embedding = await self.embedding_service.generate_embedding_vector(query)
        metadata_weight = float(self.settings.embedding_metadata_weight)
        readme_weight = float(self.settings.embedding_readme_weight)

        sql = text(
            """
            SELECT id, github_id, name, description, stars, language,
                   tags, category, ai_summary, has_ui, has_api,
                   activity_level, last_updated, readme, url, homepage,
                   COALESCE(repo_metadata_embedding <=> :query_embedding, 2.0) AS metadata_distance,
                   COALESCE(readme_embedding <=> :query_embedding, 2.0) AS readme_distance,
                   (:metadata_weight * COALESCE(repo_metadata_embedding <=> :query_embedding, 2.0) +
                    :readme_weight * COALESCE(readme_embedding <=> :query_embedding, 2.0)) AS distance
            FROM repositories
            WHERE repo_metadata_embedding IS NOT NULL OR readme_embedding IS NOT NULL
            ORDER BY distance
            LIMIT :top_k
            """
        )

        result = await db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "top_k": top_k,
                "metadata_weight": metadata_weight,
                "readme_weight": readme_weight,
            },
        )
        rows = result.mappings().all()

        return [
            {
                "id": str(row["id"]),
                "github_id": row["github_id"],
                "name": row["name"],
                "description": row["description"],
                "stars": row["stars"],
                "language": row["language"],
                "tags": row["tags"] or [],
                "category": row["category"],
                "ai_summary": row["ai_summary"],
                "has_ui": row["has_ui"],
                "has_api": row["has_api"],
                "activity_level": row["activity_level"],
                "last_updated": row["last_updated"],
                "readme": row["readme"],
                "url": row["url"],
                "distance": float(row["distance"]),
            }
            for row in rows
        ]
