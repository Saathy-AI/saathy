"""FastAPI application instance."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Union

from fastapi import Depends, FastAPI

from saathy import __version__
from saathy.config import Settings, get_settings
from saathy.connectors.github_connector import GithubConnector
from saathy.embedding.service import EmbeddingService, get_embedding_service
from saathy.vector.client import QdrantClientWrapper
from saathy.vector.repository import VectorRepository

# In-memory dictionary to hold settings during the application's lifespan.
# This is a simple approach; for more complex scenarios, consider using a more robust solution.
app_state: dict[str, Union[Settings, VectorRepository, EmbeddingService, GithubConnector, None]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load settings and initialize connectors before the app starts, and clean up on shutdown."""
    settings = get_settings()

    # Initialize services as None - will be created lazily when needed
    app_state["settings"] = settings
    app_state["vector_repo"] = None
    app_state["embedding_service"] = None

    # Initialize GitHub connector if configured
    if settings.github_webhook_secret_str and settings.github_token_str:
        logging.info("GitHub connector is configured, initializing.")
        github_connector = GithubConnector(
            name="github",
            config={
                "token": settings.github_token_str,
                "webhook_secret": settings.github_webhook_secret_str,
                "repositories": (
                    settings.github_repositories.split(",")
                    if settings.github_repositories
                    else []
                ),
            },
        )
        await github_connector.start()
        app_state["github_connector"] = github_connector
    else:
        app_state["github_connector"] = None
        logging.warning(
            "GitHub connector not configured. Skipping initialization. "
            "Provide GITHUB_WEBHOOK_SECRET and GITHUB_TOKEN to enable it."
        )

    # Initialize embedding service
    try:
        embedding_service = get_embedding_service()
        await embedding_service.warmup()
        app_state["embedding_service"] = embedding_service
        logging.info("Embedding service initialized successfully.")
    except Exception as e:
        app_state["embedding_service"] = None
        logging.error(f"Failed to initialize embedding service: {e}")

    yield

    # Stop services on shutdown
    github_connector = app_state.get("github_connector")
    if isinstance(github_connector, GithubConnector):
        logging.info("Shutting down GitHub connector.")
        await github_connector.stop()

    embedding_service = app_state.get("embedding_service")
    if isinstance(embedding_service, EmbeddingService):
        logging.info("Shutting down embedding service.")
        await embedding_service.shutdown()

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
        if "settings" not in app_state:
            settings = get_settings()
        else:
            settings = app_state["settings"]

        qdrant_url = str(settings.qdrant_url)
        if qdrant_url.startswith("http://"):
            qdrant_url = qdrant_url[7:]
        elif qdrant_url.startswith("https://"):
            qdrant_url = qdrant_url[8:]

        qdrant_url = qdrant_url.split("/")[0]

        host_port = qdrant_url.split(":")
        host = host_port[0]

        try:
            port = int(host_port[1]) if len(host_port) > 1 else 6333
        except (ValueError, IndexError):
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


@app.get("/healthz")
async def health_check(
    vector_repo: VectorRepository = Depends(get_vector_repo),
) -> dict[str, str | dict[str, str]]:
    """Health check endpoint."""
    try:
        qdrant_healthy = await vector_repo.health_check()
        if qdrant_healthy:
            return {"status": "healthy", "dependencies": {"qdrant": "healthy"}}
        else:
            return {
                "status": "unhealthy",
                "dependencies": {"qdrant": "unhealthy"},
            }
    except Exception as e:
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
