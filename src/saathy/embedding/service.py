"""Embedding service with multi-model support and optimization."""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from .models import ModelRegistry, create_default_registry
from .preprocessing import PreprocessingPipeline, PreprocessingResult

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embeddings: np.ndarray
    model_name: str
    content_type: str
    processing_time: float
    metadata: Dict[str, Any]
    quality_score: float = 1.0
    preprocessing_result: Optional[PreprocessingResult] = None


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # key -> (embedding, timestamp)

    def get(self, key: str) -> Optional[np.ndarray]:
        """Get embedding from cache if not expired."""
        if key in self._cache:
            embedding, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return embedding
            else:
                del self._cache[key]
        return None

    def set(self, key: str, embedding: np.ndarray) -> None:
        """Store embedding in cache."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[key] = (embedding, time.time())

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class EmbeddingMetrics:
    """Metrics collection for embedding operations."""

    def __init__(self):
        self.processing_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        self.model_usage: Dict[str, int] = {}
        self.content_type_stats: Dict[str, Dict[str, Any]] = {}

    def record_processing_time(
        self, model_name: str, content_type: str, time_seconds: float
    ) -> None:
        """Record processing time for a model and content type."""
        key = f"{model_name}_{content_type}"
        if key not in self.processing_times:
            self.processing_times[key] = []
        self.processing_times[key].append(time_seconds)

        # Keep only last 100 measurements
        if len(self.processing_times[key]) > 100:
            self.processing_times[key] = self.processing_times[key][-100:]

    def record_error(self, model_name: str, error_type: str) -> None:
        """Record an error for a model."""
        key = f"{model_name}_{error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

    def record_model_usage(self, model_name: str) -> None:
        """Record model usage."""
        self.model_usage[model_name] = self.model_usage.get(model_name, 0) + 1

    def record_content_type_stats(
        self, content_type: str, quality_score: float, word_count: int
    ) -> None:
        """Record content type statistics."""
        if content_type not in self.content_type_stats:
            self.content_type_stats[content_type] = {
                "total_processed": 0,
                "avg_quality_score": 0.0,
                "avg_word_count": 0.0,
                "quality_scores": [],
                "word_counts": [],
            }

        stats = self.content_type_stats[content_type]
        stats["total_processed"] += 1
        stats["quality_scores"].append(quality_score)
        stats["word_counts"].append(word_count)

        # Update averages
        stats["avg_quality_score"] = np.mean(stats["quality_scores"])
        stats["avg_word_count"] = np.mean(stats["word_counts"])

    def get_model_performance(self, model_name: str) -> Dict[str, Any]:
        """Get performance statistics for a model."""
        performance = {
            "usage_count": self.model_usage.get(model_name, 0),
            "avg_processing_time": 0.0,
            "error_rate": 0.0,
        }

        # Calculate average processing time
        times = []
        for key, time_list in self.processing_times.items():
            if key.startswith(f"{model_name}_"):
                times.extend(time_list)

        if times:
            performance["avg_processing_time"] = np.mean(times)

        # Calculate error rate
        total_errors = sum(
            count
            for key, count in self.error_counts.items()
            if key.startswith(f"{model_name}_")
        )
        total_usage = performance["usage_count"]
        if total_usage > 0:
            performance["error_rate"] = total_errors / total_usage

        return performance

    def get_content_type_performance(self, content_type: str) -> Dict[str, Any]:
        """Get performance statistics for a content type."""
        return self.content_type_stats.get(content_type, {})

    def get_summary(self) -> Dict[str, Any]:
        """Get overall metrics summary."""
        return {
            "total_models_used": len(self.model_usage),
            "total_content_types": len(self.content_type_stats),
            "total_errors": sum(self.error_counts.values()),
            "model_performance": {
                name: self.get_model_performance(name)
                for name in self.model_usage.keys()
            },
            "content_type_performance": {
                ct: self.get_content_type_performance(ct)
                for ct in self.content_type_stats.keys()
            },
        }


class EmbeddingService:
    """Main embedding service with multi-model support."""

    def __init__(self, registry: Optional[ModelRegistry] = None):
        self.registry = registry or create_default_registry()
        self.preprocessing_pipeline = PreprocessingPipeline()
        self.cache = EmbeddingCache()
        self.metrics = EmbeddingMetrics()
        self._batch_size = 32
        self._max_retries = 3

    async def initialize(self) -> None:
        """Initialize the embedding service."""
        logger.info("Initializing embedding service...")

        # Load default models
        await self.registry.load_all_models()

        # Warm up models
        await self._warmup_models()

        logger.info("Embedding service initialized successfully")

    async def _warmup_models(self) -> None:
        """Warm up all loaded models."""
        warmup_texts = [
            "This is a warmup text for the embedding service.",
            "Another warmup text to ensure models are ready.",
            "Final warmup text for optimal performance.",
        ]

        for model_name in self.registry.list_models():
            try:
                model = self.registry.get_model(model_name)
                if model and model.is_loaded():
                    await model.embed(warmup_texts)
                    logger.debug(f"Warmed up model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to warm up model {model_name}: {e}")

    def _generate_cache_key(
        self, content: str, model_name: str, content_type: str
    ) -> str:
        """Generate cache key for content."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{model_name}_{content_type}_{content_hash}"

    def _chunk_content(
        self, content: str, max_length: int, overlap: int = 50
    ) -> List[str]:
        """Chunk content into smaller pieces with overlap."""
        if len(content) <= max_length:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + max_length

            # Try to break at word boundary
            if end < len(content):
                # Find last space before end
                last_space = content.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap
            if start >= len(content):
                break

        return chunks

    async def embed_text(
        self,
        text: str,
        content_type: str = "text",
        model_name: Optional[str] = None,
        quality: str = "balanced",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingResult:
        """Embed a single text document."""
        start_time = time.time()

        try:
            # Preprocess content
            preprocessing_result = self.preprocessing_pipeline.preprocess(
                text, content_type, metadata
            )

            # Select model
            if model_name:
                model = self.registry.get_model(model_name)
                if not model:
                    raise ValueError(f"Model {model_name} not found")
            else:
                model = self.registry.get_best_model_for_content(content_type, quality)
                if not model:
                    raise ValueError(
                        f"No suitable model found for content type {content_type}"
                    )

            # Check cache
            cache_key = self._generate_cache_key(
                preprocessing_result.content, model.metadata.name, content_type
            )
            cached_embedding = self.cache.get(cache_key)

            if cached_embedding is not None:
                logger.debug(f"Using cached embedding for {cache_key}")
                processing_time = time.time() - start_time

                self.metrics.record_processing_time(
                    model.metadata.name, content_type, processing_time
                )
                self.metrics.record_model_usage(model.metadata.name)

                return EmbeddingResult(
                    embeddings=cached_embedding,
                    model_name=model.metadata.name,
                    content_type=content_type,
                    processing_time=processing_time,
                    metadata=metadata or {},
                    quality_score=preprocessing_result.quality_score,
                    preprocessing_result=preprocessing_result,
                )

            # Generate embedding
            embeddings = await model.embed(preprocessing_result.content)

            # Cache result
            self.cache.set(cache_key, embeddings)

            processing_time = time.time() - start_time

            # Record metrics
            self.metrics.record_processing_time(
                model.metadata.name, content_type, processing_time
            )
            self.metrics.record_model_usage(model.metadata.name)
            self.metrics.record_content_type_stats(
                content_type,
                preprocessing_result.quality_score,
                len(preprocessing_result.content.split()),
            )

            return EmbeddingResult(
                embeddings=embeddings,
                model_name=model.metadata.name,
                content_type=content_type,
                processing_time=processing_time,
                metadata=metadata or {},
                quality_score=preprocessing_result.quality_score,
                preprocessing_result=preprocessing_result,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            model_name_used = model_name or "unknown"
            self.metrics.record_error(model_name_used, type(e).__name__)
            logger.error(f"Embedding failed: {e}")
            raise

    async def embed_batch(
        self,
        texts: List[str],
        content_type: str = "text",
        model_name: Optional[str] = None,
        quality: str = "balanced",
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[EmbeddingResult]:
        """Embed multiple texts efficiently."""
        if not texts:
            return []

        # Select model
        if model_name:
            model = self.registry.get_model(model_name)
            if not model:
                raise ValueError(f"Model {model_name} not found")
        else:
            model = self.registry.get_best_model_for_content(content_type, quality)
            if not model:
                raise ValueError(
                    f"No suitable model found for content type {content_type}"
                )

        # Process in batches
        results = []
        batch_size = min(self._batch_size, len(texts))

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_metadata = (
                metadata_list[i : i + batch_size]
                if metadata_list
                else [None] * len(batch_texts)
            )

            # Process batch
            batch_results = await asyncio.gather(
                *[
                    self.embed_text(
                        text, content_type, model.metadata.name, quality, metadata
                    )
                    for text, metadata in zip(batch_texts, batch_metadata)
                ]
            )

            results.extend(batch_results)

        return results

    async def embed_code(
        self,
        code: str,
        language: Optional[str] = None,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingResult:
        """Embed code with specialized preprocessing."""
        if metadata is None:
            metadata = {}

        if language:
            metadata["file_extension"] = f".{language}"

        return await self.embed_text(code, "code", model_name, "high", metadata)

    async def embed_multimodal(
        self, content: str, content_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> EmbeddingResult:
        """Embed multimodal content."""
        # For now, treat as regular text embedding
        # Future: implement actual multimodal embedding
        return await self.embed_text(content, content_type, None, "high", metadata)

    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return self.registry.list_models()

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model."""
        model = self.registry.get_model(model_name)
        if not model:
            return None

        return {
            "name": model.metadata.name,
            "dimensions": model.metadata.dimensions,
            "max_context_length": model.metadata.max_context_length,
            "model_type": model.metadata.model_type,
            "performance_score": model.metadata.performance_score,
            "is_loaded": model.is_loaded(),
            "device": model.get_device(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get embedding service metrics."""
        return self.metrics.get_summary()

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")

    def set_batch_size(self, batch_size: int) -> None:
        """Set the batch size for bulk operations."""
        self._batch_size = max(1, min(batch_size, 128))  # Limit between 1 and 128
        logger.info(f"Batch size set to {self._batch_size}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": self.cache.size(),
            "max_size": self.cache.max_size,
            "ttl_seconds": self.cache.ttl_seconds,
        }


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


async def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        await _embedding_service.initialize()

    return _embedding_service
