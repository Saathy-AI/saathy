"""Integration tests for the streaming and intelligence pipeline."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.saathy.intelligence.action_generator import ActionGenerator
from src.saathy.intelligence.context_synthesizer import ContextSynthesizer
from src.saathy.streaming.event_correlator import EventCorrelator
from src.saathy.streaming.event_manager import EventManager
from src.saathy.streaming.models.events import EventType, GitHubEvent, SlackEvent


@pytest.fixture
def mock_redis_for_integration():
    """Create a mock Redis client for integration tests."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)

    # Storage
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock()

    # Event queuing
    redis_mock.lpush = AsyncMock()
    redis_mock.brpop = AsyncMock()

    # User timelines and platform indexes
    redis_mock.zadd = AsyncMock()
    redis_mock.zrangebyscore = AsyncMock()
    redis_mock.zrevrange = AsyncMock()

    # Counters
    redis_mock.incr = AsyncMock()
    redis_mock.expire = AsyncMock()

    return redis_mock


@pytest.fixture
def mock_openai_for_integration():
    """Create a mock OpenAI client for integration tests."""
    openai_mock = AsyncMock()

    # Context validation response
    validation_response = MagicMock()
    validation_response.choices[0].message.content = json.dumps(
        {
            "sufficient": True,
            "reasoning": "Context has cross-platform activity with specific PR and security keywords",
        }
    )

    # Action generation response
    action_response = MagicMock()
    action_response.choices[0].message.content = json.dumps(
        {
            "actions": [
                {
                    "title": "Review PR #456 for security vulnerability in auth module",
                    "description": "Review the pull request that addresses a critical security vulnerability in the authentication module, triggered by urgent discussion in #eng-alerts",
                    "priority": "urgent",
                    "action_type": "review",
                    "reasoning": "Security vulnerability requires immediate attention based on Slack discussion and GitHub PR activity",
                    "estimated_time_minutes": 20,
                    "related_people": ["alice", "bob"],
                    "action_links": [],
                }
            ]
        }
    )

    openai_mock.chat.completions.create.side_effect = [
        validation_response,
        action_response,
    ]

    return openai_mock


class TestStreamingIntelligencePipeline:
    """Integration tests for the complete pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_slack_github_correlation_and_action_generation(
        self, mock_redis_for_integration, mock_openai_for_integration
    ):
        """Test complete pipeline from events to actions."""

        # Setup components
        with patch("redis.asyncio.from_url", return_value=mock_redis_for_integration):
            event_manager = EventManager()
            event_correlator = EventCorrelator()
            context_synthesizer = ContextSynthesizer()
            action_generator = ActionGenerator(openai_api_key="test_key")

            # Initialize components
            await event_manager.initialize()
            await event_correlator.initialize()
            await context_synthesizer.initialize()

            # Setup mocks
            event_manager.redis = mock_redis_for_integration
            event_correlator.redis = mock_redis_for_integration
            context_synthesizer.redis = mock_redis_for_integration
            action_generator.redis = mock_redis_for_integration
            action_generator.openai_client = mock_openai_for_integration
            action_generator.context_synthesizer = context_synthesizer

            # Create test events
            base_time = datetime.now()

            slack_event = SlackEvent(
                event_id="slack_urgent_123",
                event_type=EventType.SLACK_MESSAGE,
                timestamp=base_time,
                user_id="user123",
                platform="slack",
                raw_data={
                    "channel": "C123",
                    "text": "Urgent: need review of PR #456 - security vuln!",
                },
                channel_id="C123456",
                channel_name="eng-alerts",
                message_text="Urgent: need review of PR #456 - security vulnerability in auth module!",
                keywords=["urgent", "review", "security"],
                project_context="saathy-core",
                urgency_score=0.9,
                mentioned_users=["alice", "bob"],
            )

            github_event = GitHubEvent(
                event_id="github_pr_456",
                event_type=EventType.GITHUB_PR,
                timestamp=base_time - timedelta(minutes=5),
                user_id="user123",
                platform="github",
                raw_data={"pull_request": {"number": 456}},
                repository="company/saathy-core",
                action="opened",
                pr_number=456,
                branch="security/auth-fix",
                keywords=["security", "auth", "fix"],
                project_context="saathy-core",
                urgency_score=0.7,
            )

            # Step 1: Process events through event manager
            await event_manager.process_event(slack_event)
            await event_manager.process_event(github_event)

            # Verify events were stored and queued
            assert (
                mock_redis_for_integration.setex.call_count >= 2
            )  # Both events stored
            assert (
                mock_redis_for_integration.lpush.call_count >= 2
            )  # Both events queued

            # Step 2: Mock correlation data for event correlator
            correlation_data = {
                "event_id": "slack_urgent_123",
                "timestamp": base_time.isoformat(),
                "user_id": "user123",
                "platform": "slack",
                "keywords": ["urgent", "review", "security"],
                "project_context": "saathy-core",
                "urgency_score": 0.9,
            }

            # Mock finding related events
            mock_redis_for_integration.zrangebyscore.return_value = [
                b"slack_urgent_123",
                b"github_pr_456",
            ]
            mock_redis_for_integration.get.side_effect = [
                json.dumps(
                    {
                        "event_id": "github_pr_456",
                        "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
                        "platform": "github",
                        "keywords": ["security", "auth", "fix"],
                        "project_context": "saathy-core",
                        "urgency_score": 0.7,
                        "repository": "company/saathy-core",
                        "pr_number": 456,
                    }
                )
            ]

            # Process correlation
            await event_correlator.process_event_correlation(correlation_data)

            # Verify correlation group was created and action generation triggered
            correlation_calls = [
                call
                for call in mock_redis_for_integration.setex.call_args_list
                if "correlation:" in str(call[0][0])
            ]
            assert len(correlation_calls) >= 1

            action_queue_calls = [
                call
                for call in mock_redis_for_integration.lpush.call_args_list
                if "saathy:action_generation" in str(call[0][0])
            ]
            assert len(action_queue_calls) >= 1

            # Step 3: Mock context synthesis
            correlation_id = "corr_user123_test"
            mock_correlation_data = {
                "correlation_id": correlation_id,
                "user_id": "user123",
                "primary_event": {
                    "event_id": "slack_urgent_123",
                    "platform": "slack",
                    "event_type": "slack_message",
                    "timestamp": base_time.isoformat(),
                    "keywords": ["urgent", "review", "security"],
                    "project_context": "saathy-core",
                    "urgency_score": 0.9,
                    "channel_name": "eng-alerts",
                    "message_text": "Urgent: need review of PR #456 - security vulnerability in auth module!",
                },
                "related_events": [
                    {
                        "event_id": "github_pr_456",
                        "platform": "github",
                        "event_type": "github_pr",
                        "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
                        "keywords": ["security", "auth", "fix"],
                        "project_context": "saathy-core",
                        "urgency_score": 0.7,
                        "repository": "company/saathy-core",
                        "pr_number": 456,
                        "similarity_score": 0.85,
                    }
                ],
            }

            # Mock Redis get for correlation data
            mock_redis_for_integration.get.return_value = json.dumps(
                mock_correlation_data
            )

            # Synthesize context
            context_bundle = await context_synthesizer.synthesize_context(
                correlation_id
            )

            # Verify context synthesis
            assert context_bundle is not None
            assert context_bundle.correlation_id == correlation_id
            assert context_bundle.user_id == "user123"
            assert len(context_bundle.related_events) == 1
            assert "security" in context_bundle.synthesized_context.lower()
            assert len(context_bundle.key_insights) > 0
            assert len(context_bundle.urgency_signals) > 0

            # Step 4: Generate actions
            # Mock daily limits check
            mock_redis_for_integration.get.return_value = "5"  # Within daily limit

            actions = await action_generator.generate_actions_for_correlation(
                correlation_id
            )

            # Verify actions were generated
            assert len(actions) == 1
            action = actions[0]
            assert "PR #456" in action.title
            assert "security" in action.description.lower()
            assert action.priority.value == "urgent"
            assert action.action_type.value == "review"
            assert action.user_id == "user123"
            assert action.correlation_id == correlation_id

            # Verify action was stored and added to user queue
            action_store_calls = [
                call
                for call in mock_redis_for_integration.setex.call_args_list
                if "action:" in str(call[0][0])
            ]
            assert len(action_store_calls) >= 1

            user_queue_calls = [
                call
                for call in mock_redis_for_integration.zadd.call_args_list
                if f"user:{action.user_id}:actions" in str(call[0][0])
            ]
            assert len(user_queue_calls) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_with_insufficient_context(
        self, mock_redis_for_integration, mock_openai_for_integration
    ):
        """Test pipeline behavior when context is insufficient for action generation."""

        with patch("redis.asyncio.from_url", return_value=mock_redis_for_integration):
            context_synthesizer = ContextSynthesizer()
            action_generator = ActionGenerator(openai_api_key="test_key")

            await context_synthesizer.initialize()

            context_synthesizer.redis = mock_redis_for_integration
            action_generator.redis = mock_redis_for_integration
            action_generator.context_synthesizer = context_synthesizer

            # Mock insufficient context validation
            insufficient_response = MagicMock()
            insufficient_response.choices[0].message.content = json.dumps(
                {
                    "sufficient": False,
                    "reasoning": "Context lacks specific details and cross-platform correlation",
                }
            )

            mock_openai_client = AsyncMock()
            mock_openai_client.chat.completions.create.return_value = (
                insufficient_response
            )
            action_generator.openai_client = mock_openai_client

            # Mock weak correlation data
            correlation_id = "corr_weak_context"
            weak_correlation_data = {
                "correlation_id": correlation_id,
                "user_id": "user123",
                "primary_event": {
                    "event_id": "weak_event",
                    "platform": "slack",
                    "timestamp": datetime.now().isoformat(),
                    "keywords": [],
                    "urgency_score": 0.1,
                },
                "related_events": [],
            }

            mock_redis_for_integration.get.return_value = json.dumps(
                weak_correlation_data
            )

            # Generate actions with insufficient context
            actions = await action_generator.generate_actions_for_correlation(
                correlation_id
            )

            # Should return empty list due to insufficient context
            assert actions == []

    @pytest.mark.asyncio
    async def test_pipeline_with_daily_limit_exceeded(
        self, mock_redis_for_integration, mock_openai_for_integration
    ):
        """Test pipeline behavior when daily action limit is exceeded."""

        with patch("redis.asyncio.from_url", return_value=mock_redis_for_integration):
            context_synthesizer = ContextSynthesizer()
            action_generator = ActionGenerator(openai_api_key="test_key")

            await context_synthesizer.initialize()

            context_synthesizer.redis = mock_redis_for_integration
            action_generator.redis = mock_redis_for_integration
            action_generator.context_synthesizer = context_synthesizer
            action_generator.openai_client = mock_openai_for_integration

            # Mock daily limit exceeded
            mock_redis_for_integration.get.return_value = "25"  # Over limit of 20

            # Mock good correlation data
            correlation_id = "corr_limit_test"
            good_correlation_data = {
                "correlation_id": correlation_id,
                "user_id": "user123",
                "primary_event": {
                    "event_id": "test_event",
                    "platform": "slack",
                    "timestamp": datetime.now().isoformat(),
                    "keywords": ["urgent"],
                    "urgency_score": 0.8,
                },
                "related_events": [
                    {
                        "event_id": "related_event",
                        "platform": "github",
                        "similarity_score": 0.7,
                    }
                ],
            }

            mock_redis_for_integration.get.return_value = json.dumps(
                good_correlation_data
            )

            # Generate actions with limit exceeded
            actions = await action_generator.generate_actions_for_correlation(
                correlation_id
            )

            # Should return empty list due to daily limit
            assert actions == []

    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(self, mock_redis_for_integration):
        """Test error handling throughout the pipeline."""

        with patch("redis.asyncio.from_url", return_value=mock_redis_for_integration):
            event_manager = EventManager()
            event_correlator = EventCorrelator()

            await event_manager.initialize()
            await event_correlator.initialize()

            event_manager.redis = mock_redis_for_integration
            event_correlator.redis = mock_redis_for_integration

            # Test error in event processing
            mock_redis_for_integration.setex.side_effect = Exception("Redis error")

            slack_event = SlackEvent(
                event_id="error_test",
                event_type=EventType.SLACK_MESSAGE,
                timestamp=datetime.now(),
                user_id="user123",
                platform="slack",
                raw_data={},
                channel_id="C123",
                channel_name="test",
            )

            # Should not raise exception
            await event_manager.process_event(slack_event)

            # Reset Redis mock
            mock_redis_for_integration.setex.side_effect = None
            mock_redis_for_integration.setex = AsyncMock()

            # Test error in correlation processing
            mock_redis_for_integration.zrangebyscore.side_effect = Exception(
                "Correlation error"
            )

            correlation_data = {
                "event_id": "test_event",
                "user_id": "user123",
                "timestamp": datetime.now().isoformat(),
                "platform": "slack",
            }

            # Should not raise exception
            await event_correlator.process_event_correlation(correlation_data)
