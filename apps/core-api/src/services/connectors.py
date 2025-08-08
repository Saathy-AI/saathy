"""Connector services."""

from typing import Dict, List, Any


class ConnectorManager:
    """Manages all connectors."""
    
    def __init__(self):
        self.connectors: Dict[str, Any] = {}
    
    async def register_connector(self, name: str, connector: Any) -> None:
        """Register a connector."""
        self.connectors[name] = connector
    
    async def start_all(self) -> None:
        """Start all registered connectors."""
        pass
    
    async def stop_all(self) -> None:
        """Stop all registered connectors."""
        pass
    
    async def get_active_connectors(self) -> List[str]:
        """Get list of active connectors."""
        return list(self.connectors.keys())


class GitHubConnectorService:
    """GitHub connector service."""
    
    def __init__(self, token: str, webhook_secret: str, owner: str, repo: str, 
                 vector_store=None, embedding_service=None):
        self.token = token
        self.webhook_secret = webhook_secret
        self.owner = owner
        self.repo = repo
        self.vector_store = vector_store
        self.embedding_service = embedding_service


class SlackConnectorService:
    """Slack connector service."""
    
    def __init__(self, bot_token: str, app_token: str, signing_secret: str,
                 default_channels: List[str], vector_store=None, embedding_service=None):
        self.bot_token = bot_token
        self.app_token = app_token
        self.signing_secret = signing_secret
        self.default_channels = default_channels
        self.vector_store = vector_store
        self.embedding_service = embedding_service


class NotionConnectorService:
    """Notion connector service."""
    
    def __init__(self, token: str, databases: List[str], pages: List[str],
                 poll_interval: int, vector_store=None, embedding_service=None):
        self.token = token
        self.databases = databases
        self.pages = pages
        self.poll_interval = poll_interval
        self.vector_store = vector_store
        self.embedding_service = embedding_service