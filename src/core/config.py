"""Configuration management with Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from typing import Literal, Optional

class Settings(BaseSettings):
    """Application settings with validation."""

    # Required - fail fast if missing
    SUPABASE_URL: str
    SUPABASE_KEY: SecretStr
    GROQ_API_KEY: SecretStr

    # Embedding settings
    EMBEDDING_PROVIDER: Literal["local", "azure"] = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_WARMUP: bool = True
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[SecretStr] = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_EMBEDDING_DIMENSIONS: Optional[int] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    # Chunking settings
    CHUNK_SIZE: int = Field(default=500, ge=100, le=1000)
    CHUNK_OVERLAP: int = Field(default=50, ge=0, le=200)

    # Retrieval settings
    RETRIEVAL_TOP_K: int = Field(default=3, ge=1, le=10)
    RETRIEVAL_THRESHOLD: float = Field(default=0.4, ge=0.0, le=1.0)
    RETRIEVAL_CANDIDATE_MULTIPLIER: int = Field(default=3, ge=1, le=10)  # Fetch N*top_k candidates
    TOPIC_BOOST_FACTOR: float = Field(default=0.15, ge=0.0, le=0.5)  # Boost for matching topics

    # LLM settings
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=500, ge=50, le=2000)
    LLM_TIMEOUT: float = 30.0
    MAX_RETRIES: int = 3

    # Langfuse tracing (optional)
    LANGFUSE_PUBLIC_KEY: Optional[SecretStr] = None
    LANGFUSE_SECRET_KEY: Optional[SecretStr] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    LANGFUSE_BASE_URL: Optional[str] = None

    # Environment
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
