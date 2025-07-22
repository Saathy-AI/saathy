"""Chunk visualization tools."""

import json
from typing import Any, Optional

from ..core.models import Chunk


class ChunkVisualizer:
    """Visualization tools for chunk analysis."""
    
    def __init__(self):
        self.plot_available = self._check_matplotlib()
    
    def _check_matplotlib(self) -> bool:
        """Check if matplotlib is available."""
        try:
            import matplotlib
            return True
        except ImportError:
            return False
    
    def plot_chunk_size_distribution(self, chunks: list[Chunk], save_path: Optional[str] = None) -> None:
        """Plot chunk size distribution."""
        if not self.plot_available:
            print("Matplotlib not available for plotting")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            chunk_sizes = [len(chunk.content) for chunk in chunks]
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Histogram
            ax1.hist(chunk_sizes, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax1.set_xlabel('Chunk Size (characters)')
            ax1.set_ylabel('Frequency')
            ax1.set_title('Chunk Size Distribution')
            ax1.grid(True, alpha=0.3)
            
            # Box plot
            ax2.boxplot(chunk_sizes, patch_artist=True, boxprops=dict(facecolor='lightgreen'))
            ax2.set_ylabel('Chunk Size (characters)')
            ax2.set_title('Chunk Size Box Plot')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()
                
        except Exception as e:
            print(f"Error creating plot: {e}")
    
    def plot_chunk_overlap_analysis(self, chunks: list[Chunk], save_path: Optional[str] = None) -> None:
        """Plot chunk overlap analysis."""
        if not self.plot_available or len(chunks) < 2:
            return
        
        try:
            import matplotlib.pyplot as plt
            
            chunk_indices = list(range(len(chunks)))
            previous_overlaps = [chunk.overlap_with_previous for chunk in chunks]
            next_overlaps = [chunk.overlap_with_next for chunk in chunks]
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Overlap comparison
            ax1.plot(chunk_indices, previous_overlaps, 'o-', label='Overlap with Previous', alpha=0.7)
            ax1.plot(chunk_indices, next_overlaps, 's-', label='Overlap with Next', alpha=0.7)
            ax1.set_xlabel('Chunk Index')
            ax1.set_ylabel('Overlap Size (characters)')
            ax1.set_title('Chunk Overlap Analysis')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Overlap distribution
            ax2.hist(previous_overlaps + next_overlaps, bins=15, alpha=0.7, color='orange', edgecolor='black')
            ax2.set_xlabel('Overlap Size (characters)')
            ax2.set_ylabel('Frequency')
            ax2.set_title('Overlap Size Distribution')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()
                
        except Exception as e:
            print(f"Error creating overlap plot: {e}")
    
    def plot_chunk_type_distribution(self, chunks: list[Chunk], save_path: Optional[str] = None) -> None:
        """Plot chunk type distribution."""
        if not self.plot_available:
            return
        
        try:
            import matplotlib.pyplot as plt
            
            # Count chunk types
            type_counts = {}
            for chunk in chunks:
                chunk_type = chunk.chunk_type
                type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
            
            if not type_counts:
                return
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Pie chart
            labels = list(type_counts.keys())
            sizes = list(type_counts.values())
            colors = plt.cm.Set3(range(len(labels)))
            
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
            ax1.set_title('Chunk Type Distribution')
            
            # Bar chart
            ax2.bar(labels, sizes, color=colors, alpha=0.7, edgecolor='black')
            ax2.set_xlabel('Chunk Type')
            ax2.set_ylabel('Count')
            ax2.set_title('Chunk Type Counts')
            ax2.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()
                
        except Exception as e:
            print(f"Error creating type distribution plot: {e}")
    
    def plot_quality_metrics(self, metrics: dict[str, Any], save_path: Optional[str] = None) -> None:
        """Plot quality metrics radar chart."""
        if not self.plot_available:
            return
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Extract metrics
            categories = ['Coverage', 'Coherence', 'Overlap', 'Content']
            values = [
                metrics.get('coverage_ratio', 0.0),
                metrics.get('semantic_coherence', 0.0),
                metrics.get('overlap_efficiency', 0.0),
                1.0 - metrics.get('content_loss', 0.0)
            ]
            
            # Create radar chart
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            values += values[:1]  # Complete the circle
            angles += angles[:1]
            
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            ax.plot(angles, values, 'o-', linewidth=2, label='Quality Metrics')
            ax.fill(angles, values, alpha=0.25)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_ylim(0, 1)
            ax.set_title('Chunk Quality Metrics', size=16, y=1.08)
            ax.grid(True)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()
                
        except Exception as e:
            print(f"Error creating quality metrics plot: {e}")
    
    def create_chunk_report(self, chunks: list[Chunk], original_content: str, save_path: Optional[str] = None) -> dict[str, Any]:
        """Create a comprehensive chunk analysis report."""
        from .analyzer import ChunkAnalyzer
        
        analyzer = ChunkAnalyzer()
        metrics = analyzer.analyze_chunks(chunks, original_content)
        statistics = analyzer.get_chunk_statistics(chunks)
        
        report = {
            "summary": {
                "total_chunks": metrics.total_chunks,
                "original_content_length": len(original_content),
                "total_chunk_length": sum(len(chunk.content) for chunk in chunks),
                "quality_score": metrics.quality_score
            },
            "metrics": {
                "avg_chunk_size": metrics.avg_chunk_size,
                "coverage_ratio": metrics.coverage_ratio,
                "semantic_coherence": metrics.semantic_coherence,
                "overlap_efficiency": metrics.overlap_efficiency,
                "content_loss": metrics.content_loss
            },
            "statistics": statistics,
            "chunks": [
                {
                    "index": i,
                    "content_preview": chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content,
                    "size": len(chunk.content),
                    "word_count": chunk.word_count,
                    "type": chunk.chunk_type,
                    "start_index": chunk.start_index,
                    "end_index": chunk.end_index,
                    "overlap_with_previous": chunk.overlap_with_previous,
                    "overlap_with_next": chunk.overlap_with_next
                }
                for i, chunk in enumerate(chunks)
            ]
        }
        
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report
    
    def visualize_chunk_boundaries(self, chunks: list[Chunk], original_content: str, save_path: Optional[str] = None) -> None:
        """Visualize chunk boundaries on the original content."""
        if not self.plot_available:
            return
        
        try:
            import matplotlib.pyplot as plt
            
            # Create a timeline visualization
            content_length = len(original_content)
            chunk_boundaries = [(chunk.start_index, chunk.end_index) for chunk in chunks]
            
            fig, ax = plt.subplots(figsize=(15, 6))
            
            # Plot content timeline
            ax.plot([0, content_length], [0, 0], 'k-', linewidth=2, label='Original Content')
            
            # Plot chunk boundaries
            for i, (start, end) in enumerate(chunk_boundaries):
                ax.plot([start, end], [0, 0], 'o-', linewidth=3, markersize=8, label=f'Chunk {i+1}' if i < 5 else "")
                ax.text((start + end) / 2, 0.1, f'C{i+1}', ha='center', va='bottom', fontsize=8)
            
            ax.set_xlim(0, content_length)
            ax.set_ylim(-0.5, 0.5)
            ax.set_xlabel('Character Position')
            ax.set_title('Chunk Boundaries Visualization')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()
                
        except Exception as e:
            print(f"Error creating boundary visualization: {e}") 