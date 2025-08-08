"""Connector management endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, Field

from ..dependencies import (
    ConnectorManagerDep,
    VectorStoreDep,
    EmbeddingDep,
    SettingsDep,
)

router = APIRouter()


class ConnectorResponse(BaseModel):
    """Connector status response."""
    name: str
    status: str
    uptime_seconds: Optional[float] = None
    processed_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class SyncRequest(BaseModel):
    """Manual sync request."""
    full_sync: bool = False
    since: Optional[datetime] = None
    limit: Optional[int] = 100


class ChannelInfo(BaseModel):
    """Slack channel information."""
    id: str
    name: str
    is_member: bool
    is_private: bool
    num_members: Optional[int] = None


# GitHub Connector Endpoints
@router.get("/github/status", response_model=ConnectorResponse)
async def github_connector_status(
    connector_manager: ConnectorManagerDep,
) -> ConnectorResponse:
    """Get GitHub connector status and metrics."""
    connector = await connector_manager.get_connector("github")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub connector not found"
        )
    
    status_data = await connector.get_status()
    return ConnectorResponse(**status_data)


@router.post("/github/sync", response_model=Dict[str, Any])
async def github_manual_sync(
    sync_request: SyncRequest,
    connector_manager: ConnectorManagerDep,
    vector_store: VectorStoreDep,
    embedding_service: EmbeddingDep,
) -> Dict[str, Any]:
    """Manually trigger GitHub repository synchronization."""
    connector = await connector_manager.get_connector("github")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub connector not found"
        )
    
    if connector.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"GitHub connector is not active (status: {connector.status})"
        )
    
    try:
        # Perform sync
        sync_result = await connector.sync_repository(
            full_sync=sync_request.full_sync,
            since=sync_request.since,
            limit=sync_request.limit
        )
        
        # Process and store content
        processed_count = 0
        for content in sync_result.get("contents", []):
            # Generate embeddings
            embedding = await embedding_service.embed(content.content)
            content.embedding = embedding
            
            # Store in vector database
            await vector_store.upsert([content])
            processed_count += 1
        
        return {
            "status": "success",
            "synced_at": datetime.utcnow().isoformat(),
            "processed_count": processed_count,
            "commits": sync_result.get("commits", 0),
            "issues": sync_result.get("issues", 0),
            "pull_requests": sync_result.get("pull_requests", 0),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


# Slack Connector Endpoints
@router.get("/slack/status", response_model=ConnectorResponse)
async def slack_connector_status(
    connector_manager: ConnectorManagerDep,
) -> ConnectorResponse:
    """Get Slack connector status and metrics."""
    connector = await connector_manager.get_connector("slack")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack connector not found"
        )
    
    status_data = await connector.get_status()
    return ConnectorResponse(**status_data)


@router.post("/slack/start", response_model=Dict[str, str])
async def start_slack_connector(
    connector_manager: ConnectorManagerDep,
) -> Dict[str, str]:
    """Start the Slack connector."""
    connector = await connector_manager.get_connector("slack")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack connector not found"
        )
    
    if connector.status == "active":
        return {"status": "already_running", "message": "Slack connector is already active"}
    
    try:
        await connector.start()
        return {"status": "started", "message": "Slack connector started successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Slack connector: {str(e)}"
        )


@router.post("/slack/stop", response_model=Dict[str, str])
async def stop_slack_connector(
    connector_manager: ConnectorManagerDep,
) -> Dict[str, str]:
    """Stop the Slack connector."""
    connector = await connector_manager.get_connector("slack")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack connector not found"
        )
    
    if connector.status == "inactive":
        return {"status": "already_stopped", "message": "Slack connector is already inactive"}
    
    try:
        await connector.stop()
        return {"status": "stopped", "message": "Slack connector stopped successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop Slack connector: {str(e)}"
        )


@router.get("/slack/channels", response_model=List[ChannelInfo])
async def get_slack_channels(
    connector_manager: ConnectorManagerDep,
    include_private: bool = Query(False, description="Include private channels"),
) -> List[ChannelInfo]:
    """Get list of available Slack channels."""
    connector = await connector_manager.get_connector("slack")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack connector not found"
        )
    
    if connector.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slack connector is not active (status: {connector.status})"
        )
    
    try:
        channels = await connector.list_channels(include_private=include_private)
        return [
            ChannelInfo(
                id=channel["id"],
                name=channel["name"],
                is_member=channel.get("is_member", False),
                is_private=channel.get("is_private", False),
                num_members=channel.get("num_members"),
            )
            for channel in channels
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch channels: {str(e)}"
        )


# Notion Connector Endpoints
@router.get("/notion/status", response_model=ConnectorResponse)
async def notion_connector_status(
    connector_manager: ConnectorManagerDep,
) -> ConnectorResponse:
    """Get Notion connector status and metrics."""
    connector = await connector_manager.get_connector("notion")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notion connector not found"
        )
    
    status_data = await connector.get_status()
    return ConnectorResponse(**status_data)


@router.post("/notion/start", response_model=Dict[str, str])
async def start_notion_connector(
    connector_manager: ConnectorManagerDep,
) -> Dict[str, str]:
    """Start the Notion connector polling."""
    connector = await connector_manager.get_connector("notion")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notion connector not found"
        )
    
    if connector.status == "active":
        return {"status": "already_running", "message": "Notion connector is already active"}
    
    try:
        await connector.start()
        return {"status": "started", "message": "Notion connector started successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Notion connector: {str(e)}"
        )


@router.post("/notion/stop", response_model=Dict[str, str])
async def stop_notion_connector(
    connector_manager: ConnectorManagerDep,
) -> Dict[str, str]:
    """Stop the Notion connector polling."""
    connector = await connector_manager.get_connector("notion")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notion connector not found"
        )
    
    if connector.status == "inactive":
        return {"status": "already_stopped", "message": "Notion connector is already inactive"}
    
    try:
        await connector.stop()
        return {"status": "stopped", "message": "Notion connector stopped successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop Notion connector: {str(e)}"
        )


@router.post("/notion/sync", response_model=Dict[str, Any])
async def trigger_notion_sync(
    sync_request: SyncRequest,
    connector_manager: ConnectorManagerDep,
    vector_store: VectorStoreDep,
    embedding_service: EmbeddingDep,
) -> Dict[str, Any]:
    """Manually trigger Notion synchronization."""
    connector = await connector_manager.get_connector("notion")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notion connector not found"
        )
    
    if connector.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Notion connector is not active (status: {connector.status})"
        )
    
    try:
        # Perform sync
        sync_result = await connector.sync_content(
            full_sync=sync_request.full_sync,
            since=sync_request.since,
        )
        
        # Process and store content
        processed_count = 0
        for content in sync_result.get("contents", []):
            # Generate embeddings
            embedding = await embedding_service.embed(content.content)
            content.embedding = embedding
            
            # Store in vector database
            await vector_store.upsert([content])
            processed_count += 1
        
        return {
            "status": "success",
            "synced_at": datetime.utcnow().isoformat(),
            "processed_count": processed_count,
            "pages": sync_result.get("pages", 0),
            "databases": sync_result.get("databases", 0),
            "blocks": sync_result.get("blocks", 0),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )