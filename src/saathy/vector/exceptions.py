"""Custom exceptions for vector operations."""


class VectorStoreError(Exception):
    """Base exception for vector store operations."""

    def __init__(self, message: str, details: str = None):
        """Initialize with message and optional details."""
        super().__init__(message)
        self.details = details


class VectorStoreConnectionError(VectorStoreError):
    """Raised when unable to connect to Qdrant."""

    def __init__(
        self, message: str = "Failed to connect to vector store", details: str = None
    ):
        """Initialize connection error."""
        super().__init__(message, details)


class EmbeddingDimensionError(VectorStoreError):
    """Raised when vector dimensions don't match collection configuration."""

    def __init__(self, expected: int, actual: int, details: str = None):
        """Initialize dimension error with expected and actual dimensions."""
        message = f"Vector dimension mismatch: expected {expected}, got {actual}"
        super().__init__(message, details)
        self.expected_dimensions = expected
        self.actual_dimensions = actual


class CollectionNotFoundError(VectorStoreError):
    """Raised when a collection doesn't exist."""

    def __init__(self, collection_name: str, details: str = None):
        """Initialize collection not found error."""
        message = f"Collection '{collection_name}' not found"
        super().__init__(message, details)
        self.collection_name = collection_name


class VectorOperationError(VectorStoreError):
    """Raised when a vector operation fails."""

    def __init__(self, operation: str, message: str = None, details: str = None):
        """Initialize operation error."""
        if message is None:
            message = f"Vector operation '{operation}' failed"
        super().__init__(message, details)
        self.operation = operation


class EmbeddingModelError(VectorStoreError):
    """Raised when embedding model operations fail."""

    def __init__(self, model_name: str, message: str = None, details: str = None):
        """Initialize embedding model error."""
        if message is None:
            message = f"Embedding model '{model_name}' operation failed"
        super().__init__(message, details)
        self.model_name = model_name


class BatchProcessingError(VectorStoreError):
    """Raised when batch processing fails."""

    def __init__(
        self,
        batch_size: int,
        failed_count: int,
        message: str = None,
        details: str = None,
    ):
        """Initialize batch processing error."""
        if message is None:
            message = (
                f"Batch processing failed: {failed_count}/{batch_size} items failed"
            )
        super().__init__(message, details)
        self.batch_size = batch_size
        self.failed_count = failed_count
        self.success_count = batch_size - failed_count


class SearchQueryError(VectorStoreError):
    """Raised when search query is invalid."""

    def __init__(self, query: str, message: str = None, details: str = None):
        """Initialize search query error."""
        if message is None:
            message = f"Invalid search query: {query}"
        super().__init__(message, details)
        self.query = query
