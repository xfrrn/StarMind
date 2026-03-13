"""GitHub API integration service.

Handles fetching starred repositories, READMEs, and rate-limit management.
"""

import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubService:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.star+json",  # 获取 starred_at 字段
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def fetch_starred_repos(
        self, since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all starred repositories, with optional incremental sync via `since`."""
        all_repos: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        if not self.token:
            raise ValueError("未找到 GITHUB_TOKEN，请先在环境配置中配置")

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                url = f"{GITHUB_API}/user/starred"
                params = {"page": page, "per_page": per_page}

                resp = await client.get(url, headers=self.headers, params=params)

                if resp.status_code == 401:
                    logger.error("GitHub Token 无效或已过期")
                    raise Exception("GitHub Token 无效，请检查配置")
                if resp.status_code == 403:
                    remaining = resp.headers.get("X-RateLimit-Remaining", "?")
                    reset_time = resp.headers.get("X-RateLimit-Reset", "?")
                    error_msg = f"GitHub API 请求受限或触发限流 (403). Remaining: {remaining}, Reset: {reset_time}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                for item in data:
                    # Depending on Accept header, might be wrapped in 'repo'
                    repo = item.get("repo", item) if isinstance(item, dict) else item
                    starred_at_str = item.get("starred_at") if isinstance(item, dict) else None

                    # 增量同步：跳过 starred_at 早于 since 的仓库
                    if since and starred_at_str:
                        starred_at = datetime.fromisoformat(
                            starred_at_str.replace("Z", "+00:00")
                        )
                        if starred_at <= since:
                            continue

                    all_repos.append(
                        {
                            "github_id": repo["id"],
                            "name": repo["full_name"],
                            "description": repo.get("description") or "",
                            "stars": repo.get("stargazers_count", 0),
                            "language": repo.get("language") or "",
                            "url": repo.get("html_url", ""),
                            "homepage": repo.get("homepage") or "",
                            "topics": repo.get("topics", []),
                            "updated_at": repo.get("updated_at"), # Use updated_at explicitly
                            "starred_at": starred_at_str,
                        }
                    )

                logger.info(f"Fetched page {page}, got {len(data)} repos")
                
                if len(data) < per_page:
                    break
                    
                page += 1

        logger.info(f"Total starred repos fetched: {len(all_repos)}")
        return all_repos

    async def fetch_readme(self, full_name: str) -> str:
        """Fetch README content for a repository."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{GITHUB_API}/repos/{full_name}/readme"
            headers = {
                **self.headers,
                "Accept": "application/vnd.github.raw+json",
            }

            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    return ""
                resp.raise_for_status()
                content = resp.text
                # 截断过长的 README（保留前 8000 字符）
                return content
            except Exception as e:
                logger.warning(f"Failed to fetch README for {full_name}: {e}")
                return ""
