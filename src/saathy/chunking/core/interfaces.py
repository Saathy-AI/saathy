"""Core interfaces and configuration for the chunking system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from .models import Chunk, ChunkMetadata


@dataclass
class ChunkingConfig:
    """Configuration for chunking operations."""

    max_chunk_size: int = 512
    overlap: int = 50
    min_chunk_size: int = 50
    preserve_context: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600
    parallel_processing: bool = False
    max_workers: int = 4

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be positive")
        if self.overlap < 0:
            raise ValueError("overlap must be non-negative")
        if self.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be positive")
        if self.min_chunk_size > self.max_chunk_size:
            raise ValueError("min_chunk_size cannot be greater than max_chunk_size")
        if self.overlap >= self.max_chunk_size:
            raise ValueError(
                "overlap cannot be greater than or equal to max_chunk_size"
            )
        if self.max_workers <= 0:
            raise ValueError("max_workers must be positive")


class ChunkingStrategy(ABC):
    """Base class for chunking strategies."""

    def __init__(
        self,
        max_chunk_size: int = 512,
        overlap: int = 50,
        min_chunk_size: int = 50,
        preserve_context: bool = True,
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.preserve_context = preserve_context

    @abstractmethod
    def chunk(
        self, content: str, metadata: Optional[ChunkMetadata] = None
    ) -> list[Chunk]:
        """Split content into chunks."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass

    def _add_context(self, chunks: list[Chunk], original_content: str) -> list[Chunk]:
        """Add context before and after chunks."""
        if not self.preserve_context:
            return chunks

        for i, chunk in enumerate(chunks):
            # Add context before
            if i > 0:
                prev_chunk = chunks[i - 1]
                context_start = max(0, prev_chunk.end_index - self.overlap)
                chunk.context_before = original_content[
                    context_start : chunk.start_index
                ]

            # Add context after
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                context_end = min(
                    len(original_content), next_chunk.start_index + self.overlap
                )
                chunk.context_after = original_content[chunk.end_index : context_end]

        return chunks

    def _validate_chunk(self, chunk: Chunk) -> bool:
        """Validate individual chunk."""
        return (
            len(chunk.content) >= self.min_chunk_size
            and len(chunk.content) <= self.max_chunk_size
        )


class ChunkingProcessor(ABC):
    """Abstract interface for chunking processor."""

    @abstractmethod
    def chunk_content(
        self,
        content: str,
        content_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """Chunk content with automatic strategy selection."""
        pass

    @abstractmethod
    def chunk_file(
        self, file_path: str, metadata: Optional[dict[str, Any]] = None
    ) -> list[Chunk]:
        """Chunk content from a file."""
        pass

    @abstractmethod
    def get_chunking_stats(self) -> dict[str, Any]:
        """Get chunking processor statistics."""
        pass


class ContentTypeDetector(ABC):
    """Abstract interface for content type detection."""

    @abstractmethod
    def detect_content_type(
        self, content: str, file_extension: Optional[str] = None
    ) -> str:
        """Detect content type based on patterns and file extension."""
        pass


class ChunkQualityValidator(ABC):
    """Abstract interface for chunk quality validation."""

    @abstractmethod
    def validate_chunks(
        self, chunks: list[Chunk], original_content: str
    ) -> dict[str, Any]:
        """Validate chunk quality and return metrics."""
        pass


class ChunkMerger(ABC):
    """Abstract interface for chunk merging."""

    @abstractmethod
    def merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge chunks that are too small."""
        pass


class ChunkCache(ABC):
    """Abstract interface for chunk caching."""

    @abstractmethod
    def get(self, content_hash: str) -> Optional[list[Chunk]]:
        """Get cached chunks if not expired."""
        pass

    @abstractmethod
    def set(self, content_hash: str, chunks: list[Chunk]) -> None:
        """Cache chunks with timestamp."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached entries."""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        pass
