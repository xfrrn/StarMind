from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # GitHub
    github_token: str = ""
    github_api_url: str = "https://api.github.com"
    github_sync_page_concurrency: int = 4
    github_readme_concurrency: int = 8

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

    # Chat Retrieval Filtering
    # Similarity threshold for vector search (0.0-1.0). Higher = more strict.
    chat_similarity_threshold: float = 0.5
    # Enable LLM verification after threshold filtering
    chat_llm_filter_enabled: bool = True

    # Security
    # Encryption key for sensitive data (Fernet key, 44 chars)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/starmind"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    # CORS allowed origins (comma-separated, e.g., "http://localhost:5173,http://localhost:3000")
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
