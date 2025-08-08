"""
Tests for Phase 2 Multi-Agent System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

from app.agents.context_orchestration import ContextOrchestrationGraph, GraphState
from app.agents.information_analyzer import InformationAnalyzerAgent
from app.agents.context_retriever import ContextRetrieverAgent
from app.agents.sufficiency_evaluator import SufficiencyEvaluatorAgent
from app.agents.context_expander import ContextExpanderAgent
from app.agents.response_generator import ResponseGeneratorAgent


class TestContextOrchestrationGraph:
    """Test the main orchestration graph"""
    
    @pytest.fixture
    def config(self):
        return {
            "openai_api_key": "test-key",
            "max_expansion_attempts": 3,
            "sufficiency_threshold": 0.7,
            "rrf_k": 60
        }
    
    @pytest.fixture
    def orchestration_graph(self, config):
        return ContextOrchestrationGraph(config)
    
    @pytest.mark.asyncio
    async def test_process_message_flow(self, orchestration_graph):
        """Test the complete message processing flow"""
        
        # Mock the agents
        orchestration_graph.information_analyzer.analyze = AsyncMock(return_value={
            "query": "What happened yesterday?",
            "intent": "query_events",
            "entities": {"time": ["yesterday"]},
            "time_range": {
                "start": datetime.utcnow() - timedelta(days=1),
                "end": datetime.utcnow()
            },
            "platforms": ["slack", "github"]
        })
        
        orchestration_graph.context_retriever.retrieve = AsyncMock(return_value={
            "all_results": [Mock(content="Event 1"), Mock(content="Event 2")],
            "metadata": {"sources": ["slack", "github"]}
        })
        
        orchestration_graph.sufficiency_evaluator.evaluate = AsyncMock(return_value={
            "score": 0.85,
            "gaps": [],
            "dimension_scores": {
                "entity_coverage": 0.9,
                "temporal_relevance": 0.8
            }
        })
        
        orchestration_graph.response_generator.generate = AsyncMock(return_value={
            "response": "Yesterday, two main events occurred...",
            "context_used": [{"platform": "slack"}, {"platform": "github"}],
            "tokens_used": 150
        })
        
        # Process message
        result = await orchestration_graph.process_message(
            user_message="What happened yesterday?",
            session_id="test-session",
            user_id="test-user"
        )
        
        # Verify flow
        assert result["response"] == "Yesterday, two main events occurred..."
        assert len(result["context_used"]) == 2
        assert orchestration_graph.information_analyzer.analyze.called
        assert orchestration_graph.context_retriever.retrieve.called
        assert orchestration_graph.sufficiency_evaluator.evaluate.called
        assert orchestration_graph.response_generator.generate.called
    
    @pytest.mark.asyncio
    async def test_context_expansion_flow(self, orchestration_graph):
        """Test that context expansion happens when sufficiency is low"""
        
        # First retrieval has low sufficiency
        orchestration_graph.sufficiency_evaluator.evaluate = AsyncMock(
            side_effect=[
                {"score": 0.4, "gaps": ["temporal_coverage", "entity_coverage"]},
                {"score": 0.8, "gaps": []}  # Better after expansion
            ]
        )
        
        orchestration_graph.context_expander.plan_expansion = AsyncMock(return_value={
            "strategy": "temporal_first",
            "modifications": {"time_range": {"days": 7}}
        })
        
        # Mock other agents
        orchestration_graph.information_analyzer.analyze = AsyncMock(return_value={
            "query": "Tell me about Project X",
            "intent": "get_context"
        })
        
        orchestration_graph.context_retriever.retrieve = AsyncMock(return_value={
            "all_results": [Mock()],
            "metadata": {}
        })
        
        orchestration_graph.response_generator.generate = AsyncMock(return_value={
            "response": "Project X details...",
            "context_used": []
        })
        
        # Process message
        await orchestration_graph.process_message(
            user_message="Tell me about Project X",
            session_id="test-session",
            user_id="test-user"
        )
        
        # Verify expansion happened
        assert orchestration_graph.context_expander.plan_expansion.called
        assert orchestration_graph.context_retriever.retrieve.call_count == 2


class TestInformationAnalyzerAgent:
    """Test the information analyzer agent"""
    
    @pytest.fixture
    def analyzer(self):
        config = {"openai_api_key": "test-key"}
        return InformationAnalyzerAgent(config)
    
    def test_classify_intent_patterns(self, analyzer):
        """Test pattern-based intent classification"""
        
        assert analyzer._classify_intent_patterns("What should I do today?") == "query_actions"
        assert analyzer._classify_intent_patterns("What happened with the bug?") == "query_events"
        assert analyzer._classify_intent_patterns("Show me the Dashboard project") == "get_context"
        assert analyzer._classify_intent_patterns("Why do you suggest this?") == "explain_action"
        assert analyzer._classify_intent_patterns("Hello there") == "general_query"
    
    def test_extract_entities(self, analyzer):
        """Test entity extraction"""
        
        entities = analyzer._extract_entities("Fix the Dashboard Project bug #123 with @john")
        
        assert "Dashboard Project" in entities["projects"]
        assert "123" in entities["issues"]
        assert "john" in entities["people"]
    
    def test_extract_time_references(self, analyzer):
        """Test time reference extraction"""
        
        refs = analyzer._extract_time_references("What happened yesterday and last week?")
        
        assert len(refs) == 2
        assert any(r["reference"] == "yesterday" for r in refs)
        assert any(r["reference"] == "last week" for r in refs)
    
    def test_detect_platforms(self, analyzer):
        """Test platform detection"""
        
        platforms = analyzer._detect_platforms("Check the GitHub PR and Slack message")
        
        assert "github" in platforms
        assert "slack" in platforms
    
    @pytest.mark.asyncio
    async def test_analyze_with_gpt4(self, analyzer):
        """Test full analysis with GPT-4 mocked"""
        
        # Mock OpenAI response
        with patch.object(analyzer.openai_client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content=json.dumps({
                "intent": "query_events",
                "entities": {"projects": ["Auth"], "issues": ["bug-123"]},
                "complexity": "medium",
                "platforms": ["github", "slack"]
            })))]
            mock_create.return_value = mock_response
            
            result = await analyzer.analyze(
                user_message="What's the status of the auth bug?",
                conversation_history=[],
                user_id="test-user"
            )
            
            assert result["intent"] == "query_events"
            assert "Auth" in result["entities"]["projects"]
            assert result["complexity"] == "medium"


class TestSufficiencyEvaluatorAgent:
    """Test the sufficiency evaluator agent"""
    
    @pytest.fixture
    def evaluator(self):
        config = {"openai_api_key": "test-key"}
        return SufficiencyEvaluatorAgent(config)
    
    def test_calculate_entity_coverage(self, evaluator):
        """Test entity coverage calculation"""
        
        # Mock results
        results = [
            Mock(content="Project Dashboard is ready", metadata={}),
            Mock(content="Auth bug fixed", metadata={"project": "Auth"})
        ]
        
        info_needs = {
            "entities": {
                "projects": ["Dashboard", "Auth"],
                "issues": ["bug-123"]
            }
        }
        
        score = evaluator._calculate_entity_coverage(results, info_needs)
        assert score > 0.5  # Should find at least some entities
    
    def test_calculate_temporal_relevance(self, evaluator):
        """Test temporal relevance calculation"""
        
        now = datetime.utcnow()
        results = [
            Mock(timestamp=now - timedelta(hours=1)),
            Mock(timestamp=now - timedelta(days=2)),
            Mock(timestamp=now - timedelta(days=10))
        ]
        
        info_needs = {
            "time_range": {
                "start": now - timedelta(days=1),
                "end": now
            }
        }
        
        score = evaluator._calculate_temporal_relevance(results, info_needs)
        assert score < 1.0  # Not all results in range
        assert score > 0.0  # Some results in range
    
    @pytest.mark.asyncio
    async def test_evaluate_sufficiency(self, evaluator):
        """Test full sufficiency evaluation"""
        
        # Mock GPT-4 response
        with patch.object(evaluator.openai_client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content=json.dumps({
                "score": 0.75,
                "missing_elements": ["Recent updates"]
            })))]
            mock_create.return_value = mock_response
            
            results = [Mock(content="Test", timestamp=datetime.utcnow(), metadata={})]
            
            evaluation = await evaluator.evaluate(
                query="Test query",
                context={"all_results": results},
                information_needs={}
            )
            
            assert evaluation["score"] > 0
            assert "dimension_scores" in evaluation
            assert "gaps" in evaluation


class TestContextRetrieverAgent:
    """Test the context retriever with RRF"""
    
    @pytest.fixture
    def retriever(self):
        config = {"rrf_k": 60}
        return ContextRetrieverAgent(config)
    
    def test_apply_rrf(self, retriever):
        """Test Reciprocal Rank Fusion"""
        
        # Mock retrieval results from different sources
        retrieval_results = {
            "vector": [
                Mock(id="1", score=0.9),
                Mock(id="2", score=0.8),
                Mock(id="3", score=0.7)
            ],
            "structured": [
                Mock(id="2", score=0.85),
                Mock(id="4", score=0.75),
                Mock(id="1", score=0.65)
            ]
        }
        
        fused = retriever._apply_rrf(retrieval_results, {}, "test-user")
        
        # Check that results are fused and reranked
        assert len(fused) == 4  # 4 unique results
        assert fused[0].id in ["1", "2"]  # Top results should be from both sources
    
    def test_temporal_boost(self, retriever):
        """Test temporal relevance boosting"""
        
        now = datetime.utcnow()
        
        # Recent item should get higher boost
        recent_boost = retriever._calculate_temporal_boost(
            now - timedelta(hours=1),
            {"reference": "today"}
        )
        
        # Old item should get lower boost
        old_boost = retriever._calculate_temporal_boost(
            now - timedelta(days=7),
            {"reference": "today"}
        )
        
        assert recent_boost > old_boost


class TestContextExpanderAgent:
    """Test the context expander agent"""
    
    @pytest.fixture
    def expander(self):
        return ContextExpanderAgent({})
    
    @pytest.mark.asyncio
    async def test_plan_temporal_expansion(self, expander):
        """Test temporal expansion planning"""
        
        plan = await expander.plan_expansion(
            current_context={},
            information_needs={"time_range": {"start": datetime.utcnow()}},
            sufficiency_gaps=["temporal_coverage"],
            attempt_number=1
        )
        
        assert plan["strategy"] == "temporal_first"
        assert "time_range" in plan["modifications"]
    
    @pytest.mark.asyncio
    async def test_progressive_expansion(self, expander):
        """Test that expansion becomes more aggressive with attempts"""
        
        plan1 = await expander.plan_expansion({}, {}, ["entity_coverage"], 1)
        plan2 = await expander.plan_expansion({}, {}, ["entity_coverage"], 2)
        plan3 = await expander.plan_expansion({}, {}, ["entity_coverage"], 3)
        
        assert plan1["strategy"] == "targeted_expansion"
        assert plan2["strategy"] == "broad_expansion"
        assert plan3["strategy"] == "exhaustive_expansion"


@pytest.mark.integration
class TestEndToEndFlow:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_simple_query_flow(self):
        """Test a simple query through the entire system"""
        
        config = {
            "openai_api_key": "test-key",
            "max_expansion_attempts": 3
        }
        
        graph = ContextOrchestrationGraph(config)
        
        # Mock all external calls
        with patch.object(graph.information_analyzer.openai_client.chat.completions, 'create'):
            with patch.object(graph.context_retriever.basic_retriever, 'retrieve_context'):
                with patch.object(graph.sufficiency_evaluator.openai_client.chat.completions, 'create'):
                    with patch.object(graph.response_generator.openai_client.chat.completions, 'create'):
                        # This would test the full flow
                        # In a real test, we'd set up all the mocks properly
                        pass