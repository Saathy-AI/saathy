"""Embedding service."""

class EmbeddingService:
    """Service for generating embeddings."""
    
    def __init__(self, model_name: str, batch_size: int, cache_service=None):
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_service = cache_service
    
    async def initialize(self) -> None:
        """Initialize embedding model."""
        pass