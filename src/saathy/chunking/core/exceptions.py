"""Custom exceptions for the chunking system."""


class ChunkingError(Exception):
    """Base exception for chunking-related errors."""

    pass


class ValidationError(ChunkingError):
    """Exception raised when chunking validation fails."""

    pass


class StrategyNotFoundError(ChunkingError):
    """Exception raised when a chunking strategy is not found."""

    pass


class ContentTypeDetectionError(ChunkingError):
    """Exception raised when content type detection fails."""

    pass


class ChunkingConfigurationError(ChunkingError):
    """Exception raised when chunking configuration is invalid."""

    pass


class CacheError(ChunkingError):
    """Exception raised when cache operations fail."""

    pass


class QualityValidationError(ChunkingError):
    """Exception raised when quality validation fails."""

    pass
