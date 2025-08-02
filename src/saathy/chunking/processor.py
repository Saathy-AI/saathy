"""Main chunking processor for intelligent text chunking."""

import logging
from pathlib import Path
from typing import Any, Optional

from .core import ChunkingConfig
from .core import ChunkingProcessor as ChunkingProcessorInterface
from .core import ChunkMetadata, ContentType
from .core.exceptions import StrategyNotFoundError
from .core.models import Chunk
from .strategies import (
    CodeChunker,
    DocumentChunker,
    EmailChunker,
    FixedSizeChunker,
    GitCommitChunker,
    MeetingChunker,
    SemanticChunker,
    SlackMessageChunker,
)
from .utils import (
    ChunkCache,
    ChunkMerger,
    ChunkQualityValidator,
    ContentTypeDetector,
    generate_content_hash,
)

logger = logging.getLogger(__name__)


class ChunkingProcessor(ChunkingProcessorInterface):
    """Main chunking processor for intelligent text chunking."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.config.validate()

        # Initialize utilities
        self.content_detector = ContentTypeDetector()
        self.quality_validator = ChunkQualityValidator(
            self.config.min_chunk_size, self.config.max_chunk_size
        )
        self.chunk_merger = ChunkMerger(
            self.config.min_chunk_size, self.config.max_chunk_size
        )
        self.cache = (
            ChunkCache(self.config.cache_ttl) if self.config.enable_caching else None
        )

        # Initialize chunking strategies
        self.strategies = self._initialize_strategies()

    def _initialize_strategies(self) -> dict[ContentType, Any]:
        """Initialize all chunking strategies."""
        return {
            ContentType.TEXT: SemanticChunker(
                self.config.max_chunk_size,
                self.config.overlap,
                self.config.min_chunk_size,
                self.config.preserve_context,
            ),
            ContentType.CODE: CodeChunker(
                self.config.max_chunk_size,
                self.config.overlap,
                self.config.min_chunk_size,
                self.config.preserve_context,
            ),
            ContentType.DOCUMENT: DocumentChunker(
                self.config.max_chunk_size,
                self.config.overlap,
                self.config.min_chunk_size,
                self.config.preserve_context,
            ),
            ContentType.MEETING: MeetingChunker(
                self.config.max_chunk_size,
                self.config.overlap,
                self.config.min_chunk_size,
                self.config.preserve_context,
            ),
            ContentType.GIT_COMMIT: GitCommitChunker(
                self.config.max_chunk_size,
                self.config.overlap,
                self.config.min_chunk_size,
                self.config.preserve_context,
            ),
            ContentType.SLACK_MESSAGE: SlackMessageChunker(
                self.config.max_chunk_size,
                self.config.overlap,
                self.config.min_chunk_size,
                self.config.preserve_context,
            ),
            ContentType.EMAIL: EmailChunker(
                self.config.max_chunk_size,
                self.config.overlap,
                self.config.min_chunk_size,
                self.config.preserve_context,
            ),
        }

    def chunk_content(
        self,
        content: str,
        content_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """Chunk content with automatic strategy selection."""
        # Generate content hash for caching
        content_hash = generate_content_hash(
            content,
            ContentType(content_type) if content_type else None,
            file_extension,
            self.config.max_chunk_size,
            self.config.overlap,
        )

        # Check cache first
        if self.cache:
            cached_chunks = self.cache.get(content_hash)
            if cached_chunks:
                logger.debug(f"Cache hit for content hash: {content_hash}")
                return cached_chunks

        # Detect content type if not provided
        if content_type is None:
            detected_type = self.content_detector.detect_content_type(
                content, file_extension
            )
            content_type_enum = ContentType(detected_type)
        else:
            content_type_enum = ContentType(content_type)

        # Select appropriate strategy
        strategy = self.strategies.get(content_type_enum)
        if not strategy:
            logger.warning(
                f"No strategy found for content type: {content_type_enum.value}"
            )
            strategy = self.strategies[ContentType.TEXT]

        # Create metadata
        chunk_metadata = ChunkMetadata(
            content_type=content_type_enum,
            source_file=metadata.get("source_file") if metadata else None,
            custom_fields=metadata or {},
        )

        # Perform chunking
        logger.info(f"Chunking content with {strategy.get_strategy_name()} strategy")
        try:
            chunks = strategy.chunk(content, chunk_metadata)
        except Exception as e:
            logger.warning(f"Strategy {strategy.get_strategy_name()} failed: {e}")
            # Fallback to semantic chunking
            fallback_strategy = self.strategies[ContentType.TEXT]
            logger.info(f"Falling back to {fallback_strategy.get_strategy_name()}")
            chunks = fallback_strategy.chunk(content, chunk_metadata)

        # Merge small chunks
        chunks = self.chunk_merger.merge_small_chunks(chunks)

        # Validate quality
        quality_metrics = self.quality_validator.validate_chunks(chunks, content)

        if not quality_metrics["valid"]:
            logger.warning(
                f"Chunking quality issues detected: {quality_metrics['quality_issues']}"
            )

        # Cache results
        if self.cache:
            self.cache.set(content_hash, chunks)

        return chunks

    def chunk_file(
        self, file_path: str, metadata: Optional[dict[str, Any]] = None
    ) -> list[Chunk]:
        """Chunk content from a file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            file_extension = Path(file_path).suffix
            file_metadata = metadata or {}
            file_metadata["source_file"] = file_path

            return self.chunk_content(
                content, file_extension=file_extension, metadata=file_metadata
            )

        except Exception as e:
            logger.error(f"Error chunking file {file_path}: {e}")
            raise

    def get_chunking_stats(self) -> dict[str, Any]:
        """Get chunking processor statistics."""
        stats = {
            "config": {
                "max_chunk_size": self.config.max_chunk_size,
                "overlap": self.config.overlap,
                "min_chunk_size": self.config.min_chunk_size,
                "preserve_context": self.config.preserve_context,
                "enable_caching": self.config.enable_caching,
                "enable_enterprise_features": self.config.enable_enterprise_features,
            },
            "strategies": {
                content_type.value: strategy.get_strategy_name()
                for content_type, strategy in self.strategies.items()
            },
        }

        if self.cache:
            stats["cache"] = self.cache.get_stats()

        return stats

    def add_strategy(self, content_type: ContentType, strategy: Any) -> None:
        """Add a custom chunking strategy."""
        self.strategies[content_type] = strategy
        logger.info(f"Added custom chunking strategy for {content_type.value}")

    def get_strategy(self, content_type: ContentType) -> Any:
        """Get a specific chunking strategy."""
        strategy = self.strategies.get(content_type)
        if not strategy:
            raise StrategyNotFoundError(
                f"No strategy found for content type: {content_type.value}"
            )
        return strategy

    def list_strategies(self) -> dict[str, str]:
        """list all available strategies."""
        return {
            content_type.value: strategy.get_strategy_name()
            for content_type, strategy in self.strategies.items()
        }


