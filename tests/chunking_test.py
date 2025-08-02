"""Tests for the intelligent chunking system."""

import json
import tempfile
from pathlib import Path

from src.saathy.chunking import (
    ChunkAnalyzer,
    ChunkingConfig,
    ChunkingProcessor,
    ChunkQualityMetrics,
    ChunkVisualizer,
    CodeChunker,
    ContentType,
    ContentTypeDetector,
    DocumentChunker,
    EmailChunker,
    FixedSizeChunker,
    GitCommitChunker,
    MeetingChunker,
    SemanticChunker,
    SlackMessageChunker,
)


class TestChunkingStrategies:
    """Test individual chunking strategies."""

    def test_fixed_size_chunker(self):
        """Test fixed-size chunking strategy."""
        content = "This is a test document with multiple sentences. " * 20
        chunker = FixedSizeChunker(max_chunk_size=100, overlap=20)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(len(chunk.content) <= 100 for chunk in chunks)
        assert all(chunk.chunk_type == "fixed_size" for chunk in chunks)

    def test_semantic_chunker(self):
        """Test semantic chunking strategy."""
        content = (
            """
        This is the first sentence. This is the second sentence.
        This is the third sentence. This is the fourth sentence.
        This is the fifth sentence. This is the sixth sentence.
        """
            * 10
        )

        chunker = SemanticChunker(max_chunk_size=200, overlap=30)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.chunk_type == "semantic" for chunk in chunks)

    def test_code_chunker(self):
        """Test code chunking strategy."""
        content = """
def test_function():
    \"\"\"Test function docstring.\"\"\"
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self):
        self.value = 42

    def method(self):
        return self.value
        """

        chunker = CodeChunker(max_chunk_size=150, overlap=20)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.chunk_type == "code" for chunk in chunks)

    def test_document_chunker(self):
        """Test document chunking strategy."""
        content = """
# Introduction
This is the introduction section.

## Section 1
This is the first section content.

### Subsection 1.1
This is a subsection.

## Section 2
This is the second section content.
        """

        chunker = DocumentChunker(max_chunk_size=200, overlap=30)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.chunk_type == "document" for chunk in chunks)

    def test_meeting_chunker(self):
        """Test meeting chunking strategy."""
        content = """
Alice: Hello everyone, let's start the meeting.
Bob: Good morning, I'm ready to discuss the project.
Alice: Great! Let's go through the agenda.
Bob: I have some updates on the timeline.
        """

        chunker = MeetingChunker(max_chunk_size=150, overlap=20)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.chunk_type == "meeting" for chunk in chunks)

    def test_git_commit_chunker(self):
        """Test git commit chunking strategy."""
        content = """
commit a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
Author: John Doe <john@example.com>
Date:   Mon Jan 1 12:00:00 2024 +0000

    Add new feature

    This commit adds a new feature to the system.
    It includes several improvements and bug fixes.

diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,5 @@
 def main():
-    print("Hello")
+    print("Hello, World!")
+    return 0
        """

        chunker = GitCommitChunker(max_chunk_size=200, overlap=30)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.chunk_type == "git_commit" for chunk in chunks)

    def test_slack_message_chunker(self):
        """Test Slack message chunking strategy."""
        content = """
2024-01-01 12:00:00 Alice: Hello team! :wave:
2024-01-01 12:01:00 Bob: Hi Alice! How's the project going?
2024-01-01 12:02:00 Alice: It's going well! We're on track.
2024-01-01 12:03:00 Bob: Great to hear! :thumbsup:
        """

        chunker = SlackMessageChunker(max_chunk_size=150, overlap=20)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.chunk_type == "slack_message" for chunk in chunks)

    def test_email_chunker(self):
        """Test email chunking strategy."""
        content = """
From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 12:00:00 +0000

This is the email body content.
It contains multiple paragraphs.

Best regards,
Sender
        """

        chunker = EmailChunker(max_chunk_size=200, overlap=30)
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.chunk_type == "email" for chunk in chunks)


class TestContentTypeDetection:
    """Test content type detection."""

    def test_content_type_detector(self):
        """Test automatic content type detection."""
        detector = ContentTypeDetector()

        # Test code detection
        code_content = "def test_function():\n    return True"
        assert detector.detect_content_type(code_content) == ContentType.CODE

        # Test document detection
        doc_content = "# Title\n\nThis is a document."
        assert detector.detect_content_type(doc_content) == ContentType.DOCUMENT

        # Test meeting detection
        meeting_content = "Alice: Hello\nBob: Hi"
        assert detector.detect_content_type(meeting_content) == ContentType.MEETING

        # Test git commit detection
        git_content = "commit abc123\nAuthor: John Doe"
        assert detector.detect_content_type(git_content) == ContentType.GIT_COMMIT

        # Test Slack message detection
        slack_content = "2024-01-01 12:00:00 Alice: Hello"
        assert detector.detect_content_type(slack_content) == ContentType.SLACK_MESSAGE

        # Test email detection
        email_content = "From: sender@example.com\nTo: recipient@example.com"
        assert detector.detect_content_type(email_content) == ContentType.EMAIL

    def test_file_extension_detection(self):
        """Test content type detection from file extensions."""
        detector = ContentTypeDetector()

        assert detector._get_type_from_extension(".py") == ContentType.CODE
        assert detector._get_type_from_extension(".js") == ContentType.CODE
        assert detector._get_type_from_extension(".md") == ContentType.DOCUMENT
        assert detector._get_type_from_extension(".txt") == ContentType.DOCUMENT
        assert detector._get_type_from_extension(".unknown") == ContentType.UNKNOWN


class TestChunkingProcessor:
    """Test the main chunking processor."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        config = ChunkingConfig(
            max_chunk_size=512, overlap=50, min_chunk_size=50, enable_caching=True
        )
        processor = ChunkingProcessor(config)

        assert processor.config.max_chunk_size == 512
        assert processor.config.overlap == 50
        assert processor.config.enable_caching is True

    def test_automatic_strategy_selection(self):
        """Test automatic strategy selection based on content type."""
        processor = ChunkingProcessor()

        # Test code content
        code_content = "def test():\n    return True"
        chunks = processor.chunk_content(code_content)
        assert all(chunk.metadata.content_type == ContentType.CODE for chunk in chunks)

        # Test document content
        doc_content = "# Title\n\nThis is a document."
        chunks = processor.chunk_content(doc_content)
        assert all(
            chunk.metadata.content_type == ContentType.DOCUMENT for chunk in chunks
        )

    def test_chunk_quality_validation(self):
        """Test chunk quality validation."""
        processor = ChunkingProcessor()
        content = "This is a test document. " * 50

        chunks = processor.chunk_content(content)
        stats = processor.get_chunking_stats()

        assert "config" in stats
        assert "strategies" in stats
        assert len(chunks) > 0

    def test_chunk_caching(self):
        """Test chunk caching functionality."""
        config = ChunkingConfig(enable_caching=True, cache_ttl=3600)
        processor = ChunkingProcessor(config)

        content = "This is test content for caching. " * 20

        # First chunking
        chunks1 = processor.chunk_content(content)

        # Second chunking (should use cache)
        chunks2 = processor.chunk_content(content)

        assert len(chunks1) == len(chunks2)
        assert all(c1.content == c2.content for c1, c2 in zip(chunks1, chunks2))

        # Check cache stats
        cache_stats = processor.cache.get_stats()
        assert cache_stats["valid_entries"] > 0


class TestChunkAnalysis:
    """Test chunk analysis and visualization."""

    def test_chunk_analyzer(self):
        """Test chunk analysis functionality."""
        analyzer = ChunkAnalyzer()
        processor = ChunkingProcessor()

        content = "This is a test document for analysis. " * 30
        chunks = processor.chunk_content(content)

        metrics = analyzer.analyze_chunks(chunks, content)

        assert isinstance(metrics, ChunkQualityMetrics)
        assert metrics.total_chunks > 0
        assert 0 <= metrics.quality_score <= 1
        assert 0 <= metrics.coverage_ratio <= 1

    def test_chunk_statistics(self):
        """Test chunk statistics calculation."""
        analyzer = ChunkAnalyzer()
        processor = ChunkingProcessor()

        content = "Test content for statistics. " * 25
        chunks = processor.chunk_content(content)

        stats = analyzer.get_chunk_statistics(chunks)

        assert "size_statistics" in stats
        assert "type_distribution" in stats
        assert "content_type_distribution" in stats
        assert "overlap_statistics" in stats

    def test_chunk_visualizer(self):
        """Test chunk visualization functionality."""
        visualizer = ChunkVisualizer()
        processor = ChunkingProcessor()

        content = "Test content for visualization. " * 20
        chunks = processor.chunk_content(content)

        # Test report creation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            report_path = f.name

        try:
            visualizer.create_chunk_report(chunks, content, report_path)

            # Verify report was created
            assert Path(report_path).exists()

            # Load and verify report content
            with open(report_path) as f:
                report = json.load(f)

            assert "summary" in report
            assert "quality_metrics" in report
            assert "chunks" in report

        finally:
            Path(report_path).unlink(missing_ok=True)


class TestAdvancedFeatures:
    """Test advanced chunking features."""

    def test_hierarchical_chunking(self):
        """Test hierarchical chunking with different levels."""
        processor = ChunkingProcessor()

        # Create hierarchical content
        content = """
# Main Document

## Section 1
This is the first section with multiple paragraphs.

### Subsection 1.1
This is a subsection with detailed content.

### Subsection 1.2
Another subsection with more content.

## Section 2
This is the second section.

### Subsection 2.1
Final subsection content.
        """

        chunks = processor.chunk_content(content)

        # Verify hierarchical structure is preserved
        assert len(chunks) > 1
        assert all(
            chunk.metadata.content_type == ContentType.DOCUMENT for chunk in chunks
        )

    def test_context_preservation(self):
        """Test context preservation across chunk boundaries."""
        config = ChunkingConfig(preserve_context=True, overlap=50)
        processor = ChunkingProcessor(config)

        content = "This is a long document with multiple sentences. " * 30
        chunks = processor.chunk_content(content)

        # Verify context is preserved
        for chunk in chunks:
            if chunk.context_before or chunk.context_after:
                assert len(chunk.context_before) <= config.overlap
                assert len(chunk.context_after) <= config.overlap

    def test_chunk_merging(self):
        """Test merging of small chunks."""
        config = ChunkingConfig(min_chunk_size=100, max_chunk_size=300)
        processor = ChunkingProcessor(config)

        # Create content that would result in small chunks
        content = "Short sentence. " * 10
        chunks = processor.chunk_content(content)

        # Verify chunks meet minimum size requirements
        for chunk in chunks:
            assert len(chunk.content) >= config.min_chunk_size or len(chunks) == 1


if __name__ == "__main__":
    # Run a demonstration
    print("Running chunking system demonstration...")

    # Initialize processor
    processor = ChunkingProcessor()

    # Test different content types
    test_contents = {
        "Code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class MathUtils:
    @staticmethod
    def factorial(n):
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n-1)
        """,
        "Document": """
# Machine Learning Fundamentals

## Introduction
Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models.

## Types of Learning
### Supervised Learning
Supervised learning uses labeled training data to learn patterns.

### Unsupervised Learning
Unsupervised learning finds hidden patterns in unlabeled data.
        """,
        "Meeting": """
Alice: Good morning everyone! Let's start our weekly standup.
Bob: Hi Alice! I completed the authentication module yesterday.
Charlie: I'm working on the database optimization.
Alice: Great progress! Any blockers?
Bob: No blockers from my side.
Charlie: I might need help with the query optimization.
        """,
    }

    for content_type, content in test_contents.items():
        print(f"\n--- Testing {content_type} Chunking ---")
        chunks = processor.chunk_content(content)
        print(f"Generated {len(chunks)} chunks")

        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"Chunk {i+1}: {len(chunk.content)} chars, Type: {chunk.chunk_type}")
            print(f"Preview: {chunk.content[:100]}...")

    print("\n--- Chunking System Demonstration Complete ---")
