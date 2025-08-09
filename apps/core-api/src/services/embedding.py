"""Embedding service implementation using Sentence Transformers."""

import logging
from typing import Any, Dict, List, Optional
import hashlib
import json

import torch
from sentence_transformers import SentenceTransformer
import numpy as np

from saathy_core import EmbeddingException


logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Sentence Transformers."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 32,
        cache_service=None,
        device: Optional[str] = None
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_service = cache_service
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model: Optional[SentenceTransformer] = None
        self._cache_prefix = f"embedding:{model_name}:"
    
    async def initialize(self) -> None:
        """Initialize embedding model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            
            # Warm up the model
            test_embedding = self.model.encode("test", convert_to_numpy=True)
            logger.info(
                f"Embedding model loaded successfully. "
                f"Dimension: {len(test_embedding)}, Device: {self.device}"
            )
        except Exception as e:
            raise EmbeddingException(
                model_name=self.model_name,
                message=f"Failed to initialize embedding model: {str(e)}"
            )
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"{self._cache_prefix}{text_hash}"
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        # Check cache first
        if self.cache_service:
            cache_key = self._get_cache_key(text)
            cached = await self.cache_service.get(cache_key)
            if cached:
                return json.loads(cached)
        
        try:
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            
            # Convert to list
            embedding_list = embedding.tolist()
            
            # Cache the result
            if self.cache_service:
                await self.cache_service.set(
                    cache_key,
                    json.dumps(embedding_list),
                    ttl=3600  # 1 hour
                )
            
            return embedding_list
        except Exception as e:
            raise EmbeddingException(
                model_name=self.model_name,
                message=f"Failed to generate embedding: {str(e)}"
            )
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        if not texts:
            return []
        
        # Check cache for all texts
        embeddings_map = {}
        uncached_texts = []
        uncached_indices = []
        
        if self.cache_service:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                cached = await self.cache_service.get(cache_key)
                if cached:
                    embeddings_map[i] = json.loads(cached)
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                # Process in batches
                all_embeddings = []
                for i in range(0, len(uncached_texts), self.batch_size):
                    batch = uncached_texts[i:i + self.batch_size]
                    batch_embeddings = self.model.encode(
                        batch,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        batch_size=self.batch_size
                    )
                    all_embeddings.extend(batch_embeddings.tolist())
                
                # Cache new embeddings
                if self.cache_service:
                    for text, embedding in zip(uncached_texts, all_embeddings):
                        cache_key = self._get_cache_key(text)
                        await self.cache_service.set(
                            cache_key,
                            json.dumps(embedding),
                            ttl=3600
                        )
                
                # Add to map
                for idx, embedding in zip(uncached_indices, all_embeddings):
                    embeddings_map[idx] = embedding
            except Exception as e:
                raise EmbeddingException(
                    model_name=self.model_name,
                    message=f"Failed to generate batch embeddings: {str(e)}"
                )
        
        # Return in original order
        return [embeddings_map[i] for i in range(len(texts))]
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        return self.model.get_sentence_embedding_dimension()
    
    async def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Compute cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            raise EmbeddingException(
                model_name=self.model_name,
                message=f"Failed to compute similarity: {str(e)}"
            )
    
    async def find_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[tuple[int, float]]:
        """Find most similar embeddings from candidates."""
        if not candidate_embeddings:
            return []
        
        try:
            # Compute similarities
            similarities = []
            for i, candidate in enumerate(candidate_embeddings):
                sim = await self.compute_similarity(query_embedding, candidate)
                if sim >= threshold:
                    similarities.append((i, sim))
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Return top k
            return similarities[:top_k]
        except Exception as e:
            raise EmbeddingException(
                model_name=self.model_name,
                message=f"Failed to find similar embeddings: {str(e)}"
            )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        if not self.model:
            return {
                "model_name": self.model_name,
                "status": "not_initialized"
            }
        
        return {
            "model_name": self.model_name,
            "dimension": self.get_dimension(),
            "device": str(self.device),
            "max_seq_length": self.model.max_seq_length,
            "batch_size": self.batch_size,
            "status": "ready"
        }