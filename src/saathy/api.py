"""FastAPI application instance."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Union

from fastapi import Depends, FastAPI

from saathy import __version__
from saathy.config import Settings, get_settings
from saathy.embedding.service import EmbeddingService, get_embedding_service
from saathy.telemetry import configure_logging, configure_tracing
from saathy.vector.client import QdrantClientWrapper
from saathy.vector.repository import VectorRepository

# In-memory dictionary to hold settings during the application's lifespan.
# This is a simple approach; for more complex scenarios, consider using a more robust solution.
app_state: dict[str, Union[Settings, VectorRepository, EmbeddingService, None]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load the settings before the app starts and clear them when it's done."""
    settings = get_settings()

    # Initialize services as None - will be created lazily when needed
    app_state["settings"] = settings
    app_state["vector_repo"] = None
    app_state["embedding_service"] = None

    configure_logging(settings=settings)
    configure_tracing(settings=settings, app=app)
    yield
    app_state.clear()


app = FastAPI(
    title="Saathy",
    description="A FastAPI-based application",
    version=__version__,
    lifespan=lifespan,
)


def get_vector_repo() -> VectorRepository:
    """Get the vector repository from application state, creating it if needed."""
    if app_state.get("vector_repo") is None:
        # If settings are not in app_state (e.g., in test environment), get them directly
        if "settings" not in app_state:
            settings = get_settings()
        else:
            settings = app_state["settings"]

            # Parse Qdrant URL to extract host and port
        qdrant_url = str(settings.qdrant_url)
        if qdrant_url.startswith("http://"):
            qdrant_url = qdrant_url[7:]
        elif qdrant_url.startswith("https://"):
            qdrant_url = qdrant_url[8:]

        # Remove any trailing path components
        qdrant_url = qdrant_url.split("/")[0]

        host_port = qdrant_url.split(":")
        host = host_port[0]

        # Handle port parsing with error handling
        try:
            port = int(host_port[1]) if len(host_port) > 1 else 6333
        except (ValueError, IndexError):
            # Default to 6333 if port parsing fails
            port = 6333

        qdrant_client = QdrantClientWrapper(
            host=host,
            port=port,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
            api_key=settings.qdrant_api_key_str,
        )
        app_state["vector_repo"] = VectorRepository(client=qdrant_client)

    return app_state["vector_repo"]


async def get_embedding_service_dep() -> EmbeddingService:
    """Get the embedding service from application state, creating it if needed."""
    if app_state.get("embedding_service") is None:
        embedding_service = await get_embedding_service()
        app_state["embedding_service"] = embedding_service

    return app_state["embedding_service"]


@app.get("/healthz")
async def health_check(
    vector_repo: VectorRepository = Depends(get_vector_repo),
) -> dict[str, str | dict[str, str]]:
    """Health check endpoint."""
    try:
        # First check if we can connect to Qdrant
        qdrant_healthy = await vector_repo.health_check()
        if qdrant_healthy:
            return {"status": "healthy", "dependencies": {"qdrant": "healthy"}}
        else:
            return {
                "status": "unhealthy",
                "dependencies": {"qdrant": "unhealthy"},
            }
    except Exception as e:
        # Log the exception for debugging but don't expose it in response
        import logging

        logging.warning(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "dependencies": {"qdrant": "unavailable"},
        }


@app.get("/readyz")
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint - returns OK if the service is ready to accept requests."""
    return {"status": "ready"}


@app.get("/config")
async def get_config(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Get application configuration (non-sensitive fields only)."""
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "debug": str(settings.debug),
        "log_level": settings.log_level,
        "host": settings.host,
        "port": str(settings.port),
        "workers": str(settings.workers),
        "enable_tracing": str(settings.enable_tracing),
    }


# Embedding endpoints
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""

    text: str
    content_type: str = "text"
    model_name: Optional[str] = None
    quality: str = "balanced"
    metadata: Optional[Dict[str, Any]] = None


class BatchEmbeddingRequest(BaseModel):
    """Request model for batch embedding generation."""

    texts: List[str]
    content_type: str = "text"
    model_name: Optional[str] = None
    quality: str = "balanced"
    metadata_list: Optional[List[Dict[str, Any]]] = None


class CodeEmbeddingRequest(BaseModel):
    """Request model for code embedding generation."""

    code: str
    language: Optional[str] = None
    model_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""

    embeddings: List[List[float]]
    model_name: str
    content_type: str
    processing_time: float
    quality_score: float
    metadata: Dict[str, Any]


@app.post("/embed", response_model=EmbeddingResponse)
async def embed_text(
    request: EmbeddingRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
) -> EmbeddingResponse:
    """Generate embeddings for a single text."""
    result = await embedding_service.embed_text(
        text=request.text,
        content_type=request.content_type,
        model_name=request.model_name,
        quality=request.quality,
        metadata=request.metadata,
    )

    return EmbeddingResponse(
        embeddings=result.embeddings.tolist(),
        model_name=result.model_name,
        content_type=result.content_type,
        processing_time=result.processing_time,
        quality_score=result.quality_score,
        metadata=result.metadata,
    )


@app.post("/embed/batch", response_model=List[EmbeddingResponse])
async def embed_batch(
    request: BatchEmbeddingRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
) -> List[EmbeddingResponse]:
    """Generate embeddings for multiple texts."""
    results = await embedding_service.embed_batch(
        texts=request.texts,
        content_type=request.content_type,
        model_name=request.model_name,
        quality=request.quality,
        metadata_list=request.metadata_list,
    )

    return [
        EmbeddingResponse(
            embeddings=result.embeddings.tolist(),
            model_name=result.model_name,
            content_type=result.content_type,
            processing_time=result.processing_time,
            quality_score=result.quality_score,
            metadata=result.metadata,
        )
        for result in results
    ]


@app.post("/embed/code", response_model=EmbeddingResponse)
async def embed_code(
    request: CodeEmbeddingRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
) -> EmbeddingResponse:
    """Generate embeddings for code content."""
    result = await embedding_service.embed_code(
        code=request.code,
        language=request.language,
        model_name=request.model_name,
        metadata=request.metadata,
    )

    return EmbeddingResponse(
        embeddings=result.embeddings.tolist(),
        model_name=result.model_name,
        content_type=result.content_type,
        processing_time=result.processing_time,
        quality_score=result.quality_score,
        metadata=result.metadata,
    )


@app.get("/embed/models")
async def get_available_models(
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
) -> Dict[str, Any]:
    """Get list of available embedding models."""
    models = embedding_service.get_available_models()
    model_info = {}

    for model_name in models:
        info = embedding_service.get_model_info(model_name)
        if info:
            model_info[model_name] = info

    return {"available_models": models, "model_details": model_info}


@app.get("/embed/metrics")
async def get_embedding_metrics(
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
) -> Dict[str, Any]:
    """Get embedding service metrics."""
    return embedding_service.get_metrics()


@app.get("/embed/cache/stats")
async def get_cache_stats(
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
) -> Dict[str, Any]:
    """Get embedding cache statistics."""
    return embedding_service.get_cache_stats()


@app.delete("/embed/cache")
async def clear_cache(
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
) -> Dict[str, str]:
    """Clear the embedding cache."""
    embedding_service.clear_cache()
    return {"message": "Cache cleared successfully"}
