from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected to WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            disconnected_websockets = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected_websockets.append(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected_websockets:
                self.active_connections[user_id].discard(ws)

manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# Function to notify users of new actions (called from action generator)
async def notify_new_action(user_id: str, action_data: dict):
    await manager.send_to_user(user_id, {
        "type": "new_action",
        "action": action_data
    })