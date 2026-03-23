"""GitHub syncing capabilities (starred repos and READMEs)."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


def _get_github_api_url() -> str:
    return get_settings().github_api_url


class GitHubSyncer:
    def __init__(self, token: str):
        self.token = token
        self.github_api_url = _get_github_api_url()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.star+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _normalize_since(self, since: datetime | None) -> datetime | None:
        if since is None:
            return None
        if since.tzinfo is None:
            return since.replace(tzinfo=timezone.utc)
        return since.astimezone(timezone.utc)

    def _raise_for_github_errors(self, resp: httpx.Response):
        if resp.status_code == 401:
            logger.error("GitHub token is invalid or expired")
            raise Exception("GitHub token is invalid. Please check configuration.")
        if resp.status_code == 403:
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            reset_time = resp.headers.get("X-RateLimit-Reset", "?")
            error_msg = (
                f"GitHub API rate limit reached (403). "
                f"Remaining: {remaining}, Reset: {reset_time}"
            )
            logger.error(error_msg)
            raise Exception(error_msg)

    def _parse_starred_page(
        self,
        data: list[dict[str, Any]],
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        repos: list[dict[str, Any]] = []
        logger.info("Parsing page data, since=%s, data_len=%s", since, len(data) if isinstance(data, list) else 'N/A')
        for item in data:
            repo = item.get("repo", item) if isinstance(item, dict) else item
            starred_at_str = item.get("starred_at") if isinstance(item, dict) else None

            if since and starred_at_str:
                starred_at = datetime.fromisoformat(starred_at_str.replace("Z", "+00:00"))
                if starred_at <= since:
                    logger.info("Skipping repo %s, starred_at=%s <= since=%s",
                                repo.get("full_name", "?"), starred_at, since)
                    continue

            repos.append(
                {
                    "github_id": repo["id"],
                    "name": repo["full_name"],
                    "description": repo.get("description") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "",
                    "url": repo.get("html_url", ""),
                    "homepage": repo.get("homepage") or "",
                    "topics": repo.get("topics", []),
                    "updated_at": repo.get("updated_at"),
                    "starred_at": starred_at_str,
                }
            )
        logger.info("Parsed %s repos from page", len(repos))
        return repos

    async def fetch_starred_repos(
        self,
        since: datetime | None = None,
        concurrency: int = 4,
    ) -> list[dict[str, Any]]:
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found. Please configure it first.")

        per_page = 100
        normalized_since = self._normalize_since(since)
        worker_count = max(1, concurrency)

        next_page = 1
        stop_paging = False
        page_results: dict[int, list[dict[str, Any]]] = {}
        lock = asyncio.Lock()

        async with httpx.AsyncClient(timeout=30.0) as client:
            async def worker():
                nonlocal next_page, stop_paging
                while True:
                    async with lock:
                        if stop_paging:
                            return
                        page = next_page
                        next_page += 1

                    url = f"{self.github_api_url}/user/starred"
                    params = {"page": page, "per_page": per_page}
                    resp = await client.get(url, headers=self.headers, params=params)
                    self._raise_for_github_errors(resp)
                    resp.raise_for_status()
                    data = resp.json()

                    if not data:
                        async with lock:
                            stop_paging = True
                        return

                    page_results[page] = self._parse_starred_page(data, normalized_since)
                    logger.info("Fetched page %s, got %s repos", page, len(data))

                    if len(data) < per_page:
                        async with lock:
                            stop_paging = True
                        return

            await asyncio.gather(*(worker() for _ in range(worker_count)))

        logger.info("page_results: pages=%s, total_items=%s",
                     list(page_results.keys()),
                     sum(len(v) for v in page_results.values()))

        all_repos: list[dict[str, Any]] = []
        for page in sorted(page_results.keys()):
            all_repos.extend(page_results[page])

        logger.info("Total starred repos fetched: %s", len(all_repos))
        return all_repos

    async def _fetch_readme_with_client(
        self,
        client: httpx.AsyncClient,
        full_name: str,
    ) -> str:
        url = f"{self.github_api_url}/repos/{full_name}/readme"
        headers = {
            **self.headers,
            "Accept": "application/vnd.github.raw+json",
        }
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return ""
        self._raise_for_github_errors(resp)
        resp.raise_for_status()
        return resp.text

    async def fetch_readme(self, full_name: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                return await self._fetch_readme_with_client(client, full_name)
            except Exception as e:
                logger.warning("Failed to fetch README for %s: %s", full_name, e)
                return ""

    async def fetch_readmes(
        self,
        full_names: list[str],
        concurrency: int = 8,
    ) -> dict[str, str]:
        readmes: dict[str, str] = {}
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async with httpx.AsyncClient(timeout=30.0) as client:
            async def fetch_one(full_name: str):
                async with semaphore:
                    try:
                        readmes[full_name] = await self._fetch_readme_with_client(
                            client,
                            full_name,
                        )
                    except Exception as e:
                        logger.warning("Failed to fetch README for %s: %s", full_name, e)
                        readmes[full_name] = ""

            await asyncio.gather(*(fetch_one(name) for name in full_names))

        return readmes
