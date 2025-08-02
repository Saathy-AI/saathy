"""FastAPI application instance."""

import hashlib
import hmac
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Union

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from saathy import __version__
from saathy.config import Settings, get_settings
from saathy.connectors import GithubConnector
from saathy.telemetry import configure_logging, configure_tracing
from saathy.vector.client import QdrantClientWrapper
from saathy.vector.repository import VectorRepository

# In-memory dictionary to hold application state.
app_state: dict[str, Union[Settings, VectorRepository, GithubConnector, None]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load settings and initialize connectors before the app starts, and clean up on shutdown."""
    settings = get_settings()

    # Configure logging and tracing first
    configure_logging(settings=settings)
    configure_tracing(settings=settings, app=app)

    # Store settings in app_state
    app_state["settings"] = settings
    app_state["vector_repo"] = None

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
            "GitHub connector not configured. "
            "Skipping initialization. "
            "Provide GITHUB_WEBHOOK_SECRET and GITHUB_TOKEN to enable it."
        )

    yield

    # Stop connectors on shutdown
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

class SyncRequest(BaseModel):
    repository: str


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    github_connector: GithubConnector = Depends(get_github_connector),
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
    expected_signature = "sha256=" + hmac.new(
        settings.github_webhook_secret_str.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400__BAD_REQUEST, detail="Invalid JSON payload."
        )

    event_data = {"event_type": event_type, "payload": payload}
    processed_content = await github_connector.process_event(event_data)

    if processed_content:
        logging.info(f"Processed {len(processed_content)} items from GitHub '{event_type}' event.")
        # TODO: Store processed content in the vector repository
        # vector_repo = get_vector_repo()
        # await vector_repo.add_documents(processed_content)

    return {"status": "ok", "event": event_type}


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
    sync_request: SyncRequest,
    github_connector: GithubConnector = Depends(get_github_connector),
):
    """Trigger a manual repository sync (placeholder)."""
    logging.info(
        f"Manual sync requested for repository: {sync_request.repository} "
        f"for connector {github_connector.name}. This feature is not yet implemented."
    )
    # In a real implementation, this would trigger the sync logic.
    return {"message": "Manual sync acknowledged. Feature is under development."}
