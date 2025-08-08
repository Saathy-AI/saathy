"""
Context Cache - Intelligent caching for retrieved context and query results.
Improves performance by avoiding redundant retrievals and computations.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class ContextCache:
    """
    Multi-level caching system for conversational AI:
    - Query cache: Caches similar query results
    - Context cache: Caches retrieved context
    - Embedding cache: Caches query embeddings
    - Result cache: Caches final responses
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config

        # Initialize different cache levels with TTL
        self.query_cache = TTLCache(
            maxsize=config.get("query_cache_size", 1000),
            ttl=config.get("query_cache_ttl", 300),  # 5 minutes
        )

        self.context_cache = TTLCache(
            maxsize=config.get("context_cache_size", 500),
            ttl=config.get("context_cache_ttl", 600),  # 10 minutes
        )

        self.embedding_cache = TTLCache(
            maxsize=config.get("embedding_cache_size", 2000),
            ttl=config.get("embedding_cache_ttl", 1800),  # 30 minutes
        )

        self.result_cache = TTLCache(
            maxsize=config.get("result_cache_size", 300),
            ttl=config.get("result_cache_ttl", 180),  # 3 minutes
        )

        # Cache statistics
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

        # Lock for thread-safe operations
        self.lock = asyncio.Lock()

    async def get_cached_query_result(
        self, query: str, user_id: str, time_window: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """
        Check if we have a cached result for a similar query.

        Returns cached result if found and still valid, None otherwise.
        """

        cache_key = self._generate_query_cache_key(query, user_id, time_window)

        async with self.lock:
            if cache_key in self.query_cache:
                self.stats["hits"] += 1
                logger.debug(f"Query cache hit for key: {cache_key[:20]}...")

                # Validate cache entry is still relevant
                cached_entry = self.query_cache[cache_key]
                if self._is_cache_entry_valid(cached_entry, time_window):
                    return cached_entry["result"]
                else:
                    # Invalidate stale entry
                    del self.query_cache[cache_key]

            self.stats["misses"] += 1
            return None

    async def cache_query_result(
        self,
        query: str,
        user_id: str,
        result: dict[str, Any],
        time_window: Optional[dict[str, Any]] = None,
    ):
        """Cache a query result for future use"""

        cache_key = self._generate_query_cache_key(query, user_id, time_window)

        cache_entry = {
            "result": result,
            "cached_at": datetime.utcnow(),
            "query": query,
            "user_id": user_id,
            "time_window": time_window,
        }

        async with self.lock:
            self.query_cache[cache_key] = cache_entry
            logger.debug(f"Cached query result for key: {cache_key[:20]}...")

    async def get_cached_context(
        self, information_needs: dict[str, Any], user_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get cached context for given information needs.

        Uses fuzzy matching to find similar previous contexts.
        """

        cache_key = self._generate_context_cache_key(information_needs, user_id)

        async with self.lock:
            # Exact match
            if cache_key in self.context_cache:
                self.stats["hits"] += 1
                logger.debug(f"Context cache hit for key: {cache_key[:20]}...")
                return self.context_cache[cache_key]["context"]

            # Fuzzy match for similar queries
            similar_key = self._find_similar_context(information_needs, user_id)
            if similar_key:
                self.stats["hits"] += 1
                logger.debug(f"Context cache fuzzy hit for key: {similar_key[:20]}...")
                return self.context_cache[similar_key]["context"]

            self.stats["misses"] += 1
            return None

    async def cache_context(
        self, information_needs: dict[str, Any], user_id: str, context: dict[str, Any]
    ):
        """Cache retrieved context"""

        cache_key = self._generate_context_cache_key(information_needs, user_id)

        cache_entry = {
            "context": context,
            "cached_at": datetime.utcnow(),
            "information_needs": information_needs,
            "user_id": user_id,
        }

        async with self.lock:
            self.context_cache[cache_key] = cache_entry
            logger.debug(f"Cached context for key: {cache_key[:20]}...")

    async def get_cached_embedding(self, text: str) -> Optional[list[float]]:
        """Get cached embedding for text"""

        cache_key = self._generate_embedding_cache_key(text)

        async with self.lock:
            if cache_key in self.embedding_cache:
                self.stats["hits"] += 1
                return self.embedding_cache[cache_key]

            self.stats["misses"] += 1
            return None

    async def cache_embedding(self, text: str, embedding: list[float]):
        """Cache text embedding"""

        cache_key = self._generate_embedding_cache_key(text)

        async with self.lock:
            self.embedding_cache[cache_key] = embedding

    async def get_cached_response(
        self, query: str, context_hash: str, user_id: str
    ) -> Optional[str]:
        """Get cached final response"""

        cache_key = f"{user_id}:{query[:50]}:{context_hash}"

        async with self.lock:
            if cache_key in self.result_cache:
                self.stats["hits"] += 1
                return self.result_cache[cache_key]

            self.stats["misses"] += 1
            return None

    async def cache_response(
        self, query: str, context_hash: str, user_id: str, response: str
    ):
        """Cache final response"""

        cache_key = f"{user_id}:{query[:50]}:{context_hash}"

        async with self.lock:
            self.result_cache[cache_key] = response

    def _generate_query_cache_key(
        self, query: str, user_id: str, time_window: Optional[dict[str, Any]]
    ) -> str:
        """Generate cache key for query"""

        # Normalize query
        normalized_query = query.lower().strip()

        # Include time window in key if specified
        time_str = ""
        if time_window:
            if "start" in time_window:
                time_str = time_window["start"].strftime("%Y%m%d")

        key_parts = [user_id, normalized_query, time_str]
        key_string = ":".join(filter(None, key_parts))

        # Hash for consistent key length
        return hashlib.md5(key_string.encode()).hexdigest()

    def _generate_context_cache_key(
        self, information_needs: dict[str, Any], user_id: str
    ) -> str:
        """Generate cache key for context"""

        # Extract key components
        key_components = {
            "user_id": user_id,
            "intent": information_needs.get("intent", ""),
            "entities": sorted(
                str(v) for v in information_needs.get("entities", {}).values()
            ),
            "platforms": sorted(information_needs.get("platforms", [])),
            "time_reference": information_needs.get("time_range", {}).get(
                "reference", ""
            ),
        }

        # Create stable string representation
        key_string = json.dumps(key_components, sort_keys=True)

        return hashlib.md5(key_string.encode()).hexdigest()

    def _generate_embedding_cache_key(self, text: str) -> str:
        """Generate cache key for embeddings"""

        # Normalize text
        normalized_text = text.lower().strip()

        return hashlib.md5(normalized_text.encode()).hexdigest()

    def _is_cache_entry_valid(
        self, cache_entry: dict[str, Any], current_time_window: Optional[dict[str, Any]]
    ) -> bool:
        """
        Check if a cache entry is still valid.

        Considers:
        - Age of the cache entry
        - Whether time windows have changed significantly
        """

        # Check age
        age = datetime.utcnow() - cache_entry["cached_at"]
        if age > timedelta(minutes=10):
            return False

        # Check time window compatibility
        if current_time_window and cache_entry.get("time_window"):
            cache_entry["time_window"]

            # If looking for very recent data, cached data might be stale
            if "hour" in str(current_time_window.get("reference", "")):
                if age > timedelta(minutes=5):
                    return False

        return True

    def _find_similar_context(
        self, information_needs: dict[str, Any], user_id: str
    ) -> Optional[str]:
        """
        Find similar context in cache using fuzzy matching.

        Returns cache key of similar context if found.
        """

        target_intent = information_needs.get("intent", "")
        target_entities = set()
        for entity_list in information_needs.get("entities", {}).values():
            target_entities.update([e.lower() for e in entity_list])

        best_match_key = None
        best_match_score = 0

        # Search through context cache
        for cache_key, cache_entry in self.context_cache.items():
            if cache_entry["user_id"] != user_id:
                continue

            cached_needs = cache_entry["information_needs"]

            # Calculate similarity score
            score = 0

            # Intent match
            if cached_needs.get("intent") == target_intent:
                score += 0.5

            # Entity overlap
            cached_entities = set()
            for entity_list in cached_needs.get("entities", {}).values():
                cached_entities.update([e.lower() for e in entity_list])

            if cached_entities and target_entities:
                overlap = len(cached_entities.intersection(target_entities))
                union = len(cached_entities.union(target_entities))
                if union > 0:
                    score += 0.5 * (overlap / union)

            # Update best match
            if score > best_match_score and score >= 0.7:  # Threshold
                best_match_score = score
                best_match_key = cache_key

        return best_match_key

    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""

        async with self.lock:
            # Remove from query cache
            keys_to_remove = []
            for key, entry in self.query_cache.items():
                if entry.get("user_id") == user_id:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.query_cache[key]

            # Remove from context cache
            keys_to_remove = []
            for key, entry in self.context_cache.items():
                if entry.get("user_id") == user_id:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.context_cache[key]

            logger.info(f"Invalidated cache for user: {user_id}")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics"""

        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "query_cache_size": len(self.query_cache),
            "context_cache_size": len(self.context_cache),
            "embedding_cache_size": len(self.embedding_cache),
            "result_cache_size": len(self.result_cache),
        }

    async def warmup_cache(self, common_queries: list[dict[str, Any]]):
        """
        Warmup cache with common queries.

        This can be called on startup to pre-populate cache.
        """

        logger.info(f"Warming up cache with {len(common_queries)} common queries")

        for query_data in common_queries:
            # Cache common embeddings
            if "text" in query_data:
                embedding = query_data.get("embedding")
                if embedding:
                    await self.cache_embedding(query_data["text"], embedding)

        logger.info("Cache warmup completed")
