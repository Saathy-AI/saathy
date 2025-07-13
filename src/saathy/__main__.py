"""Production-ready server entrypoint with Gunicorn and Uvicorn workers."""

import argparse
import multiprocessing
import signal
import sys
from typing import Any

import uvicorn
from gunicorn.app.base import BaseApplication

from saathy.api import app
from saathy.config import get_settings


def get_worker_count() -> int:
    """Calculate the optimal number of Gunicorn worker processes."""
    return min(multiprocessing.cpu_count() * 2 + 1, 4)


def run_dev() -> None:
    """Run the FastAPI application in development mode using Uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "saathy.api:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )


class StandaloneGunicornApplication(BaseApplication):
    """A custom Gunicorn application to run FastAPI with Uvicorn workers."""

    def __init__(self, app: Any, options: dict[str, Any] | None = None):
        """Initialize the custom Gunicorn application."""
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        """Load configuration from the options dictionary into Gunicorn."""
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self) -> Any:
        """Load the FastAPI application."""
        return self.application


def run_prod() -> None:
    """Run the FastAPI application in production mode using Gunicorn."""
    settings = get_settings()
    worker_count = get_worker_count()

    options = {
        "bind": f"{settings.host}:{settings.port}",
        "workers": worker_count,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "keepalive": 2,
        "max_requests": 1000,
        "max_requests_jitter": 50,
        "log_level": settings.log_level.lower(),
    }

    # Set worker_tmp_dir only on non-Windows systems
    if sys.platform != "win32":
        options["worker_tmp_dir"] = "/dev/shm"

    gunicorn_app = StandaloneGunicornApplication(app, options)

    def handle_exit(sig: Any, frame: Any) -> None:
        """Handle exit signals for graceful shutdown."""
        gunicorn_app.handle_exit(sig, frame)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    gunicorn_app.run()


def main() -> None:
    """Parse CLI arguments and run the application in the specified mode."""
    parser = argparse.ArgumentParser(
        description="Run the Saathy FastAPI application."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["dev", "prod"],
        default="dev",
        help="The mode to run the application in (dev or prod).",
    )
    args = parser.parse_args()

    if args.mode == "prod":
        run_prod()
    else:
        run_dev()


if __name__ == "__main__":
    main() 