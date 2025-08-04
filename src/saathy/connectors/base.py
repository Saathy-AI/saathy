import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ContentType(str, Enum):
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"


class ConnectorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ProcessedContent(BaseModel):
    id: str
    content: str
    content_type: ContentType
    source: str
    metadata: dict[str, Any]
    timestamp: datetime
    raw_data: dict[str, Any]


class BaseConnector(ABC):
    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self.status = ConnectorStatus.INACTIVE
        self.logger = logging.getLogger(f"saathy.connector.{name}")

    @abstractmethod
    async def start(self) -> None:
        """Start the connector"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the connector"""
        pass

    @abstractmethod
    async def process_event(self, event_data: dict[str, Any]) -> list[ProcessedContent]:
        """Process incoming event data into ProcessedContent objects"""
        pass

    async def health_check(self) -> bool:
        """Check connector health"""
        return self.status == ConnectorStatus.ACTIVE

    def get_status(self) -> dict[str, Any]:
        """Get connector status and metrics"""
        return {
            "name": self.name,
            "status": self.status.value,
            "config": {
                k: v
                for k, v in self.config.items()
                if "token" not in k.lower() and "secret" not in k.lower()
            },
        }
