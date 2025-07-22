"""Chunk analysis and debugging tools."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import json
import re

from .strategies import Chunk, ChunkMetadata, ContentType

logger = logging.getLogger(__name__)


@dataclass
class ChunkQualityMetrics:
    """Comprehensive chunk quality metrics."""
    total_chunks: int
    avg_chunk_size: float
    min_chunk_size: int
    max_chunk_size: int
    coverage_ratio: float
    semantic_coherence: float
    overlap_efficiency: float
    content_loss: float
    chunk_distribution: Dict[str, int]
    quality_score: float


class ChunkAnalyzer:
    """Analyzes chunk quality and characteristics."""
    
    def __init__(self):
        self.sentence_endings = r'[.!?]\s+'
        self.word_pattern = r'\b\w+\b'
    
    def analyze_chunks(self, chunks: List[Chunk], original_content: str) -> ChunkQualityMetrics:
        """Perform comprehensive chunk analysis."""
        if not chunks:
            return ChunkQualityMetrics(
                total_chunks=0,
                avg_chunk_size=0,
                min_chunk_size=0,
                max_chunk_size=0,
                coverage_ratio=0,
                semantic_coherence=0,
                overlap_efficiency=0,
                content_loss=0,
                chunk_distribution={},
                quality_score=0
            )
        
        # Basic metrics
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        total_chunk_length = sum(chunk_sizes)
        
        # Coverage analysis
        coverage_ratio = total_chunk_length / len(original_content) if original_content else 0
        
        # Semantic coherence
        semantic_coherence = self._calculate_semantic_coherence(chunks)
        
        # Overlap efficiency
        overlap_efficiency = self._calculate_overlap_efficiency(chunks)
        
        # Content loss
        content_loss = self._calculate_content_loss(chunks, original_content)
        
        # Chunk distribution by type
        chunk_distribution = Counter(chunk.chunk_type for chunk in chunks)
        
        # Quality score (weighted combination of metrics)
        quality_score = self._calculate_quality_score(
            coverage_ratio, semantic_coherence, overlap_efficiency, content_loss
        )
        
        return ChunkQualityMetrics(
            total_chunks=len(chunks),
            avg_chunk_size=sum(chunk_sizes) / len(chunk_sizes),
            min_chunk_size=min(chunk_sizes),
            max_chunk_size=max(chunk_sizes),
            coverage_ratio=coverage_ratio,
            semantic_coherence=semantic_coherence,
            overlap_efficiency=overlap_efficiency,
            content_loss=content_loss,
            chunk_distribution=dict(chunk_distribution),
            quality_score=quality_score
        )
    
    def _calculate_semantic_coherence(self, chunks: List[Chunk]) -> float:
        """Calculate semantic coherence between adjacent chunks."""
        if len(chunks) < 2:
            return 1.0
        
        coherence_scores = []
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Calculate word overlap
            current_words = set(re.findall(self.word_pattern, current_chunk.content.lower()))
            next_words = set(re.findall(self.word_pattern, next_chunk.content.lower()))
            
            if current_words and next_words:
                overlap = len(current_words & next_words)
                union = len(current_words | next_words)
                jaccard_similarity = overlap / union if union > 0 else 0
                coherence_scores.append(jaccard_similarity)
        
        return sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
    
    def _calculate_overlap_efficiency(self, chunks: List[Chunk]) -> float:
        """Calculate efficiency of overlap usage."""
        if len(chunks) < 2:
            return 1.0
        
        total_overlap = 0
        total_chunk_length = 0
        
        for chunk in chunks:
            total_overlap += chunk.overlap_with_previous + chunk.overlap_with_next
            total_chunk_length += len(chunk.content)
        
        # Efficiency is inverse of overlap ratio (lower overlap = higher efficiency)
        overlap_ratio = total_overlap / total_chunk_length if total_chunk_length > 0 else 0
        return max(0, 1 - overlap_ratio)
    
    def _calculate_content_loss(self, chunks: List[Chunk], original_content: str) -> float:
        """Calculate content loss during chunking."""
        if not original_content:
            return 0
        
        # Reconstruct content from chunks
        reconstructed = ""
        for chunk in chunks:
            reconstructed += chunk.content + " "
        
        reconstructed = reconstructed.strip()
        
        # Calculate similarity using word overlap
        original_words = set(re.findall(self.word_pattern, original_content.lower()))
        reconstructed_words = set(re.findall(self.word_pattern, reconstructed.lower()))
        
        if original_words:
            lost_words = len(original_words - reconstructed_words)
            return lost_words / len(original_words)
        
        return 0
    
    def _calculate_quality_score(self, 
                                coverage: float, 
                                coherence: float, 
                                efficiency: float, 
                                loss: float) -> float:
        """Calculate overall quality score."""
        # Weighted combination of metrics
        weights = {
            'coverage': 0.3,
            'coherence': 0.25,
            'efficiency': 0.25,
            'loss': 0.2
        }
        
        # Loss is penalized (higher loss = lower score)
        loss_score = 1 - loss
        
        score = (coverage * weights['coverage'] + 
                coherence * weights['coherence'] + 
                efficiency * weights['efficiency'] + 
                loss_score * weights['loss'])
        
        return max(0, min(1, score))  # Clamp between 0 and 1
    
    def get_chunk_statistics(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Get detailed statistics about chunks."""
        if not chunks:
            return {}
        
        # Size statistics
        sizes = [len(chunk.content) for chunk in chunks]
        size_stats = {
            'mean': np.mean(sizes),
            'median': np.median(sizes),
            'std': np.std(sizes),
            'min': np.min(sizes),
            'max': np.max(sizes),
            'percentiles': {
                '25': np.percentile(sizes, 25),
                '50': np.percentile(sizes, 50),
                '75': np.percentile(sizes, 75),
                '90': np.percentile(sizes, 90),
                '95': np.percentile(sizes, 95)
            }
        }
        
        # Type distribution
        type_distribution = Counter(chunk.chunk_type for chunk in chunks)
        
        # Content type distribution
        content_type_distribution = Counter(
            chunk.metadata.content_type.value for chunk in chunks
        )
        
        # Overlap statistics
        overlaps_prev = [chunk.overlap_with_previous for chunk in chunks]
        overlaps_next = [chunk.overlap_with_next for chunk in chunks]
        
        overlap_stats = {
            'previous_mean': np.mean(overlaps_prev),
            'next_mean': np.mean(overlaps_next),
            'total_overlap': sum(overlaps_prev) + sum(overlaps_next)
        }
        
        return {
            'size_statistics': size_stats,
            'type_distribution': dict(type_distribution),
            'content_type_distribution': dict(content_type_distribution),
            'overlap_statistics': overlap_stats,
            'total_chunks': len(chunks),
            'total_content_length': sum(sizes)
        }


class ChunkVisualizer:
    """Visualizes chunk characteristics and quality metrics."""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        self.figsize = figsize
    
    def plot_chunk_size_distribution(self, chunks: List[Chunk], save_path: Optional[str] = None):
        """Plot distribution of chunk sizes."""
        if not chunks:
            logger.warning("No chunks to visualize")
            return
        
        sizes = [len(chunk.content) for chunk in chunks]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.figsize)
        
        # Histogram
        ax1.hist(sizes, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.set_xlabel('Chunk Size (characters)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Chunk Size Distribution')
        ax1.grid(True, alpha=0.3)
        
        # Box plot
        ax2.boxplot(sizes, patch_artist=True, boxprops=dict(facecolor='lightgreen'))
        ax2.set_ylabel('Chunk Size (characters)')
        ax2.set_title('Chunk Size Box Plot')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_chunk_overlap_analysis(self, chunks: List[Chunk], save_path: Optional[str] = None):
        """Plot overlap analysis between chunks."""
        if len(chunks) < 2:
            logger.warning("Need at least 2 chunks for overlap analysis")
            return
        
        overlaps_prev = [chunk.overlap_with_previous for chunk in chunks]
        overlaps_next = [chunk.overlap_with_next for chunk in chunks]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.figsize)
        
        # Overlap comparison
        x = range(len(chunks))
        ax1.plot(x, overlaps_prev, 'o-', label='Overlap with Previous', color='blue')
        ax1.plot(x, overlaps_next, 's-', label='Overlap with Next', color='red')
        ax1.set_xlabel('Chunk Index')
        ax1.set_ylabel('Overlap Size (characters)')
        ax1.set_title('Chunk Overlap Analysis')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Overlap distribution
        all_overlaps = overlaps_prev + overlaps_next
        ax2.hist(all_overlaps, bins=15, alpha=0.7, color='orange', edgecolor='black')
        ax2.set_xlabel('Overlap Size (characters)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Overlap Size Distribution')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_chunk_type_distribution(self, chunks: List[Chunk], save_path: Optional[str] = None):
        """Plot distribution of chunk types."""
        if not chunks:
            logger.warning("No chunks to visualize")
            return
        
        type_counts = Counter(chunk.chunk_type for chunk in chunks)
        content_type_counts = Counter(chunk.metadata.content_type.value for chunk in chunks)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.figsize)
        
        # Chunk type distribution
        types, counts = zip(*type_counts.items())
        ax1.pie(counts, labels=types, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Chunk Type Distribution')
        
        # Content type distribution
        content_types, content_counts = zip(*content_type_counts.items())
        ax2.bar(content_types, content_counts, color='lightcoral')
        ax2.set_xlabel('Content Type')
        ax2.set_ylabel('Count')
        ax2.set_title('Content Type Distribution')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_quality_metrics(self, metrics: ChunkQualityMetrics, save_path: Optional[str] = None):
        """Plot quality metrics radar chart."""
        # Prepare data for radar chart
        categories = ['Coverage', 'Coherence', 'Efficiency', 'Quality Score']
        values = [
            metrics.coverage_ratio,
            metrics.semantic_coherence,
            metrics.overlap_efficiency,
            metrics.quality_score
        ]
        
        # Number of variables
        N = len(categories)
        
        # Create angles for each category
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Complete the circle
        
        # Add the first value at the end to close the plot
        values += values[:1]
        
        # Create the plot
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        # Plot the data
        ax.plot(angles, values, 'o-', linewidth=2, label='Quality Metrics')
        ax.fill(angles, values, alpha=0.25)
        
        # Set the labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 1)
        ax.set_title('Chunk Quality Metrics', size=16, y=1.08)
        
        # Add grid
        ax.grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def create_chunk_report(self, 
                           chunks: List[Chunk], 
                           original_content: str,
                           output_path: str) -> None:
        """Create a comprehensive chunk analysis report."""
        analyzer = ChunkAnalyzer()
        metrics = analyzer.analyze_chunks(chunks, original_content)
        stats = analyzer.get_chunk_statistics(chunks)
        
        # Create report
        report = {
            'summary': {
                'total_chunks': metrics.total_chunks,
                'total_content_length': len(original_content),
                'total_chunk_length': sum(len(chunk.content) for chunk in chunks),
                'quality_score': metrics.quality_score
            },
            'quality_metrics': {
                'coverage_ratio': metrics.coverage_ratio,
                'semantic_coherence': metrics.semantic_coherence,
                'overlap_efficiency': metrics.overlap_efficiency,
                'content_loss': metrics.content_loss
            },
            'size_statistics': stats.get('size_statistics', {}),
            'type_distribution': stats.get('type_distribution', {}),
            'content_type_distribution': stats.get('content_type_distribution', {}),
            'overlap_statistics': stats.get('overlap_statistics', {}),
            'chunks': [
                {
                    'index': i,
                    'content_preview': chunk.content[:100] + '...' if len(chunk.content) > 100 else chunk.content,
                    'size': len(chunk.content),
                    'type': chunk.chunk_type,
                    'content_type': chunk.metadata.content_type.value,
                    'overlap_previous': chunk.overlap_with_previous,
                    'overlap_next': chunk.overlap_with_next,
                    'metadata': chunk.metadata.custom_fields
                }
                for i, chunk in enumerate(chunks)
            ]
        }
        
        # Save report
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Chunk analysis report saved to {output_path}")
    
    def visualize_chunk_boundaries(self, 
                                  chunks: List[Chunk], 
                                  original_content: str,
                                  save_path: Optional[str] = None) -> None:
        """Visualize chunk boundaries in the original content."""
        if not chunks or not original_content:
            logger.warning("No chunks or content to visualize")
            return
        
        # Create a visualization of chunk boundaries
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Plot content length
        content_length = len(original_content)
        ax.plot([0, content_length], [0, 0], 'k-', linewidth=2, label='Original Content')
        
        # Plot chunk boundaries
        colors = plt.cm.Set3(np.linspace(0, 1, len(chunks)))
        
        for i, chunk in enumerate(chunks):
            color = colors[i]
            ax.axvspan(chunk.start_index, chunk.end_index, 
                      alpha=0.3, color=color, 
                      label=f'Chunk {i+1} ({chunk.chunk_type})')
            
            # Add chunk center marker
            center = (chunk.start_index + chunk.end_index) / 2
            ax.plot(center, 0, 'o', color=color, markersize=8)
        
        ax.set_xlabel('Character Position')
        ax.set_ylabel('Chunks')
        ax.set_title('Chunk Boundaries Visualization')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close() 