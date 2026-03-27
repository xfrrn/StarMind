"""Archive service - download and manage repository snapshots."""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.repository import Repository

logger = logging.getLogger(__name__)


class ArchiveService:
    """Service for archiving repository snapshots."""

    def __init__(self):
        self.settings = get_settings()
        self.github_token = self.settings.github_token
        self.github_api_url = self.settings.github_api_url
        # Archive storage path (relative to backend directory)
        self.archive_base_path = Path(__file__).parent.parent.parent / "data" / "archives"

    def _get_archive_path(self, repo_id: int) -> Path:
        """Get the archive file path for a repository."""
        return self.archive_base_path / str(repo_id) / "archive.zip"

    def _ensure_archive_dir(self, repo_id: int) -> Path:
        """Ensure archive directory exists and return path."""
        archive_dir = self.archive_base_path / str(repo_id)
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir

    async def _fetch_archive_from_github(self, full_name: str) -> bytes:
        """Download repository archive from GitHub."""
        url = f"{self.github_api_url}/repos/{full_name}/zipball/HEAD"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            if resp.status_code == 404:
                raise ValueError(f"Repository not found: {full_name}")
            if resp.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded")
            resp.raise_for_status()
            return resp.content

    def _compute_sha256(self, data: bytes) -> str:
        """Compute SHA256 hash of data."""
        return hashlib.sha256(data).hexdigest()

    async def create_archive(self, db: AsyncSession, repo_id: int) -> dict:
        """Create or update archive for a repository."""
        # Get repository
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        repo = result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository not found: {repo_id}")

        # Download from GitHub
        logger.info(f"Downloading archive for {repo.name}")
        archive_data = await self._fetch_archive_from_github(repo.name)

        # Compute hash
        archive_sha = self._compute_sha256(archive_data)
        archive_size = len(archive_data)

        # Save to file system
        archive_path = self._get_archive_path(repo_id)
        self._ensure_archive_dir(repo_id)
        archive_path.write_bytes(archive_data)

        # Update database
        relative_path = f"{repo_id}/archive.zip"
        repo.is_archived = True
        repo.archive_path = relative_path
        repo.archive_size = archive_size
        repo.archive_sha = archive_sha
        repo.archived_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Archive created for {repo.name}: {archive_size} bytes")

        return {
            "is_archived": True,
            "archive_path": relative_path,
            "archive_size": archive_size,
            "archive_sha": archive_sha,
            "archived_at": repo.archived_at.isoformat() + "Z",
        }

    async def get_archive_status(self, db: AsyncSession, repo_id: int) -> dict:
        """Get archive status for a repository."""
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        repo = result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository not found: {repo_id}")

        return {
            "is_archived": repo.is_archived or False,
            "archive_path": repo.archive_path or "",
            "archive_size": repo.archive_size or 0,
            "archive_sha": repo.archive_sha or "",
            "archived_at": repo.archived_at.isoformat() + "Z" if repo.archived_at else None,
        }

    async def delete_archive(self, db: AsyncSession, repo_id: int) -> None:
        """Delete archive for a repository."""
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        repo = result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository not found: {repo_id}")

        # Delete file
        archive_path = self._get_archive_path(repo_id)
        if archive_path.exists():
            archive_path.unlink()
            # Try to remove directory if empty
            try:
                archive_path.parent.rmdir()
            except OSError:
                pass

        # Update database
        repo.is_archived = False
        repo.archive_path = ""
        repo.archive_size = 0
        repo.archive_sha = ""
        repo.archived_at = None

        await db.commit()
        logger.info(f"Archive deleted for repo {repo_id}")

    def get_archive_file_path(self, repo_id: int) -> Path | None:
        """Get the file path for downloading archive."""
        archive_path = self._get_archive_path(repo_id)
        if archive_path.exists():
            return archive_path
        return None

    async def list_archived_repos(self, db: AsyncSession) -> list[dict]:
        """List all archived repositories."""
        result = await db.execute(
            select(Repository).where(Repository.is_archived == True)
        )
        repos = result.scalars().all()

        return [
            {
                "id": repo.id,
                "name": repo.name,
                "description": repo.description or "",
                "language": repo.language or "",
                "stars": repo.stars,
                "archive_size": repo.archive_size or 0,
                "archived_at": repo.archived_at.isoformat() + "Z" if repo.archived_at else None,
            }
            for repo in repos
        ]
