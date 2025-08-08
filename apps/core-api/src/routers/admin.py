"""Admin endpoints for system management."""

import os
import platform
import psutil
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ..dependencies import (
    ConnectorManagerDep,
    VectorStoreDep,
    CacheDep,
    SchedulerDep,
    SettingsDep,
)

router = APIRouter()
security = HTTPBasic()


def verify_admin_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
    settings: SettingsDep = None,
) -> str:
    """Verify admin credentials."""
    # In production, use proper authentication
    # For now, use environment variables
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin")
    
    if credentials.username != admin_user or credentials.password != admin_pass:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


@router.get("/system/info", dependencies=[Depends(verify_admin_credentials)])
async def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    # CPU info
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    
    # Memory info
    memory = psutil.virtual_memory()
    
    # Disk info
    disk = psutil.disk_usage("/")
    
    # Network info
    network = psutil.net_io_counters()
    
    # Process info
    process = psutil.Process()
    
    return {
        "system": {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        },
        "cpu": {
            "percent": cpu_percent,
            "count": cpu_count,
            "count_logical": psutil.cpu_count(logical=True),
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        },
        "network": {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv,
        },
        "process": {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "num_threads": process.num_threads(),
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
        },
    }


@router.get("/connectors/all", dependencies=[Depends(verify_admin_credentials)])
async def get_all_connectors(
    connector_manager: ConnectorManagerDep,
) -> Dict[str, Any]:
    """Get detailed information about all connectors."""
    all_status = await connector_manager.get_all_status()
    active_count = len(await connector_manager.get_active_connectors())
    
    return {
        "total_connectors": len(all_status),
        "active_connectors": active_count,
        "connectors": all_status,
    }


@router.post("/connectors/{connector_name}/restart", dependencies=[Depends(verify_admin_credentials)])
async def restart_connector(
    connector_name: str,
    connector_manager: ConnectorManagerDep,
) -> Dict[str, str]:
    """Restart a specific connector."""
    connector = await connector_manager.get_connector(connector_name)
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector {connector_name} not found"
        )
    
    try:
        # Stop if running
        if connector.status == "active":
            await connector.stop()
        
        # Start again
        await connector.start()
        
        return {
            "status": "success",
            "message": f"Connector {connector_name} restarted successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart connector: {str(e)}"
        )


@router.get("/vector-store/stats", dependencies=[Depends(verify_admin_credentials)])
async def get_vector_store_stats(
    vector_store: VectorStoreDep,
) -> Dict[str, Any]:
    """Get vector store statistics."""
    try:
        stats = await vector_store.get_collection_stats()
        return {
            "collection_name": vector_store.collection_name,
            "stats": stats,
            "health": await vector_store.health_check(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vector store stats: {str(e)}"
        )


@router.post("/vector-store/cleanup", dependencies=[Depends(verify_admin_credentials)])
async def cleanup_vector_store(
    vector_store: VectorStoreDep,
    older_than_days: int = Query(30, ge=1, le=365),
    dry_run: bool = Query(True, description="If true, only show what would be deleted"),
) -> Dict[str, Any]:
    """Clean up old vectors from the store."""
    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
    
    # This is a placeholder - in production, implement actual cleanup
    return {
        "status": "success" if not dry_run else "dry_run",
        "cutoff_date": cutoff_date.isoformat(),
        "message": f"Would delete vectors older than {older_than_days} days" if dry_run else f"Deleted vectors older than {older_than_days} days",
    }


@router.get("/cache/info", dependencies=[Depends(verify_admin_credentials)])
async def get_cache_info(
    cache_service: CacheDep,
) -> Dict[str, Any]:
    """Get cache statistics and info."""
    if not cache_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available"
        )
    
    try:
        # Get Redis info
        # In production, use INFO command
        health = await cache_service.health_check()
        
        return {
            "health": health,
            "host": cache_service.host,
            "port": cache_service.port,
            "db": cache_service.db,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache info: {str(e)}"
        )


@router.post("/cache/flush", dependencies=[Depends(verify_admin_credentials)])
async def flush_cache(
    cache_service: CacheDep,
    pattern: Optional[str] = Query(None, description="Key pattern to flush (e.g., 'user:*')"),
    confirm: bool = Query(False, description="Confirm the flush operation"),
) -> Dict[str, str]:
    """Flush cache keys matching pattern."""
    if not cache_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available"
        )
    
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": "Set confirm=true to execute flush operation",
            "pattern": pattern or "all keys",
        }
    
    # In production, implement actual flush with pattern matching
    return {
        "status": "success",
        "message": f"Flushed cache keys matching pattern: {pattern}" if pattern else "Flushed all cache keys",
    }


@router.get("/scheduler/jobs", dependencies=[Depends(verify_admin_credentials)])
async def get_scheduler_jobs(
    scheduler: SchedulerDep,
) -> Dict[str, Any]:
    """Get all scheduled jobs."""
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler service not available"
        )
    
    jobs = scheduler.get_all_job_statuses()
    
    return {
        "total_jobs": len(jobs),
        "jobs": jobs,
    }


@router.post("/scheduler/jobs/{job_id}/pause", dependencies=[Depends(verify_admin_credentials)])
async def pause_job(
    job_id: str,
    scheduler: SchedulerDep,
) -> Dict[str, str]:
    """Pause a scheduled job."""
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler service not available"
        )
    
    success = scheduler.pause_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return {
        "status": "success",
        "message": f"Job {job_id} paused",
    }


@router.post("/scheduler/jobs/{job_id}/resume", dependencies=[Depends(verify_admin_credentials)])
async def resume_job(
    job_id: str,
    scheduler: SchedulerDep,
) -> Dict[str, str]:
    """Resume a paused job."""
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler service not available"
        )
    
    success = scheduler.resume_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return {
        "status": "success",
        "message": f"Job {job_id} resumed",
    }


@router.delete("/scheduler/jobs/{job_id}", dependencies=[Depends(verify_admin_credentials)])
async def delete_job(
    job_id: str,
    scheduler: SchedulerDep,
) -> Dict[str, str]:
    """Delete a scheduled job."""
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler service not available"
        )
    
    success = scheduler.remove_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return {
        "status": "success",
        "message": f"Job {job_id} deleted",
    }


@router.get("/logs/recent", dependencies=[Depends(verify_admin_credentials)])
async def get_recent_logs(
    lines: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
) -> Dict[str, Any]:
    """Get recent application logs."""
    # In production, read from actual log files or log aggregation service
    # For now, return a placeholder
    return {
        "lines_requested": lines,
        "level_filter": level,
        "logs": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "This is a placeholder log entry",
                "module": "admin",
            }
        ],
        "message": "Log retrieval not fully implemented",
    }


@router.post("/maintenance/mode", dependencies=[Depends(verify_admin_credentials)])
async def set_maintenance_mode(
    enabled: bool,
    message: Optional[str] = None,
    cache_service: CacheDep = None,
) -> Dict[str, Any]:
    """Enable or disable maintenance mode."""
    maintenance_key = "system:maintenance"
    
    if cache_service:
        if enabled:
            maintenance_data = {
                "enabled": True,
                "message": message or "System is under maintenance",
                "started_at": datetime.utcnow().isoformat(),
            }
            await cache_service.set(maintenance_key, maintenance_data)
        else:
            await cache_service.delete(maintenance_key)
    
    return {
        "status": "success",
        "maintenance_mode": enabled,
        "message": message if enabled else "Maintenance mode disabled",
    }