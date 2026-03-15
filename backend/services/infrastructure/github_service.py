"""Infrastructure adapter for GitHub sync capability."""

from core.github import GitHubSyncer

GitHubService = GitHubSyncer

__all__ = ["GitHubService"]
