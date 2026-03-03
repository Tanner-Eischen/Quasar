"""LegacyLens configuration management."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Keys
    openai_api_key: str

    # Database
    database_url: str = "postgresql+asyncpg://legacylens:dev@localhost:5432/legacylens"

    # Models
    embedding_model: str = "text-embedding-3-small"
    embedding_dims: int = 1536
    answer_model: str = "gpt-4o"

    # Logging
    log_level: str = "INFO"

    # Chunking defaults
    chunk_target_tokens: int = 350
    chunk_max_tokens: int = 800
    chunk_min_tokens: int = 50
    fallback_window_lines: int = 50
    fallback_overlap_lines: int = 10

    # Retrieval defaults
    retrieval_top_k: int = 10

    # Rate limiting (for demo)
    rate_limit_per_minute: int = 10
    query_timeout_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
