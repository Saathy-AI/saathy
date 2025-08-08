"""Vector store service."""

class VectorStoreService:
    """Service for vector storage operations."""
    
    def __init__(self, url: str, api_key: str | None, collection_name: str, vector_size: int):
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
    
    async def initialize(self) -> None:
        """Initialize vector store connection."""
        pass
    
    async def health_check(self) -> bool:
        """Check vector store health."""
        return True
    
    async def close(self) -> None:
        """Close vector store connection."""
        pass