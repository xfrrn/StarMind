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
        "readme": repo.readme or "",
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
