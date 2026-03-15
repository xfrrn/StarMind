"""Token truncation wrapper."""

from utils.text import truncate_by_tokens


def apply_token_limit(text: str, max_tokens: int) -> str:
    return truncate_by_tokens(text or "", max_tokens)
