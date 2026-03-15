from __future__ import annotations

import re

from services.chat.models import RepoQuery
from services.chat.types import IntentType


LANGUAGE_KEYWORDS = {
    "python": "Python",
    "go": "Go",
    "golang": "Go",
    "java": "Java",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "rust": "Rust",
    "c++": "C++",
    "c#": "C#",
}

CAPABILITY_KEYWORDS = ("api", "sdk", "cli", "ui", "web", "desktop", "agent", "rag", "ocr")


class QueryParser:
    def parse(self, message: str, intent_type: IntentType) -> RepoQuery:
        text = (message or "").strip()
        low = text.lower()
        query = RepoQuery(raw_query=text, intent_type=intent_type)

        full_name_match = re.search(r"\b([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\b", text)
        if full_name_match:
            query.owner = full_name_match.group(1)
            query.repo_name = full_name_match.group(2)
            query.filters["full_name"] = f"{query.owner}/{query.repo_name}"
            query.keywords.extend([query.owner.lower(), query.repo_name.lower()])

        for raw, normalized in LANGUAGE_KEYWORDS.items():
            if re.search(rf"\b{re.escape(raw)}\b", low):
                query.language = normalized
                query.filters["language"] = normalized
                break

        if any(k in low for k in ("star", "收藏", "starred", "我的仓库")):
            query.scope = "starred"
            query.filters["scope"] = "starred"

        if intent_type == "repo_compare":
            compare_targets = re.findall(r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b", text)
            query.compare_targets = compare_targets[:6]

        topic_matches = re.findall(r"#([A-Za-z0-9_-]+)", text)
        if topic_matches:
            query.topics.extend(topic_matches)

        query.capabilities = sorted({kw for kw in CAPABILITY_KEYWORDS if kw in low})

        cleaned = re.sub(r"[^\w\s/#-]", " ", low)
        tokens = [tok for tok in cleaned.split() if len(tok) > 2]
        stop_words = {"find", "search", "repo", "repository", "project", "help", "please", "帮我", "项目"}
        query.keywords.extend(tok for tok in tokens if tok not in stop_words)
        query.keywords = list(dict.fromkeys(query.keywords))[:20]
        return query
