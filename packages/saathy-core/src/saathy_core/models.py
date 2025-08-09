"""Core models used throughout Saathy."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Types of content that can be processed."""
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    DOCUMENT = "document"
    EMAIL = "email"
    MEETING = "meeting"
    SLACK_MESSAGE = "slack_message"
    GIT_COMMIT = "git_commit"


class ProcessingStatus(str, Enum):
    """Status of content processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConnectorStatus(str, Enum):
    """Status of a connector."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class FeatureTier(str, Enum):
    """Feature availability tiers."""
    OPEN_SOURCE = "open_source"
    ENTERPRISE = "enterprise"


class ProcessedContent(BaseModel):
    """Processed content from any source."""
    id: str
    content: str
    content_type: ContentType
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    raw_data: dict[str, Any] = Field(default_factory=dict)
    
    # Optional fields for enhanced processing
    title: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    parent_id: Optional[str] = None
    embedding_id: Optional[str] = None
    chunk_ids: list[str] = Field(default_factory=list)


class ChunkMetadata(BaseModel):
    """Metadata for a text chunk."""
    source: str
    content_type: ContentType
    chunk_index: int
    total_chunks: int
    parent_id: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A chunk of text with metadata."""
    id: str
    content: str
    metadata: ChunkMetadata
    embedding: Optional[list[float]] = None
    tokens: Optional[int] = None


class Feature(BaseModel):
    """Feature definition with tier information."""
    name: str
    description: str
    tier: FeatureTier
    enabled: bool = True
    
    def is_available(self, license_tier: str) -> bool:
        """Check if feature is available for given license tier."""
        if self.tier == FeatureTier.OPEN_SOURCE:
            return self.enabled
        return license_tier == "enterprise" and self.enabled


class ConnectorConfig(BaseModel):
    """Base configuration for connectors."""
    enabled: bool = True
    poll_interval: int = 300  # seconds
    batch_size: int = 100
    max_retries: int = 3
    timeout: int = 30


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    dimension: int = 384
    normalize: bool = True


class VectorConfig(BaseModel):
    """Configuration for vector storage."""
    collection_name: str = "saathy_content"
    distance_metric: str = "cosine"
    indexed_fields: list[str] = Field(default_factory=lambda: ["content_type", "source"])


class EventCorrelation(BaseModel):
    """Correlation between events across platforms."""
    id: str
    event_ids: list[str]
    correlation_score: float
    correlation_type: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionRecommendation(BaseModel):
    """AI-generated action recommendation."""
    id: str
    user_id: str
    title: str
    description: str
    priority: str  # high, medium, low
    action_type: str
    platform_links: dict[str, str] = Field(default_factory=dict)
    correlated_events: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None
    feedback: Optional[str] = None