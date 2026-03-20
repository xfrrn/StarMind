"""Vector similarity retrieval over repositories."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from core.retrieval.embeddings import EmbeddingService


# Common columns for vector search (shared between search.py and retrieval_service.py)
VECTOR_SEARCH_COMMON_COLUMNS = """
    id, github_id, name, description, stars, language,
    tags, category, ai_summary, has_ui, has_api, activity_level,
    last_updated, readme, url
"""

# Distance calculation expression
VECTOR_SEARCH_DISTANCE_EXPR = """
    (:metadata_weight * COALESCE(repo_metadata_embedding <=> :query_embedding, 2.0) +
     :readme_weight * COALESCE(readme_embedding <=> :query_embedding, 2.0)) AS distance
"""

# Common WHERE clause for vector search
VECTOR_SEARCH_WHERE_CLAUSE = """
    repo_metadata_embedding IS NOT NULL OR readme_embedding IS NOT NULL
"""


def build_weighted_vector_search_sql(
    *,
    extra_columns: str = "",
    include_distances: bool = False,
) -> str:
    """Build SQL for weighted vector similarity search.

    Args:
        extra_columns: Additional columns to select (comma-separated)
        include_distances: If True, include individual metadata_distance and readme_distance columns

    Returns:
        SQL query string with placeholders for query_embedding, metadata_weight, readme_weight, and limit
    """
    extra_cols = f", {extra_columns}" if extra_columns else ""
    distance_columns = ""
    if include_distances:
        distance_columns = """
            COALESCE(repo_metadata_embedding <=> :query_embedding, 2.0) AS metadata_distance,
            COALESCE(readme_embedding <=> :query_embedding, 2.0) AS readme_distance,
        """

    return f"""
        SELECT {VECTOR_SEARCH_COMMON_COLUMNS}{extra_cols},
               {distance_columns}
               {VECTOR_SEARCH_DISTANCE_EXPR}
        FROM repositories
        WHERE {VECTOR_SEARCH_WHERE_CLAUSE}
        ORDER BY distance
        LIMIT :limit
    """


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

        sql = text(build_weighted_vector_search_sql(include_distances=True))

        result = await db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "limit": top_k,
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
