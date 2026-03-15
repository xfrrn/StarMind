from dataclasses import dataclass


@dataclass(frozen=True)
class ChatPolicy:
    max_retrieval_candidates: int = 20
    max_reranked_candidates: int = 8
    max_context_repos: int = 5
    max_readme_snippet_chars: int = 500
    enable_query_rewrite: bool = True
    enable_vector_search_for_search_intent: bool = True
    enable_vector_search_for_general_chat: bool = False
    min_confident_intent: float = 0.55
    response_timeout_seconds: float = 8.0
    embedding_timeout_seconds: float = 5.0
    query_embedding_cache_ttl_seconds: int = 300
    query_embedding_cache_size: int = 512
    max_prompt_context_tokens: int = 1400
