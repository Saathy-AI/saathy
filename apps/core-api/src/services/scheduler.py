"""Scheduler service."""

class SchedulerService:
    """Service for scheduled tasks."""
    
    def __init__(self, timezone: str = "UTC"):
        self.timezone = timezone
    
    def start(self) -> None:
        """Start the scheduler."""
        pass
    
    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        pass