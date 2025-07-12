"""Qdrant vector database repository layer."""

from typing import Any

from qdrant_client import QdrantClient


class VectorRepository:
    """Repository for vector operations using Qdrant."""

    def __init__(self, client: QdrantClient) -> None:
        """Initialize repository with Qdrant client."""
        self.client = client

    async def health_check(self) -> bool:
        """Check if the vector database is healthy."""
        try:
            # Simple health check - get collections info
            self.client.get_collections()
            return True
        except Exception:
            return False 