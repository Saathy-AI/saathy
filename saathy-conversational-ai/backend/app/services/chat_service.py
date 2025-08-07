from typing import Optional, Dict, List
from datetime import datetime
import openai
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat_session import (
    ChatSession, ChatSessionDB, ChatTurnDB, ChatMessage, 
    ChatResponse, SessionStatus
)
from app.models.information_needs import InformationNeeds
from app.services.information_analyzer import BasicInformationAnalyzer
from app.retrieval.hybrid_retriever import ContextRetriever
from app.utils.database import get_redis
from config.settings import get_settings

settings = get_settings()
openai.api_key = settings.openai_api_key


class ChatService:
    """Main service for handling chat conversations"""
    
    def __init__(self):
        self.analyzer = BasicInformationAnalyzer()
        self.retriever = ContextRetriever()
        self.redis_client = None
    
    async def initialize(self):
        """Initialize service connections"""
        if not self.redis_client:
            self.redis_client = await get_redis()
    
    async def create_session(self, user_id: str, db: AsyncSession) -> ChatSession:
        """Create a new chat session"""
        # Create database session
        db_session = ChatSessionDB(user_id=user_id)
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        
        # Store in Redis for fast access
        await self.initialize()
        session_key = f"session:{db_session.id}"
        session_data = {
            "user_id": user_id,
            "status": SessionStatus.ACTIVE.value,
            "created_at": datetime.utcnow().isoformat(),
            "turn_count": 0
        }
        await self.redis_client.hset(session_key, mapping=session_data)
        await self.redis_client.expire(session_key, settings.session_ttl_hours * 3600)
        
        # Return Pydantic model
        return ChatSession(
            session_id=db_session.id,
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            created_at=db_session.created_at,
            expires_at=db_session.expires_at
        )
    
    async def process_message(self, message: ChatMessage, user_id: str, 
                            db: AsyncSession) -> ChatResponse:
        """Process a user message and generate response"""
        await self.initialize()
        
        # Get or create session
        if message.session_id:
            session = await self._get_session(message.session_id, db)
            if not session or session.user_id != user_id:
                raise ValueError("Invalid session")
        else:
            session = await self.create_session(user_id, db)
            message.session_id = session.session_id
        
        # Update session activity
        await self._update_session_activity(session.session_id)
        
        # Get session context
        session_context = await self._get_session_context(session.session_id)
        
        # Analyze user query
        analysis_result = await self.analyzer.analyze_query(
            message.message, 
            user_id, 
            session_context
        )
        info_needs = analysis_result.information_needs
        
        # Retrieve context
        context = await self.retriever.retrieve(
            info_needs,
            strategy=analysis_result.suggested_retrieval_strategies[0]
        )
        
        # Generate response
        response_text = await self._generate_response(
            message.message,
            info_needs,
            context,
            session_context
        )
        
        # Save turn to database
        await self._save_turn(
            session.session_id,
            message.message,
            response_text,
            context,
            analysis_result.suggested_retrieval_strategies[0],
            db
        )
        
        # Update session context for next turn
        await self._update_session_context(
            session.session_id,
            info_needs,
            context
        )
        
        return ChatResponse(
            session_id=session.session_id,
            message=response_text,
            context_sources=self._extract_sources(context),
            retrieval_strategy=analysis_result.suggested_retrieval_strategies[0]
        )
    
    async def get_session_history(self, session_id: str, user_id: str, 
                                db: AsyncSession) -> ChatSession:
        """Get full session history"""
        # Verify session ownership
        result = await db.execute(
            select(ChatSessionDB).where(
                ChatSessionDB.id == session_id,
                ChatSessionDB.user_id == user_id
            )
        )
        db_session = result.scalar_one_or_none()
        
        if not db_session:
            raise ValueError("Session not found")
        
        # Convert to Pydantic model with turns
        session = ChatSession.from_orm(db_session)
        
        # Load turns
        result = await db.execute(
            select(ChatTurnDB).where(
                ChatTurnDB.session_id == session_id
            ).order_by(ChatTurnDB.timestamp)
        )
        turns = result.scalars().all()
        
        session.conversation_turns = [
            ChatTurnDB.from_orm(turn) for turn in turns
        ]
        
        return session
    
    async def end_session(self, session_id: str, user_id: str, 
                        db: AsyncSession) -> None:
        """End a chat session"""
        # Update database
        result = await db.execute(
            select(ChatSessionDB).where(
                ChatSessionDB.id == session_id,
                ChatSessionDB.user_id == user_id
            )
        )
        db_session = result.scalar_one_or_none()
        
        if db_session:
            db_session.status = SessionStatus.ENDED
            await db.commit()
        
        # Remove from Redis
        await self.redis_client.delete(f"session:{session_id}")
        await self.redis_client.delete(f"session:{session_id}:context")
    
    async def _get_session(self, session_id: str, db: AsyncSession) -> Optional[ChatSessionDB]:
        """Get session from database"""
        result = await db.execute(
            select(ChatSessionDB).where(
                ChatSessionDB.id == session_id,
                ChatSessionDB.status == SessionStatus.ACTIVE
            )
        )
        return result.scalar_one_or_none()
    
    async def _update_session_activity(self, session_id: str) -> None:
        """Update session last activity time"""
        await self.redis_client.hset(
            f"session:{session_id}",
            "last_activity",
            datetime.utcnow().isoformat()
        )
        await self.redis_client.expire(
            f"session:{session_id}",
            settings.session_ttl_hours * 3600
        )
    
    async def _get_session_context(self, session_id: str) -> Dict:
        """Get session context for conversation continuity"""
        context_key = f"session:{session_id}:context"
        context = await self.redis_client.get(context_key)
        
        if context:
            return json.loads(context)
        
        return {
            "turn_count": 0,
            "last_entities": [],
            "last_intent": None,
            "conversation_summary": ""
        }
    
    async def _update_session_context(self, session_id: str, 
                                    info_needs: InformationNeeds,
                                    retrieved_context: Dict) -> None:
        """Update session context after each turn"""
        current_context = await self._get_session_context(session_id)
        
        # Update context
        current_context["turn_count"] += 1
        current_context["last_entities"] = [
            {"type": e.entity_type, "value": e.value}
            for e in info_needs.entities
        ]
        current_context["last_intent"] = info_needs.intent.value
        current_context["last_query"] = info_needs.query
        
        # Store updated context
        context_key = f"session:{session_id}:context"
        await self.redis_client.set(
            context_key,
            json.dumps(current_context),
            ex=settings.context_cache_ttl_seconds
        )
    
    async def _generate_response(self, user_message: str, 
                               info_needs: InformationNeeds,
                               context: Dict,
                               session_context: Dict) -> str:
        """Generate response using GPT-4 with retrieved context"""
        
        # Prepare context summary
        context_summary = self._prepare_context_summary(context)
        
        # Build prompt
        system_prompt = """You are Saathy, an intelligent AI copilot that helps users navigate their work across multiple platforms (Slack, GitHub, Notion, etc.).

Your role is to:
1. Answer questions based on the provided context
2. Help users understand what they need to do
3. Explain connections between different events and actions
4. Provide clear, actionable insights

Keep responses conversational but informative. Reference specific information from the context when relevant."""

        user_prompt = f"""User Query: {user_message}

Query Intent: {info_needs.intent.value}
Session Turn: {session_context.get('turn_count', 0) + 1}

Retrieved Context:
{context_summary}

Previous Conversation Context:
- Last Intent: {session_context.get('last_intent', 'None')}
- Last Entities: {json.dumps(session_context.get('last_entities', []))}

Generate a helpful response that directly addresses the user's query using the provided context."""

        try:
            response = await openai.ChatCompletion.acreate(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Response generation error: {e}")
            return "I apologize, but I'm having trouble generating a response. Could you please try rephrasing your question?"
    
    def _prepare_context_summary(self, context: Dict) -> str:
        """Prepare context summary for response generation"""
        summary_parts = []
        
        # Add content results
        if context.get("content"):
            summary_parts.append("Relevant Content:")
            for item in context["content"][:3]:  # Top 3
                summary_parts.append(f"- [{item['source']}] {item['text'][:200]}...")
        
        # Add events
        if context.get("events"):
            summary_parts.append("\nRecent Events:")
            for event in context["events"][:5]:  # Top 5
                summary_parts.append(
                    f"- [{event['platform']}] {event['type']}: {event['description']}"
                )
        
        # Add actions
        if context.get("actions"):
            summary_parts.append("\nActions:")
            for action in context["actions"]:
                summary_parts.append(
                    f"- [{action['status']}] {action['description']} (Priority: {action['priority']})"
                )
        
        return "\n".join(summary_parts)
    
    def _extract_sources(self, context: Dict) -> List[Dict]:
        """Extract source information from context"""
        sources = []
        
        for item in context.get("content", [])[:3]:
            sources.append({
                "type": "content",
                "platform": item["source"],
                "timestamp": item["timestamp"],
                "preview": item["text"][:100] + "..."
            })
        
        for event in context.get("events", [])[:2]:
            sources.append({
                "type": "event",
                "platform": event["platform"],
                "timestamp": event["timestamp"],
                "preview": event["description"]
            })
        
        return sources
    
    async def _save_turn(self, session_id: str, user_message: str,
                       assistant_response: str, context: Dict,
                       retrieval_strategy: str, db: AsyncSession) -> None:
        """Save conversation turn to database"""
        turn = ChatTurnDB(
            session_id=session_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context_used=context,
            retrieval_strategy=retrieval_strategy
        )
        db.add(turn)
        await db.commit()