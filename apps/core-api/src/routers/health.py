"""Health check endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, status

from ..dependencies import (
    VectorStoreDep,
    ConnectorManagerDep,
    CacheDep,
    SettingsDep,
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
        return {
            "status": "not_ready",
            "message": "No active connectors",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
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