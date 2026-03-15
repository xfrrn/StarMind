from __future__ import annotations

from services.chat.models import IntentResult, RepoQuery, RetrievalPlan
from services.chat.policies import ChatPolicy


class RetrievalPlanner:
    def __init__(self, policy: ChatPolicy):
        self.policy = policy

    def build_plan(self, intent: IntentResult, parsed_query: RepoQuery) -> RetrievalPlan:
        if not intent.needs_retrieval:
            return RetrievalPlan(limit=self.policy.max_retrieval_candidates)

        plan = RetrievalPlan(limit=self.policy.max_retrieval_candidates)
        if parsed_query.owner and parsed_query.repo_name:
            plan.use_exact_lookup = True

        has_structured_filters = bool(parsed_query.language or parsed_query.topics or parsed_query.filters)
        if has_structured_filters:
            plan.use_metadata_filter = True

        if parsed_query.keywords or parsed_query.capabilities:
            plan.use_keyword_search = True

        if intent.intent_type == "general_chat":
            plan.use_vector_search = self.policy.enable_vector_search_for_general_chat
        else:
            plan.use_vector_search = self.policy.enable_vector_search_for_search_intent

        if intent.intent_type in {"repo_analysis", "repo_compare", "repo_recommend"}:
            plan.use_keyword_search = True
            plan.use_vector_search = True

        if not (plan.use_exact_lookup or plan.use_metadata_filter or plan.use_keyword_search or plan.use_vector_search):
            plan.use_keyword_search = True
        return plan
