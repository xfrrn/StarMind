"""Response conversion helper functions."""

from models.repository import Repository


def to_repo_out(repo: Repository) -> dict:
    return {
        "id": str(repo.id),
        "name": repo.name,
        "description": repo.description or "",
        "stars": repo.stars,
        "language": repo.language or "",
        "tags": repo.tags or [],
        "category": repo.category or "",
        "aiReason": repo.ai_summary or "",
        "hasUI": repo.has_ui,
        "hasAPI": repo.has_api,
        "activityLevel": repo.activity_level or "Medium",
        "lastUpdated": repo.last_updated or "",
        "updatedAt": repo.updated_at.isoformat() + "Z" if repo.updated_at else None,
        "readme": repo.readme or "",
        "url": repo.url or "",
    }


def to_repository_response(repo: Repository) -> dict:
    """Convert Repository model to API response format."""
    return {
        "id": str(repo.id),
        "name": repo.name,
        "description": repo.description or "",
        "stars": repo.stars,
        "language": repo.language or "",
        "tags": repo.tags or [],
        "category": repo.category or "",
        "aiReason": repo.ai_summary or "",
        "hasUI": repo.has_ui if hasattr(repo, 'has_ui') else False,
        "hasAPI": repo.has_api if hasattr(repo, 'has_api') else False,
        "activityLevel": repo.activity_level if hasattr(repo, 'activity_level') else "Medium",
        "lastUpdated": repo.last_updated if hasattr(repo, 'last_updated') else "",
        "updatedAt": repo.updated_at.isoformat() + "Z" if repo.updated_at else None,
        "readme": (repo.readme or "")[:800],
        "url": repo.url or "",
    }


def to_chat_repository_response(repo: dict) -> dict:
    return {
        "id": repo["id"],
        "name": repo["name"],
        "description": repo["description"],
        "stars": repo["stars"],
        "language": repo["language"],
        "tags": repo.get("tags", []),
        "category": repo.get("category", ""),
        "aiReason": repo.get("ai_summary", ""),
        "hasUI": repo.get("has_ui", False),
        "hasAPI": repo.get("has_api", False),
        "activityLevel": repo.get("activity_level", "Medium"),
        "lastUpdated": repo.get("last_updated", ""),
        "updatedAt": repo.get("updated_at"),
        "readme": repo.get("readme", ""),
        "url": repo.get("url", ""),
    }


def to_sync_log_item(status: str, started_at, details: str) -> dict:
    log_time = started_at.strftime("%b %d, %I:%M %p") if started_at else ""
    return {
        "status": status,
        "time": log_time,
        "details": details or "",
    }
