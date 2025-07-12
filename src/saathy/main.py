"""Gunicorn/Uvicorn entrypoint for the FastAPI application."""

import uvicorn

from saathy.config import settings


def main() -> None:
    """Run the FastAPI application."""
    uvicorn.run(
        "saathy.api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
