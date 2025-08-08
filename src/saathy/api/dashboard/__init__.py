"""Dashboard API module for Saathy V1"""

from .actions_api import router as actions_router
from .realtime_updates import manager, websocket_endpoint
from .user_preferences import router as preferences_router

__all__ = ["actions_router", "preferences_router", "websocket_endpoint", "manager"]
