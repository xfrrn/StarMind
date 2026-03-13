"""Repository analysis capability backed by LLM."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import Settings
from core.llm.client import LLMClient
from core.llm.prompts import ANALYZE_REPOSITORY_PROMPT
from utils.json_utils import parse_json_object_with_repair

logger = logging.getLogger(__name__)


class RepositoryAnalyzer:
    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client
        self._parse_failure_lock = asyncio.Lock()
        self._parse_failure_file = (
            Path(__file__).resolve().parents[2] / "logs" / "ai_analysis_parse_failures.jsonl"
        )

    async def _save_parse_failure(
        self,
        *,
        repo_name: str,
        stage: str,
        attempt: int,
        raw_content: str,
    ) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repo": repo_name,
            "stage": stage,
            "attempt": attempt,
            "model": self.settings.openai_model,
            "raw_length": len(raw_content or ""),
            "raw_content": raw_content or "",
        }
        self._parse_failure_file.parent.mkdir(parents=True, exist_ok=True)
        async with self._parse_failure_lock:
            with self._parse_failure_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @staticmethod
    def normalize_repository_analysis(result: dict[str, Any]) -> dict[str, Any]:
        tags = result.get("tags")
        if not isinstance(tags, list):
            tags = []
        tags = [str(tag).strip() for tag in tags if str(tag).strip()][:5]

        category = str(result.get("category", "Other")).strip() or "Other"
        ai_summary = str(result.get("ai_summary", "")).strip()
        activity_level = str(result.get("activity_level", "Medium")).strip() or "Medium"

        return {
            "tags": tags,
            "category": category,
            "ai_summary": ai_summary,
            "has_ui": bool(result.get("has_ui", False)),
            "has_api": bool(result.get("has_api", False)),
            "activity_level": activity_level,
        }

    async def analyze_repository(self, repo_data: dict[str, Any]) -> dict[str, Any]:
        readme_excerpt = (repo_data.get("readme") or "")[:3000]

        prompt = ANALYZE_REPOSITORY_PROMPT.format(
            name=repo_data.get("name", ""),
            description=repo_data.get("description", ""),
            language=repo_data.get("language", ""),
            stars=repo_data.get("stars", 0),
            topics=json.dumps(repo_data.get("topics", [])),
            updated_at=repo_data.get("updated_at", ""),
            readme_excerpt=readme_excerpt,
        )

        bad_content = ""
        for attempt in range(2):
            try:
                messages = [{"role": "user", "content": prompt}]
                if attempt == 1:
                    messages = [
                        {
                            "role": "system",
                            "content": "Return strict JSON only, with double quotes and no extra text.",
                        },
                        {"role": "user", "content": prompt},
                    ]

                try:
                    content = await self.llm_client.create_chat_completion(
                        messages=messages,
                        temperature=0.2,
                        max_tokens=800,
                        enforce_json=True,
                    )
                except Exception:
                    content = await self.llm_client.create_chat_completion(
                        messages=messages,
                        temperature=0.2,
                        max_tokens=800,
                        enforce_json=False,
                    )

                result = parse_json_object_with_repair(content)
                if result is not None:
                    return self.normalize_repository_analysis(result)

                bad_content = content
                await self._save_parse_failure(
                    repo_name=repo_data.get("name", "unknown"),
                    stage="analysis_parse",
                    attempt=attempt + 1,
                    raw_content=content,
                )
                logger.warning(
                    "AI analysis JSON parse failed for %s, attempt %s",
                    repo_data.get("name"),
                    attempt + 1,
                )
            except Exception as e:
                logger.error(
                    "AI analysis failed for %s, attempt %s: %s",
                    repo_data.get("name"),
                    attempt + 1,
                    e,
                )

        if bad_content:
            try:
                repair_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a JSON formatter. Convert input text into valid JSON only. "
                            "Do not add explanations."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Fix this output into valid JSON with fields: "
                            "tags, category, ai_summary, has_ui, has_api, activity_level.\n\n"
                            f"{bad_content}"
                        ),
                    },
                ]
                repaired = await self.llm_client.create_chat_completion(
                    messages=repair_messages,
                    temperature=0.2,
                    max_tokens=800,
                    enforce_json=True,
                )
                repaired_result = parse_json_object_with_repair(repaired)
                if repaired_result is not None:
                    return self.normalize_repository_analysis(repaired_result)
                await self._save_parse_failure(
                    repo_name=repo_data.get("name", "unknown"),
                    stage="repair_parse",
                    attempt=1,
                    raw_content=repaired,
                )
            except Exception as e:
                logger.warning(
                    "AI analysis JSON repair failed for %s: %s",
                    repo_data.get("name"),
                    e,
                )

        return {
            "tags": repo_data.get("topics", [])[:5],
            "category": "Other",
            "ai_summary": repo_data.get("description", ""),
            "has_ui": False,
            "has_api": False,
            "activity_level": "Medium",
        }
