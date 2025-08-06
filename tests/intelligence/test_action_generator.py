"""Test cases for the action generator."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.saathy.intelligence.action_generator import ActionGenerator
from src.saathy.intelligence.models.actions import (
    GeneratedAction, 
    ActionPriority, 
    ActionType, 
    ActionLink,
    ContextBundle
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.zadd = AsyncMock()
    redis_mock.incr = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.lpush = AsyncMock()
    redis_mock.brpop = AsyncMock()
    redis_mock.zrevrange = AsyncMock()
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_openai():
    """Create a mock OpenAI client."""
    openai_mock = AsyncMock()
    return openai_mock


@pytest.fixture
def mock_context_synthesizer():
    """Create a mock ContextSynthesizer."""
    synthesizer_mock = AsyncMock()
    synthesizer_mock.initialize = AsyncMock()
    synthesizer_mock.synthesize_context = AsyncMock()
    synthesizer_mock.close = AsyncMock()
    return synthesizer_mock


@pytest.fixture
def action_generator(mock_redis, mock_openai, mock_context_synthesizer):
    """Create an ActionGenerator with mocked dependencies."""
    with patch('redis.asyncio.from_url', return_value=mock_redis):
        with patch('src.saathy.intelligence.action_generator.ContextSynthesizer', return_value=mock_context_synthesizer):
            generator = ActionGenerator(
                openai_api_key="test_key",
                redis_url="redis://localhost:6379"
            )
            generator.redis = mock_redis
            generator.openai_client = mock_openai
            generator.context_synthesizer = mock_context_synthesizer
            return generator


@pytest.fixture
def sample_context_bundle():
    """Create a sample ContextBundle for testing."""
    return ContextBundle(
        correlation_id="corr_test_123",
        user_id="user123",
        primary_event={
            "event_id": "slack_msg_123",
            "platform": "slack",
            "event_type": "slack_message",
            "timestamp": datetime.now().isoformat(),
            "keywords": ["urgent", "review"],
            "project_context": "saathy-core"
        },
        related_events=[
            {
                "event_id": "github_pr_456",
                "platform": "github",
                "event_type": "github_pr",
                "pr_number": 456,
                "repository": "company/saathy"
            }
        ],
        synthesized_context="User needs urgent review of PR #456 for security vulnerability",
        key_insights=["Cross-platform activity", "Security focus"],
        urgency_signals=["High urgency score", "Security keywords"],
        platform_data={
            "slack": {"channels": ["eng-alerts"], "messages": []},
            "github": {"repos": ["company/saathy"], "prs": [{"number": 456}]}
        },
        correlation_strength=0.8,
        created_at=datetime.now()
    )


@pytest.fixture
def sample_gpt_response():
    """Create a sample GPT-4 response for action generation."""
    return {
        "actions": [
            {
                "title": "Review PR #456 for security vulnerability",
                "description": "Review the pull request addressing security vulnerability in authentication module",
                "priority": "urgent",
                "action_type": "review",
                "reasoning": "Security vulnerability requires immediate attention",
                "estimated_time_minutes": 20,
                "related_people": ["alice", "bob"],
                "action_links": []
            }
        ]
    }


class TestActionGenerator:
    """Test ActionGenerator functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_redis, mock_context_synthesizer):
        """Test ActionGenerator initialization."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            with patch('src.saathy.intelligence.action_generator.ContextSynthesizer', return_value=mock_context_synthesizer):
                generator = ActionGenerator(openai_api_key="test_key")
                await generator.initialize()
                
                mock_redis.ping.assert_called_once()
                mock_context_synthesizer.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_actions_for_correlation_success(self, action_generator, mock_context_synthesizer, sample_context_bundle, sample_gpt_response):
        """Test successful action generation for a correlation."""
        correlation_id = "corr_test_123"
        
        # Mock context synthesis
        mock_context_synthesizer.synthesize_context.return_value = sample_context_bundle
        
        # Mock daily limits check
        with patch.object(action_generator, 'check_daily_limits', return_value=True):
            # Mock context validation
            with patch.object(action_generator, 'validate_context_quality', return_value=True):
                # Mock GPT-4 action generation
                with patch.object(action_generator, 'generate_actions_with_gpt4', return_value=sample_gpt_response["actions"]):
                    # Mock action creation
                    mock_action = GeneratedAction(
                        action_id="action_123",
                        title="Test Action",
                        description="Test Description",
                        priority=ActionPriority.URGENT,
                        action_type=ActionType.REVIEW,
                        reasoning="Test reasoning",
                        context_summary="Test context",
                        user_id="user123",
                        correlation_id=correlation_id
                    )
                    with patch.object(action_generator, 'create_and_store_action', return_value=mock_action):
                        actions = await action_generator.generate_actions_for_correlation(correlation_id)
                        
                        assert len(actions) == 1
                        assert actions[0].title == "Test Action"

    @pytest.mark.asyncio
    async def test_generate_actions_no_context_bundle(self, action_generator, mock_context_synthesizer):
        """Test action generation when no context bundle is found."""
        correlation_id = "nonexistent_corr"
        
        # Mock context synthesis returning None
        mock_context_synthesizer.synthesize_context.return_value = None
        
        actions = await action_generator.generate_actions_for_correlation(correlation_id)
        
        assert actions == []

    @pytest.mark.asyncio
    async def test_check_daily_limits_within_limit(self, action_generator, mock_redis):
        """Test daily limits check when within limit."""
        user_id = "user123"
        
        # Mock Redis response - user has generated 5 actions today
        mock_redis.get.return_value = "5"
        
        result = await action_generator.check_daily_limits(user_id)
        
        assert result is True
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_daily_limits_exceeded(self, action_generator, mock_redis):
        """Test daily limits check when limit is exceeded."""
        user_id = "user123"
        
        # Mock Redis response - user has generated 25 actions today (over limit of 20)
        mock_redis.get.return_value = "25"
        
        result = await action_generator.check_daily_limits(user_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_context_quality_sufficient(self, action_generator, mock_openai, sample_context_bundle):
        """Test context quality validation when context is sufficient."""
        # Mock GPT-4 validation response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"sufficient": true, "reasoning": "Good context"}'
        mock_openai.chat.completions.create.return_value = mock_response
        
        result = await action_generator.validate_context_quality(sample_context_bundle)
        
        assert result is True
        mock_openai.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_context_quality_insufficient(self, action_generator, mock_openai, sample_context_bundle):
        """Test context quality validation when context is insufficient."""
        # Mock GPT-4 validation response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"sufficient": false, "reasoning": "Weak context"}'
        mock_openai.chat.completions.create.return_value = mock_response
        
        result = await action_generator.validate_context_quality(sample_context_bundle)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_actions_with_gpt4(self, action_generator, mock_openai, sample_context_bundle, sample_gpt_response):
        """Test GPT-4 action generation."""
        # Mock GPT-4 response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(sample_gpt_response)
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Mock action validation and enhancement
        with patch.object(action_generator, 'validate_action_data', return_value=True):
            with patch.object(action_generator, 'enhance_action_links', side_effect=lambda x, y: x):
                actions = await action_generator.generate_actions_with_gpt4(sample_context_bundle)
                
                assert len(actions) == 1
                assert actions[0]["title"] == "Review PR #456 for security vulnerability"
                assert actions[0]["priority"] == "urgent"

    def test_validate_action_data_valid(self, action_generator):
        """Test action data validation with valid data."""
        valid_action = {
            "title": "Review PR #123",
            "description": "Review the pull request for bug fixes",
            "priority": "high",
            "action_type": "review",
            "reasoning": "Bug fixes need review"
        }
        
        result = action_generator.validate_action_data(valid_action)
        
        assert result is True

    def test_validate_action_data_missing_field(self, action_generator):
        """Test action data validation with missing required field."""
        invalid_action = {
            "title": "Review PR #123",
            # Missing description
            "priority": "high",
            "action_type": "review",
            "reasoning": "Bug fixes need review"
        }
        
        result = action_generator.validate_action_data(invalid_action)
        
        assert result is False

    def test_validate_action_data_invalid_priority(self, action_generator):
        """Test action data validation with invalid priority."""
        invalid_action = {
            "title": "Review PR #123",
            "description": "Review the pull request",
            "priority": "invalid_priority",
            "action_type": "review",
            "reasoning": "Bug fixes need review"
        }
        
        result = action_generator.validate_action_data(invalid_action)
        
        assert result is False

    def test_actions_seem_generic_true(self, action_generator):
        """Test detecting generic actions."""
        generic_actions = [
            {
                "title": "Check messages",
                "description": "Look at your messages"
            },
            {
                "title": "Review code",
                "description": "Check the code"
            }
        ]
        
        result = action_generator.actions_seem_generic(generic_actions)
        
        assert result is True

    def test_actions_seem_generic_false(self, action_generator):
        """Test detecting specific actions."""
        specific_actions = [
            {
                "title": "Review PR #456 for security vulnerability",
                "description": "Review pull request addressing auth module security issue in saathy-core repository"
            }
        ]
        
        result = action_generator.actions_seem_generic(specific_actions)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_refine_generic_actions(self, action_generator, mock_openai):
        """Test refining generic actions."""
        generic_actions = [{"title": "Check messages", "description": "Look at messages"}]
        context = {"synthesized_context": "Urgent PR needs review"}
        
        refined_response = {
            "actions": [
                {
                    "title": "Review urgent PR #456 for security fix",
                    "description": "Specific action based on context",
                    "priority": "urgent",
                    "action_type": "review",
                    "reasoning": "Security issue needs immediate attention"
                }
            ]
        }
        
        # Mock GPT-4 refinement response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(refined_response)
        mock_openai.chat.completions.create.return_value = mock_response
        
        with patch.object(action_generator, 'validate_action_data', return_value=True):
            refined_actions = await action_generator.refine_generic_actions(generic_actions, context)
            
            assert len(refined_actions) == 1
            assert "PR #456" in refined_actions[0]["title"]

    @pytest.mark.asyncio
    async def test_enhance_action_links(self, action_generator):
        """Test enhancing actions with platform-specific links."""
        action = {
            "title": "Review PR #456",
            "description": "Review security fix",
            "action_links": []
        }
        
        context = {
            "platform_data": {
                "slack": {
                    "messages": [{"channel": "eng-alerts"}]
                },
                "github": {
                    "prs": [{"number": 456, "repo": "company/saathy"}],
                    "commits": [{"sha": "abc123", "repo": "company/saathy"}]
                },
                "notion": {
                    "pages": [{"title": "Security Review", "url": "https://notion.so/page123"}]
                }
            }
        }
        
        enhanced_action = await action_generator.enhance_action_links(action, context)
        
        assert "action_links" in enhanced_action
        assert len(enhanced_action["action_links"]) > 0
        
        # Check for GitHub PR link
        github_links = [link for link in enhanced_action["action_links"] if link["platform"] == "github"]
        assert len(github_links) > 0
        assert "pull/456" in github_links[0]["url"]

    @pytest.mark.asyncio
    async def test_create_and_store_action(self, action_generator, mock_redis):
        """Test creating and storing an action."""
        action_data = {
            "title": "Review PR #456",
            "description": "Review security fix",
            "priority": "urgent",
            "action_type": "review",
            "reasoning": "Security issue",
            "estimated_time_minutes": 15,
            "action_links": [],
            "related_people": []
        }
        
        correlation_id = "corr_123"
        user_id = "user123"
        
        # Mock Redis operations
        with patch.object(action_generator, 'store_action') as mock_store:
            with patch.object(action_generator, 'add_to_user_queue') as mock_queue:
                with patch.object(action_generator, 'increment_daily_counter') as mock_counter:
                    action = await action_generator.create_and_store_action(action_data, correlation_id, user_id)
                    
                    assert action is not None
                    assert isinstance(action, GeneratedAction)
                    assert action.title == "Review PR #456"
                    assert action.priority == ActionPriority.URGENT
                    assert action.user_id == user_id
                    assert action.correlation_id == correlation_id
                    
                    mock_store.assert_called_once()
                    mock_queue.assert_called_once()
                    mock_counter.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_action(self, action_generator, mock_redis):
        """Test storing an action in Redis."""
        action = GeneratedAction(
            action_id="action_123",
            title="Test Action",
            description="Test Description",
            priority=ActionPriority.HIGH,
            action_type=ActionType.REVIEW,
            reasoning="Test reasoning",
            context_summary="Test context",
            user_id="user123",
            correlation_id="corr_123"
        )
        
        await action_generator.store_action(action)
        
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"action:{action.action_id}"
        assert call_args[0][1] == 7 * 24 * 60 * 60  # 7 days

    @pytest.mark.asyncio
    async def test_add_to_user_queue(self, action_generator, mock_redis):
        """Test adding action to user queue."""
        user_id = "user123"
        action_id = "action_123"
        
        await action_generator.add_to_user_queue(user_id, action_id)
        
        mock_redis.zadd.assert_called()
        mock_redis.zremrangebyrank.assert_called()  # Cleanup old actions

    @pytest.mark.asyncio
    async def test_increment_daily_counter(self, action_generator, mock_redis):
        """Test incrementing daily action counter."""
        user_id = "user123"
        
        await action_generator.increment_daily_counter(user_id)
        
        mock_redis.incr.assert_called()
        mock_redis.expire.assert_called()

    @pytest.mark.asyncio
    async def test_get_user_actions(self, action_generator, mock_redis):
        """Test getting user actions."""
        user_id = "user123"
        
        # Mock Redis responses
        mock_redis.zrevrange.return_value = [b"action1", b"action2"]
        
        action_data = {
            "action_id": "action1",
            "title": "Test Action",
            "description": "Test Description",
            "priority": "high",
            "action_type": "review",
            "reasoning": "Test reasoning",
            "context_summary": "Test context",
            "user_id": user_id,
            "correlation_id": "corr_123",
            "generated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "status": "pending"
        }
        
        mock_redis.get.side_effect = [
            json.dumps(action_data),
            json.dumps({**action_data, "action_id": "action2"})
        ]
        
        actions = await action_generator.get_user_actions(user_id, limit=10)
        
        assert len(actions) == 2
        assert all(isinstance(action, GeneratedAction) for action in actions)

    @pytest.mark.asyncio
    async def test_start_action_generation_processor(self, action_generator, mock_redis):
        """Test the action generation processor background task."""
        correlation_id = "corr_123"
        
        # Mock Redis brpop to return a correlation ID then None
        mock_redis.brpop.side_effect = [
            (b"saathy:action_generation", correlation_id.encode()),
            None  # Simulates timeout
        ]
        
        # Mock action generation
        with patch.object(action_generator, 'generate_actions_for_correlation', return_value=[]):
            with patch.object(action_generator, 'notify_user_of_actions') as mock_notify:
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    try:
                        await asyncio.wait_for(
                            action_generator.start_action_generation_processor(),
                            timeout=0.1
                        )
                    except asyncio.TimeoutError:
                        pass  # Expected since this runs indefinitely

    @pytest.mark.asyncio
    async def test_error_handling_in_generate_actions(self, action_generator, mock_context_synthesizer):
        """Test error handling in generate_actions_for_correlation."""
        correlation_id = "error_corr"
        
        # Make context synthesis fail
        mock_context_synthesizer.synthesize_context.side_effect = Exception("Context error")
        
        actions = await action_generator.generate_actions_for_correlation(correlation_id)
        
        assert actions == []

    @pytest.mark.asyncio
    async def test_close_connections(self, action_generator, mock_redis, mock_context_synthesizer):
        """Test closing all connections."""
        await action_generator.close()
        
        mock_redis.close.assert_called_once()
        mock_context_synthesizer.close.assert_called_once()