"""APScheduler initialization for background jobs."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """Start the background job scheduler."""
    scheduler.start()


def stop_scheduler() -> None:
    """Stop the background job scheduler."""
    scheduler.shutdown()
