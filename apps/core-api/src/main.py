"""Saathy Core API - Main application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .dependencies import setup_dependencies, cleanup_dependencies
from .middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
)
from .routers import (
    health,
    connectors,
    webhooks,
    intelligence,
    streaming,
    admin,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting Saathy Core API...")
    
    # Setup dependencies
    await setup_dependencies(app)
    
    yield
    
    # Cleanup
    logger.info("Shutting down Saathy Core API...")
    await cleanup_dependencies(app)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()
    
    app = FastAPI(
        title="Saathy Core API",
        description="Knowledge layer and connectors for Saathy",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )
    
    # Add middleware
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            calls=settings.rate_limit_calls,
            period=settings.rate_limit_period,
        )
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(connectors.router, prefix="/api/v1/connectors", tags=["connectors"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
    app.include_router(intelligence.router, prefix="/api/v1/intelligence", tags=["intelligence"])
    app.include_router(streaming.router, prefix="/api/v1/streaming", tags=["streaming"])
    
    if settings.debug:
        app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": "Saathy Core API",
            "version": "0.1.0",
            "status": "running"
        }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app


# Create the default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )