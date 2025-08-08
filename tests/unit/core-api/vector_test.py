"""Tests for vector operations infrastructure."""

from datetime import datetime

import pytest

from saathy.vector import (
    BulkImportResult,
    CollectionStats,
    EmbeddingDimensionError,
    EmbeddingStats,
    SearchQuery,
    SearchResult,
    VectorDocument,
    VectorStoreError,
)


class TestVectorModels:
    """Test vector data models."""

    def test_vector_document_creation(self):
        """Test VectorDocument creation and validation."""
        doc = VectorDocument(
            id="test-1",
            content="This is a test document",
            embedding=[0.1, 0.2, 0.3],
            metadata={"category": "test", "source": "unit_test"},
        )

        assert doc.id == "test-1"
        assert doc.content == "This is a test document"
        assert doc.embedding == [0.1, 0.2, 0.3]
        assert doc.metadata["category"] == "test"
        assert isinstance(doc.timestamp, datetime)

    def test_search_query_validation(self):
        """Test SearchQuery validation."""
        query = SearchQuery(
            query_text="test query",
            top_k=5,
            filters={"category": "test"},
            score_threshold=0.7,
        )

        assert query.query_text == "test query"
        assert query.top_k == 5
        assert query.filters["category"] == "test"
        assert query.score_threshold == 0.7

    def test_search_query_defaults(self):
        """Test SearchQuery default values."""
        query = SearchQuery(query_text="test")

        assert query.top_k == 10
        assert query.filters is None
        assert query.score_threshold is None

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        doc = VectorDocument(
            id="test-1",
            content="Test content",
            embedding=[0.1, 0.2, 0.3],
        )

        result = SearchResult(
            document=doc,
            score=0.85,
            metadata={"rank": 1},
        )

        assert result.document.id == "test-1"
        assert result.score == 0.85
        assert result.metadata["rank"] == 1

    def test_embedding_stats_creation(self):
        """Test EmbeddingStats creation."""
        stats = EmbeddingStats(
            model_name="test-model",
            dimensions=384,
            processing_time=1.23,
            batch_size=32,
            total_vectors=100,
        )

        assert stats.model_name == "test-model"
        assert stats.dimensions == 384
        assert stats.processing_time == 1.23
        assert stats.batch_size == 32
        assert stats.total_vectors == 100

    def test_collection_stats_creation(self):
        """Test CollectionStats creation."""
        stats = CollectionStats(
            collection_name="test-collection",
            vector_count=1000,
            vector_size=384,
            points_count=1000,
            segments_count=4,
            status="green",
        )

        assert stats.collection_name == "test-collection"
        assert stats.vector_count == 1000
        assert stats.vector_size == 384
        assert stats.points_count == 1000
        assert stats.segments_count == 4
        assert stats.status == "green"

    def test_bulk_import_result_creation(self):
        """Test BulkImportResult creation and success rate calculation."""
        result = BulkImportResult(
            total_documents=100,
            successful_imports=95,
            failed_imports=5,
            processing_time=10.5,
            errors=["Error 1", "Error 2"],
        )

        assert result.total_documents == 100
        assert result.successful_imports == 95
        assert result.failed_imports == 5
        assert result.processing_time == 10.5
        assert len(result.errors) == 2
        assert result.success_rate == 95.0

    def test_bulk_import_result_zero_documents(self):
        """Test BulkImportResult with zero documents."""
        result = BulkImportResult(
            total_documents=0,
            successful_imports=0,
            failed_imports=0,
            processing_time=0.0,
        )

        assert result.success_rate == 0.0


class TestVectorExceptions:
    """Test vector operation exceptions."""

    def test_vector_store_error(self):
        """Test VectorStoreError creation."""
        error = VectorStoreError("Test error", "Additional details")

        assert str(error) == "Test error"
        assert error.details == "Additional details"

    def test_embedding_dimension_error(self):
        """Test EmbeddingDimensionError creation."""
        error = EmbeddingDimensionError(384, 256, "Dimension mismatch")

        assert "expected 384, got 256" in str(error)
        assert error.expected_dimensions == 384
        assert error.actual_dimensions == 256
        assert error.details == "Dimension mismatch"


class TestVectorModelsValidation:
    """Test model validation rules."""

    def test_search_query_top_k_validation(self):
        """Test SearchQuery top_k validation."""
        # Should work with valid range
        query = SearchQuery(query_text="test", top_k=50)
        assert query.top_k == 50

        # Should raise validation error for invalid values
        with pytest.raises(ValueError):
            SearchQuery(query_text="test", top_k=0)

        with pytest.raises(ValueError):
            SearchQuery(query_text="test", top_k=101)

    def test_search_query_score_threshold_validation(self):
        """Test SearchQuery score_threshold validation."""
        # Should work with valid range
        query = SearchQuery(query_text="test", score_threshold=0.5)
        assert query.score_threshold == 0.5

        # Should raise validation error for invalid values
        with pytest.raises(ValueError):
            SearchQuery(query_text="test", score_threshold=-0.1)

        with pytest.raises(ValueError):
            SearchQuery(query_text="test", score_threshold=1.1)

    def test_embedding_stats_dimensions_validation(self):
        """Test EmbeddingStats dimensions validation."""
        # Should work with positive dimensions
        stats = EmbeddingStats(
            model_name="test",
            dimensions=1,
            processing_time=1.0,
        )
        assert stats.dimensions == 1

        # Should raise validation error for zero or negative dimensions
        with pytest.raises(ValueError):
            EmbeddingStats(
                model_name="test",
                dimensions=0,
                processing_time=1.0,
            )

    def test_embedding_stats_processing_time_validation(self):
        """Test EmbeddingStats processing_time validation."""
        # Should work with non-negative time
        stats = EmbeddingStats(
            model_name="test",
            dimensions=384,
            processing_time=0.0,
        )
        assert stats.processing_time == 0.0

        # Should raise validation error for negative time
        with pytest.raises(ValueError):
            EmbeddingStats(
                model_name="test",
                dimensions=384,
                processing_time=-1.0,
            )
