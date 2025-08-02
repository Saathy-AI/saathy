"""Application configuration using Pydantic Settings."""

import os
from typing import Optional

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigdict


class Settings(BaseSettings):
    """Application settings with comprehensive configuration categories."""

    # Application settings
    app_name: str = Field(default="Saathy", description="Application name")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    # Database settings
    qdrant_url: HttpUrl = Field(
        default="http://localhost:6333", description="Qdrant vector database URL"
    )
    qdrant_api_key: Optional[SecretStr] = Field(
        default=None, description="Qdrant API key for authentication"
    )
    qdrant_collection_name: str = Field(
        default="documents", description="Qdrant collection name"
    )
    qdrant_vector_size: int = Field(
        default=384, description="Vector dimensions for embeddings"
    )

    # External API settings
    openai_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenAI API key for language model access"
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo", description="OpenAI model to use for completions"
    )

    # Embedding settings
    default_embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Default embedding model to use"
    )
    embedding_cache_size: int = Field(
        default=1000, description="Maximum number of cached embeddings"
    )
    embedding_cache_ttl: int = Field(
        default=3600, description="Time-to-live for cached embeddings in seconds"
    )
    embedding_batch_size: int = Field(
        default=32, description="Batch size for embedding operations"
    )
    enable_gpu_embeddings: bool = Field(
        default=True, description="Enable GPU acceleration for embeddings"
    )
    embedding_quality_preference: str = Field(
        default="balanced",
        description="Embedding quality preference (fast, balanced, high)",
    )

    # Observability settings
    service_name: str = Field(
        default="saathy", description="Service name for telemetry"
    )
    jaeger_agent_host: str = Field(
        default="localhost", description="Jaeger agent host for Thrift exporter"
    )
    jaeger_agent_port: int = Field(
        default=6831, description="Jaeger agent port for Thrift exporter"
    )
    otlp_endpoint: Optional[HttpUrl] = Field(
        default=None, description="OpenTelemetry Protocol endpoint for tracing"
    )
    enable_tracing: bool = Field(
        default=False, description="Enable distributed tracing with OpenTelemetry"
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port number")
    workers: int = Field(default=1, description="Number of worker processes")

    model_config = SettingsConfigdict(
        env_file=".env",
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def _read_secret_from_file(self, env_var_name: str) -> Optional[str]:
        """Read secret from file if *_FILE environment variable is set."""
        file_env_var = f"{env_var_name}_FILE"
        file_path = os.getenv(file_env_var)
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path) as f:
                    return f.read().strip()
            except Exception:
                return None
        return None

    @property
    def qdrant_api_key_str(self) -> Optional[str]:
        """Get Qdrant API key as string if available."""
        # First try to read from file
        file_secret = self._read_secret_from_file("QDRANT_API_KEY")
        if file_secret:
            return file_secret

        # Fall back to environment variable
        return self.qdrant_api_key.get_secret_value() if self.qdrant_api_key else None

    @property
    def openai_api_key_str(self) -> Optional[str]:
        """Get OpenAI API key as string if available."""
        # First try to read from file
        file_secret = self._read_secret_from_file("OPENAI_API_KEY")
        if file_secret:
            return file_secret

        # Fall back to environment variable
        return self.openai_api_key.get_secret_value() if self.openai_api_key else None


def get_settings() -> Settings:
    """Get a new settings instance for dependency injection."""
    return Settings()
