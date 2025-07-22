"""Vector operations package."""

from .client import QdrantClientWrapper
from .exceptions import (
    BatchProcessingError,
    CollectionNotFoundError,
    EmbeddingDimensionError,
    EmbeddingModelError,
    SearchQueryError,
    VectorOperationError,
    VectorStoreConnectionError,
    VectorStoreError,
)
from .metrics import VectorMetrics, get_metrics, operation_timer, record_operation
from .models import (
    BulkImportResult,
    CollectionStats,
    EmbeddingStats,
    SearchQuery,
    SearchResult,
    VectorDocument,
)
from .repository import VectorRepository

__all__ = [
    # Models
    "VectorDocument",
    "SearchQuery",
    "SearchResult",
    "EmbeddingStats",
    "CollectionStats",
    "BulkImportResult",
    # Client
    "QdrantClientWrapper",
    # Repository
    "VectorRepository",
    # Metrics
    "VectorMetrics",
    "get_metrics",
    "operation_timer",
    "record_operation",
    # Exceptions
    "VectorStoreError",
    "VectorStoreConnectionError",
    "EmbeddingDimensionError",
    "CollectionNotFoundError",
    "VectorOperationError",
    "EmbeddingModelError",
    "BatchProcessingError",
    "SearchQueryError",
]
