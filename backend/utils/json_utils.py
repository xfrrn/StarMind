"""JSON parsing utilities with repair fallback."""

import json
from typing import Any

import json_repair


def clean_fenced_json_text(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def extract_json_object(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or start >= end:
        return ""
    return content[start : end + 1]


def parse_json_object_with_repair(content: str) -> dict[str, Any] | None:
    cleaned = clean_fenced_json_text(content)
    if not cleaned:
        return None
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        candidate = extract_json_object(cleaned) or cleaned
        try:
            parsed = json_repair.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
