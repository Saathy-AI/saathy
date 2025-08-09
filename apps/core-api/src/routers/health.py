"""Health check endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from ..dependencies import (
    VectorStoreDep,
    ConnectorManagerDep,
    CacheDep,
    SettingsDep,
    IntelligenceDep,
)
from ..config import Settings

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    vector_store: VectorStoreDep,
    cache: CacheDep,
    settings: SettingsDep,
) -> Dict[str, Any]:
    """
    Perform health check on the application and its dependencies.
    
    Returns:
        Health status of the application and its components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "saathy-core-api",
        "version": "0.1.0",
        "environment": settings.environment,
        "checks": {}
    }
    
    # Check vector store
    try:
        vector_health = await vector_store.health_check()
        health_status["checks"]["vector_store"] = {
            "status": "healthy" if vector_health else "unhealthy",
            "collection": settings.qdrant_collection_name,
        }
    except Exception as e:
        health_status["checks"]["vector_store"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check cache
    try:
        cache_health = await cache.health_check()
        health_status["checks"]["cache"] = {
            "status": "healthy" if cache_health else "unhealthy",
        }
    except Exception as e:
        health_status["checks"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check OpenAI if configured
    if settings.openai_configured:
        health_status["checks"]["openai"] = {
            "status": "configured",
            "model": settings.openai_model,
        }
    
    return health_status


@router.get("/ready", response_model=Dict[str, str])
async def readiness_check(
    connector_manager: ConnectorManagerDep,
) -> Dict[str, str]:
    """
    Check if the application is ready to serve requests.
    
    Returns:
        Readiness status
    """
    # Check if at least one connector is active
    active_connectors = await connector_manager.get_active_connectors()
    
    if not active_connectors:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "message": "No active connectors",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    return {
        "status": "ready",
        "message": f"{len(active_connectors)} connectors active",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/live", response_model=Dict[str, str])
async def liveness_check() -> Dict[str, str]:
    """
    Simple liveness check endpoint.
    
    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/config", response_model=Dict[str, Any])
async def get_config(settings: Settings = Depends(SettingsDep)) -> Dict[str, Any]:
    """
    Get non-sensitive configuration information.
    
    Returns:
        Safe configuration values
    """
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "features": {
            "github_enabled": settings.github_enabled,
            "slack_enabled": settings.slack_enabled,
            "notion_enabled": settings.notion_enabled,
            "intelligence_enabled": settings.intelligence_enabled,
            "enterprise_features_enabled": settings.enterprise_features_enabled,
        },
        "connectors": {
            "github": {
                "configured": settings.github_configured,
                "owner": settings.github_owner,
                "repo": settings.github_repo,
            },
            "slack": {
                "configured": settings.slack_configured,
                "channels": settings.slack_default_channels,
            },
            "notion": {
                "configured": settings.notion_configured,
                "poll_interval": settings.notion_poll_interval,
            },
        },
        "vector_store": {
            "url": str(settings.qdrant_url),
            "collection": settings.qdrant_collection_name,
            "vector_size": settings.qdrant_vector_size,
        },
        "embedding": {
            "model": settings.embedding_model,
            "batch_size": settings.embedding_batch_size,
        },
    }