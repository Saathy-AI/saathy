"""Central event manager for coordinating all event processing."""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import redis.asyncio as redis

from .models.events import BaseEvent
from .event_correlator import EventCorrelator

logger = logging.getLogger(__name__)

class EventManager:
    """Central coordinator for all event processing and storage."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", redis_password: Optional[str] = None):
        """Initialize the event manager with Redis connection."""
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.redis: Optional[redis.Redis] = None
        self.correlator: Optional[EventCorrelator] = None
        self.event_queue = "saathy:events"
        self.processed_events = "saathy:processed"
        self.correlation_queue = "saathy:correlations"
        
    async def initialize(self):
        """Initialize Redis connection and correlator."""
        try:
            # Create Redis connection
            if self.redis_password:
                self.redis = redis.from_url(self.redis_url, password=self.redis_password)
            else:
                self.redis = redis.from_url(self.redis_url)
            
            # Test the connection
            await self.redis.ping()
            logger.info("Redis connection established successfully")
            
            # Initialize correlator
            self.correlator = EventCorrelator(self.redis_url, self.redis_password)
            await self.correlator.initialize()
            
        except Exception as e:
            logger.error(f"Failed to initialize EventManager: {e}")
            raise
        
    async def process_event(self, event: BaseEvent):
        """Main entry point for all events."""
        try:
            logger.info(f"Processing event: {event.event_type} from {event.platform}")
            
            # Store raw event
            await self.store_event(event)
            
            # Add to correlation queue
            await self.queue_for_correlation(event)
            
            logger.debug(f"Event {event.event_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
    
    async def store_event(self, event: BaseEvent):
        """Store event in Redis for persistence and retrieval."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            event_key = f"event:{event.event_id}"
            event_data = event.model_dump_json()
            
            # Store with expiration (30 days)
            await self.redis.setex(event_key, 30 * 24 * 60 * 60, event_data)
            
            # Add to user's event timeline with timestamp score
            user_timeline_key = f"user:{event.user_id}:events"
            await self.redis.zadd(
                user_timeline_key, 
                {event.event_id: event.timestamp.timestamp()}
            )
            
            # Expire user timeline after 30 days
            await self.redis.expire(user_timeline_key, 30 * 24 * 60 * 60)
            
            # Add to platform-specific index
            platform_index_key = f"platform:{event.platform}:events"
            await self.redis.zadd(
                platform_index_key,
                {event.event_id: event.timestamp.timestamp()}
            )
            await self.redis.expire(platform_index_key, 30 * 24 * 60 * 60)
            
            logger.debug(f"Stored event {event.event_id} in Redis")
            
        except Exception as e:
            logger.error(f"Error storing event: {e}")
    
    async def queue_for_correlation(self, event: BaseEvent):
        """Add event to correlation processing queue."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            correlation_data = {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "platform": event.platform,
                "keywords": event.keywords,
                "project_context": event.project_context,
                "urgency_score": event.urgency_score,
                "event_type": event.event_type.value
            }
            
            await self.redis.lpush(self.event_queue, json.dumps(correlation_data))
            logger.debug(f"Event {event.event_id} queued for correlation")
            
        except Exception as e:
            logger.error(f"Error queuing event for correlation: {e}")
    
    async def get_recent_events(self, user_id: str, hours: int = 2) -> List[Dict[str, Any]]:
        """Get recent events for a user for correlation analysis."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            timeline_key = f"user:{user_id}:events"
            since_timestamp = (datetime.now() - timedelta(hours=hours)).timestamp()
            
            # Get event IDs from timeline
            event_ids = await self.redis.zrangebyscore(
                timeline_key, 
                since_timestamp, 
                datetime.now().timestamp()
            )
            
            events = []
            for event_id in event_ids:
                event_key = f"event:{event_id.decode()}"
                event_data = await self.redis.get(event_key)
                if event_data:
                    event_dict = json.loads(event_data)
                    events.append(event_dict)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []
    
    async def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific event by ID."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            event_key = f"event:{event_id}"
            event_data = await self.redis.get(event_key)
            
            if event_data:
                return json.loads(event_data)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving event {event_id}: {e}")
            return None
    
    async def get_platform_events(self, platform: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent events for a specific platform."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            platform_index_key = f"platform:{platform}:events"
            since_timestamp = (datetime.now() - timedelta(hours=hours)).timestamp()
            
            event_ids = await self.redis.zrangebyscore(
                platform_index_key,
                since_timestamp,
                datetime.now().timestamp()
            )
            
            events = []
            for event_id in event_ids:
                event_key = f"event:{event_id.decode()}"
                event_data = await self.redis.get(event_key)
                if event_data:
                    event_dict = json.loads(event_data)
                    events.append(event_dict)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting platform events: {e}")
            return []
    
    async def start_correlation_processor(self):
        """Start background task to process event correlations."""
        logger.info("Starting correlation processor...")
        
        while True:
            try:
                if not self.redis:
                    logger.error("Redis not initialized for correlation processor")
                    await asyncio.sleep(5)
                    continue
                    
                # Get next event from queue (blocking with timeout)
                result = await self.redis.brpop(self.event_queue, timeout=5)
                
                if result:
                    queue_name, event_data = result
                    correlation_data = json.loads(event_data)
                    
                    # Process correlation
                    if self.correlator:
                        await self.correlator.process_event_correlation(correlation_data)
                    
            except Exception as e:
                logger.error(f"Error in correlation processor: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def cleanup_old_events(self):
        """Clean up events older than retention period."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            # This is a simplified cleanup - in production you'd want more sophisticated cleanup
            cutoff_timestamp = (datetime.now() - timedelta(days=30)).timestamp()
            
            # Clean up user timelines
            user_keys = await self.redis.keys("user:*:events")
            for key in user_keys:
                await self.redis.zremrangebyscore(key, 0, cutoff_timestamp)
                
            # Clean up platform indexes
            platform_keys = await self.redis.keys("platform:*:events")
            for key in platform_keys:
                await self.redis.zremrangebyscore(key, 0, cutoff_timestamp)
                
            logger.info("Completed cleanup of old events")
            
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
    
    async def get_user_stats(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get statistics for a user's activity."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            since_timestamp = (datetime.now() - timedelta(days=days)).timestamp()
            timeline_key = f"user:{user_id}:events"
            
            # Get recent event count
            event_count = await self.redis.zcount(
                timeline_key,
                since_timestamp,
                datetime.now().timestamp()
            )
            
            # Get events by platform
            platform_counts = {}
            recent_events = await self.get_recent_events(user_id, days * 24)
            
            for event in recent_events:
                platform = event.get("platform", "unknown")
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
            return {
                "user_id": user_id,
                "days": days,
                "total_events": event_count,
                "platform_breakdown": platform_counts,
                "most_active_platform": max(platform_counts.items(), key=lambda x: x[1])[0] if platform_counts else None
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"user_id": user_id, "error": str(e)}
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")