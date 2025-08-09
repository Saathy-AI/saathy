"""Intelligence service implementation for AI-powered insights and recommendations."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import asyncio

from openai import AsyncOpenAI

from saathy_core import ActionRecommendation, EventCorrelation

logger = logging.getLogger(__name__)


class IntelligenceService:
    """Service for AI-powered intelligence and recommendations."""
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4",
        vector_store=None,
        cache_service=None,
        embedding_service=None,
    ):
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.vector_store = vector_store
        self.cache_service = cache_service
        self.embedding_service = embedding_service
        self._client: Optional[AsyncOpenAI] = None
        self._action_cache_prefix = "intelligence:actions:"
        self._correlation_cache_prefix = "intelligence:correlations:"
        self._event_cache_prefix = "intelligence:events:"
    
    async def initialize(self) -> None:
        """Initialize intelligence service."""
        try:
            logger.info("Initializing intelligence service")
            
            if self.openai_api_key:
                self._client = AsyncOpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("No OpenAI API key provided, AI features will be limited")
            
            logger.info("Intelligence service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize intelligence service: {e}")
            raise
    
    async def get_user_actions(
        self,
        user_id: str,
        limit: int = 10,
        include_completed: bool = False,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get AI-generated action recommendations for a user."""
        cache_key = f"{self._action_cache_prefix}{user_id}:actions"
        
        # Check cache first
        if self.cache_service:
            cached = await self.cache_service.get(cache_key)
            if cached:
                actions = cached
            else:
                actions = await self._generate_user_actions(user_id)
                await self.cache_service.set(cache_key, actions, ttl=300)  # 5 min cache
        else:
            actions = await self._generate_user_actions(user_id)
        
        # Filter based on criteria
        filtered = []
        for action in actions:
            if not include_completed and action.get("completed_at"):
                continue
            if priority and action.get("priority") != priority:
                continue
            filtered.append(action)
        
        return filtered[:limit]
    
    async def _generate_user_actions(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate action recommendations using AI."""
        # Get recent user events and context
        recent_events = await self._get_user_recent_events(user_id, hours=24)
        
        if not recent_events or not self._client:
            # Return sample actions if no AI available
            return self._get_sample_actions(user_id)
        
        try:
            # Create prompt for AI
            events_summary = self._summarize_events(recent_events)
            prompt = f"""Based on the following user activity across GitHub, Slack, and Notion:

{events_summary}

Generate 5 actionable recommendations that would help this user be more productive. 
For each recommendation, provide:
1. A clear, specific title
2. A detailed description of what to do
3. Priority (high, medium, low)
4. Action type (review, create, update, communicate, organize)
5. Relevant platform links if applicable

Format as JSON array with objects containing: title, description, priority, action_type, platform_links"""

            # Generate recommendations
            response = await self._client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a productivity assistant helping users manage their work across GitHub, Slack, and Notion."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse AI response
            import json
            recommendations = json.loads(response.choices[0].message.content).get("recommendations", [])
            
            # Convert to action format
            actions = []
            for rec in recommendations:
                action = {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "title": rec.get("title", ""),
                    "description": rec.get("description", ""),
                    "priority": rec.get("priority", "medium"),
                    "action_type": rec.get("action_type", "review"),
                    "platform_links": rec.get("platform_links", {}),
                    "correlated_events": [e["id"] for e in recent_events[:3]],
                    "created_at": datetime.utcnow(),
                    "completed_at": None,
                    "feedback": None,
                }
                actions.append(action)
            
            return actions
        except Exception as e:
            logger.error(f"Failed to generate AI actions: {e}")
            return self._get_sample_actions(user_id)
    
    def _get_sample_actions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get sample actions when AI is not available."""
        now = datetime.utcnow()
        return [
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "title": "Review open pull requests",
                "description": "You have 3 pull requests waiting for review. Prioritize reviewing the critical bug fix PR first.",
                "priority": "high",
                "action_type": "review",
                "platform_links": {"github": "https://github.com/org/repo/pulls"},
                "correlated_events": [],
                "created_at": now,
                "completed_at": None,
                "feedback": None,
            },
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "title": "Update project documentation",
                "description": "The API documentation in Notion is outdated. Update it to reflect the recent changes in the authentication flow.",
                "priority": "medium",
                "action_type": "update",
                "platform_links": {"notion": "https://notion.so/api-docs"},
                "correlated_events": [],
                "created_at": now,
                "completed_at": None,
                "feedback": None,
            },
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "title": "Respond to team questions in Slack",
                "description": "Your team has asked questions in #dev-help channel that need your expertise.",
                "priority": "high",
                "action_type": "communicate",
                "platform_links": {"slack": "slack://channel?team=T123&id=C456"},
                "correlated_events": [],
                "created_at": now,
                "completed_at": None,
                "feedback": None,
            },
        ]
    
    async def mark_action_completed(self, action_id: str) -> bool:
        """Mark an action as completed."""
        # In production, this would update a database
        # For now, we'll update the cache
        if self.cache_service:
            action_key = f"{self._action_cache_prefix}action:{action_id}"
            action = await self.cache_service.get(action_key)
            if action:
                action["completed_at"] = datetime.utcnow()
                await self.cache_service.set(action_key, action, ttl=86400)  # 24 hours
                return True
        
        return False
    
    async def add_action_feedback(
        self,
        action_id: str,
        useful: bool,
        feedback_text: Optional[str] = None,
        completed: bool = False
    ) -> bool:
        """Add feedback to an action recommendation."""
        # In production, this would update a database and train the model
        if self.cache_service:
            feedback_key = f"{self._action_cache_prefix}feedback:{action_id}"
            feedback_data = {
                "action_id": action_id,
                "useful": useful,
                "feedback_text": feedback_text,
                "completed": completed,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.cache_service.set(feedback_key, feedback_data, ttl=86400 * 30)  # 30 days
            return True
        
        return False
    
    async def get_event_correlations(
        self,
        user_id: str,
        since: datetime,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Get correlations between events across platforms."""
        cache_key = f"{self._correlation_cache_prefix}{user_id}:{since.date()}"
        
        # Check cache
        if self.cache_service:
            cached = await self.cache_service.get(cache_key)
            if cached:
                return [c for c in cached if c.get("correlation_score", 0) >= min_score]
        
        # Get events and compute correlations
        events = await self._get_user_recent_events(user_id, since=since)
        correlations = await self._compute_event_correlations(events)
        
        # Cache results
        if self.cache_service:
            await self.cache_service.set(cache_key, correlations, ttl=3600)  # 1 hour
        
        return [c for c in correlations if c.get("correlation_score", 0) >= min_score]
    
    async def _compute_event_correlations(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compute correlations between events using embeddings."""
        if not events or not self.embedding_service:
            return []
        
        correlations = []
        
        # Get embeddings for all events
        event_texts = [e.get("content", "") for e in events]
        embeddings = await self.embedding_service.embed_batch(event_texts)
        
        # Find similar events
        for i, event1 in enumerate(events):
            for j, event2 in enumerate(events[i+1:], start=i+1):
                # Skip if same platform and close in time
                if (event1.get("platform") == event2.get("platform") and 
                    abs((event1.get("timestamp") - event2.get("timestamp")).total_seconds()) < 300):
                    continue
                
                # Compute similarity
                similarity = await self.embedding_service.compute_similarity(
                    embeddings[i],
                    embeddings[j]
                )
                
                if similarity >= 0.7:
                    correlation = {
                        "id": str(uuid4()),
                        "event_ids": [event1["id"], event2["id"]],
                        "correlation_score": similarity,
                        "correlation_type": self._determine_correlation_type(event1, event2),
                        "timestamp": datetime.utcnow(),
                        "metadata": {
                            "platforms": [event1.get("platform"), event2.get("platform")],
                            "event_types": [event1.get("event_type"), event2.get("event_type")],
                        }
                    }
                    correlations.append(correlation)
        
        return correlations
    
    def _determine_correlation_type(
        self,
        event1: Dict[str, Any],
        event2: Dict[str, Any]
    ) -> str:
        """Determine the type of correlation between events."""
        platform1 = event1.get("platform")
        platform2 = event2.get("platform")
        type1 = event1.get("event_type")
        type2 = event2.get("event_type")
        
        # Cross-platform patterns
        if platform1 != platform2:
            if "commit" in type1 and "message" in type2:
                return "code_discussion"
            elif "issue" in type1 and "page" in type2:
                return "issue_documentation"
            elif "pull_request" in type1 and "channel" in type2:
                return "pr_communication"
        
        # Same platform patterns
        else:
            if "commit" in type1 and "commit" in type2:
                return "related_commits"
            elif "message" in type1 and "message" in type2:
                return "conversation_thread"
        
        return "general_correlation"
    
    async def get_user_events(
        self,
        user_id: str,
        since: datetime,
        platform: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user events from all platforms."""
        return await self._get_user_recent_events(
            user_id,
            since=since,
            platform=platform,
            event_type=event_type,
            limit=limit
        )
    
    async def _get_user_recent_events(
        self,
        user_id: str,
        hours: Optional[int] = None,
        since: Optional[datetime] = None,
        platform: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent events for a user from cache or vector store."""
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
        elif not since:
            since = datetime.utcnow() - timedelta(hours=24)
        
        # In production, this would query from a database or event store
        # For now, return sample events
        events = [
            {
                "id": str(uuid4()),
                "platform": "github",
                "event_type": "pull_request",
                "content": "Created PR: Fix authentication bug in login flow",
                "user_id": user_id,
                "timestamp": datetime.utcnow() - timedelta(hours=2),
                "metadata": {"pr_number": 123, "repo": "org/repo"}
            },
            {
                "id": str(uuid4()),
                "platform": "slack",
                "event_type": "message",
                "content": "Discussing the authentication bug with the team",
                "user_id": user_id,
                "timestamp": datetime.utcnow() - timedelta(hours=1, minutes=30),
                "metadata": {"channel": "dev-help", "thread_ts": "123.456"}
            },
            {
                "id": str(uuid4()),
                "platform": "notion",
                "event_type": "page_update",
                "content": "Updated authentication documentation",
                "user_id": user_id,
                "timestamp": datetime.utcnow() - timedelta(hours=1),
                "metadata": {"page_id": "abc123", "title": "Auth Docs"}
            },
        ]
        
        # Filter based on criteria
        filtered = []
        for event in events:
            if event["timestamp"] < since:
                continue
            if platform and event["platform"] != platform:
                continue
            if event_type and event["event_type"] != event_type:
                continue
            filtered.append(event)
        
        return filtered[:limit]
    
    def _summarize_events(self, events: List[Dict[str, Any]]) -> str:
        """Create a summary of events for AI processing."""
        summary_parts = []
        
        # Group by platform
        by_platform = {}
        for event in events:
            platform = event.get("platform", "unknown")
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(event)
        
        # Summarize each platform
        for platform, platform_events in by_platform.items():
            summary_parts.append(f"\n{platform.upper()} Activity:")
            for event in platform_events[:5]:  # Limit to 5 per platform
                time_str = event.get("timestamp", datetime.utcnow()).strftime("%H:%M")
                summary_parts.append(
                    f"- [{time_str}] {event.get('event_type', 'unknown')}: "
                    f"{event.get('content', 'No description')}"
                )
        
        return "\n".join(summary_parts)
    
    async def analyze_user_activity(
        self,
        user_id: str,
        since: datetime
    ) -> Dict[str, Any]:
        """Perform deep analysis on user activity."""
        # Get events
        events = await self._get_user_recent_events(user_id, since=since)
        
        # Compute basic statistics
        stats = {
            "total_events": len(events),
            "events_by_platform": {},
            "events_by_type": {},
            "most_active_hour": None,
            "cross_platform_interactions": 0,
        }
        
        # Count by platform and type
        for event in events:
            platform = event.get("platform", "unknown")
            event_type = event.get("event_type", "unknown")
            
            stats["events_by_platform"][platform] = stats["events_by_platform"].get(platform, 0) + 1
            stats["events_by_type"][event_type] = stats["events_by_type"].get(event_type, 0) + 1
        
        # Get correlations
        correlations = await self.get_event_correlations(user_id, since)
        stats["cross_platform_interactions"] = len([
            c for c in correlations
            if len(set(c.get("metadata", {}).get("platforms", []))) > 1
        ])
        
        # Generate insights
        insights = []
        
        # Most active platform
        if stats["events_by_platform"]:
            most_active = max(stats["events_by_platform"].items(), key=lambda x: x[1])
            insights.append({
                "type": "activity_focus",
                "message": f"Most active on {most_active[0]} with {most_active[1]} events",
                "platform": most_active[0],
                "severity": "info"
            })
        
        # Cross-platform activity
        if stats["cross_platform_interactions"] > 5:
            insights.append({
                "type": "cross_platform",
                "message": f"High cross-platform activity detected ({stats['cross_platform_interactions']} interactions)",
                "severity": "positive"
            })
        
        # Patterns
        patterns = []
        if "pull_request" in stats["events_by_type"] and "message" in stats["events_by_type"]:
            patterns.append({
                "type": "collaboration",
                "description": "Active code review and discussion pattern detected"
            })
        
        # Recommendations based on analysis
        recommendations = await self.get_user_actions(user_id, limit=3)
        
        return {
            "insights": insights,
            "patterns": patterns,
            "recommendations": recommendations,
            "statistics": stats
        }