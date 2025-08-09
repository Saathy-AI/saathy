"""
Compressive Memory Manager - Implements COMEDY framework for conversation memory.
Efficiently compresses and manages conversation context across multiple turns.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CompressiveMemoryManager:
    """
    Implements the COMEDY (Compressive Memory for Dialog) framework.

    Key features:
    - Extracts and preserves key information across conversation turns
    - Tracks user preferences and patterns
    - Maintains entity and relationship dynamics
    - Provides compressed but comprehensive conversation context
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.openai_client = AsyncOpenAI(api_key=config["openai_api_key"])

        # Memory configuration
        self.max_recent_turns = config.get("max_recent_turns", 3)
        self.compression_threshold = config.get("compression_threshold", 5)
        self.entity_importance_threshold = config.get(
            "entity_importance_threshold", 0.6
        )

        # Memory structure
        self.memory_schema = {
            "user_profile": {},
            "key_events": [],
            "entity_tracking": {},
            "relationships": {},
            "conversation_patterns": {},
            "recent_context": [],
        }

    async def compress_conversation(
        self, session_turns: list[dict[str, Any]], user_id: str
    ) -> dict[str, Any]:
        """
        Compress conversation history using COMEDY framework.

        Args:
            session_turns: List of conversation turns
            user_id: User identifier

        Returns:
            Compressed memory representation
        """

        if len(session_turns) < self.compression_threshold:
            # Not enough turns to compress, return as-is
            return {
                "compressed": False,
                "memory": {
                    "recent_context": session_turns[-self.max_recent_turns :],
                    "turn_count": len(session_turns),
                },
            }

        # Extract various aspects of the conversation
        user_profile = await self._extract_user_profile(session_turns, user_id)
        key_events = self._extract_key_events(session_turns)
        entity_tracking = self._track_entities(session_turns)
        relationships = self._extract_relationships(session_turns)
        patterns = self._identify_conversation_patterns(session_turns)

        # Create compressed representation
        compressed_memory = {
            "user_profile": user_profile,
            "key_events": key_events,
            "entity_tracking": entity_tracking,
            "relationships": relationships,
            "conversation_patterns": patterns,
            "recent_context": session_turns[-self.max_recent_turns :],
            "metadata": {
                "original_turn_count": len(session_turns),
                "compression_ratio": self._calculate_compression_ratio(
                    session_turns, key_events
                ),
                "compressed_at": datetime.utcnow().isoformat(),
            },
        }

        logger.info(
            f"Compressed {len(session_turns)} turns to {len(key_events)} key events"
        )

        return {"compressed": True, "memory": compressed_memory}

    async def _extract_user_profile(
        self, turns: list[dict[str, Any]], user_id: str
    ) -> dict[str, Any]:
        """Extract user preferences and patterns using GPT-4"""

        # Prepare conversation summary for analysis
        conversation_text = self._prepare_conversation_text(
            turns[:10]
        )  # Analyze first 10 turns

        system_prompt = """Analyze this conversation to extract user profile information:

        1. Communication style (formal/casual, verbose/concise)
        2. Domain interests (what projects, features, or areas they ask about)
        3. Preferred information density (detailed/summary)
        4. Common query patterns
        5. Time preferences (when they usually need information)

        Return a JSON object with these profile elements."""

        user_prompt = f"""
        User ID: {user_id}

        Conversation:
        {conversation_text}

        Extract user profile information.
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            profile = json.loads(response.choices[0].message.content)
            profile["user_id"] = user_id
            profile["extracted_at"] = datetime.utcnow().isoformat()

            return profile

        except Exception as e:
            logger.error(f"Failed to extract user profile: {str(e)}")
            return {"user_id": user_id, "error": "extraction_failed"}

    def _extract_key_events(self, turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract key events and important moments from conversation"""

        key_events = []

        for i, turn in enumerate(turns):
            # Calculate importance score for each turn
            importance_score = self._calculate_turn_importance(turn, i, turns)

            if importance_score > self.entity_importance_threshold:
                event = {
                    "turn_index": i,
                    "timestamp": turn.get("timestamp", datetime.utcnow().isoformat()),
                    "query": turn.get("user_message", "")[:200],
                    "response_summary": self._summarize_response(
                        turn.get("assistant_response", "")
                    ),
                    "entities_mentioned": turn.get("entities", {}),
                    "intent": turn.get("intent", "unknown"),
                    "importance_score": importance_score,
                    "context_used": turn.get("context_used", []),
                }
                key_events.append(event)

        # Sort by importance and keep top events
        key_events.sort(key=lambda x: x["importance_score"], reverse=True)

        # Keep diverse set of events
        return self._diversify_events(key_events[:20])  # Keep top 20 events

    def _track_entities(self, turns: list[dict[str, Any]]) -> dict[str, Any]:
        """Track entity mentions and evolution throughout conversation"""

        entity_tracking = defaultdict(
            lambda: {
                "mentions": 0,
                "first_mentioned": None,
                "last_mentioned": None,
                "contexts": [],
                "related_entities": set(),
            }
        )

        for i, turn in enumerate(turns):
            entities = turn.get("entities", {})

            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    entity_key = f"{entity_type}:{entity.lower()}"

                    # Update tracking
                    entity_tracking[entity_key]["mentions"] += 1

                    if entity_tracking[entity_key]["first_mentioned"] is None:
                        entity_tracking[entity_key]["first_mentioned"] = i

                    entity_tracking[entity_key]["last_mentioned"] = i

                    # Track context
                    context = {
                        "turn": i,
                        "query": turn.get("user_message", "")[:100],
                        "intent": turn.get("intent", "unknown"),
                    }
                    entity_tracking[entity_key]["contexts"].append(context)

                    # Track co-occurring entities
                    for other_type, other_list in entities.items():
                        for other_entity in other_list:
                            if other_entity != entity:
                                entity_tracking[entity_key]["related_entities"].add(
                                    f"{other_type}:{other_entity.lower()}"
                                )

        # Convert sets to lists for serialization
        for entity_data in entity_tracking.values():
            entity_data["related_entities"] = list(entity_data["related_entities"])

        return dict(entity_tracking)

    def _extract_relationships(self, turns: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract relationships between entities, topics, and users"""

        relationships = {
            "user_entity_affinity": defaultdict(float),
            "entity_connections": defaultdict(set),
            "topic_progression": [],
        }

        previous_intent = None

        for turn in turns:
            # Track user affinity for entities
            entities = turn.get("entities", {})
            for _entity_type, entity_list in entities.items():
                for entity in entity_list:
                    relationships["user_entity_affinity"][entity.lower()] += 1

            # Track entity connections
            all_entities = []
            for entity_list in entities.values():
                all_entities.extend([e.lower() for e in entity_list])

            # Create connections between co-occurring entities
            for i, entity1 in enumerate(all_entities):
                for entity2 in all_entities[i + 1 :]:
                    relationships["entity_connections"][entity1].add(entity2)
                    relationships["entity_connections"][entity2].add(entity1)

            # Track topic progression
            current_intent = turn.get("intent", "unknown")
            if current_intent != previous_intent:
                relationships["topic_progression"].append(
                    {
                        "from": previous_intent,
                        "to": current_intent,
                        "turn": turns.index(turn),
                    }
                )
                previous_intent = current_intent

        # Convert sets to lists
        for entity, connections in relationships["entity_connections"].items():
            relationships["entity_connections"][entity] = list(connections)

        return dict(relationships)

    def _identify_conversation_patterns(
        self, turns: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Identify patterns in how the user interacts"""

        patterns = {
            "query_types": defaultdict(int),
            "time_patterns": defaultdict(int),
            "follow_up_frequency": 0,
            "average_session_length": len(turns),
            "platform_preferences": defaultdict(int),
        }

        for i, turn in enumerate(turns):
            # Query type patterns
            intent = turn.get("intent", "unknown")
            patterns["query_types"][intent] += 1

            # Time patterns (hour of day)
            timestamp = turn.get("timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                hour = timestamp.hour
                patterns["time_patterns"][f"hour_{hour}"] += 1

            # Platform preferences
            context_used = turn.get("context_used", [])
            for context in context_used:
                platform = context.get("platform", "unknown")
                patterns["platform_preferences"][platform] += 1

            # Follow-up detection
            if i > 0 and self._is_follow_up(turns[i - 1], turn):
                patterns["follow_up_frequency"] += 1

        # Convert to regular dicts
        patterns["query_types"] = dict(patterns["query_types"])
        patterns["time_patterns"] = dict(patterns["time_patterns"])
        patterns["platform_preferences"] = dict(patterns["platform_preferences"])

        # Calculate follow-up rate
        if len(turns) > 1:
            patterns["follow_up_rate"] = patterns["follow_up_frequency"] / (
                len(turns) - 1
            )

        return patterns

    def _calculate_turn_importance(
        self, turn: dict[str, Any], index: int, all_turns: list[dict[str, Any]]
    ) -> float:
        """Calculate importance score for a conversation turn"""

        score = 0.0

        # New entities introduced
        entities = turn.get("entities", {})
        entity_count = sum(len(v) for v in entities.values())
        score += min(entity_count * 0.1, 0.3)

        # Query complexity
        if turn.get("intent") in ["query_events", "explain_action"]:
            score += 0.2

        # Context richness
        context_used = turn.get("context_used", [])
        if len(context_used) > 3:
            score += 0.2

        # Follow-up indicator
        if index > 0 and self._is_follow_up(all_turns[index - 1], turn):
            score += 0.1

        # User satisfaction (heuristic based on response length)
        response = turn.get("assistant_response", "")
        if len(response) > 500:  # Detailed response
            score += 0.15

        # Recency boost
        recency_factor = (index / len(all_turns)) * 0.2
        score += recency_factor

        return min(score, 1.0)

    def _summarize_response(self, response: str) -> str:
        """Create a brief summary of the assistant's response"""

        if len(response) <= 150:
            return response

        # Simple extractive summary - take first and last sentences
        sentences = response.split(". ")
        if len(sentences) > 2:
            return f"{sentences[0]}... {sentences[-1]}"
        else:
            return response[:150] + "..."

    def _diversify_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure diversity in kept events"""

        if len(events) <= 10:
            return events

        # Keep events with different intents and time spans
        diverse_events = []
        seen_intents = set()

        # First pass: keep highest scoring event per intent
        for event in events:
            intent = event.get("intent", "unknown")
            if intent not in seen_intents:
                diverse_events.append(event)
                seen_intents.add(intent)

        # Second pass: fill remaining slots with high-importance events
        remaining_slots = 10 - len(diverse_events)
        for event in events:
            if event not in diverse_events and remaining_slots > 0:
                diverse_events.append(event)
                remaining_slots -= 1

        return diverse_events

    def _is_follow_up(
        self, prev_turn: dict[str, Any], current_turn: dict[str, Any]
    ) -> bool:
        """Determine if current turn is a follow-up to previous"""

        # Check entity overlap
        prev_entities = set()
        for entity_list in prev_turn.get("entities", {}).values():
            prev_entities.update([e.lower() for e in entity_list])

        current_entities = set()
        for entity_list in current_turn.get("entities", {}).values():
            current_entities.update([e.lower() for e in entity_list])

        # High overlap suggests follow-up
        if prev_entities and current_entities:
            overlap = len(prev_entities.intersection(current_entities)) / len(
                prev_entities
            )
            if overlap > 0.5:
                return True

        # Check for pronouns indicating continuation
        query = current_turn.get("user_message", "").lower()
        follow_up_indicators = ["it", "that", "this", "those", "more", "else", "also"]

        return any(indicator in query.split()[:5] for indicator in follow_up_indicators)

    def _prepare_conversation_text(self, turns: list[dict[str, Any]]) -> str:
        """Prepare conversation text for GPT-4 analysis"""

        text_parts = []

        for turn in turns:
            user_msg = turn.get("user_message", "")
            assistant_msg = turn.get("assistant_response", "")[:200]  # Limit length

            text_parts.append(f"User: {user_msg}")
            text_parts.append(f"Assistant: {assistant_msg}...")
            text_parts.append("")  # Empty line for separation

        return "\n".join(text_parts)

    def _calculate_compression_ratio(
        self, original_turns: list[dict[str, Any]], key_events: list[dict[str, Any]]
    ) -> float:
        """Calculate how much the conversation was compressed"""

        if not original_turns:
            return 0.0

        return 1 - (len(key_events) / len(original_turns))

    async def get_relevant_memory(
        self,
        query: str,
        information_needs: dict[str, Any],
        compressed_memory: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Retrieve relevant parts of compressed memory for current query.

        This is used to provide context from previous conversation turns.
        """

        relevant_memory = {
            "user_preferences": compressed_memory.get("user_profile", {}),
            "related_events": [],
            "mentioned_entities": {},
            "conversation_context": compressed_memory.get("recent_context", []),
        }

        # Find relevant key events
        query_entities = set()
        for entity_list in information_needs.get("entities", {}).values():
            query_entities.update([e.lower() for e in entity_list])

        for event in compressed_memory.get("key_events", []):
            event_entities = set()
            for entity_list in event.get("entities_mentioned", {}).values():
                event_entities.update([e.lower() for e in entity_list])

            # Check relevance
            if query_entities.intersection(event_entities) or event.get(
                "intent"
            ) == information_needs.get("intent"):
                relevant_memory["related_events"].append(event)

        # Get entity tracking info for mentioned entities
        entity_tracking = compressed_memory.get("entity_tracking", {})
        for entity in query_entities:
            for tracked_entity, info in entity_tracking.items():
                if entity in tracked_entity.lower():
                    relevant_memory["mentioned_entities"][tracked_entity] = info

        return relevant_memory
