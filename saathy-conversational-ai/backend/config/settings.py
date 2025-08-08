from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Saathy Conversational AI"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str
    redis_url: str

    # Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-1106-preview"

    # Security
    secret_key: str
    access_token_expire_minutes: int = 30

    # Session Management
    session_ttl_hours: int = 24
    max_session_turns: int = 100
    context_cache_ttl_seconds: int = 300

    # Performance
    max_concurrent_sessions: int = 100
    response_timeout_seconds: int = 30
    max_context_tokens: int = 8000

    # Retrieval Settings
    vector_search_limit: int = 20
    event_search_limit: int = 50
    action_search_limit: int = 20

    # Agent Settings
    sufficiency_threshold: float = 0.7
    max_context_expansions: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
