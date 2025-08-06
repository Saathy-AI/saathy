"""Shared pytest configuration and fixtures."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client with common methods."""
    redis_mock = AsyncMock()
    
    # Connection methods
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    
    # Storage methods
    redis_mock.get = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    
    # List methods
    redis_mock.lpush = AsyncMock()
    redis_mock.rpush = AsyncMock()
    redis_mock.lpop = AsyncMock()
    redis_mock.rpop = AsyncMock()
    redis_mock.brpop = AsyncMock()
    redis_mock.llen = AsyncMock()
    
    # Sorted set methods
    redis_mock.zadd = AsyncMock()
    redis_mock.zrem = AsyncMock()
    redis_mock.zrange = AsyncMock()
    redis_mock.zrevrange = AsyncMock()
    redis_mock.zrangebyscore = AsyncMock()
    redis_mock.zremrangebyrank = AsyncMock()
    redis_mock.zcount = AsyncMock()
    
    # Key operations
    redis_mock.keys = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.incr = AsyncMock()
    redis_mock.decr = AsyncMock()
    
    return redis_mock


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    openai_mock = AsyncMock()
    
    # Mock chat completions
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"test": "response"}'
    
    openai_mock.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return openai_mock


@pytest.fixture
def sample_timestamp():
    """Return a consistent timestamp for testing."""
    return datetime(2023, 12, 1, 12, 0, 0)


@pytest.fixture
def sample_user_id():
    """Return a sample user ID for testing."""
    return "user_test_123"


@pytest.fixture
def sample_correlation_id():
    """Return a sample correlation ID for testing."""
    return "corr_test_456"


@pytest.fixture
def sample_event_id():
    """Return a sample event ID for testing."""
    return "event_test_789"
