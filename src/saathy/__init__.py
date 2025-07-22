"""Saathy - Intelligent Document Processing and Vector Search."""

__version__ = "0.1.0"

from .api import app
from .chunking import ChunkingProcessor
from .config import settings
from .embedding import EmbeddingService
from .vector import VectorRepository

__all__ = [
    "__version__",
    "app",
    "settings",
    "VectorRepository",
    "EmbeddingService",
    "ChunkingProcessor",
]
