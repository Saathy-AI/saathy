"""
Response Generator Agent - Creates natural conversational responses.
Uses GPT-4 to generate contextual, helpful responses based on retrieved information.
"""

from typing import Dict, List, Any, Optional
import logging
from openai import AsyncOpenAI
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ResponseGeneratorAgent:
    """
    Generates natural language responses using:
    - Retrieved context
    - Query understanding
    - Conversation history
    - Sufficiency awareness
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.openai_client = AsyncOpenAI(api_key=config["openai_api_key"])
        self.max_context_length = config.get("max_context_length", 4000)
        self.temperature = config.get("response_temperature", 0.7)
    
    async def generate(self, query: str, context: Dict[str, Any], 
                      information_needs: Dict[str, Any],
                      conversation_history: List[Dict[str, Any]],
                      sufficiency_score: float) -> Dict[str, Any]:
        """
        Generate a response based on retrieved context and query understanding.
        
        Returns:
            Dict containing:
            - response: The generated response text
            - context_used: Summary of what context was used
            - tokens_used: Number of tokens consumed
        """
        
        # Prepare context for response generation
        context_summary = self._prepare_context_summary(
            context.get("all_results", []),
            information_needs
        )
        
        # Build conversation context
        conversation_context = self._build_conversation_context(conversation_history)
        
        # Generate response with appropriate strategy
        if sufficiency_score < 0.5:
            response_data = await self._generate_low_confidence_response(
                query, context_summary, information_needs, conversation_context
            )
        elif sufficiency_score < 0.8:
            response_data = await self._generate_partial_response(
                query, context_summary, information_needs, conversation_context
            )
        else:
            response_data = await self._generate_confident_response(
                query, context_summary, information_needs, conversation_context
            )
        
        # Extract context attribution
        context_used = self._extract_context_attribution(
            context.get("all_results", []),
            response_data["response"]
        )
        
        return {
            "response": response_data["response"],
            "context_used": context_used,
            "tokens_used": response_data.get("tokens_used", 0),
            "confidence_level": self._determine_confidence_level(sufficiency_score),
            "generation_timestamp": datetime.utcnow().isoformat()
        }
    
    def _prepare_context_summary(self, results: List[Any], 
                               information_needs: Dict[str, Any]) -> str:
        """Prepare context for the LLM, prioritizing relevant information"""
        
        if not results:
            return "No relevant context found."
        
        # Group by source/platform for better organization
        grouped_context = {}
        for result in results[:15]:  # Limit to top 15 results
            platform = result.metadata.get("platform", "unknown")
            if platform not in grouped_context:
                grouped_context[platform] = []
            
            # Format result for inclusion
            timestamp_str = ""
            if hasattr(result, 'timestamp') and result.timestamp:
                timestamp_str = f"[{result.timestamp.strftime('%Y-%m-%d %H:%M')}] "
            
            grouped_context[platform].append({
                "content": result.content[:500],  # Limit content length
                "timestamp": timestamp_str,
                "metadata": result.metadata
            })
        
        # Build formatted context string
        context_parts = []
        for platform, items in grouped_context.items():
            context_parts.append(f"\n=== {platform.upper()} ===")
            for item in items:
                context_parts.append(f"{item['timestamp']}{item['content']}")
        
        return "\n".join(context_parts)
    
    def _build_conversation_context(self, history: List[Dict[str, Any]]) -> str:
        """Build conversation history context"""
        
        if not history:
            return ""
        
        context_parts = ["Previous conversation:"]
        for turn in history[-3:]:  # Last 3 turns
            context_parts.append(f"User: {turn.get('user_message', '')}")
            response = turn.get('assistant_response', '')
            if len(response) > 200:
                response = response[:200] + "..."
            context_parts.append(f"Assistant: {response}")
        
        return "\n".join(context_parts)
    
    async def _generate_confident_response(self, query: str, context: str, 
                                         information_needs: Dict[str, Any],
                                         conversation_context: str) -> Dict[str, Any]:
        """Generate response when we have high confidence in the context"""
        
        system_prompt = """You are Saathy, an intelligent AI assistant that helps developers by providing contextual information from their work across multiple platforms.

You have access to relevant context from Slack, GitHub, Notion, and other platforms. Provide helpful, accurate responses based on the retrieved information.

Guidelines:
1. Be conversational and natural
2. Reference specific information from the context
3. Mention sources when relevant (e.g., "According to the Slack discussion...")
4. Be concise but comprehensive
5. Offer to help with follow-up questions"""

        user_prompt = f"""
Query: "{query}"
Intent: {information_needs.get('intent', 'unknown')}
Looking for: {json.dumps(information_needs.get('entities', {}))}

{conversation_context}

Retrieved Context:
{context}

Please provide a helpful response based on this information.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=800
            )
            
            return {
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "response": "I encountered an error while generating a response. Please try again.",
                "tokens_used": 0
            }
    
    async def _generate_partial_response(self, query: str, context: str, 
                                       information_needs: Dict[str, Any],
                                       conversation_context: str) -> Dict[str, Any]:
        """Generate response when we have partial context"""
        
        system_prompt = """You are Saathy, an intelligent AI assistant. You have found some relevant information but it may not be complete.

Guidelines:
1. Share what you found
2. Be transparent about potential gaps
3. Suggest what additional information might help
4. Offer to search more broadly or in different time ranges
5. Still be helpful with what you have"""

        user_prompt = f"""
Query: "{query}"
Intent: {information_needs.get('intent', 'unknown')}

{conversation_context}

Retrieved Context (may be incomplete):
{context}

Provide a helpful response, acknowledging any limitations in the available information.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=800
            )
            
            return {
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating partial response: {str(e)}")
            return {
                "response": "I found some information but encountered an error processing it. Please try rephrasing your question.",
                "tokens_used": 0
            }
    
    async def _generate_low_confidence_response(self, query: str, context: str, 
                                              information_needs: Dict[str, Any],
                                              conversation_context: str) -> Dict[str, Any]:
        """Generate response when we have low confidence in the context"""
        
        system_prompt = """You are Saathy, an intelligent AI assistant. You couldn't find sufficient information to fully answer the query.

Guidelines:
1. Be honest about the limitations
2. Share any relevant information you did find
3. Suggest alternative queries or approaches
4. Ask clarifying questions if needed
5. Remain helpful and positive"""

        user_prompt = f"""
Query: "{query}"
Intent: {information_needs.get('intent', 'unknown')}

{conversation_context}

Limited Context Found:
{context}

Provide a helpful response that acknowledges the limited information and suggests next steps.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=600
            )
            
            return {
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating low confidence response: {str(e)}")
            return {
                "response": "I couldn't find enough information to answer your question. Could you provide more details or try a different query?",
                "tokens_used": 0
            }
    
    def _extract_context_attribution(self, results: List[Any], response: str) -> List[Dict[str, Any]]:
        """Extract which context pieces were likely used in the response"""
        
        used_context = []
        response_lower = response.lower()
        
        for result in results[:10]:  # Check top 10 results
            # Simple heuristic: check if key phrases from context appear in response
            content_words = set(result.content.lower().split())
            response_words = set(response_lower.split())
            
            # Calculate overlap
            overlap = len(content_words.intersection(response_words))
            
            if overlap > 5:  # Threshold for considering it "used"
                used_context.append({
                    "platform": result.metadata.get("platform", "unknown"),
                    "timestamp": result.timestamp.isoformat() if hasattr(result, 'timestamp') else None,
                    "relevance": "high" if overlap > 10 else "medium",
                    "preview": result.content[:100] + "..."
                })
        
        return used_context
    
    def _determine_confidence_level(self, sufficiency_score: float) -> str:
        """Determine confidence level based on sufficiency score"""
        
        if sufficiency_score >= 0.8:
            return "high"
        elif sufficiency_score >= 0.5:
            return "medium"
        else:
            return "low"