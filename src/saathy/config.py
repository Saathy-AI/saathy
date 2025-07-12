"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Saathy"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    qdrant_url: str = "http://localhost:6333"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings() 