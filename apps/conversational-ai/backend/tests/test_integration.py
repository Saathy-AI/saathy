"""
Integration tests for the Saathy Conversational AI system.
Tests the complete flow from user message to response.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.agentic_chat_service import AgenticChatService
from app.models.chat_session import ChatMessage, ChatSession
from app.agents.context_orchestration import ContextOrchestrationGraph


class TestConversationalAIIntegration:
    """Integration tests for the complete conversational AI pipeline"""

    @pytest.fixture
    async def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        return db

    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis connection"""
        redis = AsyncMock()
        redis.get.return_value = None
        redis.set.return_value = True
        redis.delete.return_value = True
        return redis

    @pytest.fixture
    async def mock_qdrant(self):
        """Mock Qdrant client"""
        qdrant = AsyncMock()
        qdrant.search.return_value = MagicMock(points=[])
        return qdrant

    @pytest.fixture
    async def chat_service(self, mock_db, mock_redis, mock_qdrant):
        """Create AgenticChatService with mocked dependencies"""
        service = AgenticChatService()
        service.db = mock_db
        service.redis_client = mock_redis
        service.qdrant_client = mock_qdrant
        return service

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response"""
        return {
            "choices": [
                {
                    "message": {
                        "content": "Based on the context, I can help you understand the current status. The system is functioning normally."
                    }
                }
            ],
            "usage": {"total_tokens": 150}
        }

    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self, chat_service, mock_openai_response):
        """Test complete conversation from message to response"""
        
        # Mock session creation
        session_id = str(uuid4())
        user_id = "test_user"
        
        with patch("app.agents.information_analyzer.InformationAnalyzerAgent.analyze") as mock_analyze, \
             patch("app.agents.context_retriever.ContextRetrieverAgent.retrieve") as mock_retrieve, \
             patch("app.agents.sufficiency_evaluator.SufficiencyEvaluatorAgent.evaluate") as mock_evaluate, \
             patch("app.agents.response_generator.ResponseGeneratorAgent.generate") as mock_generate, \
             patch("openai.ChatCompletion.acreate") as mock_openai:

            # Setup mocks
            mock_analyze.return_value = {
                "intent": "status_query",
                "entities": ["system", "status"],
                "time_context": "current",
                "complexity": "simple"
            }
            
            mock_retrieve.return_value = {
                "content": [{"text": "System is operational", "source": "monitoring"}],
                "events": [{"event": "system_check", "status": "ok"}],
                "actions": []
            }
            
            mock_evaluate.return_value = {
                "sufficiency_score": 0.85,
                "gaps": [],
                "is_sufficient": True
            }
            
            mock_generate.return_value = {
                "response": "The system is currently operational and all services are running normally.",
                "confidence": 0.9,
                "sources_used": ["monitoring", "system_logs"]
            }
            
            mock_openai.return_value = mock_openai_response

            # Test message processing
            message = ChatMessage(content="What's the current status of the system?")
            
            response = await chat_service.process_message(session_id, message, chat_service.db)
            
            # Assertions
            assert response is not None
            assert "operational" in response.content.lower()
            
            # Verify all agents were called
            mock_analyze.assert_called_once()
            mock_retrieve.assert_called_once()
            mock_evaluate.assert_called_once()
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_expansion_flow(self, chat_service, mock_openai_response):
        """Test context expansion when initial context is insufficient"""
        
        session_id = str(uuid4())
        
        with patch("app.agents.information_analyzer.InformationAnalyzerAgent.analyze") as mock_analyze, \
             patch("app.agents.context_retriever.ContextRetrieverAgent.retrieve") as mock_retrieve, \
             patch("app.agents.sufficiency_evaluator.SufficiencyEvaluatorAgent.evaluate") as mock_evaluate, \
             patch("app.agents.context_expander.ContextExpanderAgent.expand") as mock_expand, \
             patch("app.agents.response_generator.ResponseGeneratorAgent.generate") as mock_generate, \
             patch("openai.ChatCompletion.acreate") as mock_openai:

            # Setup mocks for insufficient initial context
            mock_analyze.return_value = {
                "intent": "complex_query",
                "entities": ["project", "auth", "bug"],
                "time_context": "yesterday",
                "complexity": "complex"
            }
            
            # Initial retrieval with insufficient context
            mock_retrieve.side_effect = [
                {
                    "content": [{"text": "Limited info", "source": "logs"}],
                    "events": [],
                    "actions": []
                },
                # After expansion
                {
                    "content": [
                        {"text": "Auth bug fixed yesterday", "source": "github"},
                        {"text": "Deployment completed", "source": "ci_cd"}
                    ],
                    "events": [{"event": "bug_fix", "timestamp": "yesterday"}],
                    "actions": [{"action": "code_review", "status": "completed"}]
                }
            ]
            
            # Sufficiency evaluation: first insufficient, then sufficient
            mock_evaluate.side_effect = [
                {
                    "sufficiency_score": 0.4,
                    "gaps": ["temporal_coverage", "platform_diversity"],
                    "is_sufficient": False
                },
                {
                    "sufficiency_score": 0.9,
                    "gaps": [],
                    "is_sufficient": True
                }
            ]
            
            mock_expand.return_value = {
                "expanded_query": "auth bug project yesterday deployment",
                "expansion_strategy": "temporal_and_platform",
                "additional_entities": ["deployment", "ci_cd"]
            }
            
            mock_generate.return_value = {
                "response": "The auth bug in the project was fixed yesterday and deployed successfully.",
                "confidence": 0.95,
                "sources_used": ["github", "ci_cd", "logs"]
            }
            
            mock_openai.return_value = mock_openai_response

            # Test message processing with expansion
            message = ChatMessage(content="What happened with the auth bug in the project yesterday?")
            
            response = await chat_service.process_message(session_id, message, chat_service.db)
            
            # Assertions
            assert response is not None
            assert "fixed" in response.content.lower()
            
            # Verify expansion was triggered
            mock_expand.assert_called_once()
            assert mock_retrieve.call_count == 2  # Initial + after expansion
            assert mock_evaluate.call_count == 2  # Before and after expansion

    @pytest.mark.asyncio
    async def test_session_management(self, chat_service):
        """Test session creation, updates, and cleanup"""
        
        user_id = "test_user"
        
        # Test session creation
        session = await chat_service.create_session(user_id, chat_service.db)
        assert session.user_id == user_id
        assert session.status == "active"
        
        # Test session retrieval
        retrieved_session = await chat_service.get_session(session.id, chat_service.db)
        assert retrieved_session.id == session.id
        
        # Test session cleanup
        await chat_service.end_session(session.id, chat_service.db)
        
        # Verify session was marked as ended
        ended_session = await chat_service.get_session(session.id, chat_service.db)
        assert ended_session.status == "ended"

    @pytest.mark.asyncio
    async def test_memory_compression(self, chat_service):
        """Test conversation memory compression"""
        
        session_id = str(uuid4())
        
        # Create multiple conversation turns
        messages = [
            ChatMessage(content="What's the weather today?"),
            ChatMessage(content="How about tomorrow?"),
            ChatMessage(content="What about the project status?"),
            ChatMessage(content="Any updates on the deployment?"),
            ChatMessage(content="When will the feature be ready?"),
            ChatMessage(content="Can you summarize what we discussed?")
        ]
        
        with patch("app.memory.compressive_memory.CompressiveMemoryManager.compress_conversation") as mock_compress:
            mock_compress.return_value = {
                "user_profile": {"topics_of_interest": ["weather", "projects", "deployment"]},
                "key_events": ["weather_query", "project_status_check"],
                "relationships": {"weather": "daily_concern", "project": "work_priority"},
                "recent_context": []
            }
            
            # Process messages to trigger compression
            for message in messages:
                await chat_service.process_message(session_id, message, chat_service.db)
            
            # Verify compression was triggered
            mock_compress.assert_called()

    @pytest.mark.asyncio
    async def test_quality_metrics_tracking(self, chat_service):
        """Test that quality metrics are properly tracked"""
        
        session_id = str(uuid4())
        
        with patch("app.metrics.quality_metrics.QualityMetrics.track_conversation_quality") as mock_track:
            # Submit feedback
            feedback = {
                "relevance_score": 0.9,
                "completeness_score": 0.8,
                "helpful": True,
                "response_time": 2.5
            }
            
            await chat_service.process_user_feedback(session_id, feedback)
            
            # Verify metrics tracking
            mock_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, chat_service):
        """Test error handling and graceful degradation"""
        
        session_id = str(uuid4())
        
        with patch("app.agents.context_retriever.ContextRetrieverAgent.retrieve") as mock_retrieve:
            # Simulate retrieval failure
            mock_retrieve.side_effect = Exception("Retrieval service unavailable")
            
            message = ChatMessage(content="What's happening?")
            
            # Should handle error gracefully
            response = await chat_service.process_message(session_id, message, chat_service.db)
            
            # Should return fallback response
            assert response is not None
            assert "unavailable" in response.content.lower() or "error" in response.content.lower()

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, chat_service):
        """Test handling multiple concurrent sessions"""
        
        user_ids = [f"user_{i}" for i in range(5)]
        
        # Create multiple sessions concurrently
        sessions = await asyncio.gather(*[
            chat_service.create_session(user_id, chat_service.db) 
            for user_id in user_ids
        ])
        
        assert len(sessions) == 5
        assert all(session.status == "active" for session in sessions)
        
        # Process messages concurrently
        messages = [
            ChatMessage(content=f"Hello from {user_id}") 
            for user_id in user_ids
        ]
        
        responses = await asyncio.gather(*[
            chat_service.process_message(sessions[i].id, messages[i], chat_service.db)
            for i in range(5)
        ])
        
        assert len(responses) == 5
        assert all(response is not None for response in responses)

    @pytest.mark.asyncio
    async def test_performance_optimization(self, chat_service):
        """Test performance optimization features"""
        
        session_id = str(uuid4())
        
        with patch("app.optimization.context_cache.ContextCache.get_cached_context") as mock_cache_get, \
             patch("app.optimization.context_cache.ContextCache.cache_context") as mock_cache_set:
            
            # First call - cache miss
            mock_cache_get.return_value = None
            
            message = ChatMessage(content="System status check")
            response1 = await chat_service.process_message(session_id, message, chat_service.db)
            
            # Should cache the result
            mock_cache_set.assert_called_once()
            
            # Second call - cache hit
            mock_cache_get.return_value = {
                "content": [{"text": "Cached system status", "source": "cache"}],
                "events": [],
                "actions": []
            }
            
            response2 = await chat_service.process_message(session_id, message, chat_service.db)
            
            # Should use cached result
            assert response2 is not None