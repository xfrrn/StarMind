from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # GitHub
    github_token: str = ""
    github_api_url: str = "https://api.github.com"
    github_sync_page_concurrency: int = 4
    github_readme_concurrency: int = 8

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "DELETE"]
    cors_allow_headers: list[str] = ["Content-Type", "Authorization", "X-Correlation-ID"]

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_max_text_length: int = 8000
    embedding_dimension: int = 4096
    embedding_version: str = "v2"
    embedding_metadata_weight: float = 0.65
    embedding_readme_weight: float = 0.35
    embedding_summary_max_tokens: int = 120
    embedding_readme_max_tokens: int = 1500
    ai_analysis_concurrency: int = 1
    ai_analysis_request_delay_seconds: float = 0.5
    ai_analysis_checkpoint_every: int = 1

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/starmind"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
