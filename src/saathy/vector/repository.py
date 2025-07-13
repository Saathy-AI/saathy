"""Qdrant vector database repository layer."""
from opentelemetry import trace
from qdrant_client import QdrantClient

tracer = trace.get_tracer(__name__)


class VectorRepository:
    """Repository for vector operations using Qdrant."""

    def __init__(self, client: QdrantClient) -> None:
        """Initialize repository with Qdrant client."""
        self.client = client

    @tracer.start_as_current_span("vector_repo.health_check")
    async def health_check(self) -> bool:
        """Check if the vector database is healthy."""
        try:
            # Simple health check - get collections info
            self.client.get_collections()
            return True
        except Exception:
            return False
