"""Chunk quality validation utilities."""

import re
from typing import Any

from ..core.interfaces import ChunkQualityValidator as ChunkQualityValidatorInterface
from ..core.models import Chunk


class ChunkQualityValidator(ChunkQualityValidatorInterface):
    """Validates chunk quality and coherence."""

    def __init__(self, min_chunk_size: int = 50, max_chunk_size: int = 512):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def validate_chunks(
        self, chunks: list[Chunk], original_content: str
    ) -> dict[str, Any]:
        """Validate chunk quality and return metrics."""
        if not chunks:
            return {"valid": False, "error": "No chunks generated"}

        metrics = {
            "total_chunks": len(chunks),
            "total_content_length": len(original_content),
            "total_chunk_length": sum(len(chunk.content) for chunk in chunks),
            "avg_chunk_size": 0,
            "min_chunk_size": float("inf"),
            "max_chunk_size": 0,
            "coverage_ratio": 0,
            "quality_issues": [],
            "warnings": [],
        }

        # Calculate basic metrics
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        metrics["avg_chunk_size"] = sum(chunk_sizes) / len(chunk_sizes)
        metrics["min_chunk_size"] = min(chunk_sizes)
        metrics["max_chunk_size"] = max(chunk_sizes)
        metrics["coverage_ratio"] = (
            metrics["total_chunk_length"] / metrics["total_content_length"]
        )

        # Check for quality issues
        for i, chunk in enumerate(chunks):
            # Check minimum size
            if len(chunk.content) < self.min_chunk_size:
                metrics["quality_issues"].append(
                    {
                        "type": "chunk_too_small",
                        "chunk_index": i,
                        "size": len(chunk.content),
                        "threshold": self.min_chunk_size,
                    }
                )

            # Check maximum size
            if len(chunk.content) > self.max_chunk_size:
                metrics["quality_issues"].append(
                    {
                        "type": "chunk_too_large",
                        "chunk_index": i,
                        "size": len(chunk.content),
                        "threshold": self.max_chunk_size,
                    }
                )

            # Check for incomplete sentences
            if not self._is_complete_sentence(chunk.content):
                metrics["warnings"].append(
                    {"type": "incomplete_sentence", "chunk_index": i}
                )

        # Check coverage
        if metrics["coverage_ratio"] < 0.8:
            metrics["quality_issues"].append(
                {
                    "type": "low_coverage",
                    "coverage": metrics["coverage_ratio"],
                    "threshold": 0.8,
                }
            )

        # Check for overlaps
        overlaps = self._check_overlaps(chunks)
        if overlaps:
            metrics["overlaps"] = overlaps

        metrics["valid"] = len(metrics["quality_issues"]) == 0
        return metrics

    def _is_complete_sentence(self, content: str) -> bool:
        """Check if chunk ends with a complete sentence."""
        content = content.strip()
        if not content:
            return True

        # Check for sentence endings
        sentence_endings = r"[.!?]\s*$"
        return bool(re.search(sentence_endings, content))

    def _check_overlaps(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        """Check for overlapping chunks."""
        overlaps = []
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]

            if current_chunk.end_index > next_chunk.start_index:
                overlaps.append(
                    {
                        "chunk_index": i,
                        "overlap_size": current_chunk.end_index
                        - next_chunk.start_index,
                    }
                )

        return overlaps
