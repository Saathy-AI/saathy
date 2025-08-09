"""Base interfaces for Saathy components."""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

from .models import (
    Chunk,
    ConnectorStatus,
    ProcessedContent,
)


class BaseConnector(ABC):
    """Base interface for all connectors."""
    
    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self.status = ConnectorStatus.INACTIVE
        self.logger = logging.getLogger(f"saathy.connector.{name}")
    
    @abstractmethod
    async def start(self) -> None:
        """Start the connector."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the connector."""
        pass
    
    @abstractmethod
    async def process_event(self, event_data: dict[str, Any]) -> list[ProcessedContent]:
        """Process an event and return processed content."""
        pass
    
    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Get the current status of the connector."""
        pass
    
    async def validate_config(self) -> bool:
        """Validate connector configuration."""
        return True
    
    async def health_check(self) -> bool:
        """Perform a health check."""
        return self.status == ConnectorStatus.ACTIVE


class BaseProcessor(ABC):
    """Base interface for content processors."""
    
    @abstractmethod
    async def process(self, content: ProcessedContent) -> ProcessedContent:
        """Process content and return enhanced version."""
        pass
    
    @abstractmethod
    async def batch_process(self, contents: list[ProcessedContent]) -> list[ProcessedContent]:
        """Process multiple contents in batch."""
        pass


class BaseChunker(ABC):
    """Base interface for text chunking strategies."""
    
    @abstractmethod
    async def chunk(self, content: ProcessedContent) -> list[Chunk]:
        """Split content into chunks."""
        pass
    
    @abstractmethod
    def estimate_chunks(self, content: str) -> int:
        """Estimate number of chunks for given content."""
        pass


class BaseEmbedder(ABC):
    """Base interface for embedding generation."""
    
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        pass


class BaseVectorStore(ABC):
    """Base interface for vector storage."""
    
    @abstractmethod
    async def upsert(self, chunks: list[Chunk]) -> list[str]:
        """Store chunks with embeddings."""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query_embedding: list[float], 
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None
    ) -> list[Chunk]:
        """Search for similar chunks."""
        pass
    
    @abstractmethod
    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by IDs."""
        pass
    
    @abstractmethod
    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        """Retrieve chunks by IDs."""
        pass


class BaseEventCorrelator(ABC):
    """Base interface for event correlation."""
    
    @abstractmethod
    async def correlate(self, events: list[ProcessedContent]) -> list[tuple[str, str, float]]:
        """Find correlations between events."""
        pass
    
    @abstractmethod
    async def add_event(self, event: ProcessedContent) -> None:
        """Add event to correlation index."""
        pass


class BaseActionGenerator(ABC):
    """Base interface for action generation."""
    
    @abstractmethod
    async def generate_actions(
        self, 
        user_id: str, 
        correlated_events: list[ProcessedContent]
    ) -> list[dict[str, Any]]:
        """Generate action recommendations from correlated events."""
        pass


class BaseScheduler(ABC):
    """Base interface for task scheduling."""
    
    @abstractmethod
    def add_job(
        self,
        func: Any,
        trigger: str,
        **kwargs: Any
    ) -> str:
        """Add a scheduled job."""
        pass
    
    @abstractmethod
    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job."""
        pass
    
    @abstractmethod
    def start(self) -> None:
        """Start the scheduler."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        pass


class BaseStreamHandler(ABC):
    """Base interface for streaming data handlers."""
    
    @abstractmethod
    async def handle_stream(
        self, 
        stream: AsyncGenerator[dict[str, Any], None]
    ) -> AsyncGenerator[ProcessedContent, None]:
        """Handle streaming data and yield processed content."""
        pass