"""Semantic chunking strategy."""

import re
from typing import Optional

from .base import BaseChunkingStrategy
from ..core.models import Chunk, ChunkMetadata


class SemanticChunker(BaseChunkingStrategy):
    """Sentence boundary-aware chunking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sentence_endings = r'[.!?]\s+'
        self.paragraph_breaks = r'\n\s*\n'
        self.semantic_breaks = [
            r'\n\s*[-*+]\s+',  # List items
            r'\n\s*\d+\.\s+',  # Numbered lists
            r'\n\s*[A-Z][a-z]+:\s*$',  # Section labels
        ]
    
    def get_strategy_name(self) -> str:
        return "semantic"
    
    def _chunk_implementation(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Split content based on semantic boundaries."""
        if len(content) <= self.max_chunk_size:
            return [self._create_chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="semantic",
                metadata=metadata
            )]
        
        # Split into semantic units
        semantic_units = self._split_into_semantic_units(content)
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0
        
        for unit in semantic_units:
            unit = unit.strip()
            if not unit:
                continue
            
            unit_size = len(unit)
            
            # If adding this unit would exceed max size, create a new chunk
            if current_size + unit_size > self.max_chunk_size and current_chunk:
                chunk_content = ' '.join(current_chunk)
                end_index = start_index + len(chunk_content)
                
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="semantic",
                    metadata=metadata
                ))
                
                # Start new chunk with overlap
                overlap_start = max(0, len(chunk_content) - self.overlap)
                current_chunk = [chunk_content[overlap_start:]] if overlap_start > 0 else []
                current_size = len(current_chunk[0]) if current_chunk else 0
                start_index = end_index - self.overlap
            
            # Add unit to current chunk
            current_chunk.append(unit)
            current_size += unit_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            end_index = start_index + len(chunk_content)
            
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                chunk_type="semantic",
                metadata=metadata
            ))
        
        return chunks
    
    def _split_into_semantic_units(self, content: str) -> list[str]:
        """Split content into semantic units."""
        # First split by paragraph breaks
        paragraphs = re.split(self.paragraph_breaks, content)
        units = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Split paragraph into sentences
            sentences = re.split(self.sentence_endings, paragraph)
            units.extend([s.strip() for s in sentences if s.strip()])
        
        return units 