from __future__ import annotations

from services.chat.models import RankedRepoCandidate, RepoCandidate, RepoQuery


class Reranker:
    def rank(self, candidates: list[RepoCandidate], parsed_query: RepoQuery, top_k: int) -> list[RankedRepoCandidate]:
        ranked: list[RankedRepoCandidate] = []
        for candidate in candidates:
            breakdown: dict[str, float] = {}
            score = 0.0

            if "exact" in candidate.matched_by:
                breakdown["exact"] = 3.0
                score += 3.0
            if "metadata" in candidate.matched_by:
                breakdown["metadata"] = 1.4
                score += 1.4
            if "keyword" in candidate.matched_by:
                breakdown["keyword"] = 1.2
                score += 1.2
            if "vector" in candidate.matched_by:
                vector_score = candidate.score or 0.0
                breakdown["vector"] = round(vector_score * 1.3, 4)
                score += vector_score * 1.3

            if parsed_query.language and candidate.language and parsed_query.language == candidate.language:
                breakdown["language_match"] = 1.0
                score += 1.0

            topic_hits = len(set(parsed_query.topics) & set(candidate.topics))
            if topic_hits:
                breakdown["topic_match"] = 0.5 * topic_hits
                score += 0.5 * topic_hits

            keyword_hits = 0
            corpus = " ".join(
                [
                    candidate.full_name.lower(),
                    (candidate.description or "").lower(),
                    (candidate.analysis_summary or "").lower(),
                ]
            )
            for kw in (parsed_query.keywords + parsed_query.capabilities)[:15]:
                if kw.lower() in corpus:
                    keyword_hits += 1
            if keyword_hits:
                breakdown["keyword_hits"] = min(1.8, keyword_hits * 0.25)
                score += min(1.8, keyword_hits * 0.25)

            if candidate.stars > 1000:
                breakdown["quality_hint"] = 0.2
                score += 0.2

            why_parts = [f"{k}:{v:.2f}" for k, v in sorted(breakdown.items())]
            ranked.append(
                RankedRepoCandidate(
                    **candidate.__dict__,
                    final_score=score,
                    score_breakdown=breakdown,
                    why_relevant="; ".join(why_parts),
                )
            )

        ranked.sort(key=lambda item: item.final_score, reverse=True)
        return ranked[:top_k]
