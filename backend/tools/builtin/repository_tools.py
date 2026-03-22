"""Repository-related tools for LLM function calling."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from models.repository import Repository
from tools.tool_manager import tool

logger = logging.getLogger(__name__)


@tool("get_repository_detail", "Get detailed information about a specific repository by full name (e.g., 'owner/repo')")
async def get_repository_detail(full_name: str, db: AsyncSession) -> str:
    """Get detailed information about a repository.

    Args:
        full_name: Repository full name in format 'owner/repo'
        db: Database session

    Returns:
        JSON string with repository details
    """
    result = await db.execute(
        select(Repository).where(Repository.full_name == full_name).limit(1)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        return json.dumps({"error": f"Repository '{full_name}' not found"}, ensure_ascii=False)

    return json.dumps({
        "name": repo.full_name,
        "description": repo.description,
        "stars": repo.stars,
        "language": repo.language,
        "topics": repo.topics or [],
        "tags": repo.tags or [],
        "category": repo.category,
        "ai_summary": repo.analysis_summary,
        "has_ui": repo.has_ui,
        "has_api": repo.has_api,
        "activity_level": repo.activity_level,
        "last_updated": repo.last_updated,
        "url": repo.url,
        "readme_preview": (repo.cleaned_readme_snippet or "")[:1500],
    }, ensure_ascii=False, default=str)


@tool("list_repositories_by_language", "List repositories filtered by programming language")
async def list_repositories_by_language(language: str, limit: int, db: AsyncSession) -> str:
    """List repositories by programming language.

    Args:
        language: Programming language to filter by (e.g., 'Python', 'TypeScript')
        limit: Maximum number of results (default 10)
        db: Database session

    Returns:
        JSON string with list of repositories
    """
    limit = min(limit, 20)  # Cap at 20

    result = await db.execute(
        select(Repository)
        .where(Repository.language == language)
        .order_by(Repository.stars.desc())
        .limit(limit)
    )
    repos = result.scalars().all()

    return json.dumps([{
        "name": r.full_name,
        "description": r.description,
        "stars": r.stars,
        "language": r.language,
        "category": r.category,
    } for r in repos], ensure_ascii=False, default=str)


@tool("get_repository_statistics", "Get statistics about the user's starred repositories")
async def get_repository_statistics(db: AsyncSession) -> str:
    """Get statistics about starred repositories.

    Args:
        db: Database session

    Returns:
        JSON string with statistics
    """
    # Total count
    total_result = await db.execute(select(func.count(Repository.id)))
    total = total_result.scalar() or 0

    # Count by language
    lang_result = await db.execute(
        select(Repository.language, func.count(Repository.id).label("count"))
        .where(Repository.language.isnot(None))
        .group_by(Repository.language)
        .order_by(func.count(Repository.id).desc())
        .limit(10)
    )
    languages = [{"language": row.language, "count": row.count} for row in lang_result.all()]

    # Count by category
    cat_result = await db.execute(
        select(Repository.category, func.count(Repository.id).label("count"))
        .where(Repository.category.isnot(None), Repository.category != "")
        .group_by(Repository.category)
        .order_by(func.count(Repository.id).desc())
        .limit(10)
    )
    categories = [{"category": row.category, "count": row.count} for row in cat_result.all()]

    # UI/API stats
    ui_result = await db.execute(
        select(func.count(Repository.id)).where(Repository.has_ui == True)  # noqa: E712
    )
    ui_count = ui_result.scalar() or 0

    api_result = await db.execute(
        select(func.count(Repository.id)).where(Repository.has_api == True)  # noqa: E712
    )
    api_count = api_result.scalar() or 0

    return json.dumps({
        "total_repositories": total,
        "by_language": languages,
        "by_category": categories,
        "with_ui": ui_count,
        "with_api": api_count,
    }, ensure_ascii=False)


@tool("search_repositories_by_tags", "Search repositories by tags")
async def search_repositories_by_tags(tags: str, limit: int, db: AsyncSession) -> str:
    """Search repositories by tags.

    Args:
        tags: Comma-separated list of tags to search for
        limit: Maximum number of results (default 5)
        db: Database session

    Returns:
        JSON string with matching repositories
    """
    limit = min(limit, 20)
    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]

    if not tag_list:
        return json.dumps([], ensure_ascii=False)

    # Use PostgreSQL array overlap for tag matching
    result = await db.execute(
        select(Repository)
        .where(Repository.tags.bool_op("&&")(tag_list))  # Array overlap
        .order_by(Repository.stars.desc())
        .limit(limit)
    )
    repos = result.scalars().all()

    return json.dumps([{
        "name": r.full_name,
        "description": r.description,
        "stars": r.stars,
        "tags": r.tags,
        "matched_tags": list(set(r.tags or []) & set(tag_list)),
    } for r in repos], ensure_ascii=False, default=str)


def get_tools() -> dict[str, callable]:
    """Get all repository tools for registration."""
    return {
        "get_repository_detail": get_repository_detail,
        "list_repositories_by_language": list_repositories_by_language,
        "get_repository_statistics": get_repository_statistics,
        "search_repositories_by_tags": search_repositories_by_tags,
    }
