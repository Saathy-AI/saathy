"""Code-aware chunking strategy."""

import re
from typing import Optional

from .base import BaseChunkingStrategy
from ..core.models import Chunk, ChunkMetadata


class CodeChunker(BaseChunkingStrategy):
    """Function/class-aware code chunking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.language_patterns = {
            'python': {
                'function': r'def\s+\w+\s*\([^)]*\)\s*:',
                'class': r'class\s+\w+',
                'import': r'(?:from|import)\s+\w+',
                'comment': r'#.*$',
                'docstring': r'""".*?"""',
            },
            'javascript': {
                'function': r'function\s+\w+\s*\([^)]*\)\s*{',
                'class': r'class\s+\w+',
                'import': r'(?:import|export)\s+',
                'comment': r'//.*$|/\*.*?\*/',
            },
            'java': {
                'function': r'(?:public|private|protected)?\s*(?:static\s+)?\w+\s+\w+\s*\([^)]*\)\s*{',
                'class': r'(?:public\s+)?class\s+\w+',
                'import': r'import\s+',
                'comment': r'//.*$|/\*.*?\*/',
            }
        }
    
    def get_strategy_name(self) -> str:
        return "code"
    
    def _chunk_implementation(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Split code based on function/class boundaries."""
        if len(content) <= self.max_chunk_size:
            return [self._create_chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="code",
                metadata=metadata
            )]
        
        # Detect programming language
        language = self._detect_language(content)
        patterns = self.language_patterns.get(language, {})
        
        # Split into logical units
        units = self._split_code_units(content, patterns)
        
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0
        
        for unit in units:
            unit = unit.strip()
            if not unit:
                continue
            
            unit_size = len(unit)
            
            # If adding this unit would exceed max size, create a new chunk
            if current_size + unit_size > self.max_chunk_size and current_chunk:
                chunk_content = '\n'.join(current_chunk)
                end_index = start_index + len(chunk_content)
                
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="code",
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
            chunk_content = '\n'.join(current_chunk)
            end_index = start_index + len(chunk_content)
            
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                chunk_type="code",
                metadata=metadata
            ))
        
        return chunks
    
    def _detect_language(self, content: str) -> str:
        """Detect programming language from content."""
        content_lower = content.lower()
        
        if 'def ' in content_lower or 'import ' in content_lower or 'class ' in content_lower:
            return 'python'
        elif 'function ' in content_lower or 'var ' in content_lower or 'const ' in content_lower:
            return 'javascript'
        elif 'public class' in content_lower or 'private ' in content_lower:
            return 'java'
        else:
            return 'python'  # Default to Python
    
    def _split_code_units(self, content: str, patterns: dict[str, str]) -> list[str]:
        """Split code into logical units."""
        lines = content.split('\n')
        units = []
        current_unit = []
        
        for line in lines:
            # Check if line starts a new unit
            is_new_unit = any(re.match(pattern, line.strip()) for pattern in patterns.values())
            
            if is_new_unit and current_unit:
                units.append('\n'.join(current_unit))
                current_unit = []
            
            current_unit.append(line)
        
        # Add final unit
        if current_unit:
            units.append('\n'.join(current_unit))
        
        return units 