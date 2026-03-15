"""Backward-compatible import shim for GitHubService."""

from services.infrastructure.github_service import GitHubService

__all__ = ["GitHubService"]
