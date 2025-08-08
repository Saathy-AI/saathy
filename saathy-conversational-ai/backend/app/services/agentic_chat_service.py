"""
Agentic Chat Service - Enhanced chat service using the multi-agent system.
Integrates all Phase 2 and 3 components for intelligent conversation handling.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Optional

from config.settings import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context_orchestration import ContextOrchestrationGraph
from app.memory.compressive_memory import CompressiveMemoryManager
from app.metrics.learning_optimizer import LearningOptimizer
from app.metrics.quality_metrics import QualityMetrics
from app.models.chat_session import (
    ChatMessage,
    ChatResponse,
    ChatSession,
    ChatSessionDB,
    ChatTurnDB,
    SessionStatus,
)
from app.optimization.context_cache import ContextCache
from app.utils.database import get_redis

logger = logging.getLogger(__name__)


class AgenticChatService:
    """
    Enhanced chat service with:
    - LangGraph multi-agent orchestration
    - Compressive memory management
    - Intelligent caching
    - Quality metrics tracking
    - Learning optimization
    """

    def __init__(self):
        settings = get_settings()

        # Core configuration
        self.config = {
            "openai_api_key": settings.openai_api_key,
            "max_expansion_attempts": 3,
            "sufficiency_threshold": 0.7,
            "rrf_k": 60,
            "max_recent_turns": 3,
            "compression_threshold": 5,
            "response_temperature": 0.7,
        }

        # Initialize components
        self.orchestration_graph = ContextOrchestrationGraph(self.config)
        self.memory_manager = CompressiveMemoryManager(self.config)
        self.context_cache = ContextCache(self.config)
        self.quality_metrics = QualityMetrics(self.config)
        self.learning_optimizer = LearningOptimizer(self.config)

        self.redis_client = None
        self.initialized = False

    async def initialize(self):
        """Initialize service connections and components"""
        if not self.initialized:
            self.redis_client = await get_redis()

            # Apply optimized parameters from learning
            optimized_params = await self.learning_optimizer.get_optimized_parameters()
            self._apply_optimized_parameters(optimized_params)

            self.initialized = True
            logger.info("Agentic chat service initialized")

    def _apply_optimized_parameters(self, params: dict[str, Any]):
        """Apply optimized parameters to system configuration"""

        # Update configuration with optimized values
        self.config["sufficiency_threshold"] = params.get("sufficiency_threshold", 0.7)
        self.config["rrf_k"] = params.get("rrf_k", 60)

        # Update agent configurations
        if hasattr(self.orchestration_graph, "sufficiency_evaluator"):
            self.orchestration_graph.sufficiency_evaluator.sufficiency_threshold = (
                params["sufficiency_threshold"]
            )

        logger.info(f"Applied optimized parameters: {params}")

    async def create_session(self, user_id: str, db: AsyncSession) -> ChatSession:
        """Create a new chat session"""

        await self.initialize()

        # Create database session
        db_session = ChatSessionDB(user_id=user_id)
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)

        # Initialize session in Redis
        session_key = f"session:{db_session.id}"
        session_data = {
            "id": str(db_session.id),
            "user_id": user_id,
            "status": SessionStatus.ACTIVE.value,
            "created_at": datetime.utcnow().isoformat(),
            "conversation_turns": [],
            "compressed_memory": None,
        }

        await self.redis_client.setex(
            session_key,
            86400,  # 24 hour TTL
            json.dumps(session_data),
        )

        return ChatSession(
            id=str(db_session.id),
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            created_at=db_session.created_at,
        )

    async def process_message(
        self, session_id: str, message: ChatMessage, db: AsyncSession
    ) -> ChatResponse:
        """
        Process a user message through the agentic system.

        This is the main entry point that orchestrates:
        1. Memory retrieval
        2. Context caching
        3. Multi-agent processing
        4. Quality tracking
        5. Response generation
        """

        await self.initialize()
        start_time = time.time()

        try:
            # Get session data
            session_data = await self._get_session_data(session_id)
            if not session_data:
                raise ValueError(f"Session {session_id} not found")

            # Get conversation history and compressed memory
            conversation_history = session_data.get("conversation_turns", [])
            session_data.get("compressed_memory")

            # Check cache first
            cached_result = await self.context_cache.get_cached_query_result(
                message.content, session_data["user_id"]
            )

            if cached_result:
                logger.info(f"Cache hit for query in session {session_id}")
                response = cached_result["response"]
                metadata = cached_result["metadata"]

            else:
                # Process through multi-agent system
                result = await self.orchestration_graph.process_message(
                    user_message=message.content,
                    session_id=session_id,
                    user_id=session_data["user_id"],
                    conversation_history=conversation_history,
                )

                response = result["response"]
                metadata = result["metadata"]

                # Cache the result
                await self.context_cache.cache_query_result(
                    message.content, session_data["user_id"], result
                )

            # Calculate processing time
            processing_time = time.time() - start_time

            # Store conversation turn
            turn_data = {
                "user_message": message.content,
                "assistant_response": response,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata,
                "processing_time": processing_time,
            }

            conversation_history.append(turn_data)

            # Update session data
            session_data["conversation_turns"] = conversation_history
            session_data["last_activity"] = datetime.utcnow().isoformat()

            # Compress memory if needed
            if len(conversation_history) >= self.config["compression_threshold"]:
                compressed = await self.memory_manager.compress_conversation(
                    conversation_history, session_data["user_id"]
                )
                if compressed["compressed"]:
                    session_data["compressed_memory"] = compressed["memory"]
                    # Keep only recent turns
                    session_data["conversation_turns"] = conversation_history[-3:]

            # Save updated session
            await self._save_session_data(session_id, session_data)

            # Save to database
            await self._save_turn_to_db(
                session_id, message.content, response, metadata, db
            )

            # Track metrics
            await self._track_conversation_metrics(
                session_id,
                session_data["user_id"],
                turn_data,
                metadata,
                processing_time,
            )

            # Update cache metrics
            cache_stats = self.context_cache.get_cache_stats()
            self.quality_metrics.update_cache_metrics(cache_stats)

            return ChatResponse(
                response=response,
                context_used=metadata.get("context_used", []),
                metadata={
                    "processing_time": processing_time,
                    "confidence_level": metadata.get("confidence_level", "medium"),
                    "cache_hit": cached_result is not None,
                },
            )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)

            # Track error
            await self.quality_metrics.track_conversation_turn(
                session_id,
                {
                    "query": message.content,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "response_time": time.time() - start_time,
                },
            )

            raise

    async def _get_session_data(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get session data from Redis"""

        session_key = f"session:{session_id}"
        data = await self.redis_client.get(session_key)

        if data:
            return json.loads(data)
        return None

    async def _save_session_data(self, session_id: str, session_data: dict[str, Any]):
        """Save session data to Redis"""

        session_key = f"session:{session_id}"
        await self.redis_client.setex(
            session_key,
            86400,  # 24 hour TTL
            json.dumps(session_data),
        )

    async def _save_turn_to_db(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        metadata: dict[str, Any],
        db: AsyncSession,
    ):
        """Save conversation turn to database"""

        turn = ChatTurnDB(
            session_id=session_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context_used=metadata.get("context_used", []),
            retrieval_strategy=metadata.get("retrieval_strategy", "agentic"),
            metadata=metadata,
        )

        db.add(turn)
        await db.commit()

    async def _track_conversation_metrics(
        self,
        session_id: str,
        user_id: str,
        turn_data: dict[str, Any],
        metadata: dict[str, Any],
        processing_time: float,
    ):
        """Track conversation metrics for quality monitoring"""

        # Extract metrics from metadata
        sufficiency_score = None
        if "sufficiency_evaluation" in metadata:
            sufficiency_score = metadata["sufficiency_evaluation"].get("score")

        expansion_attempts = 0
        for key in metadata:
            if key.startswith("expansion_attempt_"):
                expansion_attempts += 1

        # Track turn metrics
        await self.quality_metrics.track_conversation_turn(
            session_id,
            {
                "user_id": user_id,
                "query": turn_data["user_message"],
                "response": turn_data["assistant_response"],
                "response_time": processing_time,
                "sufficiency_score": sufficiency_score,
                "expansion_attempts": expansion_attempts,
                "context_size": metadata.get("context_size", 0),
                "tokens_used": metadata.get("tokens_used", 0),
                "confidence_level": metadata.get("confidence_level", "unknown"),
                "intent": metadata.get("analysis", {}).get("intent", "unknown"),
            },
        )

    async def process_user_feedback(self, session_id: str, feedback: dict[str, Any]):
        """Process explicit user feedback"""

        await self.quality_metrics.track_user_feedback(session_id, feedback)

        # Trigger learning if we have enough feedback
        learning_items = []
        while not self.quality_metrics.feedback_queue.empty():
            try:
                item = await self.quality_metrics.feedback_queue.get()
                learning_items.append(item)
            except Exception:
                break

        if len(learning_items) >= self.learning_optimizer.batch_size:
            # Process feedback batch
            optimization_result = await self.learning_optimizer.process_feedback_batch(
                learning_items
            )

            # Apply new parameters
            if optimization_result["status"] == "updated":
                self._apply_optimized_parameters(optimization_result["new_params"])

    async def get_session_metrics(self, session_id: str) -> dict[str, Any]:
        """Get metrics for a specific session"""
        return self.quality_metrics.get_session_metrics(session_id)

    async def get_system_metrics(self) -> dict[str, Any]:
        """Get overall system metrics"""

        # Get quality metrics
        quality_metrics = self.quality_metrics.get_system_metrics()

        # Get cache metrics
        cache_metrics = self.context_cache.get_cache_stats()

        # Get learning metrics
        learning_summary = self.learning_optimizer.get_performance_summary()

        # Update performance trends
        await self.learning_optimizer.analyze_performance_trends(quality_metrics)

        return {
            "quality": quality_metrics,
            "cache": cache_metrics,
            "learning": learning_summary,
            "current_parameters": await self.learning_optimizer.get_optimized_parameters(),
        }

    async def export_analytics(self) -> dict[str, Any]:
        """Export comprehensive analytics data"""

        return {
            "metrics": await self.quality_metrics.export_metrics_for_analysis(),
            "learning": await self.learning_optimizer.export_learning_data(),
            "system_state": {
                "cache_stats": self.context_cache.get_cache_stats(),
                "active_sessions": await self._count_active_sessions(),
            },
        }

    async def _count_active_sessions(self) -> int:
        """Count active sessions in Redis"""

        cursor = 0
        count = 0

        while True:
            cursor, keys = await self.redis_client.scan(
                cursor, match="session:*", count=100
            )
            count += len(keys)

            if cursor == 0:
                break

        return count
