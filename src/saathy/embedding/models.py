"""Embedding model registry and management."""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata for embedding models."""

    name: str
    dimensions: int
    max_context_length: int
    model_type: str  # "local", "openai", "code", "multimodal"
    performance_score: float = 0.0
    download_size_mb: Optional[float] = None
    gpu_optimized: bool = False
    multilingual: bool = False
    code_specialized: bool = False
    description: str = ""


class EmbeddingModel:
    """Base class for embedding models."""

    def __init__(self, metadata: ModelMetadata):
        self.metadata = metadata
        self._model: Optional[Any] = None
        self._device: Optional[str] = None
        self._is_loaded = False

    async def load(self) -> None:
        """Load the model asynchronously."""
        raise NotImplementedError

    async def embed(self, texts: Union[str, list[str]]) -> np.ndarray:
        """Generate embeddings for input texts."""
        raise NotImplementedError

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded

    def get_device(self) -> Optional[str]:
        """Get the device the model is running on."""
        return self._device


class SentenceTransformerModel(EmbeddingModel):
    """Local sentence transformer model."""

    def __init__(self, metadata: ModelMetadata, model_name: str):
        super().__init__(metadata)
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None

    async def load(self) -> None:
        """Load the sentence transformer model."""
        try:
            # Detect GPU availability
            if torch.cuda.is_available():
                self._device = "cuda"
                logger.info(f"Using GPU for model {self.metadata.name}")
            else:
                self._device = "cpu"
                logger.info(f"Using CPU for model {self.metadata.name}")

            # Load model with device specification
            self._model = SentenceTransformer(self.model_name, device=self._device)

            # Warm up the model
            await self._warmup()

            self._is_loaded = True
            logger.info(f"Successfully loaded model {self.metadata.name}")

        except Exception as e:
            logger.error(f"Failed to load model {self.metadata.name}: {e}")
            raise

    async def _warmup(self) -> None:
        """Warm up the model with sample input."""
        try:
            warmup_text = "This is a warmup text for the embedding model."
            _ = self._model.encode(warmup_text, convert_to_numpy=True)
            logger.debug(f"Model {self.metadata.name} warmed up successfully")
        except Exception as e:
            logger.warning(f"Model warmup failed for {self.metadata.name}: {e}")

    async def embed(self, texts: Union[str, list[str]]) -> np.ndarray:
        """Generate embeddings using sentence transformer."""
        if not self._is_loaded:
            await self.load()

        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings = self._model.encode(
                texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32
            )
            return embeddings
        except Exception as e:
            logger.error(f"Embedding generation failed for {self.metadata.name}: {e}")
            raise


class OpenAIModel(EmbeddingModel):
    """OpenAI API-based embedding model."""

    def __init__(
        self,
        metadata: ModelMetadata,
        api_key: str,
        model_name: str = "text-embedding-ada-002",
    ):
        super().__init__(metadata)
        self.api_key = api_key
        self.model_name = model_name
        self._client = None

    async def load(self) -> None:
        """Initialize OpenAI client."""
        try:
            import openai

            self._client = openai.AsyncOpenAI(api_key=self.api_key)
            self._is_loaded = True
            logger.info(f"OpenAI client initialized for {self.metadata.name}")
        except ImportError:
            raise ImportError(
                "openai package is required for OpenAI embeddings"
            ) from None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ImportError(f"Failed to initialize OpenAI client: {e}") from e

    async def embed(self, texts: Union[str, list[str]]) -> np.ndarray:
        """Generate embeddings using OpenAI API."""
        if not self._is_loaded:
            await self.load()

        if isinstance(texts, str):
            texts = [texts]

        try:
            response = await self._client.embeddings.create(
                model=self.model_name, input=texts
            )

            embeddings = np.array([data.embedding for data in response.data])
            return embeddings

        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise


class ModelRegistry:
    """Registry for managing embedding models."""

    def __init__(self):
        self._models: dict[str, EmbeddingModel] = {}
        self._settings = get_settings()
        self._cache_dir = Path.home() / ".cache" / "saathy" / "models"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def register_model(self, model: EmbeddingModel) -> None:
        """Register a model in the registry."""
        self._models[model.metadata.name] = model
        logger.info(f"Registered model: {model.metadata.name}")

    def get_model(self, name: str) -> Optional[EmbeddingModel]:
        """Get a model by name."""
        return self._models.get(name)

    def list_models(self) -> list[str]:
        """list all registered model names."""
        return list(self._models.keys())

    def get_model_by_type(self, model_type: str) -> list[EmbeddingModel]:
        """Get all models of a specific type."""
        return [
            model
            for model in self._models.values()
            if model.metadata.model_type == model_type
        ]

    async def load_model(self, name: str) -> EmbeddingModel:
        """Load a specific model."""
        model = self.get_model(name)
        if not model:
            raise ValueError(f"Model {name} not found in registry")

        if not model.is_loaded():
            await model.load()

        return model

    async def load_all_models(self) -> None:
        """Load all registered models."""
        tasks = [self.load_model(name) for name in self.list_models()]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_best_model_for_content(
        self, content_type: str, quality: str = "balanced"
    ) -> Optional[EmbeddingModel]:
        """Get the best model for a specific content type and quality preference."""
        candidates = []

        for model in self._models.values():
            if content_type == "code" and model.metadata.code_specialized:
                candidates.append(model)
            elif content_type == "text" and not model.metadata.code_specialized:
                candidates.append(model)
            elif (
                content_type == "multimodal"
                and model.metadata.model_type == "multimodal"
            ):
                candidates.append(model)

        if not candidates:
            return None

        # Sort by performance score and quality preference
        if quality == "fast":
            candidates.sort(
                key=lambda m: (-m.metadata.performance_score, m.metadata.dimensions)
            )
        elif quality == "high":
            candidates.sort(
                key=lambda m: (m.metadata.performance_score, -m.metadata.dimensions)
            )
        else:  # balanced
            candidates.sort(key=lambda m: m.metadata.performance_score, reverse=True)

        return candidates[0] if candidates else None


# Predefined model configurations
PREDEFINED_MODELS = {
    "all-MiniLM-L6-v2": ModelMetadata(
        name="all-MiniLM-L6-v2",
        dimensions=384,
        max_context_length=256,
        model_type="local",
        performance_score=0.85,
        download_size_mb=90,
        gpu_optimized=True,
        multilingual=False,
        code_specialized=False,
        description="Fast and efficient general-purpose model",
    ),
    "all-mpnet-base-v2": ModelMetadata(
        name="all-mpnet-base-v2",
        dimensions=768,
        max_context_length=384,
        model_type="local",
        performance_score=0.92,
        download_size_mb=420,
        gpu_optimized=True,
        multilingual=False,
        code_specialized=False,
        description="High-quality general-purpose model",
    ),
    "codebert-base": ModelMetadata(
        name="flax-sentence-embeddings/st-codesearch-distilroberta-base",
        dimensions=768,
        max_context_length=512,
        model_type="local",
        performance_score=0.88,
        download_size_mb=500,
        gpu_optimized=True,
        multilingual=False,
        code_specialized=True,
        description="Specialized for code understanding",
    ),
    "openai-ada-002": ModelMetadata(
        name="text-embedding-ada-002",
        dimensions=1536,
        max_context_length=8191,
        model_type="openai",
        performance_score=0.95,
        gpu_optimized=False,
        multilingual=False,
        code_specialized=False,
        description="High-quality OpenAI embeddings",
    ),
}


def create_default_registry() -> ModelRegistry:
    """Create a registry with default models."""
    registry = ModelRegistry()
    settings = get_settings()

    # Add local models
    for _, metadata in PREDEFINED_MODELS.items():
        if metadata.model_type == "local":
            model = SentenceTransformerModel(metadata, metadata.name)
            registry.register_model(model)

    # Add OpenAI model if API key is available
    if settings.openai_api_key_str:
        openai_metadata = PREDEFINED_MODELS["openai-ada-002"]
        openai_model = OpenAIModel(openai_metadata, settings.openai_api_key_str)
        registry.register_model(openai_model)

    return registry
