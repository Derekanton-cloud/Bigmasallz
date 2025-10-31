"""Application configuration using Pydantic settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised application settings loaded from environment variables."""

    app_name: str = Field("SynthX.AI", description="Public facing application name")
    api_v1_prefix: str = Field("/api/v1", description="Base prefix for API routes")
    environment: str = Field("development", description="Application environment")
    debug: bool = Field(False, description="Toggle debug features")
    host: str = Field("0.0.0.0", description="Host for FastAPI server")
    port: int = Field(8080, description="Port for FastAPI server")
    log_level: str = Field("INFO", description="Default log level")
    log_dir: Path = Field(Path("logs"), description="Directory where logs are stored")
    generated_data_dir: Path = Field(
        Path("generated"),
        description="Directory where generated datasets are persisted",
    )

    cors_origins: List[str] = Field(
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins for API access",
    )

    gemini_api_key: Optional[str] = Field(
        default=None,
        description="API key for Google Gemini models",
        env="GEMINI_API_KEY",
    )
    schema_llm_model: str = Field(
        "gemini-1.5-pro-latest",
        description="Gemini model used for schema generation",
    )
    data_llm_model: str = Field(
        "gemini-1.5-flash-latest",
        description="Gemini model used for data generation",
    )

    langsmith_api_key: Optional[str] = Field(
        default=None,
        description="LangSmith API key for tracing and analytics",
        env="LANGSMITH_API_KEY",
    )
    langsmith_project: Optional[str] = Field(
        default="synthx-ai",
        description="LangSmith project name",
    )

    chroma_host: str = Field(
        "chromadb",
        description="Hostname for ChromaDB instance",
    )
    chroma_port: int = Field(8000, description="Port for ChromaDB instance")
    chroma_collection: str = Field(
        "synthx_dataset_dedup",
        description="Collection name used for deduplication embeddings",
    )

    max_rows_per_chunk: int = Field(
        500,
        description="Maximum number of rows generated per async chunk",
    )
    max_concurrent_chunks: int = Field(
        5,
        description="Maximum number of data generation chunks running concurrently",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("log_dir", "generated_data_dir", mode="before")
    def _coerce_path(cls, value: str | Path) -> Path:
        """Ensure directories are materialized as Path objects."""
        return Path(value)

    @field_validator("cors_origins", mode="before")
    def _split_cors(cls, value: str | List[str]) -> List[str]:
        """Support comma separated origins from env vars."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    settings = Settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_data_dir.mkdir(parents=True, exist_ok=True)
    return settings
