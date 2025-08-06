"""Test cases for the event manager."""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.saathy.streaming.event_manager import EventManager
from src.saathy.streaming.models.events import SlackEvent, EventType


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock()
    redis_mock.zadd = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.lpush = AsyncMock()
    redis_mock.zrangebyscore = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.brpop = AsyncMock()
    return redis_mock


@pytest.fixture
def event_manager(mock_redis):
    """Create an EventManager with mocked Redis."""
    with patch('redis.asyncio.from_url', return_value=mock_redis):
        manager = EventManager()
        manager.redis = mock_redis
        return manager


@pytest.fixture
def sample_slack_event():
    """Create a sample SlackEvent for testing."""
    return SlackEvent(
        event_id="slack_test_123",
        event_type=EventType.SLACK_MESSAGE,
        timestamp=datetime.now(),
        user_id="U123456",
        platform="slack",
        raw_data={"channel": "C123", "text": "Hello world"},
        channel_id="C123456",
        channel_name="general",
        message_text="Hello world",
        keywords=["greeting"],
        urgency_score=0.3,
    )


class TestEventManager:
    """Test EventManager functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_redis):
        """Test EventManager initialization."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            manager = EventManager()
            await manager.initialize()
            
            mock_redis.ping.assert_called_once()
            assert manager.redis is not None

    @pytest.mark.asyncio
    async def test_process_event(self, event_manager, mock_redis, sample_slack_event):
        """Test processing an event."""
        await event_manager.process_event(sample_slack_event)
        
        # Verify event was stored
        mock_redis.setex.assert_called()
        store_call = mock_redis.setex.call_args
        assert store_call[0][0] == f"event:{sample_slack_event.event_id}"
        assert store_call[0][1] == 30 * 24 * 60 * 60  # 30 days
        
        # Verify event was added to user timeline
        mock_redis.zadd.assert_called()
        
        # Verify event was queued for correlation
        mock_redis.lpush.assert_called()

    @pytest.mark.asyncio
    async def test_store_event(self, event_manager, mock_redis, sample_slack_event):
        """Test event storage functionality."""
        await event_manager.store_event(sample_slack_event)
        
        # Check that setex was called for event storage
        event_key = f"event:{sample_slack_event.event_id}"
        mock_redis.setex.assert_any_call(
            event_key, 
            30 * 24 * 60 * 60, 
            sample_slack_event.model_dump_json()
        )
        
        # Check user timeline update
        timeline_key = f"user:{sample_slack_event.user_id}:events"
        mock_redis.zadd.assert_any_call(
            timeline_key,
            {sample_slack_event.event_id: sample_slack_event.timestamp.timestamp()}
        )
        
        # Check platform index update
        platform_key = f"platform:{sample_slack_event.platform}:events"
        mock_redis.zadd.assert_any_call(
            platform_key,
            {sample_slack_event.event_id: sample_slack_event.timestamp.timestamp()}
        )

    @pytest.mark.asyncio
    async def test_queue_for_correlation(self, event_manager, mock_redis, sample_slack_event):
        """Test queuing event for correlation."""
        await event_manager.queue_for_correlation(sample_slack_event)
        
        # Verify lpush was called with correct queue and data
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        
        assert call_args[0][0] == "saathy:events"
        correlation_data = json.loads(call_args[0][1])
        
        assert correlation_data["event_id"] == sample_slack_event.event_id
        assert correlation_data["user_id"] == sample_slack_event.user_id
        assert correlation_data["platform"] == sample_slack_event.platform
        assert correlation_data["keywords"] == sample_slack_event.keywords

    @pytest.mark.asyncio
    async def test_get_recent_events(self, event_manager, mock_redis):
        """Test retrieving recent events for a user."""
        user_id = "test_user"
        
        # Mock Redis responses
        mock_redis.zrangebyscore.return_value = [b"event1", b"event2"]
        mock_redis.get.side_effect = [
            json.dumps({"event_id": "event1", "platform": "slack"}),
            json.dumps({"event_id": "event2", "platform": "github"}),
        ]
        
        events = await event_manager.get_recent_events(user_id, hours=2)
        
        # Verify correct Redis calls
        timeline_key = f"user:{user_id}:events"
        mock_redis.zrangebyscore.assert_called()
        assert mock_redis.get.call_count == 2
        
        # Verify returned events
        assert len(events) == 2
        assert events[0]["event_id"] == "event1"
        assert events[1]["event_id"] == "event2"

    @pytest.mark.asyncio
    async def test_get_event_by_id(self, event_manager, mock_redis):
        """Test retrieving a specific event by ID."""
        event_id = "test_event_123"
        event_data = {"event_id": event_id, "platform": "slack"}
        
        mock_redis.get.return_value = json.dumps(event_data)
        
        result = await event_manager.get_event_by_id(event_id)
        
        mock_redis.get.assert_called_once_with(f"event:{event_id}")
        assert result == event_data

    @pytest.mark.asyncio
    async def test_get_event_by_id_not_found(self, event_manager, mock_redis):
        """Test retrieving non-existent event."""
        mock_redis.get.return_value = None
        
        result = await event_manager.get_event_by_id("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_platform_events(self, event_manager, mock_redis):
        """Test retrieving events for a specific platform."""
        platform = "github"
        
        mock_redis.zrangebyscore.return_value = [b"event1", b"event2"]
        mock_redis.get.side_effect = [
            json.dumps({"event_id": "event1", "platform": "github"}),
            json.dumps({"event_id": "event2", "platform": "github"}),
        ]
        
        events = await event_manager.get_platform_events(platform, hours=24)
        
        platform_key = f"platform:{platform}:events"
        mock_redis.zrangebyscore.assert_called()
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_get_user_stats(self, event_manager, mock_redis):
        """Test getting user activity statistics."""
        user_id = "test_user"
        
        # Mock Redis responses
        mock_redis.zcount.return_value = 15
        mock_redis.zrangebyscore.return_value = [b"event1", b"event2", b"event3"]
        mock_redis.get.side_effect = [
            json.dumps({"platform": "slack"}),
            json.dumps({"platform": "github"}),
            json.dumps({"platform": "slack"}),
        ]
        
        stats = await event_manager.get_user_stats(user_id, days=7)
        
        assert stats["user_id"] == user_id
        assert stats["days"] == 7
        assert stats["total_events"] == 15
        assert stats["platform_breakdown"]["slack"] == 2
        assert stats["platform_breakdown"]["github"] == 1
        assert stats["most_active_platform"] == "slack"

    @pytest.mark.asyncio
    async def test_correlation_processor_loop(self, event_manager, mock_redis):
        """Test the correlation processor background task."""
        # Mock Redis brpop to return an event then None
        mock_redis.brpop.side_effect = [
            (b"saathy:events", b'{"event_id": "test", "user_id": "user1"}'),
            None  # Simulates timeout
        ]
        
        # Mock correlator
        event_manager.correlator = AsyncMock()
        event_manager.correlator.process_event_correlation = AsyncMock()
        
        # Run one iteration of the processor
        with patch('asyncio.sleep', new_callable=AsyncMock):
            try:
                await asyncio.wait_for(
                    event_manager.start_correlation_processor(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                pass  # Expected since this runs indefinitely
        
        # Verify correlation processing was called
        event_manager.correlator.process_event_correlation.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_events(self, event_manager, mock_redis):
        """Test cleanup of old events."""
        # Mock keys and zremrangebyscore
        mock_redis.keys.side_effect = [
            [b"user:1:events", b"user:2:events"],  # User timeline keys
            [b"platform:slack:events", b"platform:github:events"]  # Platform keys
        ]
        mock_redis.zremrangebyscore = AsyncMock()
        
        await event_manager.cleanup_old_events()
        
        # Verify cleanup was called for user timelines and platform indexes
        assert mock_redis.zremrangebyscore.call_count == 4  # 2 users + 2 platforms

    @pytest.mark.asyncio
    async def test_error_handling_in_process_event(self, event_manager, mock_redis, sample_slack_event):
        """Test error handling in process_event."""
        # Make store_event fail
        mock_redis.setex.side_effect = Exception("Redis error")
        
        # Should not raise exception
        await event_manager.process_event(sample_slack_event)
        
        # Verify error was logged (in real implementation)
        # This would require a logging mock to verify

    @pytest.mark.asyncio
    async def test_redis_not_initialized_error(self):
        """Test error handling when Redis is not initialized."""
        manager = EventManager()
        # Don't initialize Redis
        
        events = await manager.get_recent_events("user1")
        assert events == []  # Should return empty list on error