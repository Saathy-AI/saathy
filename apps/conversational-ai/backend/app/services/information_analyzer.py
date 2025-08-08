import json
import re
from datetime import datetime, timedelta
from typing import Optional

import openai
from config.settings import get_settings

from app.models.information_needs import (
    ExtractedEntity,
    InformationNeeds,
    QueryAnalysisResult,
    QueryIntent,
    TimeReference,
)

settings = get_settings()
openai.api_key = settings.openai_api_key


class BasicInformationAnalyzer:
    """Analyzes user queries to extract information needs"""

    def __init__(self):
        self.intent_patterns = {
            QueryIntent.QUERY_ACTIONS: [
                r"what should i do",
                r"what do i need to",
                r"what's? (?:next|pending|urgent)",
                r"my (?:tasks?|actions?|todos?)",
            ],
            QueryIntent.QUERY_EVENTS: [
                r"what happened (?:with|to|in)",
                r"tell me about",
                r"update me on",
                r"status of",
            ],
            QueryIntent.GET_CONTEXT: [
                r"show me (?:the )?(.*) project",
                r"(?:get|fetch|display) (.*) (?:info|information|details)",
                r"everything (?:about|related to)",
            ],
            QueryIntent.EXPLAIN_ACTION: [
                r"why (?:do you|did you|are you) suggest",
                r"explain (?:the|this) (?:action|recommendation)",
                r"reason for",
            ],
            QueryIntent.TIMELINE_QUERY: [
                r"what happened (?:yesterday|today|this week|last week)",
                r"timeline of",
                r"history of",
            ],
            QueryIntent.SEARCH_CONTENT: [
                r"find (?:me )?(.*)",
                r"search for (.*)",
                r"look for (.*)",
            ],
        }

        self.time_patterns = {
            "today": lambda: (datetime.now().replace(hour=0, minute=0), datetime.now()),
            "yesterday": lambda: (
                (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0),
                (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59),
            ),
            "this week": lambda: (
                datetime.now() - timedelta(days=datetime.now().weekday()),
                datetime.now(),
            ),
            "last week": lambda: (
                datetime.now() - timedelta(days=datetime.now().weekday() + 7),
                datetime.now() - timedelta(days=datetime.now().weekday()),
            ),
            "last (\\d+) days?": lambda match: (
                datetime.now() - timedelta(days=int(match.group(1))),
                datetime.now(),
            ),
            "past (\\d+) hours?": lambda match: (
                datetime.now() - timedelta(hours=int(match.group(1))),
                datetime.now(),
            ),
        }

        self.platform_keywords = {
            "slack": ["slack", "channel", "dm", "thread"],
            "github": ["github", "pr", "pull request", "issue", "commit", "review"],
            "notion": ["notion", "doc", "document", "page", "wiki"],
            "jira": ["jira", "ticket", "story", "epic", "sprint"],
        }

    async def analyze_query(
        self, user_message: str, user_id: str, session_context: Optional[dict] = None
    ) -> QueryAnalysisResult:
        """Analyze user query to extract information needs"""

        # Start with pattern-based analysis
        intent, intent_confidence = self._detect_intent(user_message)
        time_reference = self._extract_time_reference(user_message)
        platforms = self._detect_platforms(user_message)
        entities = self._extract_basic_entities(user_message)

        # Determine complexity
        complexity = self._assess_complexity(user_message, entities, platforms)

        # For complex queries, enhance with GPT-4
        if complexity != "simple" or intent_confidence < 0.7:
            enhanced_analysis = await self._gpt4_analysis(
                user_message, intent, entities, session_context
            )
            intent = enhanced_analysis.get("intent", intent)
            intent_confidence = enhanced_analysis.get("confidence", intent_confidence)
            entities.extend(enhanced_analysis.get("entities", []))

        # Build information needs
        info_needs = InformationNeeds(
            query=user_message,
            user_id=user_id,
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities,
            time_reference=time_reference,
            platforms=platforms,
            complexity=complexity,
            requires_correlation=len(platforms) > 1,
            requires_explanation=intent == QueryIntent.EXPLAIN_ACTION,
            required_context_types=self._determine_required_context(intent, platforms),
            session_context=session_context or {},
            previous_turn_relevant=self._check_turn_relevance(
                user_message, session_context
            ),
        )

        # Determine retrieval strategies
        strategies = self._suggest_retrieval_strategies(info_needs)

        return QueryAnalysisResult(
            information_needs=info_needs,
            confidence_score=intent_confidence,
            suggested_retrieval_strategies=strategies,
        )

    def _detect_intent(self, query: str) -> tuple[QueryIntent, float]:
        """Detect query intent using pattern matching"""
        query_lower = query.lower()
        best_match = (QueryIntent.GENERAL_HELP, 0.3)

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return (intent, 0.9)

        return best_match

    def _extract_time_reference(self, query: str) -> Optional[TimeReference]:
        """Extract temporal references from query"""
        query_lower = query.lower()

        for pattern, time_func in self.time_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if callable(time_func):
                    start, end = time_func() if not match.groups() else time_func(match)
                    return TimeReference(
                        reference_type="relative",
                        start_time=start,
                        end_time=end,
                        relative_expression=match.group(0),
                    )

        # Check for absolute dates (simple pattern)
        date_pattern = r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
        date_match = re.search(date_pattern, query)
        if date_match:
            # Simple date parsing (can be enhanced)
            return TimeReference(
                reference_type="absolute", relative_expression=date_match.group(0)
            )

        return None

    def _detect_platforms(self, query: str) -> set:
        """Detect mentioned platforms"""
        query_lower = query.lower()
        detected = set()

        for platform, keywords in self.platform_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.add(platform)

        return detected

    def _extract_basic_entities(self, query: str) -> list[ExtractedEntity]:
        """Extract basic entities using patterns"""
        entities = []

        # Extract quoted strings as potential project/feature names
        quoted = re.findall(r'"([^"]+)"', query)
        for q in quoted:
            entities.append(
                ExtractedEntity(entity_type="project", value=q, confidence=0.8)
            )

        # Extract potential project names (capitalized words)
        cap_words = re.findall(r"\b[A-Z][a-zA-Z]+\b", query)
        for word in cap_words:
            if word not in ["I", "The", "What", "Why", "How"]:
                entities.append(
                    ExtractedEntity(entity_type="project", value=word, confidence=0.5)
                )

        # Extract @mentions as people
        mentions = re.findall(r"@(\w+)", query)
        for mention in mentions:
            entities.append(
                ExtractedEntity(entity_type="person", value=mention, confidence=0.9)
            )

        return entities

    def _assess_complexity(
        self, query: str, entities: list[ExtractedEntity], platforms: set
    ) -> str:
        """Assess query complexity"""
        word_count = len(query.split())
        entity_count = len(entities)
        platform_count = len(platforms)

        if word_count > 20 or entity_count > 3 or platform_count > 2:
            return "complex"
        elif word_count > 10 or entity_count > 1 or platform_count > 1:
            return "moderate"
        else:
            return "simple"

    async def _gpt4_analysis(
        self,
        query: str,
        initial_intent: QueryIntent,
        initial_entities: list[ExtractedEntity],
        session_context: Optional[dict],
    ) -> dict:
        """Enhanced analysis using GPT-4"""

        prompt = f"""Analyze this user query for a conversational AI system:
Query: "{query}"

Initial analysis:
- Intent: {initial_intent.value}
- Entities: {[e.dict() for e in initial_entities]}
- Session context: {json.dumps(session_context or {}, indent=2)}

Extract:
1. The primary intent (one of: query_actions, query_events, get_context, explain_action, general_help, timeline_query, search_content)
2. Confidence score (0-1)
3. Additional entities (projects, people, features, platforms)
4. Any implicit time references

Return JSON format:
{{
    "intent": "intent_name",
    "confidence": 0.9,
    "entities": [
        {{"entity_type": "project", "value": "Dashboard", "confidence": 0.8}},
        ...
    ],
    "time_context": "description of temporal context if any"
}}"""

        try:
            response = await openai.ChatCompletion.acreate(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing user queries.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result = json.loads(response.choices[0].message.content)

            # Convert entities to ExtractedEntity objects
            entities = [ExtractedEntity(**e) for e in result.get("entities", [])]

            return {
                "intent": QueryIntent(result.get("intent", initial_intent.value)),
                "confidence": result.get("confidence", 0.7),
                "entities": entities,
            }

        except Exception as e:
            print(f"GPT-4 analysis failed: {e}")
            return {"intent": initial_intent, "confidence": 0.5, "entities": []}

    def _determine_required_context(
        self, intent: QueryIntent, platforms: set
    ) -> list[str]:
        """Determine what types of context are needed"""
        context_types = []

        if intent == QueryIntent.QUERY_ACTIONS:
            context_types.extend(["actions", "tasks", "deadlines"])
        elif intent == QueryIntent.QUERY_EVENTS:
            context_types.extend(["events", "timeline", "changes"])
        elif intent == QueryIntent.GET_CONTEXT:
            context_types.extend(["documents", "discussions", "code"])
        elif intent == QueryIntent.EXPLAIN_ACTION:
            context_types.extend(["action_history", "reasoning", "context"])

        # Add platform-specific context
        if "github" in platforms:
            context_types.extend(["pull_requests", "issues", "commits"])
        if "slack" in platforms:
            context_types.extend(["messages", "threads"])
        if "notion" in platforms:
            context_types.extend(["documents", "pages"])

        return list(set(context_types))

    def _check_turn_relevance(
        self, query: str, session_context: Optional[dict]
    ) -> bool:
        """Check if previous conversation turn is relevant"""
        if not session_context or "last_entities" not in session_context:
            return False

        # Check for pronouns or references
        pronouns = ["it", "that", "this", "them", "those"]
        query_lower = query.lower()

        return any(pronoun in query_lower.split() for pronoun in pronouns)

    def _suggest_retrieval_strategies(self, info_needs: InformationNeeds) -> list[str]:
        """Suggest retrieval strategies based on information needs"""
        strategies = ["hybrid"]  # Always use hybrid as base

        if info_needs.time_reference:
            strategies.append("temporal_focused")

        if len(info_needs.platforms) > 1:
            strategies.append("cross_platform_correlation")

        if info_needs.intent == QueryIntent.EXPLAIN_ACTION:
            strategies.append("action_context_retrieval")

        if info_needs.complexity == "complex":
            strategies.append("multi_stage_expansion")

        return strategies
