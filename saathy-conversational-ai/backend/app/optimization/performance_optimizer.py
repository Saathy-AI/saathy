"""
Performance optimization utilities for the conversational AI system.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from functools import wraps
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization tracking."""
    response_time: float
    token_count: int
    cache_hits: int
    cache_misses: int
    context_expansions: int
    retrieval_time: float
    processing_time: float


class PerformanceOptimizer:
    """
    Performance optimization manager for the conversational AI system.
    
    Handles:
    - Response time optimization
    - Cache performance monitoring
    - Context expansion optimization
    - Resource usage tracking
    """
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.optimization_config = {
            "max_response_time": 30.0,
            "target_response_time": 5.0,
            "cache_hit_threshold": 0.8,
            "max_context_expansions": 3,
        }
    
    async def optimize_response_time(self, target_time: float = 5.0) -> Dict[str, Any]:
        """
        Optimize response time based on historical metrics.
        
        Args:
            target_time: Target response time in seconds
            
        Returns:
            Optimization recommendations
        """
        if not self.metrics_history:
            return {"status": "no_data", "recommendations": []}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 interactions
        avg_response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics)
        
        recommendations = []
        
        if avg_response_time > target_time:
            recommendations.append({
                "type": "response_time",
                "issue": f"Average response time ({avg_response_time:.2f}s) exceeds target ({target_time}s)",
                "suggestion": "Consider reducing context size or optimizing retrieval"
            })
        
        return {
            "status": "optimized",
            "current_avg": avg_response_time,
            "target": target_time,
            "recommendations": recommendations
        }
    
    def record_metrics(self, metrics: PerformanceMetrics) -> None:
        """
        Record performance metrics for optimization analysis.
        
        Args:
            metrics: Performance metrics to record
        """
        self.metrics_history.append(metrics)
        
        # Keep only last 100 metrics to prevent memory bloat
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        logger.debug(f"Recorded metrics: {metrics}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current performance metrics.
        
        Returns:
            Performance summary statistics
        """
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-20:]  # Last 20 interactions
        
        return {
            "total_interactions": len(self.metrics_history),
            "recent_interactions": len(recent_metrics),
            "avg_response_time": sum(m.response_time for m in recent_metrics) / len(recent_metrics),
            "avg_token_count": sum(m.token_count for m in recent_metrics) / len(recent_metrics),
            "cache_hit_rate": sum(m.cache_hits for m in recent_metrics) / max(sum(m.cache_hits + m.cache_misses for m in recent_metrics), 1),
            "avg_context_expansions": sum(m.context_expansions for m in recent_metrics) / len(recent_metrics),
        }
    
    def should_expand_context(self, current_expansions: int, response_time: float) -> bool:
        """
        Determine if context should be expanded based on performance metrics.
        
        Args:
            current_expansions: Current number of context expansions
            response_time: Current response time
            
        Returns:
            True if context should be expanded
        """
        if current_expansions >= self.optimization_config["max_context_expansions"]:
            return False
        
        if response_time > self.optimization_config["max_response_time"]:
            return False
        
        return True
    
    def optimize_cache_strategy(self) -> Dict[str, Any]:
        """
        Optimize cache strategy based on hit rates.
        
        Returns:
            Cache optimization recommendations
        """
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-50:]  # Last 50 interactions
        total_hits = sum(m.cache_hits for m in recent_metrics)
        total_misses = sum(m.cache_misses for m in recent_metrics)
        total_requests = total_hits + total_misses
        
        if total_requests == 0:
            return {"status": "no_data"}
        
        hit_rate = total_hits / total_requests
        
        recommendations = []
        
        if hit_rate < self.optimization_config["cache_hit_threshold"]:
            recommendations.append({
                "type": "cache_optimization",
                "issue": f"Cache hit rate ({hit_rate:.2%}) below threshold ({self.optimization_config['cache_hit_threshold']:.2%})",
                "suggestion": "Consider expanding cache size or improving cache keys"
            })
        
        return {
            "status": "analyzed",
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "recommendations": recommendations
        }


def performance_monitor(func):
    """
    Decorator to monitor function performance.
    
    Args:
        func: Function to monitor
        
    Returns:
        Wrapped function with performance monitoring
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log performance metrics
            logger.info(f"{func.__name__} executed in {execution_time:.3f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper
