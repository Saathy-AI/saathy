"""Content chunking strategies for embedding generation."""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a content chunk."""
    
    content: str
    start_index: int
    end_index: int
    chunk_type: str
    metadata: Dict[str, Any]
    overlap_with_previous: int = 0
    overlap_with_next: int = 0


class ChunkingStrategy(ABC):
    """Base class for chunking strategies."""
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
    @abstractmethod
    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split content into chunks."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this chunking strategy."""
        pass


class FixedSizeChunking(ChunkingStrategy):
    """Fixed-size chunking with overlap."""
    
    def get_strategy_name(self) -> str:
        return "fixed_size"
        
    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split content into fixed-size chunks."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="fixed_size",
                metadata=metadata or {}
            )]
            
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.max_chunk_size
            
            # Try to break at word boundary
            if end < len(content):
                last_space = content.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
                    
            chunk_content = content[start:end].strip()
            if chunk_content:
                # Calculate overlaps
                overlap_prev = min(self.overlap, start)
                overlap_next = min(self.overlap, len(content) - end)
                
                chunks.append(Chunk(
                    content=chunk_content,
                    start_index=start,
                    end_index=end,
                    chunk_type="fixed_size",
                    metadata=metadata or {},
                    overlap_with_previous=overlap_prev,
                    overlap_with_next=overlap_next
                ))
                
            start = end - self.overlap
            if start >= len(content):
                break
                
        return chunks


class SemanticChunking(ChunkingStrategy):
    """Semantic chunking based on content structure."""
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        super().__init__(max_chunk_size, overlap)
        self.sentence_endings = r'[.!?]\s+'
        self.paragraph_breaks = r'\n\s*\n'
        
    def get_strategy_name(self) -> str:
        return "semantic"
        
    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split content based on semantic boundaries."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="semantic",
                metadata=metadata or {}
            )]
            
        # Split into sentences first
        sentences = re.split(self.sentence_endings, content)
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed max size, create a new chunk
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_content = ' '.join(current_chunk)
                end_index = start_index + len(chunk_content)
                
                chunks.append(Chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="semantic",
                    metadata=metadata or {},
                    overlap_with_previous=self.overlap,
                    overlap_with_next=self.overlap
                ))
                
                # Start new chunk with overlap
                overlap_start = max(0, len(chunk_content) - self.overlap)
                current_chunk = [chunk_content[overlap_start:]] if overlap_start > 0 else []
                current_size = len(current_chunk[0]) if current_chunk else 0
                start_index = end_index - self.overlap
                
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size
            
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            end_index = start_index + len(chunk_content)
            
            chunks.append(Chunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                chunk_type="semantic",
                metadata=metadata or {},
                overlap_with_previous=self.overlap,
                overlap_with_next=0
            ))
            
        return chunks


class DocumentAwareChunking(ChunkingStrategy):
    """Document-aware chunking that respects document structure."""
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        super().__init__(max_chunk_size, overlap)
        self.section_patterns = [
            r'^#{1,6}\s+',  # Markdown headers
            r'^[A-Z][A-Z\s]+\n[-=]+\n',  # Underlined headers
            r'^\d+\.\s+',  # Numbered sections
            r'^[A-Z][a-z]+\s*:\s*$',  # Section labels
        ]
        
    def get_strategy_name(self) -> str:
        return "document_aware"
        
    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split content based on document structure."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="document_aware",
                metadata=metadata or {}
            )]
            
        # Split into sections
        sections = self._split_into_sections(content)
        chunks = []
        
        for section in sections:
            if len(section['content']) <= self.max_chunk_size:
                # Section fits in one chunk
                chunks.append(Chunk(
                    content=section['content'],
                    start_index=section['start'],
                    end_index=section['end'],
                    chunk_type="document_aware",
                    metadata={**(metadata or {}), 'section_type': section['type']}
                ))
            else:
                # Split section into smaller chunks
                section_chunks = self._chunk_section(section, metadata)
                chunks.extend(section_chunks)
                
        return chunks
        
    def _split_into_sections(self, content: str) -> List[Dict[str, Any]]:
        """Split content into sections based on headers."""
        lines = content.split('\n')
        sections = []
        current_section = {
            'content': '',
            'start': 0,
            'end': 0,
            'type': 'body'
        }
        
        for i, line in enumerate(lines):
            # Check if line is a section header
            is_header = any(re.match(pattern, line) for pattern in self.section_patterns)
            
            if is_header and current_section['content']:
                # End current section
                current_section['end'] = current_section['start'] + len(current_section['content'])
                sections.append(current_section)
                
                # Start new section
                current_section = {
                    'content': line + '\n',
                    'start': current_section['end'],
                    'end': 0,
                    'type': 'header'
                }
            else:
                current_section['content'] += line + '\n'
                
        # Add final section
        if current_section['content']:
            current_section['end'] = current_section['start'] + len(current_section['content'])
            sections.append(current_section)
            
        return sections
        
    def _chunk_section(self, section: Dict[str, Any], metadata: Optional[Dict[str, Any]]) -> List[Chunk]:
        """Split a section into chunks."""
        content = section['content']
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.max_chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                last_period = content.rfind('.', start, end)
                if last_period > start:
                    end = last_period + 1
                    
            chunk_content = content[start:end].strip()
            if chunk_content:
                chunks.append(Chunk(
                    content=chunk_content,
                    start_index=section['start'] + start,
                    end_index=section['start'] + end,
                    chunk_type="document_aware",
                    metadata={**(metadata or {}), 'section_type': section['type']},
                    overlap_with_previous=self.overlap,
                    overlap_with_next=self.overlap
                ))
                
            start = end - self.overlap
            if start >= len(content):
                break
                
        return chunks


class CodeChunking(ChunkingStrategy):
    """Specialized chunking for code content."""
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        super().__init__(max_chunk_size, overlap)
        self.function_patterns = {
            'python': r'def\s+\w+\s*\([^)]*\)\s*:',
            'javascript': r'function\s+\w+\s*\([^)]*\)\s*\{',
            'java': r'(public|private|protected)?\s*\w+\s+\w+\s*\([^)]*\)\s*\{',
        }
        
    def get_strategy_name(self) -> str:
        return "code"
        
    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split code content based on function boundaries."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="code",
                metadata=metadata or {}
            )]
            
        # Detect language
        language = metadata.get('language', 'unknown') if metadata else 'unknown'
        
        # Split into functions
        functions = self._extract_functions(content, language)
        
        if not functions:
            # Fall back to fixed-size chunking
            fixed_chunker = FixedSizeChunking(self.max_chunk_size, self.overlap)
            return fixed_chunker.chunk(content, metadata)
            
        chunks = []
        for func in functions:
            if len(func['content']) <= self.max_chunk_size:
                # Function fits in one chunk
                chunks.append(Chunk(
                    content=func['content'],
                    start_index=func['start'],
                    end_index=func['end'],
                    chunk_type="code",
                    metadata={**(metadata or {}), 'function_name': func['name']}
                ))
            else:
                # Split large function
                func_chunks = self._chunk_function(func, metadata)
                chunks.extend(func_chunks)
                
        return chunks
        
    def _extract_functions(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Extract functions from code."""
        functions = []
        pattern = self.function_patterns.get(language)
        
        if not pattern:
            return functions
            
        matches = list(re.finditer(pattern, content, re.MULTILINE))
        
        for i, match in enumerate(matches):
            start = match.start()
            
            # Find function end (simplified)
            if i < len(matches) - 1:
                end = matches[i + 1].start()
            else:
                end = len(content)
                
            func_content = content[start:end].strip()
            func_name = match.group().split('(')[0].split()[-1]
            
            functions.append({
                'name': func_name,
                'content': func_content,
                'start': start,
                'end': end
            })
            
        return functions
        
    def _chunk_function(self, func: Dict[str, Any], metadata: Optional[Dict[str, Any]]) -> List[Chunk]:
        """Split a large function into chunks."""
        content = func['content']
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.max_chunk_size
            
            # Try to break at line boundary
            if end < len(content):
                last_newline = content.rfind('\n', start, end)
                if last_newline > start:
                    end = last_newline
                    
            chunk_content = content[start:end].strip()
            if chunk_content:
                chunks.append(Chunk(
                    content=chunk_content,
                    start_index=func['start'] + start,
                    end_index=func['start'] + end,
                    chunk_type="code",
                    metadata={**(metadata or {}), 'function_name': func['name']},
                    overlap_with_previous=self.overlap,
                    overlap_with_next=self.overlap
                ))
                
            start = end - self.overlap
            if start >= len(content):
                break
                
        return chunks


class ChunkingPipeline:
    """Pipeline for content chunking."""
    
    def __init__(self):
        self.strategies = {
            "fixed": FixedSizeChunking(),
            "semantic": SemanticChunking(),
            "document": DocumentAwareChunking(),
            "code": CodeChunking()
        }
        
    def chunk(self, content: str, strategy: str = "semantic", 
              max_chunk_size: Optional[int] = None, overlap: Optional[int] = None,
              metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Chunk content using the specified strategy."""
        if strategy not in self.strategies:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
            
        chunker = self.strategies[strategy]
        
        # Update chunker parameters if provided
        if max_chunk_size is not None:
            chunker.max_chunk_size = max_chunk_size
        if overlap is not None:
            chunker.overlap = overlap
            
        return chunker.chunk(content, metadata)
        
    def get_available_strategies(self) -> List[str]:
        """Get list of available chunking strategies."""
        return list(self.strategies.keys())
        
    def add_strategy(self, name: str, strategy: ChunkingStrategy) -> None:
        """Add a custom chunking strategy."""
        self.strategies[name] = strategy
        logger.info(f"Added custom chunking strategy: {name}")
        
    def validate_chunks(self, chunks: List[Chunk], original_content: str) -> Dict[str, Any]:
        """Validate chunk quality and coverage."""
        if not chunks:
            return {"valid": False, "error": "No chunks generated"}
            
        # Check coverage
        total_chunk_length = sum(len(chunk.content) for chunk in chunks)
        coverage_ratio = total_chunk_length / len(original_content) if original_content else 0
        
        # Check for overlaps
        overlaps = []
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            if current_chunk.end_index > next_chunk.start_index:
                overlaps.append({
                    'chunk_index': i,
                    'overlap_size': current_chunk.end_index - next_chunk.start_index
                })
                
        # Check chunk sizes
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        max_size = max(chunk_sizes) if chunk_sizes else 0
        min_size = min(chunk_sizes) if chunk_sizes else 0
        
        return {
            "valid": coverage_ratio > 0.8,  # At least 80% coverage
            "coverage_ratio": coverage_ratio,
            "total_chunks": len(chunks),
            "avg_chunk_size": avg_size,
            "max_chunk_size": max_size,
            "min_chunk_size": min_size,
            "overlaps": overlaps,
            "warnings": []
        } 