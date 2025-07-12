"""FastAPI application instance."""

from fastapi import FastAPI

from saathy import __version__

app = FastAPI(
    title="Saathy",
    description="A FastAPI-based application",
    version=__version__,
)


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"} 