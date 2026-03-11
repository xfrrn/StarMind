"""AI analysis service.

Uses OpenAI API for repository analysis, embedding generation, and chat.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

ANALYZE_PROMPT = """\
You are an expert software analyst. Analyze the following GitHub repository and return a JSON object with these fields:

- "tags": list of 3-5 concise tags describing the project (e.g. ["AI", "LLM", "RAG", "Framework"])
- "category": one of "Frontend", "Backend", "AI / ML", "DevOps", "Mobile", "Database", "Security", "Tooling", "Other"
- "ai_summary": a 2-3 sentence summary of what the project does and why it's useful (in the same language as the description, or English if unclear)
- "has_ui": boolean, whether the project provides a user interface
- "has_api": boolean, whether the project provides an API or SDK
- "activity_level": one of "High", "Medium", "Low" based on the update recency and star count

Repository info:
- Name: {name}
- Description: {description}
- Language: {language}
- Stars: {stars}
- Topics: {topics}
- Last updated: {updated_at}
- README (excerpt): {readme_excerpt}

Return ONLY valid JSON, no markdown fences or extra text.
"""

CHAT_PROMPT = """\
You are StarMind, an AI assistant that helps users find relevant projects from their GitHub starred repositories.

The user asked: "{query}"

Here are the most relevant repositories found from their starred list:

{repos_context}

Based on these repositories, provide a helpful, concise answer to the user's question. Explain why each recommended repository is relevant. If none of the repositories match well, say so honestly.

Respond in the same language as the user's query. Use markdown formatting for readability.
"""


async def analyze_repository(repo_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze a repository using LLM and return structured metadata."""
    readme_excerpt = (repo_data.get("readme") or "")[:3000]

    prompt = ANALYZE_PROMPT.format(
        name=repo_data.get("name", ""),
        description=repo_data.get("description", ""),
        language=repo_data.get("language", ""),
        stars=repo_data.get("stars", 0),
        topics=json.dumps(repo_data.get("topics", [])),
        updated_at=repo_data.get("updated_at", ""),
        readme_excerpt=readme_excerpt,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        content = response.choices[0].message.content.strip()
        # 清理可能的 markdown 代码块包裹
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        result = json.loads(content)
        return result
    except Exception as e:
        logger.error(f"AI analysis failed for {repo_data.get('name')}: {e}")
        return {
            "tags": repo_data.get("topics", [])[:5],
            "category": "Other",
            "ai_summary": repo_data.get("description", ""),
            "has_ui": False,
            "has_api": False,
            "activity_level": "Medium",
        }


async def generate_embedding(text_content: str) -> list[float]:
    """Generate an embedding vector for the given text using OpenAI Embedding API."""
    try:
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text_content[:8000],  # API limit
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return [0.0] * 1536  # fallback zero vector


def _build_embedding_text(repo: dict[str, Any]) -> str:
    """Build a text representation of a repository for embedding."""
    parts = [
        repo.get("name", ""),
        repo.get("description", ""),
        repo.get("language", ""),
        " ".join(repo.get("tags", [])),
        repo.get("category", ""),
        repo.get("ai_summary", ""),
        (repo.get("readme") or "")[:2000],
    ]
    return " ".join(filter(None, parts))


async def generate_repo_embedding(repo: dict[str, Any]) -> list[float]:
    """Generate embedding for a repository's combined text."""
    text_content = _build_embedding_text(repo)
    return await generate_embedding(text_content)


async def semantic_search(
    db: AsyncSession, query: str, top_k: int = 5
) -> list[dict[str, Any]]:
    """Search repositories by semantic similarity using pgvector."""
    query_embedding = await generate_embedding(query)

    # Use pgvector's <=> operator for cosine distance
    sql = text("""
        SELECT id, github_id, name, description, stars, language,
               tags, category, ai_summary, has_ui, has_api,
               activity_level, last_updated, readme, url, homepage,
               embedding <=> :query_embedding AS distance
        FROM repositories
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :query_embedding
        LIMIT :top_k
    """)

    result = await db.execute(
        sql,
        {"query_embedding": str(query_embedding), "top_k": top_k},
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


async def chat_with_repos(query: str, repos: list[dict[str, Any]]) -> str:
    """Generate a natural language answer based on the query and matched repos."""
    if not repos:
        repos_context = "No relevant repositories were found."
    else:
        parts = []
        for i, repo in enumerate(repos, 1):
            parts.append(
                f"{i}. **{repo['name']}** (⭐ {repo['stars']:,})\n"
                f"   Language: {repo['language']}\n"
                f"   Description: {repo['description']}\n"
                f"   AI Summary: {repo.get('ai_summary', 'N/A')}\n"
                f"   Tags: {', '.join(repo.get('tags', []))}\n"
            )
        repos_context = "\n".join(parts)

    prompt = CHAT_PROMPT.format(query=query, repos_context=repos_context)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        return "I'm sorry, I encountered an error while generating a response. Please try again later."
