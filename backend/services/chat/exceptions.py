class ChatPipelineError(Exception):
    """Base error for chat pipeline."""


class RetrievalError(ChatPipelineError):
    """Raised when retrieval cannot proceed."""


class GenerationError(ChatPipelineError):
    """Raised when response generation fails."""
