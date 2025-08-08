"""Dependency injection and application state management."""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Depends

from .config import Settings, get_settings
from .services.vector_store import VectorStoreService
from .services.embedding import EmbeddingService
from .services.scheduler import SchedulerService
from .services.connectors import (
    ConnectorManager,
    GitHubConnectorService,
    SlackConnectorService,
    NotionConnectorService,
)
from .services.intelligence import IntelligenceService
from .services.cache import CacheService

logger = logging.getLogger(__name__)

# Application state storage
app_state: Dict[str, Any] = {}


async def setup_dependencies(app: FastAPI) -> None:
    """Initialize all application dependencies."""
    settings = get_settings()
    
    logger.info("Setting up application dependencies...")
    
    # Initialize cache service
    cache_service = CacheService(settings.redis_url)
    await cache_service.initialize()
    app_state["cache"] = cache_service
    
    # Initialize vector store
    vector_store = VectorStoreService(
        url=str(settings.qdrant_url),
        api_key=settings.qdrant_api_key_str,
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.qdrant_vector_size,
    )
    await vector_store.initialize()
    app_state["vector_store"] = vector_store
    
    # Initialize embedding service
    embedding_service = EmbeddingService(
        model_name=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
        cache_service=cache_service,
    )
    await embedding_service.initialize()
    app_state["embedding"] = embedding_service
    
    # Initialize scheduler
    if settings.scheduler_enabled:
        scheduler = SchedulerService(timezone=settings.scheduler_timezone)
        scheduler.start()
        app_state["scheduler"] = scheduler
    
    # Initialize connector manager
    connector_manager = ConnectorManager()
    app_state["connector_manager"] = connector_manager
    
    # Initialize individual connectors
    if settings.github_configured:
        github_connector = GitHubConnectorService(
            token=settings.get_secret_value(settings.github_token),
            webhook_secret=settings.get_secret_value(settings.github_webhook_secret),
            owner=settings.github_owner,
            repo=settings.github_repo,
            vector_store=vector_store,
            embedding_service=embedding_service,
        )
        await connector_manager.register_connector("github", github_connector)
    
    if settings.slack_configured:
        slack_connector = SlackConnectorService(
            bot_token=settings.get_secret_value(settings.slack_bot_token),
            app_token=settings.get_secret_value(settings.slack_app_token),
            signing_secret=settings.get_secret_value(settings.slack_signing_secret),
            default_channels=settings.slack_default_channels,
            vector_store=vector_store,
            embedding_service=embedding_service,
        )
        await connector_manager.register_connector("slack", slack_connector)
    
    if settings.notion_configured:
        notion_connector = NotionConnectorService(
            token=settings.get_secret_value(settings.notion_token),
            databases=settings.notion_databases.split(",") if settings.notion_databases else [],
            pages=settings.notion_pages.split(",") if settings.notion_pages else [],
            poll_interval=settings.notion_poll_interval,
            vector_store=vector_store,
            embedding_service=embedding_service,
        )
        await connector_manager.register_connector("notion", notion_connector)
    
    # Initialize intelligence service
    if settings.intelligence_enabled and settings.openai_configured:
        intelligence_service = IntelligenceService(
            api_key=settings.openai_api_key_str,
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            correlation_threshold=settings.correlation_threshold,
            vector_store=vector_store,
            cache_service=cache_service,
        )
        await intelligence_service.initialize()
        app_state["intelligence"] = intelligence_service
    
    # Start all connectors
    await connector_manager.start_all()
    
    # Store settings for reference
    app_state["settings"] = settings
    
    logger.info("Application dependencies initialized successfully")


async def cleanup_dependencies(app: FastAPI) -> None:
    """Cleanup all application dependencies."""
    logger.info("Cleaning up application dependencies...")
    
    # Stop all connectors
    if "connector_manager" in app_state:
        await app_state["connector_manager"].stop_all()
    
    # Stop scheduler
    if "scheduler" in app_state:
        app_state["scheduler"].shutdown()
    
    # Close vector store connection
    if "vector_store" in app_state:
        await app_state["vector_store"].close()
    
    # Close cache connection
    if "cache" in app_state:
        await app_state["cache"].close()
    
    # Clear app state
    app_state.clear()
    
    logger.info("Application dependencies cleaned up successfully")


# Dependency injection functions
def get_vector_store() -> VectorStoreService:
    """Get vector store service instance."""
    if "vector_store" not in app_state:
        raise RuntimeError("Vector store not initialized")
    return app_state["vector_store"]


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance."""
    if "embedding" not in app_state:
        raise RuntimeError("Embedding service not initialized")
    return app_state["embedding"]


def get_connector_manager() -> ConnectorManager:
    """Get connector manager instance."""
    if "connector_manager" not in app_state:
        raise RuntimeError("Connector manager not initialized")
    return app_state["connector_manager"]


def get_scheduler() -> Optional[SchedulerService]:
    """Get scheduler service instance."""
    return app_state.get("scheduler")


def get_intelligence_service() -> Optional[IntelligenceService]:
    """Get intelligence service instance."""
    return app_state.get("intelligence")


def get_cache_service() -> CacheService:
    """Get cache service instance."""
    if "cache" not in app_state:
        raise RuntimeError("Cache service not initialized")
    return app_state["cache"]


# Dependency shortcuts for FastAPI
VectorStoreDep = Depends(get_vector_store)
EmbeddingDep = Depends(get_embedding_service)
ConnectorManagerDep = Depends(get_connector_manager)
SchedulerDep = Depends(get_scheduler)
IntelligenceDep = Depends(get_intelligence_service)
CacheDep = Depends(get_cache_service)
SettingsDep = Depends(get_settings)