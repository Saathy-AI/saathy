#!/usr/bin/env python3
"""Demonstration of the Modular Chunking System."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from saathy.chunking import (
    ChunkingProcessor, ChunkingConfig, ContentType,
    FixedSizeChunker, SemanticChunker, CodeChunker,
    ContentTypeDetector
)
from saathy.chunking.analysis import ChunkAnalyzer, ChunkVisualizer


def demonstrate_modular_architecture():
    """Demonstrate the modular architecture of the chunking system."""
    
    print("🏗️  Modular Chunking System Architecture")
    print("=" * 50)
    
    # 1. Core Configuration
    print("\n1. Core Configuration")
    config = ChunkingConfig(
        max_chunk_size=512,
        overlap=50,
        min_chunk_size=50,
        preserve_context=True,
        enable_caching=True
    )
    print(f"   Configuration: {config}")
    
    # 2. Content Type Detection
    print("\n2. Content Type Detection")
    detector = ContentTypeDetector()
    
    test_cases = [
        ("Python Code", "def hello():\n    print('Hello')", None),
        ("Markdown Document", "# Title\n\nContent", None),
        ("Meeting Transcript", "Alice: Hello\nBob: Hi", None),
    ]
    
    for name, content, extension in test_cases:
        detected_type = detector.detect_content_type(content, extension)
        print(f"   {name:20} -> {detected_type}")
    
    # 3. Individual Strategies
    print("\n3. Individual Strategies")
    
    # Fixed Size Strategy
    fixed_chunker = FixedSizeChunker(max_chunk_size=100, overlap=20)
    print(f"   FixedSizeChunker: {fixed_chunker.get_strategy_name()}")
    
    # Semantic Strategy
    semantic_chunker = SemanticChunker(max_chunk_size=200, overlap=30)
    print(f"   SemanticChunker: {semantic_chunker.get_strategy_name()}")
    
    # Code Strategy
    code_chunker = CodeChunker(max_chunk_size=150, overlap=25)
    print(f"   CodeChunker: {code_chunker.get_strategy_name()}")
    
    # 4. Main Processor
    print("\n4. Main Processor")
    processor = ChunkingProcessor(config)
    
    # Test different content types
    test_contents = {
        "Code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
        """,
        
        "Document": """
# Machine Learning Fundamentals

## Introduction
Machine learning is a subset of artificial intelligence.

## Types of Learning
### Supervised Learning
Uses labeled training data.
        """,
        
        "Meeting": """
Alice: Good morning everyone!
Bob: Hi Alice! I completed the authentication module.
Alice: Great! Any blockers?
Bob: No blockers from my side.
        """
    }
    
    for content_type, content in test_contents.items():
        print(f"\n   Processing {content_type}:")
        chunks = processor.chunk_content(content)
        print(f"     Generated {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
            print(f"     Chunk {i+1}: {len(chunk.content)} chars, Type: {chunk.chunk_type}")
    
    # 5. Analysis Tools
    print("\n5. Analysis Tools")
    analyzer = ChunkAnalyzer()
    visualizer = ChunkVisualizer()
    
    # Analyze chunks
    content = "This is a test document for analysis. " * 20
    chunks = processor.chunk_content(content)
    metrics = analyzer.analyze_chunks(chunks, content)
    
    print(f"   Quality Score: {metrics.quality_score:.2f}")
    print(f"   Coverage Ratio: {metrics.coverage_ratio:.2f}")
    print(f"   Semantic Coherence: {metrics.semantic_coherence:.2f}")
    
    # 6. Strategy Management
    print("\n6. Strategy Management")
    strategies = processor.list_strategies()
    print("   Available strategies:")
    for content_type, strategy_name in strategies.items():
        print(f"     {content_type}: {strategy_name}")
    
    # 7. Statistics
    print("\n7. Processor Statistics")
    stats = processor.get_chunking_stats()
    print(f"   Configuration: {stats['config']}")
    print(f"   Cache enabled: {stats['config']['enable_caching']}")


def demonstrate_extensibility():
    """Demonstrate how to extend the system with custom strategies."""
    
    print("\n🔧 Extensibility Demonstration")
    print("=" * 50)
    
    # Create a custom chunking strategy
    from saathy.chunking.core import ChunkingStrategy
    from saathy.chunking.core.models import Chunk, ChunkMetadata
    from typing import Optional
    
    class CustomChunker(ChunkingStrategy):
        """Custom chunking strategy for demonstration."""
        
        def get_strategy_name(self) -> str:
            return "custom"
        
        def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
            """Custom chunking logic."""
            # Simple word-based chunking
            words = content.split()
            chunks = []
            
            for i in range(0, len(words), 10):  # 10 words per chunk
                chunk_words = words[i:i+10]
                chunk_content = " ".join(chunk_words)
                
                if chunk_content:
                    chunks.append(Chunk(
                        content=chunk_content,
                        start_index=0,  # Simplified for demo
                        end_index=len(chunk_content),
                        chunk_type="custom",
                        metadata=metadata or ChunkMetadata(content_type=ContentType.TEXT)
                    ))
            
            return chunks
    
    # Add custom strategy to processor
    processor = ChunkingProcessor()
    custom_strategy = CustomChunker()
    
    # Add strategy for a new content type
    processor.add_strategy(ContentType.TEXT, custom_strategy)
    
    print("   Added custom chunking strategy")
    print(f"   Available strategies: {list(processor.list_strategies().keys())}")
    
    # Test custom strategy
    content = "This is a test of the custom chunking strategy. " * 5
    chunks = processor.chunk_content(content, content_type="text")
    
    print(f"   Custom strategy generated {len(chunks)} chunks")
    for i, chunk in enumerate(chunks[:3]):
        print(f"     Chunk {i+1}: {chunk.content[:50]}...")


def demonstrate_error_handling():
    """Demonstrate error handling in the modular system."""
    
    print("\n⚠️  Error Handling Demonstration")
    print("=" * 50)
    
    from saathy.chunking.core.exceptions import ChunkingError, ValidationError
    
    # Test invalid configuration
    try:
        invalid_config = ChunkingConfig(
            max_chunk_size=0,  # Invalid
            overlap=100,
            min_chunk_size=200  # Greater than max_chunk_size
        )
        invalid_config.validate()
    except ValidationError as e:
        print(f"   Configuration validation error: {e}")
    
    # Test strategy not found
    processor = ChunkingProcessor()
    try:
        strategy = processor.get_strategy(ContentType.UNKNOWN)
    except Exception as e:
        print(f"   Strategy not found error: {e}")
    
    # Test invalid content
    try:
        chunks = processor.chunk_content("")  # Empty content
        print(f"   Empty content handled gracefully: {len(chunks)} chunks")
    except Exception as e:
        print(f"   Error handling empty content: {e}")


if __name__ == "__main__":
    try:
        demonstrate_modular_architecture()
        demonstrate_extensibility()
        demonstrate_error_handling()
        
        print("\n🎉 Modular Chunking System Demonstration Complete!")
        print("\nKey Benefits of Modular Architecture:")
        print("  ✅ Separation of concerns")
        print("  ✅ Easy to extend and customize")
        print("  ✅ Reusable components")
        print("  ✅ Better error handling")
        print("  ✅ Clear interfaces and contracts")
        print("  ✅ Testable individual components")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc() 