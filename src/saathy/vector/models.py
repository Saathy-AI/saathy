"""Pydantic models for vector operations."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """Represents a document with its vector embedding."""

    id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Document text content")
    embedding: list[float] = Field(..., description="Vector embedding of the document")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Document creation timestamp"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class SearchQuery(BaseModel):
    """Search query parameters."""

    query_text: str = Field(..., description="Text to search for")
    top_k: int = Field(
        default=10, ge=1, le=100, description="Number of results to return"
    )
    filters: Optional[dict[str, Any]] = Field(
        default=None, description="Metadata filters for search"
    )
    score_threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Minimum similarity score"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "query_text": "machine learning algorithms",
                "top_k": 5,
                "filters": {"category": "technology"},
                "score_threshold": 0.7,
            }
        }


class SearchResult(BaseModel):
    """Search result with document and similarity score."""

    document: VectorDocument = Field(..., description="Matched document")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional result metadata"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class EmbeddingStats(BaseModel):
    """Statistics for embedding operations."""

    model_name: str = Field(..., description="Name of the embedding model used")
    dimensions: int = Field(..., gt=0, description="Vector dimensions")
    processing_time: float = Field(
        ..., ge=0.0, description="Processing time in seconds"
    )
    batch_size: Optional[int] = Field(
        default=None, ge=1, description="Batch size used for processing"
    )
    total_vectors: Optional[int] = Field(
        default=None, ge=0, description="Total number of vectors processed"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "dimensions": 384,
                "processing_time": 1.23,
                "batch_size": 32,
                "total_vectors": 100,
            }
        }


class CollectionStats(BaseModel):
    """Collection statistics and metadata."""

    collection_name: str = Field(..., description="Name of the vector collection")
    vector_count: int = Field(
        ..., ge=0, description="Total number of vectors in collection"
    )
    vector_size: int = Field(
        ..., gt=0, description="Dimensions of vectors in collection"
    )
    points_count: int = Field(
        ..., ge=0, description="Total number of points (documents)"
    )
    segments_count: int = Field(
        ..., ge=0, description="Number of segments in collection"
    )
    status: str = Field(..., description="Collection status (green/yellow/red)")
    last_updated: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class BulkImportResult(BaseModel):
    """Result of bulk import operation."""

    total_documents: int = Field(..., ge=0, description="Total documents processed")
    successful_imports: int = Field(
        ..., ge=0, description="Successfully imported documents"
    )
    failed_imports: int = Field(..., ge=0, description="Failed imports")
    processing_time: float = Field(
        ..., ge=0.0, description="Total processing time in seconds"
    )
    errors: list[str] = Field(
        default_factory=list, description="list of error messages"
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_documents == 0:
            return 0.0
        return (self.successful_imports / self.total_documents) * 100
