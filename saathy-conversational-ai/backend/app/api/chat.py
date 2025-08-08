import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user  # Placeholder for auth
from app.models.chat_session import ChatMessage, ChatResponse, ChatSession
from app.services.chat_service import ChatService
from app.utils.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])
chat_service = ChatService()

# In-memory WebSocket connections (in production, use Redis pub/sub)
active_connections: dict[str, WebSocket] = {}


@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Create a new chat session"""
    try:
        session = await chat_service.create_session(current_user, db)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    message: ChatMessage,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response"""
    try:
        # Ensure session_id matches
        message.session_id = session_id

        # Process message
        response = await chat_service.process_message(message, current_user, db)

        # Send to WebSocket if connected
        if current_user in active_connections:
            await active_connections[current_user].send_json(
                {"type": "response", "data": response.dict()}
            )

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sessions/{session_id}/history", response_model=ChatSession)
async def get_session_history(
    session_id: str,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation history for a session"""
    try:
        session = await chat_service.get_session_history(session_id, current_user, db)
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/sessions/{session_id}")
async def end_session(
    session_id: str,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a chat session"""
    try:
        await chat_service.end_session(session_id, current_user, db)
        return {"message": "Session ended successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_id: str, db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()

    # In production, verify user authentication via token
    user_id = None

    try:
        # Initial authentication
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)
        user_id = auth_data.get("user_id")  # In production, verify token

        if not user_id:
            await websocket.send_json({"error": "Authentication required"})
            await websocket.close()
            return

        # Store connection
        active_connections[user_id] = websocket

        # Send connection confirmation
        await websocket.send_json({"type": "connected", "session_id": session_id})

        # Handle messages
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Send typing indicator
            await websocket.send_json({"type": "typing", "is_typing": True})

            # Process message
            message = ChatMessage(
                message=message_data["message"], session_id=session_id
            )

            try:
                response = await chat_service.process_message(message, user_id, db)

                # Send response
                await websocket.send_json({"type": "response", "data": response.dict()})

                # Stop typing indicator
                await websocket.send_json({"type": "typing", "is_typing": False})

            except Exception as e:
                await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        if user_id and user_id in active_connections:
            del active_connections[user_id]
    except Exception as e:
        print(f"WebSocket error: {e}")
        if user_id and user_id in active_connections:
            del active_connections[user_id]
        await websocket.close()


# Placeholder auth function - implement actual authentication
async def get_current_user(authorization: Optional[str] = None) -> str:
    """Get current user from auth token"""
    # In production, verify JWT token and extract user_id
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    # For demo purposes, return a test user
    return "test_user_123"
