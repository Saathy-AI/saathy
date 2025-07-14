"""FastAPI application instance."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Union

from fastapi import Depends, FastAPI
from qdrant_client import QdrantClient

from saathy import __version__
from saathy.config import Settings, get_settings
from saathy.telemetry import configure_logging, configure_tracing
from saathy.vector.repository import VectorRepository

# In-memory dictionary to hold settings during the application's lifespan.
# This is a simple approach; for more complex scenarios, consider using a more robust solution.
app_state: dict[str, Union[Settings, VectorRepository, None]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load the settings before the app starts and clear them when it's done."""
    settings = get_settings()

    # Initialize vector_repo as None - will be created lazily when needed
    app_state["settings"] = settings
    app_state["vector_repo"] = None

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
        settings = app_state["settings"]
        qdrant_client = QdrantClient(
            url=str(settings.qdrant_url),
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
        return {
            "status": "unhealthy",
            "dependencies": {"qdrant": "unhealthy"},
        }
    except Exception:
        return {
            "status": "unhealthy",
            "dependencies": {"qdrant": "unavailable"},
        }


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
