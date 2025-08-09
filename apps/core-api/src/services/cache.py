"""Cache service implementation using Redis."""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio.client import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching operations using Redis."""
    
    def __init__(
        self,
        host: str,
        port: int,
        password: Optional[str] = None,
        db: int = 0,
        decode_responses: bool = True,
        max_connections: int = 10,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.decode_responses = decode_responses
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self._client: Optional[Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            logger.info(f"Connecting to Redis at {self.host}:{self.port}")
            
            # Create connection pool
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=self.decode_responses,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
            )
            
            # Create client
            self._client = redis.Redis(connection_pool=pool)
            
            # Test connection
            await self._client.ping()
            
            # Initialize pubsub
            self._pubsub = self._client.pubsub()
            
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        if not self._client:
            return False
        
        try:
            response = await self._client.ping()
            return response is True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            value = await self._client.get(key)
            
            # Try to deserialize JSON
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
        except RedisError as e:
            logger.error(f"Error getting key {key}: {e}")
            raise
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        """
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            # Serialize complex objects to JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            # Set with optional TTL
            if ttl:
                result = await self._client.setex(
                    key, ttl, value
                )
            else:
                result = await self._client.set(
                    key, value, nx=nx, xx=xx
                )
            
            return bool(result)
        except RedisError as e:
            logger.error(f"Error setting key {key}: {e}")
            raise
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            return await self._client.delete(*keys)
        except RedisError as e:
            logger.error(f"Error deleting keys {keys}: {e}")
            raise
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            return await self._client.exists(*keys)
        except RedisError as e:
            logger.error(f"Error checking keys {keys}: {e}")
            raise
    
    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set expiration for a key."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            return await self._client.expire(key, ttl)
        except RedisError as e:
            logger.error(f"Error setting expiration for key {key}: {e}")
            raise
    
    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple values."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            values = await self._client.mget(keys)
            
            # Try to deserialize JSON values
            result = []
            for value in values:
                if value and isinstance(value, str):
                    try:
                        result.append(json.loads(value))
                    except json.JSONDecodeError:
                        result.append(value)
                else:
                    result.append(value)
            
            return result
        except RedisError as e:
            logger.error(f"Error getting multiple keys: {e}")
            raise
    
    async def mset(self, mapping: Dict[str, Any]) -> bool:
        """Set multiple values."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            # Serialize complex values
            processed = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    processed[key] = json.dumps(value)
                else:
                    processed[key] = value
            
            return await self._client.mset(processed)
        except RedisError as e:
            logger.error(f"Error setting multiple keys: {e}")
            raise
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            return await self._client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Error incrementing key {key}: {e}")
            raise
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a counter."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            return await self._client.decrby(key, amount)
        except RedisError as e:
            logger.error(f"Error decrementing key {key}: {e}")
            raise
    
    # List operations
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of a list."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            # Serialize complex values
            processed = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed.append(json.dumps(value))
                else:
                    processed.append(value)
            
            return await self._client.lpush(key, *processed)
        except RedisError as e:
            logger.error(f"Error pushing to list {key}: {e}")
            raise
    
    async def rpop(self, key: str) -> Optional[Any]:
        """Pop value from the right of a list."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            value = await self._client.rpop(key)
            
            # Try to deserialize JSON
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
        except RedisError as e:
            logger.error(f"Error popping from list {key}: {e}")
            raise
    
    async def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        """Get range of values from a list."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            values = await self._client.lrange(key, start, stop)
            
            # Try to deserialize JSON values
            result = []
            for value in values:
                if isinstance(value, str):
                    try:
                        result.append(json.loads(value))
                    except json.JSONDecodeError:
                        result.append(value)
                else:
                    result.append(value)
            
            return result
        except RedisError as e:
            logger.error(f"Error getting list range {key}: {e}")
            raise
    
    # Pub/Sub operations
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to a channel."""
        if not self._client:
            raise RuntimeError("Cache client not initialized")
        
        try:
            # Serialize complex messages
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            
            return await self._client.publish(channel, message)
        except RedisError as e:
            logger.error(f"Error publishing to channel {channel}: {e}")
            raise
    
    async def subscribe(self, *channels: str) -> None:
        """Subscribe to channels."""
        if not self._pubsub:
            raise RuntimeError("PubSub not initialized")
        
        try:
            await self._pubsub.subscribe(*channels)
        except RedisError as e:
            logger.error(f"Error subscribing to channels {channels}: {e}")
            raise
    
    async def get_message(self, timeout: float = 0.0) -> Optional[Dict[str, Any]]:
        """Get next message from subscribed channels."""
        if not self._pubsub:
            raise RuntimeError("PubSub not initialized")
        
        try:
            message = await self._pubsub.get_message(timeout=timeout)
            
            # Deserialize data if it's JSON
            if message and message.get('data') and isinstance(message['data'], str):
                try:
                    message['data'] = json.loads(message['data'])
                except json.JSONDecodeError:
                    pass
            
            return message
        except RedisError as e:
            logger.error(f"Error getting message: {e}")
            raise
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        
        if self._client:
            await self._client.close()
            self._client = None
        
        logger.info("Redis connection closed")