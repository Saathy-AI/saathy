"""Test cases for the event correlator."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.saathy.streaming.event_correlator import EventCorrelator


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.zrangebyscore = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.zadd = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.lpush = AsyncMock()
    return redis_mock


@pytest.fixture
def correlator(mock_redis):
    """Create an EventCorrelator with mocked Redis."""
    with patch('redis.asyncio.from_url', return_value=mock_redis):
        correlator = EventCorrelator()
        correlator.redis = mock_redis
        return correlator


@pytest.fixture
def sample_event_data():
    """Create sample event data for testing."""
    return {
        "event_id": "test_event_123",
        "timestamp": datetime.now().isoformat(),
        "user_id": "user123",
        "platform": "slack",
        "keywords": ["urgent", "review"],
        "project_context": "saathy-core",
        "urgency_score": 0.7,
        "event_type": "slack_message"
    }


@pytest.fixture
def related_events_data():
    """Create sample related events data."""
    base_time = datetime.now()
    return [
        {
            "event_id": "github_event_456",
            "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
            "user_id": "user123",
            "platform": "github",
            "keywords": ["review", "pr"],
            "project_context": "saathy-core",
            "urgency_score": 0.5,
            "event_type": "github_pr"
        },
        {
            "event_id": "notion_event_789",
            "timestamp": (base_time - timedelta(minutes=10)).isoformat(),
            "user_id": "user123",
            "platform": "notion",
            "keywords": ["status", "update"],
            "project_context": "saathy-core",
            "urgency_score": 0.3,
            "event_type": "notion_page_update"
        }
    ]


class TestEventCorrelator:
    """Test EventCorrelator functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_redis):
        """Test EventCorrelator initialization."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            correlator = EventCorrelator()
            await correlator.initialize()
            
            mock_redis.ping.assert_called_once()
            assert correlator.redis is not None

    @pytest.mark.asyncio
    async def test_process_event_correlation_with_related_events(self, correlator, mock_redis, sample_event_data):
        """Test processing event correlation when related events exist."""
        # Mock find_related_events to return some events
        related_events = [
            {"event_id": "related1", "similarity_score": 0.8},
            {"event_id": "related2", "similarity_score": 0.6}
        ]
        
        with patch.object(correlator, 'find_related_events', return_value=related_events):
            with patch.object(correlator, 'create_correlation_group', return_value="corr_123"):
                with patch.object(correlator, 'trigger_action_generation') as mock_trigger:
                    await correlator.process_event_correlation(sample_event_data)
                    
                    mock_trigger.assert_called_once_with("corr_123")

    @pytest.mark.asyncio
    async def test_process_event_correlation_no_related_events(self, correlator, sample_event_data):
        """Test processing event correlation when no related events exist."""
        with patch.object(correlator, 'find_related_events', return_value=[]):
            with patch.object(correlator, 'create_correlation_group') as mock_create:
                await correlator.process_event_correlation(sample_event_data)
                
                mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_related_events(self, correlator, mock_redis, sample_event_data):
        """Test finding related events."""
        # Mock Redis responses
        mock_redis.zrangebyscore.return_value = [b"event1", b"event2", b"test_event_123"]
        mock_redis.get.side_effect = [
            json.dumps({
                "event_id": "event1",
                "timestamp": datetime.now().isoformat(),
                "platform": "github",
                "keywords": ["review", "urgent"],
                "project_context": "saathy-core"
            }),
            json.dumps({
                "event_id": "event2", 
                "timestamp": datetime.now().isoformat(),
                "platform": "notion",
                "keywords": ["status"],
                "project_context": "different-project"
            })
        ]
        
        related = await correlator.find_related_events(sample_event_data)
        
        # Should find at least one related event (the one with matching project context)
        assert len(related) >= 1
        assert all("similarity_score" in event for event in related)

    def test_calculate_event_similarity_same_project(self, correlator):
        """Test similarity calculation for events in same project."""
        event1 = {
            "platform": "slack",
            "project_context": "saathy-core",
            "keywords": ["urgent", "review"],
            "timestamp": datetime.now().isoformat(),
            "urgency_score": 0.7,
            "event_type": "slack_message"
        }
        
        event2 = {
            "platform": "github",
            "project_context": "saathy-core",
            "keywords": ["review", "pr"],
            "timestamp": datetime.now().isoformat(),
            "urgency_score": 0.5,
            "event_type": "github_pr"
        }
        
        score = correlator.calculate_event_similarity(event1, event2)
        
        # Should have high similarity due to same project and shared keywords
        assert score > 0.5
        assert score <= 1.0

    def test_calculate_event_similarity_different_projects(self, correlator):
        """Test similarity calculation for events in different projects."""
        event1 = {
            "platform": "slack",
            "project_context": "project-a",
            "keywords": ["urgent"],
            "timestamp": datetime.now().isoformat(),
            "urgency_score": 0.3,
            "event_type": "slack_message"
        }
        
        event2 = {
            "platform": "github",
            "project_context": "project-b",
            "keywords": ["docs"],
            "timestamp": datetime.now().isoformat(),
            "urgency_score": 0.2,
            "event_type": "github_push"
        }
        
        score = correlator.calculate_event_similarity(event1, event2)
        
        # Should have low similarity due to different projects and keywords
        assert score < 0.3

    def test_calculate_event_similarity_cross_platform_bonus(self, correlator):
        """Test cross-platform similarity bonus."""
        event1 = {
            "platform": "slack",
            "keywords": ["test"],
            "timestamp": datetime.now().isoformat(),
            "event_type": "slack_message"
        }
        
        event2 = {
            "platform": "github",
            "keywords": ["test"],
            "timestamp": datetime.now().isoformat(),
            "event_type": "github_pr"
        }
        
        score = correlator.calculate_event_similarity(event1, event2)
        
        # Should get cross-platform bonus
        assert score >= 0.2  # Minimum for cross-platform bonus

    def test_calculate_event_similarity_time_proximity(self, correlator):
        """Test time proximity bonus in similarity calculation."""
        base_time = datetime.now()
        
        event1 = {
            "platform": "slack",
            "timestamp": base_time.isoformat(),
            "keywords": ["test"],
            "event_type": "slack_message"
        }
        
        # Event 5 minutes apart
        event2 = {
            "platform": "github",
            "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
            "keywords": ["test"],
            "event_type": "github_pr"
        }
        
        score = correlator.calculate_event_similarity(event1, event2)
        
        # Should get time proximity bonus
        assert score > 0.2

    def test_calculate_event_type_correlation(self, correlator):
        """Test event type correlation bonuses."""
        # Slack message -> GitHub PR should get bonus
        score1 = correlator.calculate_event_type_correlation(
            {"event_type": "slack_message"},
            {"event_type": "github_pr"}
        )
        assert score1 == 0.15
        
        # GitHub PR -> Slack reaction should get bonus
        score2 = correlator.calculate_event_type_correlation(
            {"event_type": "github_pr"},
            {"event_type": "slack_reaction"}
        )
        assert score2 == 0.1
        
        # Unrelated types should get no bonus
        score3 = correlator.calculate_event_type_correlation(
            {"event_type": "slack_message"},
            {"event_type": "notion_page_update"}
        )
        assert score3 == 0.1  # Some bonus for slack->notion

    @pytest.mark.asyncio
    async def test_create_correlation_group(self, correlator, mock_redis, sample_event_data, related_events_data):
        """Test creating a correlation group."""
        correlation_id = await correlator.create_correlation_group(sample_event_data, related_events_data)
        
        # Verify correlation ID format
        assert correlation_id.startswith("corr_")
        assert sample_event_data["user_id"] in correlation_id
        
        # Verify Redis storage
        mock_redis.setex.assert_called()
        mock_redis.zadd.assert_called()

    def test_calculate_group_strength(self, correlator, sample_event_data, related_events_data):
        """Test calculating correlation group strength."""
        # Add similarity scores to related events
        for i, event in enumerate(related_events_data):
            event["similarity_score"] = 0.7 - (i * 0.1)
        
        strength = correlator.calculate_group_strength(sample_event_data, related_events_data)
        
        assert 0.0 <= strength <= 1.0
        assert strength > 0.5  # Should be relatively strong due to good similarity scores

    @pytest.mark.asyncio
    async def test_trigger_action_generation(self, correlator, mock_redis):
        """Test triggering action generation."""
        correlation_id = "test_correlation_123"
        
        await correlator.trigger_action_generation(correlation_id)
        
        mock_redis.lpush.assert_called_once_with("saathy:action_generation", correlation_id)

    @pytest.mark.asyncio
    async def test_get_correlation_by_id(self, correlator, mock_redis):
        """Test retrieving correlation by ID."""
        correlation_id = "test_correlation_123"
        correlation_data = {
            "correlation_id": correlation_id,
            "primary_event": {"event_id": "primary"},
            "related_events": []
        }
        
        mock_redis.get.return_value = json.dumps(correlation_data)
        
        result = await correlator.get_correlation_by_id(correlation_id)
        
        assert result == correlation_data
        mock_redis.get.assert_called_once_with(f"correlation:{correlation_id}")

    @pytest.mark.asyncio
    async def test_get_user_correlations(self, correlator, mock_redis):
        """Test getting correlations for a user."""
        user_id = "test_user"
        
        # Mock Redis responses
        mock_redis.zrangebyscore.return_value = [b"corr1", b"corr2"]
        
        # Mock get_correlation_by_id calls
        correlator.get_correlation_by_id = AsyncMock()
        correlator.get_correlation_by_id.side_effect = [
            {"correlation_id": "corr1"},
            {"correlation_id": "corr2"}
        ]
        
        correlations = await correlator.get_user_correlations(user_id, hours=24)
        
        assert len(correlations) == 2
        assert correlations[0]["correlation_id"] == "corr1"
        assert correlations[1]["correlation_id"] == "corr2"

    @pytest.mark.asyncio
    async def test_update_correlation_status(self, correlator, mock_redis):
        """Test updating correlation status."""
        correlation_id = "test_correlation"
        status = "completed"
        
        # Mock existing correlation data
        existing_data = {
            "correlation_id": correlation_id,
            "status": "pending"
        }
        
        correlator.get_correlation_by_id = AsyncMock(return_value=existing_data)
        
        await correlator.update_correlation_status(correlation_id, status)
        
        # Verify Redis update
        mock_redis.setex.assert_called()
        call_args = mock_redis.setex.call_args[0]
        stored_data = json.loads(call_args[2])
        assert stored_data["status"] == status
        assert "updated_at" in stored_data

    @pytest.mark.asyncio
    async def test_error_handling_in_process_event_correlation(self, correlator, sample_event_data):
        """Test error handling in process_event_correlation."""
        # Make find_related_events fail
        with patch.object(correlator, 'find_related_events', side_effect=Exception("Test error")):
            # Should not raise exception
            await correlator.process_event_correlation(sample_event_data)

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, correlator, mock_redis, sample_event_data):
        """Test that events below similarity threshold are filtered out."""
        # Mock events with low similarity
        mock_redis.zrangebyscore.return_value = [b"event1", b"event2"]
        mock_redis.get.side_effect = [
            json.dumps({
                "event_id": "event1",
                "timestamp": datetime.now().isoformat(),
                "platform": "different",
                "keywords": ["different"],
                "project_context": "different"
            }),
            json.dumps({
                "event_id": "event2",
                "timestamp": datetime.now().isoformat(),
                "platform": "also_different",
                "keywords": ["also_different"],
                "project_context": "also_different"
            })
        ]
        
        related = await correlator.find_related_events(sample_event_data)
        
        # Should filter out events with low similarity
        assert len(related) == 0  # No events should meet the threshold