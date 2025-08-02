"""Tests for the embedding service."""

from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from saathy.embedding.chunking import (
    ChunkingPipeline,
    CodeChunking,
    FixedSizeChunking,
    SemanticChunking,
)
from saathy.embedding.models import (
    EmbeddingModel,
    ModelMetadata,
    ModelRegistry,
    SentenceTransformerModel,
)
from saathy.embedding.preprocessing import (
    CodePreprocessor,
    PreprocessingPipeline,
    PreprocessingResult,
    TextPreprocessor,
)
from saathy.embedding.service import (
    EmbeddingCache,
    EmbeddingMetrics,
    EmbeddingResult,
    EmbeddingService,
)


class TestModelMetadata:
    """Test ModelMetadata class."""

    def test_model_metadata_creation(self):
        """Test creating ModelMetadata instance."""
        metadata = ModelMetadata(
            name="test-model",
            dimensions=384,
            max_context_length=256,
            model_type="local",
            performance_score=0.85,
            description="Test model",
        )

        assert metadata.name == "test-model"
        assert metadata.dimensions == 384
        assert metadata.max_context_length == 256
        assert metadata.model_type == "local"
        assert metadata.performance_score == 0.85
        assert metadata.description == "Test model"


class TestEmbeddingModel:
    """Test base EmbeddingModel class."""

    def test_embedding_model_creation(self):
        """Test creating EmbeddingModel instance."""
        metadata = ModelMetadata(
            name="test-model",
            dimensions=384,
            max_context_length=256,
            model_type="local",
        )

        model = EmbeddingModel(metadata)
        assert model.metadata == metadata
        assert not model.is_loaded()
        assert model.get_device() is None


class TestSentenceTransformerModel:
    """Test SentenceTransformerModel class."""

    @pytest.mark.asyncio
    async def test_sentence_transformer_model_creation(self):
        """Test creating SentenceTransformerModel instance."""
        metadata = ModelMetadata(
            name="all-MiniLM-L6-v2",
            dimensions=384,
            max_context_length=256,
            model_type="local",
        )

        model = SentenceTransformerModel(metadata, "all-MiniLM-L6-v2")
        assert model.model_name == "all-MiniLM-L6-v2"
        assert not model.is_loaded()

    @pytest.mark.slow
    @pytest.mark.asyncio
    @patch("saathy.embedding.models.SentenceTransformer")
    @patch("saathy.embedding.models.torch")
    async def test_sentence_transformer_load(
        self, mock_torch, mock_sentence_transformer
    ):
        """Test loading SentenceTransformer model."""
        # Mock torch.cuda.is_available to return False (CPU)
        mock_torch.cuda.is_available.return_value = False

        # Mock SentenceTransformer
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_sentence_transformer.return_value = mock_model

        metadata = ModelMetadata(
            name="all-MiniLM-L6-v2",
            dimensions=384,
            max_context_length=256,
            model_type="local",
        )

        model = SentenceTransformerModel(metadata, "all-MiniLM-L6-v2")
        await model.load()

        assert model.is_loaded()
        assert model.get_device() == "cpu"
        mock_sentence_transformer.assert_called_once_with(
            "all-MiniLM-L6-v2", device="cpu"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    @patch("saathy.embedding.models.SentenceTransformer")
    @patch("saathy.embedding.models.torch")
    async def test_sentence_transformer_embed(
        self, mock_torch, mock_sentence_transformer
    ):
        """Test embedding generation with SentenceTransformer."""
        mock_torch.cuda.is_available.return_value = False

        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_sentence_transformer.return_value = mock_model

        metadata = ModelMetadata(
            name="all-MiniLM-L6-v2",
            dimensions=384,
            max_context_length=256,
            model_type="local",
        )

        model = SentenceTransformerModel(metadata, "all-MiniLM-L6-v2")
        await model.load()

        texts = ["Hello world", "Test text"]
        embeddings = await model.embed(texts)

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (2, 3)
        # The model is called twice: once during warmup and once during embedding
        assert mock_model.encode.call_count == 2


class TestModelRegistry:
    """Test ModelRegistry class."""

    def test_model_registry_creation(self):
        """Test creating ModelRegistry instance."""
        registry = ModelRegistry()
        assert len(registry.list_models()) == 0

    def test_register_model(self):
        """Test registering a model."""
        registry = ModelRegistry()

        metadata = ModelMetadata(
            name="test-model",
            dimensions=384,
            max_context_length=256,
            model_type="local",
        )
        model = EmbeddingModel(metadata)

        registry.register_model(model)
        assert "test-model" in registry.list_models()
        assert registry.get_model("test-model") == model

    def test_get_model_by_type(self):
        """Test getting models by type."""
        registry = ModelRegistry()

        # Add models of different types
        local_metadata = ModelMetadata(
            name="local-model",
            dimensions=384,
            max_context_length=256,
            model_type="local",
        )
        local_model = EmbeddingModel(local_metadata)

        openai_metadata = ModelMetadata(
            name="openai-model",
            dimensions=1536,
            max_context_length=8191,
            model_type="openai",
        )
        openai_model = EmbeddingModel(openai_metadata)

        registry.register_model(local_model)
        registry.register_model(openai_model)

        local_models = registry.get_model_by_type("local")
        assert len(local_models) == 1
        assert local_models[0] == local_model

        openai_models = registry.get_model_by_type("openai")
        assert len(openai_models) == 1
        assert openai_models[0] == openai_model

    def test_get_best_model_for_content(self):
        """Test getting best model for content type."""
        registry = ModelRegistry()

        # Add a code-specialized model
        code_metadata = ModelMetadata(
            name="code-model",
            dimensions=768,
            max_context_length=512,
            model_type="local",
            code_specialized=True,
            performance_score=0.88,
        )
        code_model = EmbeddingModel(code_metadata)

        # Add a general text model
        text_metadata = ModelMetadata(
            name="text-model",
            dimensions=384,
            max_context_length=256,
            model_type="local",
            code_specialized=False,
            performance_score=0.85,
        )
        text_model = EmbeddingModel(text_metadata)

        registry.register_model(code_model)
        registry.register_model(text_model)

        # Test code content
        best_code_model = registry.get_best_model_for_content("code")
        assert best_code_model == code_model

        # Test text content
        best_text_model = registry.get_best_model_for_content("text")
        assert best_text_model == text_model


class TestTextPreprocessor:
    """Test TextPreprocessor class."""

    def test_text_preprocessor_creation(self):
        """Test creating TextPreprocessor instance."""
        preprocessor = TextPreprocessor()
        assert preprocessor.get_content_type() == "text"

    def test_text_preprocessing(self):
        """Test text preprocessing."""
        preprocessor = TextPreprocessor()
        text = "  This   is   a   test   text.  \n\n  With   multiple   spaces.  "

        result = preprocessor.preprocess(text)

        assert isinstance(result, PreprocessingResult)
        assert result.content_type == "text"
        assert "  " not in result.content  # No double spaces
        assert result.quality_score > 0
        assert "whitespace_cleaning" in result.preprocessing_steps
        assert "newline_normalization" in result.preprocessing_steps

    def test_language_detection(self):
        """Test language detection."""
        preprocessor = TextPreprocessor()

        # English text
        english_result = preprocessor.preprocess(
            "The quick brown fox jumps over the lazy dog."
        )
        assert english_result.language == "en"

        # Non-English text
        non_english_result = preprocessor.preprocess("1234567890")
        assert non_english_result.language is None


class TestCodePreprocessor:
    """Test CodePreprocessor class."""

    def test_code_preprocessor_creation(self):
        """Test creating CodePreprocessor instance."""
        preprocessor = CodePreprocessor()
        assert preprocessor.get_content_type() == "code"

    def test_python_code_preprocessing(self):
        """Test Python code preprocessing."""
        preprocessor = CodePreprocessor()
        code = '''
def hello_world():
    # This is a comment
    print("Hello, World!")

def another_function():
    """This is a docstring"""
    return True
'''

        result = preprocessor.preprocess(code, {"file_extension": ".py"})

        assert isinstance(result, PreprocessingResult)
        assert result.content_type == "code"
        assert result.metadata["language"] == "python"
        assert "comment_removal" in result.preprocessing_steps
        assert "function_extraction" in result.preprocessing_steps
        assert len(result.metadata["functions"]) > 0

    def test_javascript_code_preprocessing(self):
        """Test JavaScript code preprocessing."""
        preprocessor = CodePreprocessor()
        code = """
function helloWorld() {
    // This is a comment
    console.log("Hello, World!");
}

const anotherFunction = () => {
    /* This is a block comment */
    return true;
};
"""

        result = preprocessor.preprocess(code, {"file_extension": ".js"})

        assert result.metadata["language"] == "javascript"
        assert "comment_removal" in result.preprocessing_steps
        assert len(result.metadata["functions"]) > 0


class TestChunkingStrategies:
    """Test chunking strategies."""

    @pytest.mark.slow
    def test_fixed_size_chunking(self):
        """Test fixed-size chunking."""
        chunker = FixedSizeChunking(max_chunk_size=10, overlap=2)
        text = "This is a test text that should be chunked into smaller pieces."

        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 10
            assert chunk.chunk_type == "fixed_size"

    def test_semantic_chunking(self):
        """Test semantic chunking."""
        chunker = SemanticChunking(max_chunk_size=50, overlap=5)
        text = "This is the first sentence. This is the second sentence. This is the third sentence."

        chunks = chunker.chunk(text)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.chunk_type == "semantic"

    def test_code_chunking(self):
        """Test code chunking."""
        chunker = CodeChunking(max_chunk_size=100, overlap=10)
        code = """
def function1():
    return "hello"

def function2():
    return "world"
"""

        chunks = chunker.chunk(code, {"language": "python"})

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.chunk_type == "code"


class TestEmbeddingCache:
    """Test EmbeddingCache class."""

    def test_cache_creation(self):
        """Test creating EmbeddingCache instance."""
        cache = EmbeddingCache(max_size=100, ttl_seconds=3600)
        assert cache.max_size == 100
        assert cache.ttl_seconds == 3600
        assert cache.size() == 0

    def test_cache_set_get(self):
        """Test setting and getting from cache."""
        cache = EmbeddingCache(max_size=10, ttl_seconds=3600)
        embedding = np.array([0.1, 0.2, 0.3])

        cache.set("test_key", embedding)
        assert cache.size() == 1

        retrieved = cache.get("test_key")
        assert np.array_equal(retrieved, embedding)

    def test_cache_eviction(self):
        """Test cache eviction when full."""
        cache = EmbeddingCache(max_size=2, ttl_seconds=3600)

        cache.set("key1", np.array([1]))
        cache.set("key2", np.array([2]))
        cache.set("key3", np.array([3]))  # Should evict key1

        assert cache.size() == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None


class TestEmbeddingMetrics:
    """Test EmbeddingMetrics class."""

    def test_metrics_creation(self):
        """Test creating EmbeddingMetrics instance."""
        metrics = EmbeddingMetrics()
        assert len(metrics.processing_times) == 0
        assert len(metrics.error_counts) == 0
        assert len(metrics.model_usage) == 0

    def test_record_processing_time(self):
        """Test recording processing time."""
        metrics = EmbeddingMetrics()
        metrics.record_processing_time("model1", "text", 1.5)

        key = "model1_text"
        assert key in metrics.processing_times
        assert 1.5 in metrics.processing_times[key]

    def test_record_model_usage(self):
        """Test recording model usage."""
        metrics = EmbeddingMetrics()
        metrics.record_model_usage("model1")
        metrics.record_model_usage("model1")

        assert metrics.model_usage["model1"] == 2

    def test_get_model_performance(self):
        """Test getting model performance."""
        metrics = EmbeddingMetrics()
        metrics.record_processing_time("model1", "text", 1.0)
        metrics.record_processing_time("model1", "text", 2.0)
        metrics.record_model_usage("model1")
        metrics.record_model_usage("model1")

        performance = metrics.get_model_performance("model1")
        assert performance["usage_count"] == 2
        assert performance["avg_processing_time"] == 1.5
        assert performance["error_rate"] == 0.0


class TestEmbeddingService:
    """Test EmbeddingService class."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry for testing."""
        registry = Mock()
        registry.list_models.return_value = ["test-model"]
        registry.get_model.return_value = None
        registry.get_best_model_for_content.return_value = None
        return registry

    @pytest.fixture
    def mock_model(self):
        """Create a mock embedding model."""
        model = Mock()
        model.metadata.name = "test-model"
        model.is_loaded.return_value = True
        model.embed = AsyncMock(return_value=np.array([[0.1, 0.2, 0.3]]))
        return model

    @pytest.mark.asyncio
    async def test_embedding_service_creation(self, mock_registry):
        """Test creating EmbeddingService instance."""
        service = EmbeddingService(registry=mock_registry)
        assert service.registry == mock_registry
        assert service.cache is not None
        assert service.metrics is not None

    @pytest.mark.asyncio
    async def test_embed_text(self, mock_registry, mock_model):
        """Test embedding a single text."""
        mock_registry.get_best_model_for_content.return_value = mock_model

        service = EmbeddingService(registry=mock_registry)

        result = await service.embed_text("Hello world", "text")

        assert isinstance(result, EmbeddingResult)
        assert result.model_name == "test-model"
        assert result.content_type == "text"
        assert result.embeddings.shape == (1, 3)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_registry, mock_model):
        """Test batch embedding."""
        mock_registry.get_best_model_for_content.return_value = mock_model

        service = EmbeddingService(registry=mock_registry)

        texts = ["Hello", "World", "Test"]
        results = await service.embed_batch(texts, "text")

        assert len(results) == 3
        for result in results:
            assert isinstance(result, EmbeddingResult)
            assert result.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_embed_code(self, mock_registry, mock_model):
        """Test code embedding."""
        mock_registry.get_best_model_for_content.return_value = mock_model

        service = EmbeddingService(registry=mock_registry)

        code = "def hello(): return 'world'"
        result = await service.embed_code(code, "python")

        assert isinstance(result, EmbeddingResult)
        assert result.content_type == "code"
        assert result.metadata.get("file_extension") == ".python"

    def test_get_available_models(self, mock_registry):
        """Test getting available models."""
        service = EmbeddingService(registry=mock_registry)
        models = service.get_available_models()

        assert models == ["test-model"]
        mock_registry.list_models.assert_called_once()

    def test_get_metrics(self, mock_registry):
        """Test getting metrics."""
        service = EmbeddingService(registry=mock_registry)
        metrics = service.get_metrics()

        assert isinstance(metrics, dict)
        assert "total_models_used" in metrics

    def test_clear_cache(self, mock_registry):
        """Test clearing cache."""
        service = EmbeddingService(registry=mock_registry)

        # Add something to cache
        service.cache.set("test", np.array([1, 2, 3]))
        assert service.cache.size() > 0

        # Clear cache
        service.clear_cache()
        assert service.cache.size() == 0


class TestChunkingPipeline:
    """Test ChunkingPipeline class."""

    def test_pipeline_creation(self):
        """Test creating ChunkingPipeline instance."""
        pipeline = ChunkingPipeline()
        strategies = pipeline.get_available_strategies()

        expected_strategies = ["fixed", "semantic", "document", "code"]
        for strategy in expected_strategies:
            assert strategy in strategies

    @pytest.mark.slow
    def test_chunk_with_strategy(self):
        """Test chunking with specific strategy."""
        pipeline = ChunkingPipeline()
        text = "This is a test text that should be chunked."

        chunks = pipeline.chunk(text, strategy="fixed", max_chunk_size=10)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.chunk_type == "fixed_size"

    @pytest.mark.slow
    def test_validate_chunks(self):
        """Test chunk validation."""
        pipeline = ChunkingPipeline()
        text = "This is a test text."

        chunks = pipeline.chunk(text, strategy="fixed", max_chunk_size=10)
        validation = pipeline.validate_chunks(chunks, text)

        assert "valid" in validation
        assert "coverage_ratio" in validation
        assert "total_chunks" in validation


class TestPreprocessingPipeline:
    """Test PreprocessingPipeline class."""

    def test_pipeline_creation(self):
        """Test creating PreprocessingPipeline instance."""
        pipeline = PreprocessingPipeline()
        types = pipeline.get_supported_types()

        expected_types = ["text", "code", "meeting", "image"]
        for content_type in expected_types:
            assert content_type in types

    def test_preprocess_text(self):
        """Test text preprocessing."""
        pipeline = PreprocessingPipeline()
        text = "  This   is   a   test   text.  "

        result = pipeline.preprocess(text, "text")

        assert isinstance(result, PreprocessingResult)
        assert result.content_type == "text"
        assert "  " not in result.content  # No double spaces

    def test_preprocess_code(self):
        """Test code preprocessing."""
        pipeline = PreprocessingPipeline()
        code = """
def test():
    # This is a comment
    return True
"""

        result = pipeline.preprocess(code, "code", {"file_extension": ".py"})

        assert isinstance(result, PreprocessingResult)
        assert result.content_type == "code"
        assert result.metadata["language"] == "python"
        assert "# This is a comment" not in result.content  # Comment removed

    def test_preprocess_unknown_type(self):
        """Test preprocessing with unknown content type."""
        pipeline = PreprocessingPipeline()
        text = "Test text"

        result = pipeline.preprocess(text, "unknown_type")

        # Should fall back to text preprocessor
        assert result.content_type == "text"
