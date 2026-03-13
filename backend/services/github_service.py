"""Backward-compatible GitHub service facade."""

from core.github import GitHubSyncer

GitHubService = GitHubSyncer

__all__ = ["GitHubService"]
