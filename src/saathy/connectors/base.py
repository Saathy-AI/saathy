from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

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
    metadata: Dict[str, Any]
    timestamp: datetime
    raw_data: Dict[str, Any]

class BaseConnector(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.status = ConnectorStatus.INACTIVE

    @abstractmethod
    async def start(self) -> None:
        """Start the connector"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the connector"""
        pass
    
    @abstractmethod
    async def process_event(self, event_data: Dict[str, Any]) -> List[ProcessedContent]:
        """Process incoming event data"""
        pass
    
    async def health_check(self) -> bool:
        """Check connector health"""
        return self.status == ConnectorStatus.ACTIVE
