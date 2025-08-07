from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, SearchRequest
import redis.asyncio as redis
from app.models.information_needs import InformationNeeds
from config.settings import get_settings
from app.utils.database import get_redis

settings = get_settings()


class SearchResult:
    """Represents a search result from any source"""
    def __init__(self, id: str, content: str, source: str, 
                 score: float, metadata: Dict[str, Any]):
        self.id = id
        self.content = content
        self.source = source  # "vector", "event", "action", etc.
        self.score = score
        self.metadata = metadata
        self.timestamp = metadata.get("timestamp", datetime.now())


class BasicHybridRetriever:
    """Basic hybrid retrieval engine combining multiple search strategies"""
    
    def __init__(self):
        self.qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key
        )
        self.collection_name = "saathy_content"
        self.redis_client = None
    
    async def initialize(self):
        """Initialize connections"""
        self.redis_client = await get_redis()
    
    async def retrieve_context(self, info_needs: InformationNeeds) -> Dict[str, List[SearchResult]]:
        """
        Retrieve context using multiple search strategies in parallel
        
        Returns:
            Dictionary with keys: 'content', 'events', 'actions'
        """
        if not self.redis_client:
            await self.initialize()
        
        # Execute searches in parallel
        tasks = [
            self._vector_search(info_needs),
            self._structured_search(info_needs),
            self._get_user_actions(info_needs)
        ]
        
        vector_results, event_results, action_results = await asyncio.gather(*tasks)
        
        # Basic merging and ranking
        return {
            'content': self._rank_results(vector_results, info_needs)[:5],
            'events': self._rank_results(event_results, info_needs)[:10],
            'actions': self._rank_results(action_results, info_needs)[:5]
        }
    
    async def _vector_search(self, info_needs: InformationNeeds) -> List[SearchResult]:
        """
        Perform vector similarity search using Qdrant
        """
        try:
            # Generate embedding for the query (simplified - should use actual embedding model)
            query_embedding = await self._generate_embedding(info_needs.query)
            
            # Build metadata filters
            filters = []
            
            # Time filter
            if info_needs.time_reference and info_needs.time_reference.start_time:
                filters.append(
                    FieldCondition(
                        key="timestamp",
                        range={
                            "gte": info_needs.time_reference.start_time.timestamp(),
                            "lte": info_needs.time_reference.end_time.timestamp() if info_needs.time_reference.end_time else datetime.now().timestamp()
                        }
                    )
                )
            
            # Platform filter
            if info_needs.platforms:
                filters.append(
                    FieldCondition(
                        key="platform",
                        match=MatchValue(any=list(info_needs.platforms))
                    )
                )
            
            # User filter
            filters.append(
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=info_needs.user_id)
                )
            )
            
            # Perform search
            search_filter = Filter(must=filters) if filters else None
            
            results = await self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=settings.vector_search_limit,
                with_payload=True
            )
            
            # Convert to SearchResult objects
            return [
                SearchResult(
                    id=str(result.id),
                    content=result.payload.get("content", ""),
                    source="vector",
                    score=result.score,
                    metadata=result.payload
                )
                for result in results
            ]
            
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    async def _structured_search(self, info_needs: InformationNeeds) -> List[SearchResult]:
        """
        Search for structured events from Redis timeline
        """
        try:
            # Build Redis key pattern
            user_key = f"user:{info_needs.user_id}:events"
            
            # Get events from Redis sorted set
            if info_needs.time_reference and info_needs.time_reference.start_time:
                start_score = info_needs.time_reference.start_time.timestamp()
                end_score = info_needs.time_reference.end_time.timestamp() if info_needs.time_reference.end_time else datetime.now().timestamp()
                
                events = await self.redis_client.zrangebyscore(
                    user_key,
                    start_score,
                    end_score,
                    withscores=True,
                    start=0,
                    num=settings.event_search_limit
                )
            else:
                # Get recent events
                events = await self.redis_client.zrevrange(
                    user_key,
                    0,
                    settings.event_search_limit - 1,
                    withscores=True
                )
            
            results = []
            for event_id, score in events:
                # Get event details
                event_data = await self.redis_client.hgetall(f"event:{event_id}")
                
                if event_data:
                    # Filter by platform if needed
                    if info_needs.platforms and event_data.get("platform") not in info_needs.platforms:
                        continue
                    
                    # Filter by entities if present
                    relevant = True
                    if info_needs.entities:
                        event_content = event_data.get("content", "").lower()
                        entity_values = [e.value.lower() for e in info_needs.entities]
                        relevant = any(entity in event_content for entity in entity_values)
                    
                    if relevant:
                        results.append(SearchResult(
                            id=event_id,
                            content=event_data.get("content", ""),
                            source="event",
                            score=1.0,  # Will be adjusted by ranking
                            metadata={
                                "timestamp": datetime.fromtimestamp(score),
                                "platform": event_data.get("platform"),
                                "event_type": event_data.get("type"),
                                **event_data
                            }
                        ))
            
            return results
            
        except Exception as e:
            print(f"Structured search error: {e}")
            return []
    
    async def _get_user_actions(self, info_needs: InformationNeeds) -> List[SearchResult]:
        """
        Get user's pending and recent actions
        """
        try:
            results = []
            
            # Get pending actions
            pending_key = f"user:{info_needs.user_id}:actions:pending"
            pending_actions = await self.redis_client.smembers(pending_key)
            
            for action_id in pending_actions:
                action_data = await self.redis_client.hgetall(f"action:{action_id}")
                if action_data:
                    results.append(SearchResult(
                        id=action_id,
                        content=action_data.get("description", ""),
                        source="action",
                        score=1.5,  # Boost pending actions
                        metadata={
                            "status": "pending",
                            "priority": action_data.get("priority", "normal"),
                            **action_data
                        }
                    ))
            
            # Get recent completed actions
            completed_key = f"user:{info_needs.user_id}:actions:completed"
            recent_completed = await self.redis_client.zrevrange(
                completed_key,
                0,
                settings.action_search_limit - len(results) - 1,
                withscores=True
            )
            
            for action_id, score in recent_completed:
                action_data = await self.redis_client.hgetall(f"action:{action_id}")
                if action_data:
                    results.append(SearchResult(
                        id=action_id,
                        content=action_data.get("description", ""),
                        source="action",
                        score=1.0,
                        metadata={
                            "status": "completed",
                            "completed_at": datetime.fromtimestamp(score),
                            **action_data
                        }
                    ))
            
            return results
            
        except Exception as e:
            print(f"Action search error: {e}")
            return []
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text (placeholder - should use actual embedding model)
        """
        # In production, this would use OpenAI embeddings or similar
        # For now, return a random vector
        return np.random.rand(1536).tolist()
    
    def _rank_results(self, results: List[SearchResult], info_needs: InformationNeeds) -> List[SearchResult]:
        """
        Basic ranking of results based on timestamp and relevance
        """
        if not results:
            return []
        
        # Calculate temporal relevance
        now = datetime.now()
        for result in results:
            # Temporal decay - newer is better
            age_hours = (now - result.timestamp).total_seconds() / 3600
            temporal_score = np.exp(-0.1 * age_hours)
            
            # Entity matching boost
            entity_boost = 1.0
            if info_needs.entities:
                content_lower = result.content.lower()
                for entity in info_needs.entities:
                    if entity.value.lower() in content_lower:
                        entity_boost += 0.3 * entity.confidence
            
            # Platform relevance
            platform_boost = 1.0
            if info_needs.platforms and result.metadata.get("platform") in info_needs.platforms:
                platform_boost = 1.2
            
            # Combined score
            result.score = result.score * temporal_score * entity_boost * platform_boost
        
        # Sort by score
        return sorted(results, key=lambda x: x.score, reverse=True)


class ContextRetriever:
    """
    High-level context retriever that orchestrates different retrieval strategies
    """
    
    def __init__(self):
        self.hybrid_retriever = BasicHybridRetriever()
    
    async def retrieve(self, info_needs: InformationNeeds, 
                      strategy: Optional[str] = "hybrid") -> Dict[str, Any]:
        """
        Retrieve context based on information needs and strategy
        """
        if strategy == "hybrid" or strategy not in ["vector_only", "structured_only"]:
            results = await self.hybrid_retriever.retrieve_context(info_needs)
        elif strategy == "vector_only":
            vector_results = await self.hybrid_retriever._vector_search(info_needs)
            results = {"content": vector_results, "events": [], "actions": []}
        elif strategy == "structured_only":
            event_results = await self.hybrid_retriever._structured_search(info_needs)
            action_results = await self.hybrid_retriever._get_user_actions(info_needs)
            results = {"content": [], "events": event_results, "actions": action_results}
        
        # Format results for response
        return self._format_results(results, info_needs)
    
    def _format_results(self, results: Dict[str, List[SearchResult]], 
                       info_needs: InformationNeeds) -> Dict[str, Any]:
        """
        Format results for use in response generation
        """
        formatted = {
            "total_results": sum(len(r) for r in results.values()),
            "content": [
                {
                    "id": r.id,
                    "text": r.content,
                    "source": r.metadata.get("platform", "unknown"),
                    "timestamp": r.timestamp.isoformat(),
                    "relevance_score": r.score
                }
                for r in results.get("content", [])
            ],
            "events": [
                {
                    "id": r.id,
                    "description": r.content,
                    "type": r.metadata.get("event_type", "unknown"),
                    "platform": r.metadata.get("platform", "unknown"),
                    "timestamp": r.timestamp.isoformat()
                }
                for r in results.get("events", [])
            ],
            "actions": [
                {
                    "id": r.id,
                    "description": r.content,
                    "status": r.metadata.get("status", "unknown"),
                    "priority": r.metadata.get("priority", "normal")
                }
                for r in results.get("actions", [])
            ],
            "query_info": {
                "intent": info_needs.intent.value,
                "complexity": info_needs.complexity,
                "platforms_searched": list(info_needs.platforms) if info_needs.platforms else ["all"]
            }
        }
        
        return formatted