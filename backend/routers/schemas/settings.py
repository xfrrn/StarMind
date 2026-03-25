from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """Response model for user settings."""

    # === User Info ===
    github_username: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""

    # === API Keys (masked) ===
    github_token_set: bool = False
    github_token_masked: str = ""
    openai_api_key_set: bool = False
    openai_api_key_masked: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # === Chat Retrieval ===
    chat_similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    chat_llm_filter_enabled: bool = True

    # === Sync Configuration ===
    github_sync_page_concurrency: int = Field(default=4, ge=1, le=10)
    github_readme_concurrency: int = Field(default=8, ge=1, le=20)
    ai_analysis_concurrency: int = Field(default=1, ge=1, le=5)

    # === Feature Toggles ===
    auto_summarize: bool = True
    include_readmes: bool = True

    # === Auto Sync ===
    auto_sync_enabled: bool = False
    auto_sync_time: str = "00:00"  # HH:MM format
    timezone: str = "Asia/Shanghai"
    last_sync_at: str | None = None  # ISO format datetime


class SettingsUpdate(BaseModel):
    """Update model for user settings."""

    # === User Info ===
    github_username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None

    # === API Keys (sensitive, encrypted on server) ===
    github_token: str | None = None
    openai_api_key: str | None = None

    # === OpenAI Config ===
    openai_base_url: str | None = None
    openai_model: str | None = None

    # === Chat Retrieval ===
    chat_similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    chat_llm_filter_enabled: bool | None = None

    # === Sync Configuration ===
    github_sync_page_concurrency: int | None = Field(default=None, ge=1, le=10)
    github_readme_concurrency: int | None = Field(default=None, ge=1, le=20)
    ai_analysis_concurrency: int | None = Field(default=None, ge=1, le=5)

    # === Feature Toggles ===
    auto_summarize: bool | None = None
    include_readmes: bool | None = None

    # === Auto Sync ===
    auto_sync_enabled: bool | None = None
    auto_sync_time: str | None = None  # HH:MM format
    timezone: str | None = None


class TestConnectionResponse(BaseModel):
    """Response model for connection testing."""

    success: bool
    message: str
