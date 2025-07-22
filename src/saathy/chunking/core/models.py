"""Core data models for the chunking system."""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ContentType(Enum):
    """Content type enumeration."""
    TEXT = "text"
    CODE = "code"
    DOCUMENT = "document"
    MEETING = "meeting"
    GIT_COMMIT = "git_commit"
    SLACK_MESSAGE = "slack_message"
    EMAIL = "email"
    UNKNOWN = "unknown"


@dataclass
class ChunkMetadata:
    """Enhanced metadata for chunks."""
    content_type: ContentType
    source_file: Optional[str] = None
    source_line_start: Optional[int] = None
    source_line_end: Optional[int] = None
    chunk_id: Optional[str] = None
    parent_chunk_id: Optional[str] = None
    hierarchy_level: int = 0
    semantic_score: float = 0.0
    token_count: int = 0
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Enhanced content chunk with metadata."""
    content: str
    start_index: int
    end_index: int
    chunk_type: str
    metadata: ChunkMetadata
    overlap_with_previous: int = 0
    overlap_with_next: int = 0
    context_before: str = ""
    context_after: str = ""
    
    def __post_init__(self):
        """Generate chunk ID if not provided."""
        if not self.metadata.chunk_id:
            content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
            self.metadata.chunk_id = f"{self.chunk_type}_{content_hash}"
    
    @property
    def size(self) -> int:
        """Get chunk size in characters."""
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        """Get chunk word count."""
        return len(self.content.split())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert chunk to dictionary representation."""
        return {
            "content": self.content,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "chunk_type": self.chunk_type,
            "metadata": {
                "content_type": self.metadata.content_type.value,
                "source_file": self.metadata.source_file,
                "chunk_id": self.metadata.chunk_id,
                "token_count": self.metadata.token_count,
                "custom_fields": self.metadata.custom_fields
            },
            "overlap_with_previous": self.overlap_with_previous,
            "overlap_with_next": self.overlap_with_next,
            "context_before": self.context_before,
            "context_after": self.context_after
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        """Create chunk from dictionary representation."""
        metadata = ChunkMetadata(
            content_type=ContentType(data["metadata"]["content_type"]),
            source_file=data["metadata"].get("source_file"),
            chunk_id=data["metadata"].get("chunk_id"),
            token_count=data["metadata"].get("token_count", 0),
            custom_fields=data["metadata"].get("custom_fields", {})
        )
        
        return cls(
            content=data["content"],
            start_index=data["start_index"],
            end_index=data["end_index"],
            chunk_type=data["chunk_type"],
            metadata=metadata,
            overlap_with_previous=data.get("overlap_with_previous", 0),
            overlap_with_next=data.get("overlap_with_next", 0),
            context_before=data.get("context_before", ""),
            context_after=data.get("context_after", "")
        ) 