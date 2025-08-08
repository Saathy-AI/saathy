"""Vector store service implementation."""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SearchRequest,
    VectorParams,
)

from saathy_core import Chunk, VectorStoreException


logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for vector storage operations using Qdrant."""
    
    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        collection_name: str = "saathy_content",
        vector_size: int = 384,
        distance_metric: str = "cosine"
    ):
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance_metric = self._get_distance_metric(distance_metric)
        self.client: Optional[QdrantClient] = None
    
    def _get_distance_metric(self, metric: str) -> Distance:
        """Convert string metric to Qdrant Distance enum."""
        metrics = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT,
        }
        return metrics.get(metric.lower(), Distance.COSINE)
    
    async def initialize(self) -> None:
        """Initialize vector store connection and create collection if needed."""
        try:
            # Create Qdrant client
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=30,
            )
            
            # Check if collection exists
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                await self._create_collection()
            else:
                logger.info(f"Collection {self.collection_name} already exists")
            
            # Verify connection
            if not await self.health_check():
                raise VectorStoreException(
                    store_name="qdrant",
                    operation="initialize",
                    message="Health check failed after initialization"
                )
            
            logger.info("Vector store initialized successfully")
        except Exception as e:
            raise VectorStoreException(
                store_name="qdrant",
                operation="initialize",
                message=f"Failed to initialize vector store: {str(e)}"
            )
    
    async def _create_collection(self) -> None:
        """Create the vector collection."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        await self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=self.distance_metric,
            ),
        )
        
        # Create indexes for common filter fields
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="content_type",
            field_schema="keyword",
        )
        
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="source",
            field_schema="keyword",
        )
        
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="timestamp",
            field_schema="datetime",
        )
    
    async def health_check(self) -> bool:
        """Check vector store health."""
        if not self.client:
            return False
        
        try:
            # Try to get collection info
            info = await self.client.get_collection(self.collection_name)
            return info is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def upsert(self, chunks: List[Chunk]) -> List[str]:
        """Store chunks with embeddings."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        if not chunks:
            return []
        
        try:
            points = []
            ids = []
            
            for chunk in chunks:
                if not chunk.embedding:
                    logger.warning(f"Chunk {chunk.id} has no embedding, skipping")
                    continue
                
                # Generate ID if not provided
                chunk_id = chunk.id or str(uuid4())
                ids.append(chunk_id)
                
                # Create point
                point = PointStruct(
                    id=chunk_id,
                    vector=chunk.embedding,
                    payload={
                        "content": chunk.content,
                        "content_type": chunk.metadata.content_type.value,
                        "source": chunk.metadata.source,
                        "chunk_index": chunk.metadata.chunk_index,
                        "total_chunks": chunk.metadata.total_chunks,
                        "parent_id": chunk.metadata.parent_id,
                        "timestamp": chunk.metadata.timestamp.isoformat(),
                        "metadata": chunk.metadata.metadata,
                        "tokens": chunk.tokens,
                    }
                )
                points.append(point)
            
            # Batch upsert
            if points:
                await self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True,
                )
                logger.info(f"Upserted {len(points)} chunks to vector store")
            
            return ids
        except Exception as e:
            raise VectorStoreException(
                store_name="qdrant",
                operation="upsert",
                message=f"Failed to upsert chunks: {str(e)}"
            )
    
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Search for similar chunks."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        try:
            # Build filter conditions
            filter_conditions = []
            if filters:
                for field, value in filters.items():
                    if value is not None:
                        filter_conditions.append(
                            FieldCondition(
                                key=field,
                                match=MatchValue(value=value)
                            )
                        )
            
            # Create search request
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Perform search
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter,
                with_payload=True,
                with_vectors=True,
            )
            
            # Convert results to chunks
            chunks = []
            for result in results:
                payload = result.payload
                chunk = Chunk(
                    id=str(result.id),
                    content=payload["content"],
                    metadata={
                        "source": payload["source"],
                        "content_type": payload["content_type"],
                        "chunk_index": payload["chunk_index"],
                        "total_chunks": payload["total_chunks"],
                        "parent_id": payload["parent_id"],
                        "timestamp": payload["timestamp"],
                        "metadata": payload.get("metadata", {}),
                        "score": result.score,
                    },
                    embedding=result.vector,
                    tokens=payload.get("tokens"),
                )
                chunks.append(chunk)
            
            logger.info(f"Found {len(chunks)} similar chunks")
            return chunks
        except Exception as e:
            raise VectorStoreException(
                store_name="qdrant",
                operation="search",
                message=f"Failed to search chunks: {str(e)}"
            )
    
    async def delete(self, chunk_ids: List[str]) -> int:
        """Delete chunks by IDs."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        if not chunk_ids:
            return 0
        
        try:
            result = await self.client.delete(
                collection_name=self.collection_name,
                points_selector=chunk_ids,
                wait=True,
            )
            
            deleted_count = len(chunk_ids)  # Qdrant doesn't return count
            logger.info(f"Deleted {deleted_count} chunks from vector store")
            return deleted_count
        except Exception as e:
            raise VectorStoreException(
                store_name="qdrant",
                operation="delete",
                message=f"Failed to delete chunks: {str(e)}"
            )
    
    async def get_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        """Retrieve chunks by IDs."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        if not chunk_ids:
            return []
        
        try:
            results = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=chunk_ids,
                with_payload=True,
                with_vectors=True,
            )
            
            # Convert results to chunks
            chunks = []
            for result in results:
                payload = result.payload
                chunk = Chunk(
                    id=str(result.id),
                    content=payload["content"],
                    metadata={
                        "source": payload["source"],
                        "content_type": payload["content_type"],
                        "chunk_index": payload["chunk_index"],
                        "total_chunks": payload["total_chunks"],
                        "parent_id": payload["parent_id"],
                        "timestamp": payload["timestamp"],
                        "metadata": payload.get("metadata", {}),
                    },
                    embedding=result.vector,
                    tokens=payload.get("tokens"),
                )
                chunks.append(chunk)
            
            logger.info(f"Retrieved {len(chunks)} chunks by IDs")
            return chunks
        except Exception as e:
            raise VectorStoreException(
                store_name="qdrant",
                operation="get_by_ids",
                message=f"Failed to retrieve chunks: {str(e)}"
            )
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        try:
            info = await self.client.get_collection(self.collection_name)
            return {
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance,
                }
            }
        except Exception as e:
            raise VectorStoreException(
                store_name="qdrant",
                operation="get_collection_stats",
                message=f"Failed to get collection stats: {str(e)}"
            )
    
    async def close(self) -> None:
        """Close vector store connection."""
        if self.client:
            # Qdrant client doesn't have explicit close, but we can cleanup
            self.client = None
            logger.info("Vector store connection closed")