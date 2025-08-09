"""Core API configuration using Pydantic Settings."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with comprehensive configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    app_name: str = Field(default="Saathy Core API", description="Application name")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=4, description="Number of worker processes")
    
    # Security settings
    secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-production"),
        description="Secret key for security"
    )
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_calls: int = Field(default=100, description="Number of calls allowed")
    rate_limit_period: int = Field(default=60, description="Period in seconds")
    
    # Vector database settings
    qdrant_url: HttpUrl = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL"
    )
    qdrant_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Qdrant API key"
    )
    qdrant_collection_name: str = Field(
        default="saathy_content",
        description="Qdrant collection name"
    )
    qdrant_vector_size: int = Field(
        default=384,
        description="Vector dimensions"
    )
    
    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis URL for caching"
    )
    redis_ttl: int = Field(
        default=3600,
        description="Redis cache TTL in seconds"
    )
    
    # Embedding settings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    embedding_batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation"
    )
    
    # OpenAI settings
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4",
        description="OpenAI model for intelligence features"
    )
    openai_temperature: float = Field(
        default=0.7,
        description="Temperature for OpenAI completions"
    )
    
    # Connector settings - GitHub
    github_enabled: bool = Field(default=True, description="Enable GitHub connector")
    github_webhook_secret: Optional[SecretStr] = Field(
        default=None,
        description="GitHub webhook secret"
    )
    github_token: Optional[SecretStr] = Field(
        default=None,
        description="GitHub personal access token"
    )
    github_owner: Optional[str] = Field(
        default=None,
        description="GitHub organization/owner"
    )
    github_repo: Optional[str] = Field(
        default=None,
        description="GitHub repository name"
    )
    
    # Connector settings - Slack
    slack_enabled: bool = Field(default=True, description="Enable Slack connector")
    slack_bot_token: Optional[SecretStr] = Field(
        default=None,
        description="Slack bot token"
    )
    slack_app_token: Optional[SecretStr] = Field(
        default=None,
        description="Slack app token for Socket Mode"
    )
    slack_signing_secret: Optional[SecretStr] = Field(
        default=None,
        description="Slack signing secret"
    )
    slack_default_channels: list[str] = Field(
        default_factory=list,
        description="Default Slack channels to monitor"
    )
    
    # Connector settings - Notion
    notion_enabled: bool = Field(default=True, description="Enable Notion connector")
    notion_token: Optional[SecretStr] = Field(
        default=None,
        description="Notion integration token"
    )
    notion_databases: str = Field(
        default="",
        description="Comma-separated Notion database IDs"
    )
    notion_pages: str = Field(
        default="",
        description="Comma-separated Notion page IDs"
    )
    notion_poll_interval: int = Field(
        default=300,
        description="Notion polling interval in seconds"
    )
    
    # Scheduler settings
    scheduler_enabled: bool = Field(
        default=True,
        description="Enable scheduled tasks"
    )
    scheduler_timezone: str = Field(
        default="UTC",
        description="Timezone for scheduled tasks"
    )
    
    # Intelligence features
    intelligence_enabled: bool = Field(
        default=True,
        description="Enable AI intelligence features"
    )
    correlation_threshold: float = Field(
        default=0.7,
        description="Threshold for event correlation"
    )
    action_generation_enabled: bool = Field(
        default=True,
        description="Enable action generation"
    )
    
    # Enterprise features
    license_key: Optional[SecretStr] = Field(
        default=None,
        description="Enterprise license key"
    )
    enterprise_features_enabled: bool = Field(
        default=False,
        description="Enable enterprise features"
    )
    
    # Monitoring
    telemetry_enabled: bool = Field(
        default=True,
        description="Enable telemetry"
    )
    jaeger_endpoint: Optional[str] = Field(
        default=None,
        description="Jaeger endpoint for tracing"
    )
    metrics_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"
    
    @property
    def github_configured(self) -> bool:
        """Check if GitHub connector is properly configured."""
        return bool(
            self.github_enabled and
            self.github_token and
            self.github_webhook_secret
        )
    
    @property
    def slack_configured(self) -> bool:
        """Check if Slack connector is properly configured."""
        return bool(
            self.slack_enabled and
            self.slack_bot_token and
            self.slack_app_token and
            self.slack_signing_secret
        )
    
    @property
    def notion_configured(self) -> bool:
        """Check if Notion connector is properly configured."""
        return bool(
            self.notion_enabled and
            self.notion_token and
            (self.notion_databases or self.notion_pages)
        )
    
    @property
    def openai_configured(self) -> bool:
        """Check if OpenAI is properly configured."""
        return bool(self.openai_api_key)
    
    def get_secret_value(self, secret: Optional[SecretStr]) -> Optional[str]:
        """Safely get secret value."""
        return secret.get_secret_value() if secret else None
    
    # Handle file-based secrets
    @property
    def qdrant_api_key_str(self) -> Optional[str]:
        """Get Qdrant API key from env or file."""
        if self.qdrant_api_key:
            return self.get_secret_value(self.qdrant_api_key)
        
        # Try file-based secret
        key_file = os.getenv("QDRANT_API_KEY_FILE")
        if key_file and os.path.exists(key_file):
            with open(key_file, "r") as f:
                return f.read().strip()
        return None
    
    @property
    def openai_api_key_str(self) -> Optional[str]:
        """Get OpenAI API key from env or file."""
        if self.openai_api_key:
            return self.get_secret_value(self.openai_api_key)
        
        # Try file-based secret
        key_file = os.getenv("OPENAI_API_KEY_FILE")
        if key_file and os.path.exists(key_file):
            with open(key_file, "r") as f:
                return f.read().strip()
        return None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()