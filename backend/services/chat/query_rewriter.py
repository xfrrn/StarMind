from __future__ import annotations

from services.chat.models import RepoQuery


class QueryRewriter:
    """Lightweight query rewrite hook for future expansion."""

    def rewrite(self, parsed_query: RepoQuery) -> list[str]:
        variants: list[str] = []
        base = parsed_query.raw_query.strip()
        if base:
            variants.append(base)
        if parsed_query.keywords:
            variants.append(" ".join(parsed_query.keywords[:8]))
        if parsed_query.language and parsed_query.capabilities:
            variants.append(f"{parsed_query.language} {' '.join(parsed_query.capabilities)}")
        # Keep deterministic and short; future versions can use LLM rewrite.
        return list(dict.fromkeys(v for v in variants if v))
