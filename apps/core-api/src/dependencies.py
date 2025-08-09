"""Dependency injection for FastAPI application."""

import logging
from typing import AsyncGenerator

from .config import Settings
from .services.vector_store import VectorStoreService
from .services.embedding import EmbeddingService
from .services.cache import CacheService
from .services.scheduler import SchedulerService
from .services.connectors import (
    ConnectorManager,
    GitHubConnectorService,
    SlackConnectorService,
    NotionConnectorService,
)
from .services.intelligence import IntelligenceService

# Globals for state management
settings = Settings()
vector_store_service = None
embedding_service = None
cache_service = None
scheduler_service = None
connector_manager = None
intelligence_service = None

logger = logging.getLogger(__name__)


async def initialize_services():
    """Initialize all services during startup."""
    global vector_store_service, embedding_service, cache_service
    global scheduler_service, connector_manager, intelligence_service
    
    try:
        # Initialize cache service
        if settings.redis_host:
            cache_service = CacheService(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
            )
            await cache_service.initialize()
            logger.info("Cache service initialized")
        
        # Initialize vector store
        vector_store_service = VectorStoreService(
            url=str(settings.qdrant_url),
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
        )
        await vector_store_service.initialize()
        logger.info("Vector store service initialized")
        
        # Initialize embedding service
        embedding_service = EmbeddingService(
            model_name=settings.embedding_model,
            batch_size=settings.embedding_batch_size,
            cache_service=cache_service,
        )
        await embedding_service.initialize()
        logger.info("Embedding service initialized")
        
        # Initialize scheduler
        scheduler_service = SchedulerService(
            timezone=settings.timezone,
        )
        await scheduler_service.initialize()
        logger.info("Scheduler service initialized")
        
        # Initialize connector manager
        connector_manager = ConnectorManager()
        
        # Register GitHub connector if configured
        if settings.github_configured:
            github_connector = GitHubConnectorService(
                token=settings.github_token,
                webhook_secret=settings.github_webhook_secret,
                owner=settings.github_owner,
                repo=settings.github_repo,
                vector_store=vector_store_service,
                embedding_service=embedding_service,
            )
            await connector_manager.register_connector("github", github_connector)
        
        # Register Slack connector if configured
        if settings.slack_configured:
            slack_connector = SlackConnectorService(
                bot_token=settings.slack_bot_token,
                app_token=settings.slack_app_token,
                signing_secret=settings.slack_signing_secret,
                default_channels=settings.slack_default_channels,
                vector_store=vector_store_service,
                embedding_service=embedding_service,
            )
            await connector_manager.register_connector("slack", slack_connector)
        
        # Register Notion connector if configured
        if settings.notion_configured:
            notion_connector = NotionConnectorService(
                token=settings.notion_token,
                databases=settings.notion_databases,
                pages=settings.notion_pages,
                poll_interval=settings.notion_poll_interval,
                vector_store=vector_store_service,
                embedding_service=embedding_service,
            )
            await connector_manager.register_connector("notion", notion_connector)
        
        logger.info("Connector manager initialized")
        
        # Initialize intelligence service
        if settings.intelligence_enabled:
            intelligence_service = IntelligenceService(
                openai_api_key=settings.openai_api_key,
                openai_model=settings.openai_model,
                vector_store=vector_store_service,
                cache_service=cache_service,
                embedding_service=embedding_service,
            )
            await intelligence_service.initialize()
            logger.info("Intelligence service initialized")
        
        # Start all connectors
        await connector_manager.start_all()
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


async def cleanup_services():
    """Cleanup all services during shutdown."""
    global vector_store_service, embedding_service, cache_service
    global scheduler_service, connector_manager, intelligence_service
    
    try:
        # Stop all connectors
        if connector_manager:
            await connector_manager.stop_all()
        
        # Close vector store
        if vector_store_service:
            await vector_store_service.close()
        
        # Close cache
        if cache_service:
            await cache_service.close()
        
        # Shutdown scheduler
        if scheduler_service:
            await scheduler_service.shutdown()
        
        logger.info("All services cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


# Dependency injection functions
async def get_settings() -> Settings:
    """Get application settings."""
    return settings


async def get_vector_store() -> VectorStoreService:
    """Get vector store service."""
    if not vector_store_service:
        raise RuntimeError("Vector store service not initialized")
    return vector_store_service


async def get_embedding_service() -> EmbeddingService:
    """Get embedding service."""
    if not embedding_service:
        raise RuntimeError("Embedding service not initialized")
    return embedding_service


async def get_cache_service() -> CacheService:
    """Get cache service."""
    return cache_service  # Can be None


async def get_scheduler_service() -> SchedulerService:
    """Get scheduler service."""
    if not scheduler_service:
        raise RuntimeError("Scheduler service not initialized")
    return scheduler_service


async def get_connector_manager() -> ConnectorManager:
    """Get connector manager."""
    if not connector_manager:
        raise RuntimeError("Connector manager not initialized")
    return connector_manager


async def get_intelligence_service() -> IntelligenceService:
    """Get intelligence service."""
    return intelligence_service  # Can be None


# Type aliases for dependency injection
SettingsDep = Settings
VectorStoreDep = VectorStoreService
EmbeddingDep = EmbeddingService
CacheDep = CacheService
SchedulerDep = SchedulerService
ConnectorManagerDep = ConnectorManager
IntelligenceDep = IntelligenceService