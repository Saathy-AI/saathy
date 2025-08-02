"""Qdrant vector database repository layer with comprehensive CRUD operations."""

import time
from typing import Any

import structlog
from opentelemetry import trace
from qdrant_client.http import models

from .client import QdrantClientWrapper
from .exceptions import (
    BatchProcessingError,
    EmbeddingDimensionError,
    VectorOperationError,
)
from .models import (
    BulkImportResult,
    CollectionStats,
    SearchQuery,
    SearchResult,
    VectorDocument,
)

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class VectorRepository:
    """Repository for vector operations using Qdrant with comprehensive CRUD support."""

    def __init__(self, client: QdrantClientWrapper) -> None:
        """Initialize repository with Qdrant client wrapper."""
        self.client = client
        self.collection_name = client.collection_name
        self.vector_size = client.vector_size

    @tracer.start_as_current_span("vector_repo.health_check")
    async def health_check(self) -> bool:
        """Check if the vector database is healthy."""
        try:
            return await self.client.health_check()
        except Exception as e:
            logger.warning("Vector repository health check failed", error=str(e))
            return False

    @tracer.start_as_current_span("vector_repo.upsert_vectors")
    async def upsert_vectors(
        self, documents: list[VectorDocument], batch_size: int = 32
    ) -> int:
        """Upsert vectors with batch processing support.

        Args:
            documents: list of documents to upsert
            batch_size: Number of documents to process in each batch

        Returns:
            Number of successfully upserted documents
        """
        if not documents:
            logger.warning("No documents provided for upsert")
            return 0

        start_time = time.time()
        total_documents = len(documents)
        successful_upserts = 0
        failed_upserts = 0
        errors = []

        logger.info(
            "Starting vector upsert",
            total_documents=total_documents,
            batch_size=batch_size,
        )

        # Ensure collection exists
        await self.client.ensure_collection_exists()

        # Process in batches
        for i in range(0, total_documents, batch_size):
            batch = documents[i : i + batch_size]
            batch_start_time = time.time()

            try:
                # Validate vector dimensions first
                for doc in batch:
                    if len(doc.embedding) != self.vector_size:
                        raise EmbeddingDimensionError(
                            self.vector_size, len(doc.embedding)
                        )

                # Prepare batch data
                points = [
                    models.PointStruct(
                        id=doc.id,
                        vector=doc.embedding,
                        payload={
                            "content": doc.content,
                            "metadata": doc.metadata,
                            "timestamp": doc.timestamp.isoformat(),
                        },
                    )
                    for doc in batch
                ]

                # Upsert batch
                await self.client._execute_with_retry(
                    "upsert_batch",
                    lambda client, pts=points: client.upsert(
                        collection_name=self.collection_name,
                        points=pts,
                    ),
                )

                batch_success = len(batch)
                successful_upserts += batch_success
                batch_time = time.time() - batch_start_time

                logger.debug(
                    "Batch upsert completed",
                    batch_number=i // batch_size + 1,
                    batch_size=batch_success,
                    batch_time=batch_time,
                )

            except Exception as e:
                batch_failed = len(batch)
                failed_upserts += batch_failed
                error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                errors.append(error_msg)

                logger.error(
                    "Batch upsert failed",
                    batch_number=i // batch_size + 1,
                    batch_size=batch_failed,
                    error=str(e),
                )

        total_time = time.time() - start_time

        logger.info(
            "Vector upsert completed",
            total_documents=total_documents,
            successful=successful_upserts,
            failed=failed_upserts,
            total_time=total_time,
        )

        if failed_upserts > 0:
            raise BatchProcessingError(
                batch_size=total_documents,
                failed_count=failed_upserts,
                details="; ".join(errors),
            )

        return successful_upserts

    @tracer.start_as_current_span("vector_repo.search_similar")
    async def search_similar(
        self, query: SearchQuery, collection_name: str = None
    ) -> list[SearchResult]:
        """Search for similar vectors with filtering and pagination.

        Args:
            query: Search query parameters
            collection_name: Optional collection name override

        Returns:
            list of search results with documents and scores
        """
        collection_name = collection_name or self.collection_name
        start_time = time.time()

        logger.info(
            "Starting vector search",
            query_length=len(query.query_text),
            top_k=query.top_k,
            filters=query.filters,
        )

        try:
            # Prepare search parameters
            search_params = {
                "collection_name": collection_name,
                "query_vector": query.query_text,  # This should be the embedding vector
                "limit": query.top_k,
                "with_payload": True,
                "with_vectors": False,  # Don't return vectors in results
            }

            # Add score threshold if specified
            if query.score_threshold is not None:
                search_params["score_threshold"] = query.score_threshold

            # Add filters if specified
            if query.filters:
                search_params["query_filter"] = self._build_filter(query.filters)

            # Execute search
            search_response = await self.client._execute_with_retry(
                "search", lambda client: client.search(**search_params)
            )

            # Convert to SearchResult objects
            results = [
                SearchResult(
                    document=VectorDocument(
                        id=point.id,
                        content=point.payload.get("content", ""),
                        embedding=[],  # Not included in search results
                        metadata=point.payload.get("metadata", {}),
                        timestamp=point.payload.get("timestamp"),
                    ),
                    score=point.score,
                    metadata={"point_id": point.id},
                )
                for point in search_response
            ]

            search_time = time.time() - start_time

            logger.info(
                "Vector search completed",
                results_count=len(results),
                search_time=search_time,
            )

            return results

        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise VectorOperationError("search", details=str(e)) from e

    @tracer.start_as_current_span("vector_repo.delete_vectors")
    async def delete_vectors(
        self, ids: list[str], soft_delete: bool = False, collection_name: str = None
    ) -> int:
        """Delete vectors by IDs with soft delete option.

        Args:
            ids: list of document IDs to delete
            soft_delete: If True, mark as deleted instead of removing
            collection_name: Optional collection name override

        Returns:
            Number of successfully deleted documents
        """
        collection_name = collection_name or self.collection_name
        start_time = time.time()

        logger.info(
            "Starting vector deletion",
            ids_count=len(ids),
            soft_delete=soft_delete,
        )

        try:
            if soft_delete:
                # Soft delete: update metadata to mark as deleted
                points = [
                    models.PointStruct(
                        id=doc_id,
                        payload={"deleted": True, "deleted_at": time.time()},
                    )
                    for doc_id in ids
                ]

                await self.client._execute_with_retry(
                    "soft_delete",
                    lambda client: client.upsert(
                        collection_name=collection_name,
                        points=points,
                    ),
                )
            else:
                # Hard delete: remove points completely
                await self.client._execute_with_retry(
                    "hard_delete",
                    lambda client: client.delete(
                        collection_name=collection_name,
                        points_selector=models.PointIdslist(points=ids),
                    ),
                )

            delete_time = time.time() - start_time

            logger.info(
                "Vector deletion completed",
                deleted_count=len(ids),
                delete_time=delete_time,
            )

            return len(ids)

        except Exception as e:
            logger.error("Vector deletion failed", error=str(e))
            raise VectorOperationError("delete", details=str(e)) from e

    @tracer.start_as_current_span("vector_repo.get_collection_stats")
    async def get_collection_stats(
        self, collection_name: str = None
    ) -> CollectionStats:
        """Get collection statistics for monitoring.

        Args:
            collection_name: Optional collection name override

        Returns:
            Collection statistics
        """
        collection_name = collection_name or self.collection_name

        try:
            info = await self.client.get_collection_info(collection_name)

            stats = CollectionStats(
                collection_name=info["name"],
                vector_count=info["vector_count"],
                vector_size=info["config"]["vector_size"],
                points_count=info["points_count"],
                segments_count=info["segments_count"],
                status=info["status"],
                last_updated=None,  # Qdrant doesn't provide this directly
            )

            logger.debug(
                "Retrieved collection stats",
                collection=collection_name,
                vector_count=stats.vector_count,
                status=stats.status,
            )

            return stats

        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            raise VectorOperationError("get_stats", details=str(e)) from e

    @tracer.start_as_current_span("vector_repo.bulk_import")
    async def bulk_import(
        self, documents: list[VectorDocument], batch_size: int = 32
    ) -> BulkImportResult:
        """Bulk import documents for initial data loading.

        Args:
            documents: list of documents to import
            batch_size: Number of documents to process in each batch

        Returns:
            Bulk import result with statistics
        """
        start_time = time.time()
        total_documents = len(documents)
        successful_imports = 0
        failed_imports = 0
        errors = []

        logger.info(
            "Starting bulk import",
            total_documents=total_documents,
            batch_size=batch_size,
        )

        try:
            # Use upsert_vectors for the actual import
            successful_imports = await self.upsert_vectors(documents, batch_size)
            failed_imports = total_documents - successful_imports

        except BatchProcessingError as e:
            # Extract information from batch processing error
            successful_imports = e.success_count
            failed_imports = e.failed_count
            errors.append(str(e))

        except Exception as e:
            failed_imports = total_documents
            errors.append(str(e))
            logger.error("Bulk import failed", error=str(e))

        processing_time = time.time() - start_time

        result = BulkImportResult(
            total_documents=total_documents,
            successful_imports=successful_imports,
            failed_imports=failed_imports,
            processing_time=processing_time,
            errors=errors,
        )

        logger.info(
            "Bulk import completed",
            total=result.total_documents,
            successful=result.successful_imports,
            failed=result.failed_imports,
            success_rate=result.success_rate,
            processing_time=result.processing_time,
        )

        return result

    def _build_filter(self, filters: dict[str, Any]) -> models.Filter:
        """Build Qdrant filter from dictionary of conditions."""
        conditions = []

        for key, value in filters.items():
            if isinstance(value, (str, int, float, bool)):
                conditions.append(
                    models.FieldCondition(key=key, match=models.MatchValue(value=value))
                )
            elif isinstance(value, list):
                conditions.append(
                    models.FieldCondition(key=key, match=models.MatchAny(any=value))
                )
            elif isinstance(value, dict):
                # Handle range queries
                if "gte" in value or "lte" in value:
                    range_params = {}
                    if "gte" in value:
                        range_params["gte"] = value["gte"]
                    if "lte" in value:
                        range_params["lte"] = value["lte"]

                    conditions.append(
                        models.FieldCondition(
                            key=key, range=models.DatetimeRange(**range_params)
                        )
                    )

        if len(conditions) == 1:
            return models.Filter(must=conditions)
        else:
            return models.Filter(must=conditions)
