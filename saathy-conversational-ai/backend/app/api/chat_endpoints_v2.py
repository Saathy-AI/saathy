"""
Chat API v2 - Enhanced endpoints using the agentic chat service.
Includes metrics, feedback, and analytics endpoints.
"""

import json
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatMessage, ChatResponse, ChatSession
from app.services.agentic_chat_service import AgenticChatService
from app.utils.auth import get_current_user
from app.utils.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/chat", tags=["chat-v2"])

# Initialize the agentic chat service
chat_service = AgenticChatService()


class CreateSessionRequest(BaseModel):
    """Request model for creating a new chat session"""

    metadata: Optional[dict[str, Any]] = None


class UserFeedback(BaseModel):
    """Model for user feedback on responses"""

    relevance_score: Optional[float] = None  # 0-1
    completeness_score: Optional[float] = None  # 0-1
    helpful: Optional[bool] = None
    feedback_text: Optional[str] = None


@router.post("/sessions", response_model=ChatSession)
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new chat session with the agentic system.

    This initializes:
    - Session state in database and Redis
    - Memory management
    - Metrics tracking
    """
    try:
        session = await chat_service.create_session(
            user_id=current_user["user_id"], db=db
        )

        logger.info(
            f"Created agentic chat session {session.id} for user {current_user['user_id']}"
        )
        return session

    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create session") from e


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: UUID,
    message: ChatMessage,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to the agentic chat system.

    Features:
    - Multi-agent processing with LangGraph
    - Intelligent context retrieval with RRF
    - Dynamic context expansion
    - Response caching
    - Quality metrics tracking
    """
    try:
        response = await chat_service.process_message(
            session_id=str(session_id), message=message, db=db
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to process message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process message") from e


@router.post("/sessions/{session_id}/feedback")
async def submit_feedback(
    session_id: UUID,
    feedback: UserFeedback,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit user feedback for a conversation.

    This feedback is used to:
    - Track user satisfaction
    - Identify quality issues
    - Trigger learning optimizations
    - Improve future responses
    """
    try:
        await chat_service.process_user_feedback(
            session_id=str(session_id), feedback=feedback.dict(exclude_none=True)
        )

        return {"status": "feedback_received"}

    except Exception as e:
        logger.error(f"Failed to process feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process feedback") from e


@router.get("/sessions/{session_id}/metrics")
async def get_session_metrics(
    session_id: UUID, current_user: dict = Depends(get_current_user)
):
    """
    Get detailed metrics for a specific chat session.

    Returns:
    - Response times
    - Sufficiency scores
    - Expansion rates
    - Error rates
    - Intent distribution
    """
    try:
        metrics = await chat_service.get_session_metrics(str(session_id))

        if "error" in metrics:
            raise HTTPException(status_code=404, detail=metrics["error"])

        return metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get metrics") from e


@router.get("/metrics/system")
async def get_system_metrics(current_user: dict = Depends(get_current_user)):
    """
    Get overall system metrics and performance data.

    Returns:
    - Quality metrics (response times, sufficiency, errors)
    - Cache performance
    - Learning optimization status
    - Current system parameters
    """
    try:
        metrics = await chat_service.get_system_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get metrics") from e


@router.get("/analytics/export")
async def export_analytics(current_user: dict = Depends(get_current_user)):
    """
    Export comprehensive analytics data for analysis.

    Includes:
    - Problematic conversations
    - Learning queue items
    - Performance trends
    - User behavior patterns

    Note: This endpoint may be slow for large datasets.
    """
    try:
        # Check if user has admin privileges (implement your own logic)
        # if not is_admin(current_user):
        #     raise HTTPException(status_code=403, detail="Admin access required")

        analytics = await chat_service.export_analytics()
        return analytics

    except Exception as e:
        logger.error(f"Failed to export analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export analytics") from e


@router.websocket("/sessions/{session_id}/ws")
async def websocket_chat(
    websocket: WebSocket, session_id: UUID, db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat with the agentic system.

    Features:
    - Real-time message processing
    - Typing indicators
    - Live metrics updates
    - Error handling
    """
    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Send typing indicator
            await websocket.send_json({"type": "typing", "status": "processing"})

            # Process message
            try:
                message = ChatMessage(content=message_data["content"])
                response = await chat_service.process_message(
                    session_id=str(session_id), message=message, db=db
                )

                # Send response
                await websocket.send_json(
                    {
                        "type": "message",
                        "response": response.response,
                        "context_used": response.context_used,
                        "metadata": response.metadata,
                    }
                )

            except Exception as e:
                # Send error
                await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()


# Health check endpoint
@router.get("/health")
async def health_check():
    """Check if the agentic chat service is healthy"""
    try:
        # Could add more sophisticated health checks here
        return {
            "status": "healthy",
            "service": "agentic-chat-v2",
            "initialized": chat_service.initialized,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
