"""Dashboard API module for Saathy V1"""

from .actions_api import router as actions_router
from .user_preferences import router as preferences_router
from .realtime_updates import websocket_endpoint, manager

__all__ = ['actions_router', 'preferences_router', 'websocket_endpoint', 'manager']