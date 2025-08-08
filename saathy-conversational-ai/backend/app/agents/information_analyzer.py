"""
Information Analyzer Agent - GPT-4 powered query understanding.
Analyzes user queries to extract intent, entities, time references, and platform mentions.
"""

from typing import Dict, List, Any, Optional
import re
from datetime import datetime, timedelta
import logging
from openai import AsyncOpenAI
import json

logger = logging.getLogger(__name__)


class InformationAnalyzerAgent:
    """
    Analyzes user queries to understand:
    - Intent (query_actions, query_events, get_context, explain_action)
    - Entities (projects, people, features)
    - Time references
    - Platform mentions
    - Query complexity
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.openai_client = AsyncOpenAI(api_key=config["openai_api_key"])
        
        # Intent patterns for quick classification
        self.intent_patterns = {
            "query_actions": [
                r"what should i do",
                r"what.*my.*tasks",
                r"what.*pending",
                r"action items",
                r"todo"
            ],
            "query_events": [
                r"what happened",
                r"what.*discuss",
                r"show.*activity",
                r"recent.*changes",
                r"updates?"
            ],
            "get_context": [
                r"show me.*project",
                r"tell me about",
                r"information.*about",
                r"details.*on",
                r"explain.*project"
            ],
            "explain_action": [
                r"why.*suggest",
                r"why should i",
                r"reason.*for",
                r"explain.*recommendation"
            ]
        }
        
        # Platform keywords
        self.platform_keywords = {
            "slack": ["slack", "channel", "thread", "dm", "message"],
            "github": ["github", "pr", "pull request", "issue", "commit", "review"],
            "notion": ["notion", "doc", "document", "page", "wiki"],
            "jira": ["jira", "ticket", "story", "epic", "sprint"]
        }
    
    async def analyze(self, user_message: str, conversation_history: List[Dict[str, Any]], 
                     user_id: str) -> Dict[str, Any]:
        """
        Analyze user message to extract information needs.
        
        Returns structured information about what the user is looking for.
        """
        
        # Quick pattern-based intent classification
        initial_intent = self._classify_intent_patterns(user_message)
        
        # Extract entities and time references
        entities = self._extract_entities(user_message)
        time_refs = self._extract_time_references(user_message)
        platforms = self._detect_platforms(user_message)
        
        # Use GPT-4 for deeper analysis
        gpt_analysis = await self._gpt4_analyze(
            user_message, 
            conversation_history,
            initial_intent,
            entities
        )
        
        # Combine analyses
        information_needs = {
            "query": user_message,
            "intent": gpt_analysis.get("intent", initial_intent),
            "entities": {
                **entities,
                **gpt_analysis.get("entities", {})
            },
            "time_range": self._determine_time_range(time_refs, gpt_analysis.get("temporal_context")),
            "platforms": list(set(platforms + gpt_analysis.get("platforms", []))),
            "complexity": gpt_analysis.get("complexity", "simple"),
            "requires_context_from": gpt_analysis.get("requires_context_from", []),
            "conversation_context": self._extract_conversation_context(conversation_history),
            "user_id": user_id
        }
        
        logger.info(f"Analyzed query - Intent: {information_needs['intent']}, "
                   f"Entities: {len(information_needs['entities'])}, "
                   f"Platforms: {information_needs['platforms']}")
        
        return information_needs
    
    def _classify_intent_patterns(self, message: str) -> str:
        """Quick pattern-based intent classification"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        return "general_query"
    
    def _extract_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract named entities from the message"""
        entities = {
            "projects": [],
            "people": [],
            "features": [],
            "issues": []
        }
        
        # Project patterns (capitalized words, "X project", etc.)
        project_patterns = [
            r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+project\b',
            r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b'
        ]
        
        for pattern in project_patterns:
            matches = re.findall(pattern, message)
            entities["projects"].extend(matches)
        
        # People (@ mentions or names)
        people_pattern = r'@(\w+)|(?:with|from|by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        people_matches = re.findall(people_pattern, message)
        for match in people_matches:
            person = match[0] or match[1]
            if person:
                entities["people"].append(person)
        
        # Issue/bug references
        issue_patterns = [
            r'(?:issue|bug|ticket)\s*#?(\d+)',
            r'#(\d+)',
            r'([A-Z]+-\d+)'  # JIRA style
        ]
        
        for pattern in issue_patterns:
            matches = re.findall(pattern, message)
            entities["issues"].extend(matches)
        
        # Clean up duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def _extract_time_references(self, message: str) -> List[Dict[str, Any]]:
        """Extract temporal references from the message"""
        time_refs = []
        message_lower = message.lower()
        
        # Relative time patterns
        relative_patterns = {
            "today": timedelta(days=0),
            "yesterday": timedelta(days=1),
            "last week": timedelta(days=7),
            "this week": timedelta(days=0),  # Current week
            "last month": timedelta(days=30),
            "past hour": timedelta(hours=1),
            "past day": timedelta(days=1),
            "past week": timedelta(days=7)
        }
        
        for pattern, delta in relative_patterns.items():
            if pattern in message_lower:
                time_refs.append({
                    "type": "relative",
                    "reference": pattern,
                    "delta": delta
                })
        
        # Specific time patterns (e.g., "30 minutes", "2 hours ago")
        time_amount_pattern = r'(\d+)\s+(minute|hour|day|week)s?\s*(?:ago)?'
        matches = re.findall(time_amount_pattern, message_lower)
        for amount, unit in matches:
            delta = timedelta(**{f"{unit}s": int(amount)})
            time_refs.append({
                "type": "specific",
                "reference": f"{amount} {unit}s ago",
                "delta": delta
            })
        
        return time_refs
    
    def _detect_platforms(self, message: str) -> List[str]:
        """Detect which platforms are mentioned in the message"""
        message_lower = message.lower()
        detected = []
        
        for platform, keywords in self.platform_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected.append(platform)
        
        return detected
    
    async def _gpt4_analyze(self, message: str, conversation_history: List[Dict[str, Any]], 
                           initial_intent: str, initial_entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """Use GPT-4 for deeper query analysis"""
        
        system_prompt = """You are an expert at understanding user queries in a development context.
        Analyze the user's message and extract:
        1. Intent: What is the user trying to do? (query_actions, query_events, get_context, explain_action, general_query)
        2. Entities: Projects, people, features, or issues mentioned
        3. Temporal context: When is the user interested in? (specific times, ranges)
        4. Platforms: Which platforms should we search? (slack, github, notion, jira)
        5. Complexity: Is this a simple or complex query?
        6. Context requirements: What additional context might be needed?
        
        Return a JSON object with these fields."""
        
        # Build conversation context
        context = "Previous conversation:\n"
        for turn in conversation_history[-3:]:  # Last 3 turns
            context += f"User: {turn.get('user_message', '')}\n"
            context += f"Assistant: {turn.get('assistant_response', '')[:200]}...\n"
        
        user_prompt = f"""
        Current message: "{message}"
        
        Initial analysis:
        - Intent: {initial_intent}
        - Entities found: {json.dumps(initial_entities)}
        
        {context}
        
        Please provide a comprehensive analysis of what the user is looking for.
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"GPT-4 analysis failed: {str(e)}")
            # Fallback to initial analysis
            return {
                "intent": initial_intent,
                "entities": initial_entities,
                "complexity": "simple"
            }
    
    def _determine_time_range(self, time_refs: List[Dict[str, Any]], 
                             gpt_temporal: Optional[str]) -> Dict[str, Any]:
        """Determine the time range for the query"""
        
        if not time_refs and not gpt_temporal:
            # Default to last 7 days
            return {
                "start": datetime.utcnow() - timedelta(days=7),
                "end": datetime.utcnow(),
                "reference": "default_recent"
            }
        
        # Use the most specific time reference
        if time_refs:
            ref = time_refs[0]  # Take the first/most specific
            end_time = datetime.utcnow()
            start_time = end_time - ref["delta"]
            
            return {
                "start": start_time,
                "end": end_time,
                "reference": ref["reference"]
            }
        
        # Parse GPT temporal context if no explicit refs
        if gpt_temporal:
            # Handle GPT's temporal understanding
            # This would be more sophisticated in production
            return {
                "start": datetime.utcnow() - timedelta(days=7),
                "end": datetime.utcnow(),
                "reference": gpt_temporal
            }
    
    def _extract_conversation_context(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract relevant context from conversation history"""
        
        if not conversation_history:
            return {}
        
        # Extract mentioned entities across the conversation
        all_entities = {
            "projects": [],
            "people": [],
            "features": []
        }
        
        for turn in conversation_history[-5:]:  # Last 5 turns
            if "entities" in turn:
                for key in all_entities:
                    all_entities[key].extend(turn["entities"].get(key, []))
        
        # Deduplicate
        for key in all_entities:
            all_entities[key] = list(set(all_entities[key]))
        
        return {
            "mentioned_entities": all_entities,
            "turn_count": len(conversation_history)
        }