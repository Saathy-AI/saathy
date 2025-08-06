"""Event correlation engine for finding related cross-platform events."""

import asyncio
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class EventCorrelator:
    """Finds and groups related events across platforms for action generation."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", redis_password: Optional[str] = None):
        """Initialize the correlator with Redis connection."""
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.redis: Optional[redis.Redis] = None
        self.correlation_window_minutes = 30
        self.similarity_threshold = 0.3
        
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            if self.redis_password:
                self.redis = redis.from_url(self.redis_url, password=self.redis_password)
            else:
                self.redis = redis.from_url(self.redis_url)
            
            await self.redis.ping()
            logger.info("Event correlator Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize EventCorrelator: {e}")
            raise
        
    async def process_event_correlation(self, event_data: Dict[str, Any]):
        """Process correlation for a single event."""
        try:
            user_id = event_data["user_id"]
            event_timestamp = datetime.fromisoformat(event_data["timestamp"])
            
            logger.debug(f"Processing correlation for event {event_data['event_id']}")
            
            # Find related events in time window
            related_events = await self.find_related_events(event_data)
            
            if related_events:
                # Create or update correlation group
                correlation_id = await self.create_correlation_group(event_data, related_events)
                logger.info(f"Created correlation group {correlation_id} with {len(related_events)} related events")
                
                # Trigger action generation for this group
                await self.trigger_action_generation(correlation_id)
            else:
                logger.debug(f"No related events found for {event_data['event_id']}")
                
        except Exception as e:
            logger.error(f"Error in event correlation: {e}")
    
    async def find_related_events(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find events related to the given event using multiple similarity metrics."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            user_id = event_data["user_id"]
            event_timestamp = datetime.fromisoformat(event_data["timestamp"])
            
            # Get events in time window
            window_start = event_timestamp - timedelta(minutes=self.correlation_window_minutes)
            window_end = event_timestamp + timedelta(minutes=self.correlation_window_minutes)
            
            timeline_key = f"user:{user_id}:events"
            event_ids = await self.redis.zrangebyscore(
                timeline_key,
                window_start.timestamp(),
                window_end.timestamp()
            )
            
            related_events = []
            for event_id in event_ids:
                event_id_str = event_id.decode()
                if event_id_str == event_data["event_id"]:
                    continue  # Skip self
                    
                # Get event details
                event_key = f"event:{event_id_str}"
                stored_event_data = await self.redis.get(event_key)
                
                if stored_event_data:
                    stored_event = json.loads(stored_event_data)
                    
                    # Check if events are related
                    similarity_score = self.calculate_event_similarity(event_data, stored_event)
                    
                    if similarity_score >= self.similarity_threshold:
                        related_events.append({
                            **stored_event,
                            "similarity_score": similarity_score
                        })
            
            # Sort by similarity score (highest first)
            related_events.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            return related_events[:5]  # Max 5 related events to avoid noise
            
        except Exception as e:
            logger.error(f"Error finding related events: {e}")
            return []
    
    def calculate_event_similarity(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> float:
        """Calculate similarity score between two events using multiple factors."""
        try:
            score = 0.0
            
            # Same project context (strong indicator)
            if (event1.get("project_context") and event2.get("project_context") and
                event1["project_context"] == event2["project_context"]):
                score += 0.4
            
            # Shared keywords (semantic similarity)
            keywords1 = set(event1.get("keywords", []))
            keywords2 = set(event2.get("keywords", []))
            
            if keywords1 and keywords2:
                keyword_overlap = len(keywords1.intersection(keywords2))
                keyword_union = len(keywords1.union(keywords2))
                if keyword_union > 0:
                    score += 0.3 * (keyword_overlap / keyword_union)
            
            # Cross-platform bonus (different platforms often complement each other)
            if event1["platform"] != event2["platform"]:
                platform_combinations = {
                    ("slack", "github"), ("github", "slack"),
                    ("slack", "notion"), ("notion", "slack"),
                    ("github", "notion"), ("notion", "github")
                }
                if (event1["platform"], event2["platform"]) in platform_combinations:
                    score += 0.2
            
            # Time proximity bonus (closer in time = more likely related)
            time1 = datetime.fromisoformat(event1["timestamp"])
            time2 = datetime.fromisoformat(event2["timestamp"])
            time_diff_minutes = abs((time1 - time2).total_seconds()) / 60
            
            if time_diff_minutes < 15:  # Very close in time
                score += 0.15
            elif time_diff_minutes < 30:  # Moderately close
                score += 0.1
            
            # Urgency correlation (both high urgency = likely related)
            urgency1 = event1.get("urgency_score", 0)
            urgency2 = event2.get("urgency_score", 0)
            if urgency1 > 0.5 and urgency2 > 0.5:
                score += 0.1
            
            # Event type correlation bonuses
            score += self.calculate_event_type_correlation(event1, event2)
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Error calculating event similarity: {e}")
            return 0.0
    
    def calculate_event_type_correlation(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> float:
        """Calculate bonus score for specific event type combinations."""
        type1 = event1.get("event_type", "")
        type2 = event2.get("event_type", "")
        
        # Slack discussion -> GitHub activity
        if (type1 == "slack_message" and type2.startswith("github_")) or \
           (type2 == "slack_message" and type1.startswith("github_")):
            return 0.15
        
        # GitHub PR -> Slack reaction (approval/review)
        if (type1 == "github_pr" and type2 == "slack_reaction") or \
           (type2 == "github_pr" and type1 == "slack_reaction"):
            return 0.1
        
        # Notion update -> Slack notification
        if (type1.startswith("notion_") and type2 == "slack_message") or \
           (type2.startswith("notion_") and type1 == "slack_message"):
            return 0.1
        
        # GitHub push -> Notion documentation update
        if (type1 == "github_push" and type2.startswith("notion_")) or \
           (type2 == "github_push" and type1.startswith("notion_")):
            return 0.1
        
        return 0.0
    
    async def create_correlation_group(self, primary_event: Dict[str, Any], related_events: List[Dict[str, Any]]) -> str:
        """Create a correlation group for related events."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            # Generate correlation ID
            correlation_id = f"corr_{primary_event['user_id']}_{int(datetime.now().timestamp())}_{hash(primary_event['event_id']) % 1000}"
            
            # Create correlation data
            correlation_data = {
                "correlation_id": correlation_id,
                "primary_event": primary_event,
                "related_events": related_events,
                "created_at": datetime.now().isoformat(),
                "user_id": primary_event["user_id"],
                "status": "pending_action_generation",
                "correlation_strength": self.calculate_group_strength(primary_event, related_events)
            }
            
            # Store correlation group
            correlation_key = f"correlation:{correlation_id}"
            await self.redis.setex(
                correlation_key,
                24 * 60 * 60,  # 24 hours expiration
                json.dumps(correlation_data)
            )
            
            # Add to user's correlations list
            user_correlations_key = f"user:{primary_event['user_id']}:correlations"
            await self.redis.zadd(
                user_correlations_key,
                {correlation_id: datetime.now().timestamp()}
            )
            
            # Expire user correlations after 7 days
            await self.redis.expire(user_correlations_key, 7 * 24 * 60 * 60)
            
            logger.debug(f"Created correlation group {correlation_id}")
            return correlation_id
            
        except Exception as e:
            logger.error(f"Error creating correlation group: {e}")
            return ""
    
    def calculate_group_strength(self, primary_event: Dict[str, Any], related_events: List[Dict[str, Any]]) -> float:
        """Calculate the overall strength of the correlation group."""
        if not related_events:
            return 0.0
        
        # Average similarity scores
        similarity_scores = [event.get("similarity_score", 0) for event in related_events]
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        
        # Bonus for multiple platforms
        platforms = {primary_event["platform"]}
        for event in related_events:
            platforms.add(event["platform"])
        
        platform_bonus = min(0.3, (len(platforms) - 1) * 0.1)  # Bonus for cross-platform
        
        # Bonus for urgency
        urgency_scores = [primary_event.get("urgency_score", 0)]
        urgency_scores.extend([event.get("urgency_score", 0) for event in related_events])
        avg_urgency = sum(urgency_scores) / len(urgency_scores)
        urgency_bonus = avg_urgency * 0.2
        
        return min(1.0, avg_similarity + platform_bonus + urgency_bonus)
    
    async def trigger_action_generation(self, correlation_id: str):
        """Trigger action generation for a correlation group."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            # Add to action generation queue
            action_queue_key = "saathy:action_generation"
            await self.redis.lpush(action_queue_key, correlation_id)
            
            logger.info(f"Triggered action generation for correlation {correlation_id}")
            
        except Exception as e:
            logger.error(f"Error triggering action generation: {e}")
    
    async def get_correlation_by_id(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a correlation group by ID."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            correlation_key = f"correlation:{correlation_id}"
            correlation_data = await self.redis.get(correlation_key)
            
            if correlation_data:
                return json.loads(correlation_data)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving correlation {correlation_id}: {e}")
            return None
    
    async def get_user_correlations(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent correlations for a user."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            since_timestamp = (datetime.now() - timedelta(hours=hours)).timestamp()
            user_correlations_key = f"user:{user_id}:correlations"
            
            correlation_ids = await self.redis.zrangebyscore(
                user_correlations_key,
                since_timestamp,
                datetime.now().timestamp()
            )
            
            correlations = []
            for correlation_id in correlation_ids:
                correlation_data = await self.get_correlation_by_id(correlation_id.decode())
                if correlation_data:
                    correlations.append(correlation_data)
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error getting user correlations: {e}")
            return []
    
    async def update_correlation_status(self, correlation_id: str, status: str):
        """Update the status of a correlation group."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            correlation_data = await self.get_correlation_by_id(correlation_id)
            if correlation_data:
                correlation_data["status"] = status
                correlation_data["updated_at"] = datetime.now().isoformat()
                
                correlation_key = f"correlation:{correlation_id}"
                await self.redis.setex(
                    correlation_key,
                    24 * 60 * 60,  # 24 hours
                    json.dumps(correlation_data)
                )
                
                logger.debug(f"Updated correlation {correlation_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Error updating correlation status: {e}")
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Event correlator Redis connection closed")