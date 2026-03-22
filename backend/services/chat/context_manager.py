"""Context management for chat conversations.

Handles token estimation, context compression, and message history management.
Borrowed from SurveyAgent's RAG design patterns.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CompressionStrategy(str, Enum):
    """Strategies for compressing conversation context."""

    TRUNCATE = "truncate"      # Remove oldest messages
    HALVING = "halving"        # Keep recent 50%
    SUMMARIZE = "summarize"    # Use LLM to summarize (not implemented yet)


@dataclass
class ContextConfig:
    """Configuration for context management."""

    max_tokens: int = 128000           # Maximum context tokens (for gpt-4o)
    compression_threshold: float = 0.85  # Trigger compression at 85% capacity
    keep_recent_messages: int = 6       # Always keep last N message pairs
    strategy: CompressionStrategy = CompressionStrategy.TRUNCATE


class ContextManager:
    """Manages conversation context with token estimation and compression."""

    # Token estimation constants
    CHARS_PER_TOKEN_ENGLISH = 4.0
    CHARS_PER_TOKEN_CHINESE = 1.5
    IMAGE_TOKENS = 85
    MESSAGE_OVERHEAD = 4  # Tokens for role, separators, etc.

    def __init__(self, config: ContextConfig | None = None):
        self.config = config or ContextConfig()

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text content.

        Uses different estimates for Chinese vs English content.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Count Chinese characters
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        english_chars = len(text) - chinese_chars

        # Estimate tokens
        chinese_tokens = chinese_chars / self.CHARS_PER_TOKEN_CHINESE
        english_tokens = english_chars / self.CHARS_PER_TOKEN_ENGLISH

        return int(chinese_tokens + english_tokens)

    def estimate_message_tokens(self, message: dict[str, Any]) -> int:
        """Estimate tokens for a single message."""
        content = message.get("content", "")
        if isinstance(content, str):
            text_tokens = self.estimate_tokens(content)
        elif isinstance(content, list):
            # Multi-part content (text + images)
            text_tokens = 0
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_tokens += self.estimate_tokens(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        text_tokens += self.IMAGE_TOKENS
                elif isinstance(part, str):
                    text_tokens += self.estimate_tokens(part)
        else:
            text_tokens = self.estimate_tokens(str(content))

        return text_tokens + self.MESSAGE_OVERHEAD

    def estimate_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate total tokens for a list of messages."""
        return sum(self.estimate_message_tokens(msg) for msg in messages)

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        """Check if context compression should be triggered."""
        current_tokens = self.estimate_messages_tokens(messages)
        threshold = self.config.max_tokens * self.config.compression_threshold
        return current_tokens > threshold

    def compress(
        self,
        messages: list[dict[str, Any]],
        system_message: str | None = None,
    ) -> list[dict[str, Any]]:
        """Compress conversation context to fit within token limits.

        Args:
            messages: List of conversation messages
            system_message: System message to always preserve (if any)

        Returns:
            Compressed list of messages
        """
        if not self.should_compress(messages):
            return messages

        if self.config.strategy == CompressionStrategy.TRUNCATE:
            return self._compress_truncate(messages, system_message)
        elif self.config.strategy == CompressionStrategy.HALVING:
            return self._compress_halving(messages, system_message)
        else:
            # Default to truncate
            return self._compress_truncate(messages, system_message)

    def _compress_truncate(
        self,
        messages: list[dict[str, Any]],
        system_message: str | None = None,
    ) -> list[dict[str, Any]]:
        """Truncate oldest messages to fit context."""
        result = []

        # Add system message first if provided
        if system_message:
            result.append({"role": "system", "content": system_message})

        # Always keep recent messages (as pairs to maintain conversation flow)
        keep_pairs = self.config.keep_recent_messages
        recent_start = max(0, len(messages) - keep_pairs * 2)

        # Add messages from recent_start onwards
        for msg in messages[recent_start:]:
            # Skip system messages (already handled)
            if msg.get("role") == "system":
                continue
            result.append(msg)

        logger.info(
            "Context compressed (truncate): %d -> %d messages",
            len(messages),
            len(result),
        )
        return result

    def _compress_halving(
        self,
        messages: list[dict[str, Any]],
        system_message: str | None = None,
    ) -> list[dict[str, Any]]:
        """Keep recent half of messages."""
        result = []

        if system_message:
            result.append({"role": "system", "content": system_message})

        # Keep recent 50%
        keep_count = len(messages) // 2
        for msg in messages[-keep_count:]:
            if msg.get("role") == "system":
                continue
            result.append(msg)

        logger.info(
            "Context compressed (halving): %d -> %d messages",
            len(messages),
            len(result),
        )
        return result

    def prepare_messages(
        self,
        history: list[dict[str, Any]] | None,
        current_message: str,
        system_prompt: str | None = None,
        context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Prepare messages for LLM API call.

        Args:
            history: Conversation history
            current_message: Current user message
            system_prompt: System prompt for the LLM
            context: Additional context (e.g., retrieved documents)

        Returns:
            List of messages ready for LLM API
        """
        messages: list[dict[str, Any]] = []

        # Build system message
        system_content = ""
        if system_prompt:
            system_content = system_prompt
        if context:
            if system_content:
                system_content += f"\n\n参考资料:\n{context}"
            else:
                system_content = f"参考资料:\n{context}"

        if system_content:
            messages.append({"role": "system", "content": system_content})

        # Add history (with compression if needed)
        if history:
            # Only include user/assistant messages in history
            history_messages = [
                msg for msg in history
                if msg.get("role") in ("user", "assistant")
            ]

            # Compress if needed (excluding system message for now)
            if self.should_compress(history_messages):
                history_messages = self._compress_truncate(history_messages, None)

            messages.extend(history_messages)

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages


def format_token_count(tokens: int) -> str:
    """Format token count for display."""
    if tokens < 1000:
        return str(tokens)
    elif tokens < 10000:
        return f"{tokens / 1000:.1f}K"
    else:
        return f"{tokens / 1000:.0f}K"


# Global instance with default config
_default_context_manager: ContextManager | None = None


def get_context_manager() -> ContextManager:
    """Get or create the default context manager."""
    global _default_context_manager
    if _default_context_manager is None:
        _default_context_manager = ContextManager()
    return _default_context_manager
