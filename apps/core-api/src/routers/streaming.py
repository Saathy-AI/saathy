"""Streaming endpoints for real-time updates."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..dependencies import (
    CacheDep,
    ConnectorManagerDep,
    VectorStoreDep,
    IntelligenceDep,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def event_stream(
    user_id: str,
    cache_service: CacheDep,
    connector_manager: ConnectorManagerDep,
    intelligence_service: IntelligenceDep,
    include_actions: bool = True,
    include_events: bool = True,
    include_correlations: bool = False,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a user."""
    logger.info(f"Starting event stream for user {user_id}")
    
    # Channel for user events
    event_channel = f"events:user:{user_id}"
    action_channel = f"actions:user:{user_id}"
    
    try:
        # Subscribe to Redis channels if available
        if cache_service:
            await cache_service.subscribe(event_channel, action_channel)
        
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'user_id': user_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        
        # Send current state
        if include_actions and intelligence_service:
            actions = await intelligence_service.get_user_actions(user_id, limit=5)
            yield f"event: actions\ndata: {json.dumps({'actions': actions})}\n\n"
        
        # Main event loop
        last_heartbeat = datetime.utcnow()
        
        while True:
            try:
                # Check for messages from Redis
                if cache_service:
                    message = await cache_service.get_message(timeout=0.1)
                    
                    if message and message.get('type') == 'message':
                        channel = message.get('channel', '')
                        data = message.get('data')
                        
                        if channel == event_channel and include_events:
                            yield f"event: platform_event\ndata: {json.dumps(data)}\n\n"
                        elif channel == action_channel and include_actions:
                            yield f"event: action_update\ndata: {json.dumps(data)}\n\n"
                
                # Send heartbeat every 30 seconds
                if (datetime.utcnow() - last_heartbeat).total_seconds() > 30:
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    last_heartbeat = datetime.utcnow()
                
                # Check for new correlations periodically
                if include_correlations and intelligence_service:
                    # This would be triggered by actual events in production
                    pass
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                logger.info(f"Event stream cancelled for user {user_id}")
                break
            except Exception as e:
                logger.error(f"Error in event stream for user {user_id}: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"Fatal error in event stream: {e}")
        yield f"event: error\ndata: {json.dumps({'error': 'Stream terminated'})}\n\n"
    
    finally:
        logger.info(f"Closing event stream for user {user_id}")
        yield f"event: close\ndata: {json.dumps({'reason': 'Stream closed'})}\n\n"


@router.get("/events/user/{user_id}")
async def stream_user_events(
    user_id: str,
    cache_service: CacheDep,
    connector_manager: ConnectorManagerDep,
    intelligence_service: IntelligenceDep,
    include_actions: bool = Query(True, description="Include action recommendations"),
    include_events: bool = Query(True, description="Include platform events"),
    include_correlations: bool = Query(False, description="Include event correlations"),
) -> EventSourceResponse:
    """
    Stream real-time events for a user using Server-Sent Events (SSE).
    
    Event types:
    - connected: Initial connection established
    - platform_event: New event from GitHub/Slack/Notion
    - action_update: New or updated action recommendation
    - correlation: New event correlation detected
    - heartbeat: Keep-alive signal
    - error: Error occurred
    - close: Stream is closing
    """
    return EventSourceResponse(
        event_stream(
            user_id,
            cache_service,
            connector_manager,
            intelligence_service,
            include_actions,
            include_events,
            include_correlations,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )


@router.post("/events/broadcast")
async def broadcast_event(
    event_data: Dict[str, Any],
    cache_service: CacheDep,
    platform: str = Query(..., regex="^(github|slack|notion|system)$"),
    event_type: str = Query(..., description="Type of event"),
    user_id: Optional[str] = Query(None, description="Target user ID"),
) -> Dict[str, str]:
    """
    Broadcast an event to connected clients.
    
    This endpoint is typically called by connectors or internal services
    to notify clients of new events.
    """
    if not cache_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available for broadcasting"
        )
    
    try:
        # Prepare event
        event = {
            "id": event_data.get("id", str(datetime.utcnow().timestamp())),
            "platform": platform,
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": event_data,
        }
        
        # Determine channel
        if user_id:
            channel = f"events:user:{user_id}"
        else:
            channel = f"events:platform:{platform}"
        
        # Publish to Redis
        subscribers = await cache_service.publish(channel, event)
        
        logger.info(
            f"Broadcasted {event_type} event to {subscribers} subscribers "
            f"on channel {channel}"
        )
        
        return {
            "status": "success",
            "channel": channel,
            "subscribers": str(subscribers),
            "event_id": event["id"],
        }
    
    except Exception as e:
        logger.error(f"Failed to broadcast event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to broadcast event: {str(e)}"
        )


@router.get("/stream/connectors")
async def stream_connector_status(
    connector_manager: ConnectorManagerDep,
    cache_service: CacheDep,
) -> EventSourceResponse:
    """
    Stream real-time connector status updates.
    
    Useful for monitoring connector health and activity.
    """
    async def connector_stream():
        """Generate connector status events."""
        try:
            # Send initial status
            all_status = await connector_manager.get_all_status()
            yield f"event: status\ndata: {json.dumps(all_status)}\n\n"
            
            # Subscribe to connector status channel
            if cache_service:
                await cache_service.subscribe("connectors:status")
            
            last_check = datetime.utcnow()
            
            while True:
                try:
                    # Check for status updates from Redis
                    if cache_service:
                        message = await cache_service.get_message(timeout=0.1)
                        
                        if message and message.get('type') == 'message':
                            yield f"event: status_update\ndata: {json.dumps(message.get('data'))}\n\n"
                    
                    # Periodic full status check every 10 seconds
                    if (datetime.utcnow() - last_check).total_seconds() > 10:
                        all_status = await connector_manager.get_all_status()
                        yield f"event: status\ndata: {json.dumps(all_status)}\n\n"
                        last_check = datetime.utcnow()
                    
                    await asyncio.sleep(0.1)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in connector stream: {e}")
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    await asyncio.sleep(1)
        
        finally:
            yield f"event: close\ndata: {json.dumps({'reason': 'Stream closed'})}\n\n"
    
    return EventSourceResponse(
        connector_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.websocket("/ws/user/{user_id}")
async def websocket_endpoint(
    websocket,  # WebSocket from FastAPI
    user_id: str,
    connector_manager: ConnectorManagerDep,
    intelligence_service: IntelligenceDep,
    cache_service: CacheDep,
):
    """
    WebSocket endpoint for bidirectional real-time communication.
    
    Supports:
    - Receiving commands from client
    - Sending real-time updates
    - Interactive queries
    """
    await websocket.accept()
    
    try:
        logger.info(f"WebSocket connection established for user {user_id}")
        
        # Send initial data
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Subscribe to user channels
        if cache_service:
            await cache_service.subscribe(
                f"events:user:{user_id}",
                f"actions:user:{user_id}",
            )
        
        # Create tasks for receiving and sending
        async def receive_messages():
            """Handle incoming WebSocket messages."""
            while True:
                try:
                    data = await websocket.receive_json()
                    message_type = data.get("type")
                    
                    if message_type == "ping":
                        await websocket.send_json({"type": "pong"})
                    
                    elif message_type == "get_actions":
                        if intelligence_service:
                            actions = await intelligence_service.get_user_actions(
                                user_id,
                                limit=data.get("limit", 10)
                            )
                            await websocket.send_json({
                                "type": "actions",
                                "actions": actions,
                            })
                    
                    elif message_type == "complete_action":
                        action_id = data.get("action_id")
                        if action_id and intelligence_service:
                            success = await intelligence_service.mark_action_completed(action_id)
                            await websocket.send_json({
                                "type": "action_completed",
                                "action_id": action_id,
                                "success": success,
                            })
                    
                except Exception as e:
                    logger.error(f"Error receiving WebSocket message: {e}")
                    break
        
        async def send_updates():
            """Send updates from Redis to WebSocket."""
            while True:
                try:
                    if cache_service:
                        message = await cache_service.get_message(timeout=0.1)
                        
                        if message and message.get('type') == 'message':
                            await websocket.send_json({
                                "type": "update",
                                "channel": message.get('channel'),
                                "data": message.get('data'),
                            })
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error sending WebSocket update: {e}")
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            receive_messages(),
            send_updates(),
        )
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    
    finally:
        logger.info(f"WebSocket connection closed for user {user_id}")
        await websocket.close()