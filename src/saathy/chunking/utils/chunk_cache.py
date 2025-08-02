"""Chunk caching utilities."""

import time
from typing import Any, Optional

from ..core.interfaces import ChunkCache as ChunkCacheInterface
from ..core.models import Chunk


class ChunkCache(ChunkCacheInterface):
    """Caches chunked results for repeated content."""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.cache: dict[str, tuple[list[Chunk], float]] = {}

    def get(self, content_hash: str) -> Optional[list[Chunk]]:
        """Get cached chunks if not expired."""
        if content_hash in self.cache:
            chunks, timestamp = self.cache[content_hash]
            if time.time() - timestamp < self.ttl:
                return chunks
            else:
                # Remove expired entry
                del self.cache[content_hash]

        return None

    def set(self, content_hash: str, chunks: list[Chunk]) -> None:
        """Cache chunks with timestamp."""
        self.cache[content_hash] = (chunks, time.time())

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1
            for _, (_, timestamp) in self.cache.items()
            if current_time - timestamp < self.ttl
        )

        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
        }
