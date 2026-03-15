from __future__ import annotations

import re

from services.chat.models import IntentResult


class IntentRouter:
    def route(self, message: str) -> IntentResult:
        text = (message or "").strip()
        low = text.lower()
        if not text:
            return IntentResult(intent_type="unknown", confidence=0.0, needs_retrieval=False, reason="empty")

        if self._is_repo_compare(text, low):
            return IntentResult("repo_compare", 0.9, True, "comparison keywords")
        if self._is_repo_analysis(text, low):
            return IntentResult("repo_analysis", 0.87, True, "analysis keywords")
        if self._is_repo_recommend(text, low):
            return IntentResult("repo_recommend", 0.84, True, "recommendation keywords")
        if self._is_repo_search(text, low):
            return IntentResult("repo_search", 0.82, True, "search keywords")
        if self._is_general_chat(text, low):
            return IntentResult("general_chat", 0.75, False, "general question")
        return IntentResult("unknown", 0.4, False, "fallback")

    @staticmethod
    def _is_repo_compare(text: str, low: str) -> bool:
        return any(k in low for k in ("compare", "vs", "对比", "比较")) or low.count("/") >= 2

    @staticmethod
    def _is_repo_analysis(text: str, low: str) -> bool:
        return bool(re.search(r"\b(analy[sz]e|review|评估|分析)\b", low)) or bool(
            re.search(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text)
        )

    @staticmethod
    def _is_repo_recommend(text: str, low: str) -> bool:
        return any(k in low for k in ("recommend", "推荐", "suggest", "适合", "最好"))

    @staticmethod
    def _is_repo_search(text: str, low: str) -> bool:
        repo_terms = ("repo", "repository", "仓库", "项目", "查找", "搜索", "star", "收藏")
        return any(k in low for k in repo_terms)

    @staticmethod
    def _is_general_chat(text: str, low: str) -> bool:
        general_terms = ("what is", "解释", "是什么", "hello", "hi", "你好", "怎么")
        return any(k in low for k in general_terms)
