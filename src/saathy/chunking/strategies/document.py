"""Document structure-aware chunking strategy."""

import re
from typing import Optional

from .base import BaseChunkingStrategy
from ..core.models import Chunk, ChunkMetadata


class DocumentChunker(BaseChunkingStrategy):
    """Structure-aware document chunking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.header_patterns = [
            r'^#{1,6}\s+',  # Markdown headers
            r'^[A-Z][A-Z\s]+\n[-=]+\n',  # Underlined headers
            r'^\d+\.\s+[A-Z]',  # Numbered sections
            r'^[A-Z][a-z]+:\s*$',  # Section labels
        ]
    
    def get_strategy_name(self) -> str:
        return "document"
    
    def _chunk_implementation(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Split document based on structure and headers."""
        if len(content) <= self.max_chunk_size:
            return [self._create_chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="document",
                metadata=metadata
            )]
        
        # Split into sections based on headers
        sections = self._split_into_sections(content)
        
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            section_size = len(section)
            
            # If adding this section would exceed max size, create a new chunk
            if current_size + section_size > self.max_chunk_size and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                end_index = start_index + len(chunk_content)
                
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="document",
                    metadata=metadata
                ))
                
                # Start new chunk with overlap
                overlap_start = max(0, len(chunk_content) - self.overlap)
                current_chunk = [chunk_content[overlap_start:]] if overlap_start > 0 else []
                current_size = len(current_chunk[0]) if current_chunk else 0
                start_index = end_index - self.overlap
            
            # Add section to current chunk
            current_chunk.append(section)
            current_size += section_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            end_index = start_index + len(chunk_content)
            
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                chunk_type="document",
                metadata=metadata
            ))
        
        return chunks
    
    def _split_into_sections(self, content: str) -> list[str]:
        """Split document into sections based on headers."""
        lines = content.split('\n')
        sections = []
        current_section = []
        
        for line in lines:
            # Check if line is a header
            is_header = any(re.match(pattern, line) for pattern in self.header_patterns)
            
            if is_header and current_section:
                sections.append('\n'.join(current_section))
                current_section = []
            
            current_section.append(line)
        
        # Add final section
        if current_section:
            sections.append('\n'.join(current_section))
        
        return sections 