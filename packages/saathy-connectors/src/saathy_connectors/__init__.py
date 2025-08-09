"""Saathy Connectors - Platform integration framework."""

from .base import BaseConnector, ConnectorStatus
from .github import GitHubConnector
from .slack import SlackConnector
from .notion import NotionConnector
from .manager import ConnectorManager

__version__ = "0.1.0"

__all__ = [
    "BaseConnector",
    "ConnectorStatus",
    "GitHubConnector",
    "SlackConnector",
    "NotionConnector",
    "ConnectorManager",
]