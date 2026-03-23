from utils.response_utils import to_chat_repository_response, to_repository_response

from models.repository import Repository


def to_repo_response(repo: Repository) -> dict:
    """Convert Repository model to API response format for repo chat."""
    return {
        "id": str(repo.id),
        "name": repo.full_name or repo.name,
        "description": repo.description or "",
        "stars": repo.stars,
        "language": repo.language or "",
        "tags": repo.tags or [],
        "category": repo.category or "",
        "aiReason": repo.analysis_summary or "",
        "hasUI": repo.has_ui,
        "hasAPI": repo.has_api,
        "activityLevel": repo.activity_level or "Medium",
        "lastUpdated": repo.last_updated or "",
        "readme": (repo.cleaned_readme_snippet or "")[:800],
        "url": repo.url or "",
    }


__all__ = ["to_chat_repository_response", "to_repository_response", "to_repo_response"]
