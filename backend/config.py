from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # GitHub
    github_token: str = ""
    github_sync_page_concurrency: int = 4
    github_readme_concurrency: int = 8

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    ai_analysis_concurrency: int = 1
    ai_analysis_request_delay_seconds: float = 0.5

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
