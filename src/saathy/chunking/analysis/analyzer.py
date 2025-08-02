"""Chunk analysis and quality metrics."""

from dataclasses import dataclass
from typing import Any

from ..core.models import Chunk


@dataclass
class ChunkQualityMetrics:
    """Comprehensive quality metrics for chunks."""

    total_chunks: int
    avg_chunk_size: float
    coverage_ratio: float
    semantic_coherence: float
    overlap_efficiency: float
    content_loss: float
    chunk_distribution: dict[str, int]
    quality_score: float


class ChunkAnalyzer:
    """Analyzes chunk quality and characteristics."""

    def analyze_chunks(
        self, chunks: list[Chunk], original_content: str
    ) -> ChunkQualityMetrics:
        """Calculate comprehensive quality metrics."""
        if not chunks:
            return ChunkQualityMetrics(
                total_chunks=0,
                avg_chunk_size=0.0,
                coverage_ratio=0.0,
                semantic_coherence=0.0,
                overlap_efficiency=0.0,
                content_loss=0.0,
                chunk_distribution={},
                quality_score=0.0,
            )

        # Basic metrics
        total_chunks = len(chunks)
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)

        # Coverage ratio
        total_chunk_length = sum(chunk_sizes)
        coverage_ratio = (
            total_chunk_length / len(original_content) if original_content else 0.0
        )

        # Semantic coherence
        semantic_coherence = self._calculate_semantic_coherence(chunks)

        # Overlap efficiency
        overlap_efficiency = self._calculate_overlap_efficiency(chunks)

        # Content loss
        content_loss = self._calculate_content_loss(chunks, original_content)

        # Chunk distribution
        chunk_distribution = self._get_chunk_distribution(chunks)

        # Overall quality score
        quality_score = self._calculate_quality_score(
            coverage_ratio, semantic_coherence, overlap_efficiency, content_loss
        )

        return ChunkQualityMetrics(
            total_chunks=total_chunks,
            avg_chunk_size=avg_chunk_size,
            coverage_ratio=coverage_ratio,
            semantic_coherence=semantic_coherence,
            overlap_efficiency=overlap_efficiency,
            content_loss=content_loss,
            chunk_distribution=chunk_distribution,
            quality_score=quality_score,
        )

    def _calculate_semantic_coherence(self, chunks: list[Chunk]) -> float:
        """Calculate semantic coherence between adjacent chunks."""
        if len(chunks) < 2:
            return 1.0

        coherence_scores = []
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]

            # Calculate word overlap
            current_words = set(current_chunk.content.lower().split())
            next_words = set(next_chunk.content.lower().split())

            if current_words and next_words:
                overlap = len(current_words.intersection(next_words))
                union = len(current_words.union(next_words))
                coherence = overlap / union if union > 0 else 0.0
                coherence_scores.append(coherence)

        return (
            sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
        )

    def _calculate_overlap_efficiency(self, chunks: list[Chunk]) -> float:
        """Calculate how efficiently overlap is used."""
        if len(chunks) < 2:
            return 1.0

        overlap_scores = []
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]

            # Calculate actual overlap
            actual_overlap = current_chunk.overlap_with_next
            expected_overlap = (
                min(len(current_chunk.content), len(next_chunk.content)) * 0.1
            )  # 10% expected

            if expected_overlap > 0:
                efficiency = min(actual_overlap / expected_overlap, 1.0)
                overlap_scores.append(efficiency)

        return sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0.0

    def _calculate_content_loss(
        self, chunks: list[Chunk], original_content: str
    ) -> float:
        """Calculate if any content is lost during chunking."""
        if not original_content:
            return 0.0

        # Reconstruct content from chunks
        reconstructed = ""
        for chunk in chunks:
            reconstructed += chunk.content + " "

        reconstructed = reconstructed.strip()

        # Calculate similarity (simplified)
        original_words = set(original_content.lower().split())
        reconstructed_words = set(reconstructed.lower().split())

        if original_words:
            lost_words = original_words - reconstructed_words
            content_loss = len(lost_words) / len(original_words)
            return content_loss

        return 0.0

    def _get_chunk_distribution(self, chunks: list[Chunk]) -> dict[str, int]:
        """Get distribution of chunk types."""
        distribution = {}
        for chunk in chunks:
            chunk_type = chunk.chunk_type
            distribution[chunk_type] = distribution.get(chunk_type, 0) + 1
        return distribution

    def _calculate_quality_score(
        self,
        coverage_ratio: float,
        semantic_coherence: float,
        overlap_efficiency: float,
        content_loss: float,
    ) -> float:
        """Calculate overall quality score."""
        # Weighted average of metrics
        weights = {"coverage": 0.3, "coherence": 0.3, "overlap": 0.2, "loss": 0.2}

        # Convert content loss to a positive score
        content_score = 1.0 - content_loss

        quality_score = (
            coverage_ratio * weights["coverage"]
            + semantic_coherence * weights["coherence"]
            + overlap_efficiency * weights["overlap"]
            + content_score * weights["loss"]
        )

        return min(max(quality_score, 0.0), 1.0)

    def get_chunk_statistics(self, chunks: list[Chunk]) -> dict[str, Any]:
        """Get detailed statistics about chunks."""
        if not chunks:
            return {}

        chunk_sizes = [len(chunk.content) for chunk in chunks]
        word_counts = [chunk.word_count for chunk in chunks]

        return {
            "total_chunks": len(chunks),
            "size_stats": {
                "min": min(chunk_sizes),
                "max": max(chunk_sizes),
                "mean": sum(chunk_sizes) / len(chunk_sizes),
                "median": sorted(chunk_sizes)[len(chunk_sizes) // 2],
            },
            "word_stats": {
                "min": min(word_counts),
                "max": max(word_counts),
                "mean": sum(word_counts) / len(word_counts),
                "median": sorted(word_counts)[len(word_counts) // 2],
            },
            "type_distribution": self._get_chunk_distribution(chunks),
            "overlap_stats": {
                "avg_previous_overlap": sum(
                    chunk.overlap_with_previous for chunk in chunks
                )
                / len(chunks),
                "avg_next_overlap": sum(chunk.overlap_with_next for chunk in chunks)
                / len(chunks),
            },
        }
