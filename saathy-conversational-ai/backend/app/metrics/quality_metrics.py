"""
Quality Metrics - Tracks conversation quality and system performance.
Provides feedback loops for continuous improvement.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np
from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class QualityMetrics:
    """
    Comprehensive metrics tracking for the conversational AI system.

    Tracks:
    - Response quality and relevance
    - Context sufficiency
    - User satisfaction signals
    - System performance
    - Error rates and patterns
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config

        # Initialize Prometheus metrics
        self._init_prometheus_metrics()

        # In-memory metrics storage for analysis
        self.conversation_metrics = defaultdict(list)
        self.user_metrics = defaultdict(
            lambda: {
                "total_queries": 0,
                "successful_queries": 0,
                "avg_satisfaction": 0.0,
                "common_intents": defaultdict(int),
                "avg_response_time": 0.0,
            }
        )

        # Thresholds for quality assessment
        self.thresholds = {
            "low_satisfaction": 0.5,
            "slow_response": 2.0,  # seconds
            "low_sufficiency": 0.6,
            "high_expansion_rate": 0.3,
        }

        # Learning feedback storage
        self.feedback_queue = asyncio.Queue(maxsize=1000)

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics collectors"""

        # Response metrics
        self.response_time = Histogram(
            "saathy_response_time_seconds",
            "Time taken to generate response",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        )

        self.query_counter = Counter(
            "saathy_queries_total",
            "Total number of queries processed",
            ["intent", "status"],
        )

        self.sufficiency_score = Summary(
            "saathy_sufficiency_score", "Context sufficiency scores"
        )

        self.expansion_rate = Gauge(
            "saathy_expansion_rate", "Rate of context expansion needed"
        )

        # Quality metrics
        self.relevance_score = Summary(
            "saathy_relevance_score", "Response relevance scores"
        )

        self.user_satisfaction = Summary(
            "saathy_user_satisfaction", "User satisfaction scores"
        )

        # System metrics
        self.cache_hit_rate = Gauge(
            "saathy_cache_hit_rate", "Cache hit rate percentage"
        )

        self.error_counter = Counter(
            "saathy_errors_total", "Total number of errors", ["error_type"]
        )

    async def track_conversation_turn(self, session_id: str, turn_data: dict[str, Any]):
        """
        Track metrics for a single conversation turn.

        Args:
            session_id: Unique session identifier
            turn_data: Data about the conversation turn including:
                - query: User query
                - response: Generated response
                - response_time: Time taken
                - sufficiency_score: Context sufficiency
                - expansion_attempts: Number of expansions
                - context_size: Amount of context used
                - intent: Detected intent
                - error: Any error that occurred
        """

        # Record in Prometheus
        if "error" not in turn_data:
            self.response_time.observe(turn_data.get("response_time", 0))
            self.query_counter.labels(
                intent=turn_data.get("intent", "unknown"), status="success"
            ).inc()

            if "sufficiency_score" in turn_data:
                self.sufficiency_score.observe(turn_data["sufficiency_score"])
        else:
            self.query_counter.labels(
                intent=turn_data.get("intent", "unknown"), status="error"
            ).inc()
            self.error_counter.labels(
                error_type=turn_data.get("error_type", "unknown")
            ).inc()

        # Store detailed metrics
        metric_entry = {
            "timestamp": datetime.utcnow(),
            "session_id": session_id,
            "user_id": turn_data.get("user_id"),
            "query": turn_data.get("query", "")[:200],  # Truncate for storage
            "intent": turn_data.get("intent", "unknown"),
            "response_time": turn_data.get("response_time", 0),
            "sufficiency_score": turn_data.get("sufficiency_score", 0),
            "expansion_attempts": turn_data.get("expansion_attempts", 0),
            "context_size": turn_data.get("context_size", 0),
            "tokens_used": turn_data.get("tokens_used", 0),
            "confidence_level": turn_data.get("confidence_level", "unknown"),
            "error": turn_data.get("error"),
        }

        self.conversation_metrics[session_id].append(metric_entry)

        # Update user metrics
        user_id = turn_data.get("user_id")
        if user_id:
            await self._update_user_metrics(user_id, metric_entry)

        # Check for quality issues
        quality_issues = self._identify_quality_issues(metric_entry)
        if quality_issues:
            await self._queue_for_learning(metric_entry, quality_issues)

    async def track_user_feedback(self, session_id: str, feedback: dict[str, Any]):
        """
        Track explicit user feedback.

        Args:
            session_id: Session identifier
            feedback: Feedback data including:
                - relevance_score: How relevant was the response (0-1)
                - completeness_score: How complete was the response (0-1)
                - helpful: Was the response helpful (boolean)
                - feedback_text: Optional text feedback
        """

        # Record in Prometheus
        if "relevance_score" in feedback:
            self.relevance_score.observe(feedback["relevance_score"])

        satisfaction = (
            feedback.get("relevance_score", 0.5) * 0.5
            + feedback.get("completeness_score", 0.5) * 0.5
        )
        self.user_satisfaction.observe(satisfaction)

        # Store feedback
        if session_id in self.conversation_metrics:
            # Find the last turn for this session
            if self.conversation_metrics[session_id]:
                last_turn = self.conversation_metrics[session_id][-1]
                last_turn["user_feedback"] = feedback
                last_turn["satisfaction_score"] = satisfaction

                # Queue for learning if low satisfaction
                if satisfaction < self.thresholds["low_satisfaction"]:
                    await self._queue_for_learning(last_turn, ["low_satisfaction"])

    async def _update_user_metrics(self, user_id: str, metric_entry: dict[str, Any]):
        """Update aggregated metrics for a user"""

        user_metric = self.user_metrics[user_id]

        # Update counters
        user_metric["total_queries"] += 1
        if "error" not in metric_entry:
            user_metric["successful_queries"] += 1

        # Update intent frequency
        intent = metric_entry.get("intent", "unknown")
        user_metric["common_intents"][intent] += 1

        # Update average response time (running average)
        prev_avg = user_metric["avg_response_time"]
        n = user_metric["total_queries"]
        new_time = metric_entry.get("response_time", 0)
        user_metric["avg_response_time"] = ((n - 1) * prev_avg + new_time) / n

        # Update satisfaction if available
        if "satisfaction_score" in metric_entry:
            prev_sat = user_metric["avg_satisfaction"]
            new_sat = metric_entry["satisfaction_score"]
            user_metric["avg_satisfaction"] = ((n - 1) * prev_sat + new_sat) / n

    def _identify_quality_issues(self, metric_entry: dict[str, Any]) -> list[str]:
        """Identify quality issues in a conversation turn"""

        issues = []

        # Slow response
        if metric_entry.get("response_time", 0) > self.thresholds["slow_response"]:
            issues.append("slow_response")

        # Low sufficiency
        if (
            metric_entry.get("sufficiency_score", 1.0)
            < self.thresholds["low_sufficiency"]
        ):
            issues.append("low_sufficiency")

        # High expansion rate
        if metric_entry.get("expansion_attempts", 0) > 1:
            issues.append("high_expansion_rate")

        # Error occurred
        if metric_entry.get("error"):
            issues.append("error_occurred")

        # Low confidence
        if metric_entry.get("confidence_level") == "low":
            issues.append("low_confidence")

        return issues

    async def _queue_for_learning(
        self, metric_entry: dict[str, Any], issues: list[str]
    ):
        """Queue problematic cases for learning optimization"""

        learning_entry = {
            "timestamp": datetime.utcnow(),
            "metric_entry": metric_entry,
            "issues": issues,
            "priority": self._calculate_learning_priority(issues),
        }

        try:
            await self.feedback_queue.put(learning_entry)
            logger.debug(f"Queued learning entry with issues: {issues}")
        except asyncio.QueueFull:
            logger.warning("Learning feedback queue is full, dropping entry")

    def _calculate_learning_priority(self, issues: list[str]) -> float:
        """Calculate priority for learning based on issues"""

        priority_weights = {
            "error_occurred": 1.0,
            "low_satisfaction": 0.8,
            "low_sufficiency": 0.6,
            "high_expansion_rate": 0.5,
            "slow_response": 0.4,
            "low_confidence": 0.3,
        }

        return sum(priority_weights.get(issue, 0.1) for issue in issues)

    def get_session_metrics(self, session_id: str) -> dict[str, Any]:
        """Get metrics for a specific session"""

        if session_id not in self.conversation_metrics:
            return {"error": "Session not found"}

        turns = self.conversation_metrics[session_id]

        if not turns:
            return {"error": "No data for session"}

        # Calculate session statistics
        total_time = sum(t.get("response_time", 0) for t in turns)
        avg_sufficiency = np.mean([t.get("sufficiency_score", 0) for t in turns])
        total_expansions = sum(t.get("expansion_attempts", 0) for t in turns)
        error_count = sum(1 for t in turns if t.get("error"))

        return {
            "session_id": session_id,
            "turn_count": len(turns),
            "total_response_time": total_time,
            "avg_response_time": total_time / len(turns),
            "avg_sufficiency_score": avg_sufficiency,
            "total_expansion_attempts": total_expansions,
            "expansion_rate": total_expansions / len(turns),
            "error_rate": error_count / len(turns),
            "intents": [t.get("intent", "unknown") for t in turns],
            "satisfaction_scores": [
                t.get("satisfaction_score") for t in turns if "satisfaction_score" in t
            ],
        }

    def get_user_metrics(self, user_id: str) -> dict[str, Any]:
        """Get aggregated metrics for a user"""

        if user_id not in self.user_metrics:
            return {"error": "User not found"}

        metrics = self.user_metrics[user_id].copy()

        # Add success rate
        if metrics["total_queries"] > 0:
            metrics["success_rate"] = (
                metrics["successful_queries"] / metrics["total_queries"]
            )
        else:
            metrics["success_rate"] = 0.0

        # Convert defaultdict to regular dict
        metrics["common_intents"] = dict(metrics["common_intents"])

        return metrics

    def get_system_metrics(self) -> dict[str, Any]:
        """Get overall system metrics"""

        # Calculate global statistics
        all_turns = []
        for turns in self.conversation_metrics.values():
            all_turns.extend(turns)

        if not all_turns:
            return {"error": "No data available"}

        # Response time statistics
        response_times = [t.get("response_time", 0) for t in all_turns]

        # Sufficiency statistics
        sufficiency_scores = [
            t.get("sufficiency_score", 0) for t in all_turns if "sufficiency_score" in t
        ]

        # Expansion statistics
        expansion_counts = [t.get("expansion_attempts", 0) for t in all_turns]

        # Error statistics
        error_count = sum(1 for t in all_turns if t.get("error"))

        # Intent distribution
        intent_counts = defaultdict(int)
        for turn in all_turns:
            intent_counts[turn.get("intent", "unknown")] += 1

        return {
            "total_conversations": len(self.conversation_metrics),
            "total_turns": len(all_turns),
            "avg_response_time": np.mean(response_times),
            "p95_response_time": np.percentile(response_times, 95),
            "avg_sufficiency_score": np.mean(sufficiency_scores)
            if sufficiency_scores
            else 0,
            "expansion_rate": sum(e > 0 for e in expansion_counts)
            / len(expansion_counts),
            "error_rate": error_count / len(all_turns),
            "intent_distribution": dict(intent_counts),
            "active_users": len(self.user_metrics),
        }

    async def export_metrics_for_analysis(self) -> dict[str, Any]:
        """Export metrics for offline analysis and model improvement"""

        # Get all conversations with issues
        problematic_conversations = []

        for session_id, turns in self.conversation_metrics.items():
            session_issues = []

            for turn in turns:
                issues = self._identify_quality_issues(turn)
                if issues:
                    session_issues.append({"turn": turn, "issues": issues})

            if session_issues:
                problematic_conversations.append(
                    {"session_id": session_id, "problematic_turns": session_issues}
                )

        # Get learning queue items
        learning_items = []
        while not self.feedback_queue.empty():
            try:
                item = await self.feedback_queue.get()
                learning_items.append(item)
            except asyncio.QueueEmpty:
                break

        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "system_metrics": self.get_system_metrics(),
            "problematic_conversations": problematic_conversations,
            "learning_queue": learning_items,
            "user_metrics_summary": {
                user_id: self.get_user_metrics(user_id)
                for user_id in list(self.user_metrics.keys())[
                    :100
                ]  # Limit to 100 users
            },
        }

    def update_cache_metrics(self, cache_stats: dict[str, Any]):
        """Update cache-related metrics"""

        if "hit_rate" in cache_stats:
            self.cache_hit_rate.set(cache_stats["hit_rate"] * 100)

    def reset_session_metrics(self, session_id: str):
        """Reset metrics for a session (e.g., after conversation ends)"""

        if session_id in self.conversation_metrics:
            del self.conversation_metrics[session_id]
