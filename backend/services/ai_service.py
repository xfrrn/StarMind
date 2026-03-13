"""AI analysis service.

Uses OpenAI API for repository analysis, embedding generation, and chat.
"""

import json
import logging
import hashlib
import re
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json_repair
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

_parse_failure_lock = asyncio.Lock()
_parse_failure_file = (
    Path(__file__).resolve().parents[1] / "logs" / "ai_analysis_parse_failures.jsonl"
)


async def _save_parse_failure(
    *,
    repo_name: str,
    stage: str,
    attempt: int,
    raw_content: str,
):
    cleaned = _clean_json_text(raw_content)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo": repo_name,
        "stage": stage,
        "attempt": attempt,
        "model": settings.openai_model,
        "raw_length": len(raw_content or ""),
        "cleaned_length": len(cleaned or ""),
        "raw_content": raw_content or "",
        "cleaned_content": cleaned or "",
    }
    _parse_failure_file.parent.mkdir(parents=True, exist_ok=True)
    async with _parse_failure_lock:
        with _parse_failure_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _truncate_by_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    tokens = text.split()
    if len(tokens) <= max_tokens:
        return text
    return " ".join(tokens[:max_tokens])


def clean_readme_for_embedding(raw_readme: str) -> str:
    text = raw_readme or ""
    if not text:
        return ""

    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^[#>\-\*\+\d\.\s]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()

    return _truncate_by_tokens(text, int(settings.embedding_readme_max_tokens))


def build_metadata_text(repo: dict[str, Any]) -> str:
    summary = _truncate_by_tokens(
        str(repo.get("ai_summary", "")),
        int(settings.embedding_summary_max_tokens),
    )
    parts = [
        str(repo.get("name", "")),
        str(repo.get("description", "")),
        " ".join(repo.get("topics", []) or []),
        " ".join(repo.get("tags", []) or []),
        summary,
    ]
    merged = " ".join(part for part in parts if part).strip()
    return _truncate_by_tokens(merged, int(settings.embedding_readme_max_tokens))


def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _clean_json_text(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _extract_json_object(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or start >= end:
        return ""
    return content[start:end + 1]


def _parse_analysis_json(content: str) -> dict[str, Any] | None:
    cleaned = _clean_json_text(content)
    if not cleaned:
        return None
    try:
        return json.loads(cleaned)
    except Exception:
        candidate = _extract_json_object(cleaned) or cleaned
        try:
            parsed = json_repair.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
            return None
        except Exception:
            return None


def _normalize_analysis_result(result: dict[str, Any]) -> dict[str, Any]:
    tags = result.get("tags")
    if not isinstance(tags, list):
        tags = []
    tags = [str(tag).strip() for tag in tags if str(tag).strip()][:5]

    category = str(result.get("category", "Other")).strip() or "Other"
    ai_summary = str(result.get("ai_summary", "")).strip()
    activity_level = str(result.get("activity_level", "Medium")).strip() or "Medium"

    return {
        "tags": tags,
        "category": category,
        "ai_summary": ai_summary,
        "has_ui": bool(result.get("has_ui", False)),
        "has_api": bool(result.get("has_api", False)),
        "activity_level": activity_level,
    }


async def _request_analysis_content(
    messages: list[dict[str, str]], enforce_json: bool
) -> str:
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 800,
    }
    if enforce_json:
        kwargs["response_format"] = {"type": "json_object"}
    response = await client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "").strip()


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

    bad_content = ""
    for attempt in range(2):
        try:
            messages = [{"role": "user", "content": prompt}]
            if attempt == 1:
                messages = [
                    {
                        "role": "system",
                        "content": "Return strict JSON only, with double quotes and no extra text.",
                    },
                    {"role": "user", "content": prompt},
                ]
            try:
                content = await _request_analysis_content(
                    messages=messages, enforce_json=True
                )
            except Exception:
                # Fallback for providers that do not support response_format.
                content = await _request_analysis_content(
                    messages=messages, enforce_json=False
                )
            result = _parse_analysis_json(content)
            if result is not None:
                return _normalize_analysis_result(result)
            bad_content = content
            await _save_parse_failure(
                repo_name=repo_data.get("name", "unknown"),
                stage="analysis_parse",
                attempt=attempt + 1,
                raw_content=content,
            )
            logger.warning(
                f"AI analysis JSON parse failed for {repo_data.get('name')}, attempt {attempt + 1}"
            )
        except Exception as e:
            logger.error(
                f"AI analysis failed for {repo_data.get('name')}, attempt {attempt + 1}: {e}"
            )

    if bad_content:
        try:
            repair_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a JSON formatter. Convert input text into valid JSON only. "
                        "Do not add explanations."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Fix this output into valid JSON with fields: "
                        "tags, category, ai_summary, has_ui, has_api, activity_level.\n\n"
                        f"{bad_content}"
                    ),
                },
            ]
            repaired = await _request_analysis_content(
                messages=repair_messages, enforce_json=True
            )
            parsed_repaired = _parse_analysis_json(repaired)
            if parsed_repaired is not None:
                return _normalize_analysis_result(parsed_repaired)
            await _save_parse_failure(
                repo_name=repo_data.get("name", "unknown"),
                stage="repair_parse",
                attempt=1,
                raw_content=repaired,
            )
        except Exception as e:
            logger.warning(
                f"AI analysis JSON repair failed for {repo_data.get('name')}: {e}"
            )

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
            input=text_content[:8000],
        )
        embedding = response.data[0].embedding
        expected_dim = int(settings.embedding_dimension)
        if len(embedding) != expected_dim:
            logger.error(
                "Embedding dimension mismatch: expected %s, got %s (model=%s).",
                expected_dim,
                len(embedding),
                settings.openai_embedding_model,
            )
            return [0.0] * expected_dim
        return embedding
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return [0.0] * int(settings.embedding_dimension)


def _build_embedding_text(repo: dict[str, Any]) -> str:
    """Legacy single-embedding input (kept for compatibility)."""
    metadata_text = build_metadata_text(repo)
    readme_text = clean_readme_for_embedding(repo.get("readme", ""))
    return " ".join(part for part in [metadata_text, readme_text] if part)


async def generate_repo_embedding(repo: dict[str, Any]) -> list[float]:
    """Generate embedding for a repository's combined text."""
    text_content = _build_embedding_text(repo)
    return await generate_embedding(text_content)


async def generate_dual_embeddings(repo: dict[str, Any]) -> dict[str, Any]:
    metadata_text = build_metadata_text(repo)
    readme_text = clean_readme_for_embedding(repo.get("readme", ""))

    repo_metadata_embedding = None
    readme_embedding = None
    if metadata_text:
        repo_metadata_embedding = await generate_embedding(metadata_text)
    if readme_text:
        readme_embedding = await generate_embedding(readme_text)

    return {
        "metadata_text": metadata_text,
        "readme_text": readme_text,
        "metadata_hash": _hash_text(metadata_text),
        "readme_hash": _hash_text(readme_text),
        "repo_metadata_embedding": repo_metadata_embedding,
        "readme_embedding": readme_embedding,
    }


async def semantic_search(
    db: AsyncSession, query: str, top_k: int = 5
) -> list[dict[str, Any]]:
    """Search repositories by weighted dual-embedding similarity."""
    query_embedding = await generate_embedding(query)
    metadata_weight = float(settings.embedding_metadata_weight)
    readme_weight = float(settings.embedding_readme_weight)

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


async def chat_with_repos(query: str, repos: list[dict[str, Any]]) -> str:
    """Generate a natural language answer based on the query and matched repos."""
    if not repos:
        repos_context = "No relevant repositories were found."
    else:
        parts = []
        for i, repo in enumerate(repos, 1):
            parts.append(
                f"{i}. **{repo['name']}** ({repo['stars']:,} stars)\n"
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
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        return "I'm sorry, I encountered an error while generating a response. Please try again later."
