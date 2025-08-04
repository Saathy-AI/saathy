"""FastAPI application instance."""

import hashlib
import hmac
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Union

from fastapi import Depends, FastAPI, HTTPException, Request, status

from saathy import __version__
from saathy.config import Settings, get_settings
from saathy.connectors import ContentProcessor, GithubConnector
from saathy.embedding.service import EmbeddingService, get_embedding_service
from saathy.vector.client import QdrantClientWrapper
from saathy.vector.repository import VectorRepository

# In-memory dictionary to hold settings during the application's lifespan.
# This is a simple approach; for more complex scenarios, consider using a more robust solution.
app_state: dict[
    str,
    Union[
        Settings,
        VectorRepository,
        EmbeddingService,
        GithubConnector,
        ContentProcessor,
        None,
    ],
] = {}


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
        embedding_service = await get_embedding_service()
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


def get_content_processor() -> ContentProcessor:
    """Get the content processor from application state, creating it if needed."""
    if app_state.get("content_processor") is None:
        embedding_service = app_state.get("embedding_service")
        vector_repo = get_vector_repo()

        if not embedding_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Embedding service is not available.",
            )

        app_state["content_processor"] = ContentProcessor(
            embedding_service=embedding_service,
            vector_repo=vector_repo,
        )

    return app_state["content_processor"]


def get_github_connector() -> GithubConnector:
    """Get the GitHub connector from application state, raising an error if unavailable."""
    github_connector = app_state.get("github_connector")
    if not isinstance(github_connector, GithubConnector):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub connector is not configured or available.",
        )
    return github_connector


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


# --- GitHub Connector Endpoints ---


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    github_connector: GithubConnector = Depends(get_github_connector),
    content_processor: ContentProcessor = Depends(get_content_processor),
):
    """Handle incoming GitHub webhook events after verifying the signature."""
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Hub-Signature-256 header is missing.",
        )

    if not settings.github_webhook_secret_str:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub webhook secret is not configured.",
        )

    body = await request.body()
    expected_signature = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret_str.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
    )

    if not hmac.compare_digest(signature_header, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature."
        )

    event_type = request.headers.get("X-GitHub-Event")
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-GitHub-Event header is missing.",
        )

    if event_type == "ping":
        logging.info("Received GitHub ping event.")
        return {"message": "pong"}

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload."
        ) from e

    # Process the event using the GitHub connector
    event_data = {"event_type": event_type, "payload": payload}
    processed_content = await github_connector.process_event(event_data)

    # Process and store content using the content processor
    if processed_content:
        processing_result = await content_processor.process_and_store(processed_content)
        logging.info(
            f"Processed {len(processed_content)} items from GitHub '{event_type}' event. "
            f"Result: {processing_result['processed_items']}/{processing_result['total_items']} items stored."
        )

        return {
            "status": "ok",
            "event": event_type,
            "processing_result": processing_result,
        }
    else:
        return {
            "status": "ok",
            "event": event_type,
            "processing_result": {
                "total_items": 0,
                "processed_items": 0,
                "failed_items": 0,
            },
        }


@app.get("/connectors/github/status")
async def github_connector_status(
    github_connector: GithubConnector = Depends(get_github_connector),
):
    """Return the health and status of the GitHub connector."""
    is_healthy = await github_connector.health_check()
    return {
        "name": github_connector.name,
        "status": github_connector.status.value,
        "healthy": is_healthy,
    }


@app.post("/connectors/github/sync")
async def github_manual_sync(
    repository: str,
    github_connector: GithubConnector = Depends(get_github_connector),
):
    """Trigger a manual repository sync (placeholder)."""
    logging.info(
        f"Manual sync requested for repository: {repository} "
        f"for connector {github_connector.name}. This feature is not yet implemented."
    )
    # In a real implementation, this would trigger the sync logic.
    return {"message": "Manual sync acknowledged. Feature is under development."}
