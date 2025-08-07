"""Qdrant client wrapper with connection management and error handling."""

import asyncio
from typing import Any, Optional

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from .exceptions import (
    CollectionNotFoundError,
    VectorStoreConnectionError,
    VectorStoreError,
)

logger = structlog.get_logger(__name__)


class QdrantClientWrapper:
    """Async wrapper for Qdrant client with connection pooling and retry logic."""

    def __init__(
        self,
        url: Optional[str] = None,
        host: str = "localhost",
        port: int = 6333,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        collection_name: str = "documents",
        vector_size: int = 384,
        distance: str = "Cosine",
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize Qdrant client wrapper.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            collection_name: Default collection name
            vector_size: Vector dimensions
            distance: Distance metric (Cosine, Euclidean, Dot)
        """
        self.url = url
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.api_key = api_key

        # Initialize client
        self._client: Optional[QdrantClient] = None
        self._connection_pool: dict[str, QdrantClient] = {}

        logger.info(
            "Initializing Qdrant client",
            host=host,
            port=port,
            collection=collection_name,
            vector_size=vector_size,
        )

    async def _get_client(self) -> QdrantClient:
        """Get or create Qdrant client with connection pooling."""
        if self._client is None:
            try:
                if self.url:
                    client_kwargs = {"url": self.url, "timeout": self.timeout}
                    if self.api_key:
                        client_kwargs["api_key"] = self.api_key
                    self._client = QdrantClient(**client_kwargs)
                else:
                    client_kwargs = {
                        "host": self.host,
                        "port": self.port,
                        "timeout": self.timeout,
                        # Force HTTP unless explicitly using a URL with https
                        "https": False,
                    }
                    if self.api_key:
                        client_kwargs["api_key"] = self.api_key
                    self._client = QdrantClient(**client_kwargs)
                logger.debug("Created new Qdrant client connection")
            except Exception as e:
                logger.error("Failed to create Qdrant client", error=str(e))
                raise VectorStoreConnectionError(
                    f"Failed to connect to Qdrant at {self.host}:{self.port}",
                    details=str(e),
                ) from e

        return self._client

    async def _execute_with_retry(self, operation: str, func, *args, **kwargs) -> Any:
        """Execute operation with retry logic and exponential backoff."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                client = await self._get_client()
                result = func(client, *args, **kwargs)

                # Log successful operation
                logger.debug(
                    f"Vector operation '{operation}' completed",
                    attempt=attempt + 1,
                )
                return result

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Vector operation '{operation}' failed",
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                    error=str(e),
                )

                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

                    # Reset client connection on failure
                    if isinstance(e, (ConnectionError, UnexpectedResponse)):
                        self._client = None
                        logger.debug("Reset Qdrant client connection")
                else:
                    break

        # All retries exhausted
        logger.error(
            f"Vector operation '{operation}' failed after {self.max_retries + 1} attempts",
            error=str(last_exception),
        )
        raise VectorStoreError(
            f"Operation '{operation}' failed after {self.max_retries + 1} attempts",
            details=str(last_exception),
        )

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy and accessible."""
        try:
            await self._execute_with_retry(
                "health_check", lambda client: client.get_collections()
            )
            logger.debug("Qdrant health check passed")
            return True
        except Exception as e:
            logger.warning("Qdrant health check failed", error=str(e))
            return False

    async def ensure_collection_exists(self, collection_name: str = None) -> None:
        """Ensure collection exists, create if it doesn't."""
        collection_name = collection_name or self.collection_name

        try:
            # Check if collection exists
            collections = await self._execute_with_retry(
                "get_collections", lambda client: client.get_collections()
            )

            existing_collections = [c.name for c in collections.collections]

            if collection_name not in existing_collections:
                logger.info(f"Creating collection '{collection_name}'")

                await self._execute_with_retry(
                    "create_collection",
                    lambda client: client.create_collection(
                        collection_name=collection_name,
                        vectors_config=models.VectorParams(
                            size=self.vector_size,
                            distance=self.distance,
                        ),
                    ),
                )

                logger.info(f"Collection '{collection_name}' created successfully")
            else:
                logger.debug(f"Collection '{collection_name}' already exists")

        except Exception as e:
            logger.error(
                f"Failed to ensure collection '{collection_name}' exists", error=str(e)
            )
            raise VectorStoreError(
                f"Failed to ensure collection '{collection_name}' exists",
                details=str(e),
            ) from e

    async def get_collection_info(self, collection_name: str = None) -> dict[str, Any]:
        """Get collection information and statistics."""
        collection_name = collection_name or self.collection_name

        try:
            info = await self._execute_with_retry(
                "get_collection_info",
                lambda client: client.get_collection(collection_name),
            )

            return {
                "name": info.name,
                "vector_count": info.vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance,
                },
            }

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(collection_name, details=str(e)) from e
            raise VectorStoreError(
                f"Failed to get collection info for '{collection_name}'", details=str(e)
            ) from e

    async def delete_collection(self, collection_name: str = None) -> None:
        """Delete a collection."""
        collection_name = collection_name or self.collection_name

        try:
            await self._execute_with_retry(
                "delete_collection",
                lambda client: client.delete_collection(collection_name),
            )
            logger.info(f"Collection '{collection_name}' deleted successfully")

        except Exception as e:
            logger.error(
                f"Failed to delete collection '{collection_name}'", error=str(e)
            )
            raise VectorStoreError(
                f"Failed to delete collection '{collection_name}'", details=str(e)
            ) from e

    async def close(self) -> None:
        """Close all client connections."""
        if self._client:
            # Qdrant client doesn't have explicit close method, just clear reference
            self._client = None
            logger.debug("Qdrant client connections closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
