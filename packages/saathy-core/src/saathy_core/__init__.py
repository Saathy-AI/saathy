"""Saathy Core - Shared models, interfaces, and utilities."""

from .models import (
    ContentType,
    ProcessingStatus,
    FeatureTier,
    Feature,
)
from .interfaces import (
    BaseConnector,
    BaseProcessor,
    BaseChunker,
    BaseEmbedder,
)
from .exceptions import (
    SaathyException,
    ConnectorException,
    ProcessingException,
    EmbeddingException,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "ContentType",
    "ProcessingStatus", 
    "FeatureTier",
    "Feature",
    # Interfaces
    "BaseConnector",
    "BaseProcessor",
    "BaseChunker",
    "BaseEmbedder",
    # Exceptions
    "SaathyException",
    "ConnectorException",
    "ProcessingException",
    "EmbeddingException",
]