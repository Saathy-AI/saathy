"""
Integration tests for the Agentic Chat Service
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import json

from app.services.agentic_chat_service import AgenticChatService
from app.models.chat_session import ChatSession, ConversationTurn, ChatMessage


@pytest.mark.integration
class TestAgenticChatServiceIntegration:
    """Integration tests for the complete agentic chat service"""
    
    @pytest.fixture
    async def service(self):
        """Create service with test configuration"""
        config = {
            "openai_api_key": "test-key",
            "max_expansion_attempts": 2,
            "sufficiency_threshold": 0.7,
            "rrf_k": 60,
            "enable_caching": True,
            "enable_learning": True
        }
        
        service = AgenticChatService(config)
        await service.initialize()
        return service
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        
        # Mock session retrieval
        mock_session = Mock(spec=ChatSession)
        mock_session.id = "test-session"
        mock_session.user_id = "test-user"
        mock_session.conversation_turns = []
        
        db.query.return_value.filter.return_value.first.return_value = mock_session
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        return db
    
    @pytest.mark.asyncio
    async def test_complete_message_flow_with_caching(self, service, mock_db):
        """Test complete message processing flow with caching"""
        
        # Mock LangGraph orchestration
        with patch.object(service.orchestration_graph, 'process_message') as mock_process:
            mock_process.return_value = {
                "response": "Based on the data, Project X is on track.",
                "context_used": [
                    {"platform": "github", "preview": "PR merged"},
                    {"platform": "slack", "preview": "Team update"}
                ],
                "metadata": {
                    "processing_time": 1.2,
                    "confidence_level": "high",
                    "sufficiency_score": 0.85,
                    "cache_hit": False
                },
                "analysis": {
                    "intent": "get_context",
                    "entities": {"projects": ["Project X"]}
                }
            }
            
            # First message - should process normally
            message1 = ChatMessage(content="Tell me about Project X")
            result1 = await service.process_message("test-session", message1, mock_db)
            
            assert result1["response"] == "Based on the data, Project X is on track."
            assert len(result1["context_used"]) == 2
            assert mock_process.call_count == 1
            
            # Same message again - should hit cache
            message2 = ChatMessage(content="Tell me about Project X")
            result2 = await service.process_message("test-session", message2, mock_db)
            
            # Should still get same response but from cache
            assert result2["response"] == result1["response"]
            assert result2["metadata"]["cache_hit"] == True
            # Process should not be called again
            assert mock_process.call_count == 1
    
    @pytest.mark.asyncio
    async def test_memory_compression_trigger(self, service, mock_db):
        """Test that memory compression triggers after threshold"""
        
        # Create session with multiple turns
        mock_session = Mock(spec=ChatSession)
        mock_session.id = "test-session"
        mock_session.user_id = "test-user"
        mock_session.conversation_turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                assistant_response=f"Response {i}",
                timestamp=datetime.utcnow()
            )
            for i in range(6)  # Above compression threshold
        ]
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        
        # Mock memory compression
        with patch.object(service.memory_manager, 'compress_conversation') as mock_compress:
            mock_compress.return_value = {
                "compressed": True,
                "memory": {
                    "user_profile": {"interests": ["Project X"]},
                    "key_events": [{"summary": "Discussed Project X"}],
                    "recent_context": []
                }
            }
            
            # Mock orchestration
            with patch.object(service.orchestration_graph, 'process_message'):
                message = ChatMessage(content="Another message")
                await service.process_message("test-session", message, mock_db)
                
                # Compression should have been called
                assert mock_compress.called
    
    @pytest.mark.asyncio
    async def test_feedback_triggers_learning(self, service, mock_db):
        """Test that user feedback triggers learning optimization"""
        
        # First create some conversation history with metrics
        service.quality_metrics.conversation_metrics["test-session"] = [
            {
                "query": "Test query",
                "response_time": 2.5,  # Slow
                "sufficiency_score": 0.6,  # Low
                "intent": "query_events"
            }
        ]
        
        # Submit feedback
        feedback = {
            "relevance_score": 0.4,  # Low satisfaction
            "completeness_score": 0.5,
            "helpful": False
        }
        
        # Mock learning optimizer
        with patch.object(service.learning_optimizer, 'process_feedback_batch') as mock_learn:
            mock_learn.return_value = {
                "status": "updated",
                "adjustments": {
                    "sufficiency_threshold": -0.05
                },
                "new_params": {
                    "sufficiency_threshold": 0.65
                }
            }
            
            await service.process_user_feedback("test-session", feedback)
            
            # Learning should have been triggered
            assert mock_learn.called
            
            # New parameters should be applied
            assert service._system_params["sufficiency_threshold"] == 0.65
    
    @pytest.mark.asyncio
    async def test_metrics_aggregation(self, service, mock_db):
        """Test that metrics are properly aggregated"""
        
        # Process multiple messages
        with patch.object(service.orchestration_graph, 'process_message') as mock_process:
            # Different response characteristics
            responses = [
                {
                    "response": "Response 1",
                    "context_used": [],
                    "metadata": {
                        "processing_time": 1.0,
                        "sufficiency_score": 0.9,
                        "expansion_attempts": 0
                    },
                    "analysis": {"intent": "query_events"}
                },
                {
                    "response": "Response 2",
                    "context_used": [],
                    "metadata": {
                        "processing_time": 2.0,
                        "sufficiency_score": 0.7,
                        "expansion_attempts": 1
                    },
                    "analysis": {"intent": "get_context"}
                }
            ]
            
            mock_process.side_effect = responses
            
            # Process messages
            for i in range(2):
                message = ChatMessage(content=f"Message {i}")
                await service.process_message("test-session", message, mock_db)
        
        # Get session metrics
        metrics = await service.get_session_metrics("test-session")
        
        assert metrics["turn_count"] == 2
        assert metrics["avg_response_time"] == 1.5
        assert metrics["avg_sufficiency_score"] == 0.8
        assert metrics["expansion_rate"] == 0.5
        assert "query_events" in metrics["intents"]
        assert "get_context" in metrics["intents"]
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, service, mock_db):
        """Test that service handles errors gracefully"""
        
        # Mock orchestration to fail first, then succeed
        with patch.object(service.orchestration_graph, 'process_message') as mock_process:
            mock_process.side_effect = [
                Exception("OpenAI API error"),
                {
                    "response": "Recovered response",
                    "context_used": [],
                    "metadata": {"error_recovery": True}
                }
            ]
            
            # First attempt should fail but be handled
            message1 = ChatMessage(content="Test message")
            result1 = await service.process_message("test-session", message1, mock_db)
            
            assert "error" in result1
            assert "sorry" in result1["response"].lower()
            
            # Second attempt should work
            message2 = ChatMessage(content="Test message again")
            result2 = await service.process_message("test-session", message2, mock_db)
            
            assert result2["response"] == "Recovered response"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_new_data(self, service, mock_db):
        """Test that cache is properly invalidated when needed"""
        
        # Cache a result
        await service.context_cache.cache_query_result(
            "Old query",
            "test-user",
            {"response": "Old cached response"}
        )
        
        # Verify it's cached
        cached = await service.context_cache.get_cached_query_result("Old query", "test-user")
        assert cached is not None
        
        # Invalidate user cache (simulating new data arrival)
        await service.context_cache.invalidate_user_cache("test-user")
        
        # Cache should be cleared
        cached_after = await service.context_cache.get_cached_query_result("Old query", "test-user")
        assert cached_after is None
    
    @pytest.mark.asyncio
    async def test_system_metrics_export(self, service, mock_db):
        """Test system metrics export functionality"""
        
        # Add some data
        service.quality_metrics.conversation_metrics["session1"] = [
            {"response_time": 1.0, "sufficiency_score": 0.8}
        ]
        service.quality_metrics.conversation_metrics["session2"] = [
            {"response_time": 1.5, "sufficiency_score": 0.9}
        ]
        
        # Get system metrics
        system_metrics = await service.get_system_metrics()
        
        assert system_metrics["quality"]["total_conversations"] >= 2
        assert system_metrics["quality"]["total_turns"] >= 2
        assert "avg_response_time" in system_metrics["quality"]
        assert "cache" in system_metrics
        assert "current_parameters" in system_metrics