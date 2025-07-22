"""Metrics and monitoring for vector operations."""

import asyncio
import time
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class VectorMetrics:
    """Metrics collector for vector operations."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.operation_times: dict[str, list] = {}
        self.operation_counts: dict[str, int] = {}
        self.error_counts: dict[str, int] = {}
        self.collection_stats: dict[str, dict[str, Any]] = {}

    def record_operation(
        self, operation: str, duration: float, success: bool = True
    ) -> None:
        """Record operation timing and success/failure.

        Args:
            operation: Name of the operation
            duration: Operation duration in seconds
            success: Whether the operation was successful
        """
        # Record timing
        if operation not in self.operation_times:
            self.operation_times[operation] = []
        self.operation_times[operation].append(duration)

        # Record count
        if operation not in self.operation_counts:
            self.operation_counts[operation] = 0
        self.operation_counts[operation] += 1

        # Record errors
        if not success:
            if operation not in self.error_counts:
                self.error_counts[operation] = 0
            self.error_counts[operation] += 1

        logger.debug(
            "Vector operation recorded",
            operation=operation,
            duration=duration,
            success=success,
        )

    def get_operation_stats(self, operation: str) -> dict[str, Any]:
        """Get statistics for a specific operation.

        Args:
            operation: Name of the operation

        Returns:
            Dictionary with operation statistics
        """
        times = self.operation_times.get(operation, [])
        total_count = self.operation_counts.get(operation, 0)
        error_count = self.error_counts.get(operation, 0)
        success_count = total_count - error_count

        if not times:
            return {
                "operation": operation,
                "total_count": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
            }

        return {
            "operation": operation,
            "total_count": total_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (
                (success_count / total_count * 100) if total_count > 0 else 0.0
            ),
            "avg_duration": sum(times) / len(times),
            "min_duration": min(times),
            "max_duration": max(times),
            "p50_duration": sorted(times)[len(times) // 2],
            "p95_duration": sorted(times)[int(len(times) * 0.95)],
            "p99_duration": sorted(times)[int(len(times) * 0.99)],
        }

    def get_all_stats(self) -> dict[str, Any]:
        """Get statistics for all operations.

        Returns:
            Dictionary with all operation statistics
        """
        all_operations = set(self.operation_counts.keys())
        stats = {}

        for operation in all_operations:
            stats[operation] = self.get_operation_stats(operation)

        return {
            "operations": stats,
            "total_operations": sum(self.operation_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "overall_success_rate": (
                (
                    (
                        sum(self.operation_counts.values())
                        - sum(self.error_counts.values())
                    )
                    / sum(self.operation_counts.values())
                    * 100
                )
                if sum(self.operation_counts.values()) > 0
                else 0.0
            ),
        }

    def update_collection_stats(
        self, collection_name: str, stats: dict[str, Any]
    ) -> None:
        """Update collection statistics.

        Args:
            collection_name: Name of the collection
            stats: Collection statistics
        """
        self.collection_stats[collection_name] = {
            **stats,
            "last_updated": time.time(),
        }

        logger.debug(
            "Collection stats updated",
            collection=collection_name,
            vector_count=stats.get("vector_count"),
            status=stats.get("status"),
        )

    def get_collection_stats(self, collection_name: str) -> Optional[dict[str, Any]]:
        """Get collection statistics.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection statistics or None if not found
        """
        return self.collection_stats.get(collection_name)

    def get_all_collection_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all collections.

        Returns:
            Dictionary with all collection statistics
        """
        return self.collection_stats.copy()

    def reset(self) -> None:
        """Reset all metrics."""
        self.operation_times.clear()
        self.operation_counts.clear()
        self.error_counts.clear()
        self.collection_stats.clear()
        logger.info("Vector metrics reset")


# Global metrics instance
_metrics = VectorMetrics()


def get_metrics() -> VectorMetrics:
    """Get the global metrics instance."""
    return _metrics


def record_operation(operation: str, duration: float, success: bool = True) -> None:
    """Record an operation in the global metrics.

    Args:
        operation: Name of the operation
        duration: Operation duration in seconds
        success: Whether the operation was successful
    """
    _metrics.record_operation(operation, duration, success)


def operation_timer(operation: str):
    """Decorator to automatically time and record operations.

    Args:
        operation: Name of the operation to record

    Returns:
        Decorator function
    """

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                record_operation(operation, duration, success=True)
                return result
            except Exception:
                duration = time.time() - start_time
                record_operation(operation, duration, success=False)
                raise

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                record_operation(operation, duration, success=True)
                return result
            except Exception:
                duration = time.time() - start_time
                record_operation(operation, duration, success=False)
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
