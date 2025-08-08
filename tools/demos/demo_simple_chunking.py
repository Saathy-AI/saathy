#!/usr/bin/env python3
"""Simple demonstration of the unified chunking system."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def main():
    """Demonstrate the simplified chunking system."""
    print("🚀 Saathy Intelligent Chunking System Demo")
    print("=" * 50)

    try:
        # Import the chunking system
        from saathy.chunking import (
            ChunkingConfig,
            ChunkingProcessor,
        )

        print("✅ Successfully imported chunking system")

        # Create a processor with default configuration
        processor = ChunkingProcessor()
        print("✅ Created chunking processor")

        # Demo 1: Basic text chunking
        print("\n📝 Demo 1: Basic Text Chunking")
        print("-" * 30)
        text = """
        Artificial intelligence has revolutionized many aspects of modern life.
        Machine learning algorithms can now process vast amounts of data and
        identify patterns that were previously impossible to detect. Natural
        language processing has enabled computers to understand and generate
        human-like text. Computer vision allows machines to interpret and
        analyze visual information from the world around us.
        """

        chunks = processor.chunk_content(text.strip())
        print(f"Input text length: {len(text)} characters")
        print(f"Generated {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks[:3], 1):  # Show first 3 chunks
            print(
                f"  Chunk {i}: {len(chunk.content)} chars - '{chunk.content[:50]}...'"
            )

        # Demo 2: Code chunking
        print("\n💻 Demo 2: Code Chunking")
        print("-" * 25)
        code_sample = '''
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MathUtils:
    """Utility class for mathematical operations."""

    @staticmethod
    def factorial(n):
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n-1)

    def gcd(self, a, b):
        while b:
            a, b = b, a % b
        return a
'''

        code_chunks = processor.chunk_content(code_sample.strip(), content_type="code")
        print(f"Generated {len(code_chunks)} code chunks:")
        for i, chunk in enumerate(code_chunks, 1):
            print(f"  Code chunk {i}: {len(chunk.content)} chars")
            # Show first few lines of each chunk
            lines = chunk.content.strip().split("\n")[:2]
            for line in lines:
                if line.strip():
                    print(f"    {line}")
            if len(chunk.content.strip().split("\n")) > 2:
                print("    ...")

        # Demo 3: Document chunking
        print("\n📄 Demo 3: Document Chunking")
        print("-" * 28)
        document = """
# Machine Learning Guide

## Introduction

Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.

## Types of Machine Learning

### Supervised Learning
Supervised learning uses labeled training data to learn a mapping function.

### Unsupervised Learning
Unsupervised learning finds hidden patterns in data without labeled examples.

### Reinforcement Learning
Reinforcement learning learns through interaction with an environment.

## Conclusion

Machine learning continues to evolve and find new applications across industries.
"""

        doc_chunks = processor.chunk_content(document.strip(), content_type="document")
        print(f"Generated {len(doc_chunks)} document chunks:")
        for i, chunk in enumerate(doc_chunks, 1):
            first_line = chunk.content.strip().split("\n")[0]
            print(f"  Doc chunk {i}: '{first_line}' ({len(chunk.content)} chars)")

        # Demo 4: Strategy configuration
        print("\n⚙️  Demo 4: Custom Configuration")
        print("-" * 33)

        # Create processor with custom config
        config = ChunkingConfig(
            max_chunk_size=200,  # Smaller chunks
            overlap=25,  # Less overlap
            min_chunk_size=20,  # Smaller minimum
        )
        custom_processor = ChunkingProcessor(config)

        custom_chunks = custom_processor.chunk_content(text.strip())
        print(
            f"With custom config: {len(custom_chunks)} chunks (vs {len(chunks)} with default)"
        )

        # Demo 5: Available strategies
        print("\n🎯 Demo 5: Available Strategies")
        print("-" * 31)
        strategies = processor.list_strategies()
        print("Available chunking strategies:")
        for content_type, strategy_name in strategies.items():
            print(f"  {content_type}: {strategy_name}")

        print("\n🎉 Demo completed successfully!")
        print("\nThe simplified chunking system provides:")
        print("✅ Multiple intelligent chunking strategies")
        print("✅ Automatic content type detection")
        print("✅ Configurable chunk sizes and overlap")
        print("✅ Quality validation and optimization")
        print("✅ All features in a single, unified package")

    except Exception as e:
        print(f"❌ Error running demo: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
