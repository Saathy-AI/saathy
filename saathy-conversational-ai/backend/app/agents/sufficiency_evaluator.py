"""
Context Sufficiency Evaluator Agent - Determines if retrieved context is sufficient.
Uses multi-dimensional scoring to evaluate context completeness.
"""

import json
import logging
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class SufficiencyEvaluatorAgent:
    """
    Evaluates context sufficiency using multiple dimensions:
    - Entity coverage
    - Temporal relevance
    - Platform coverage
    - GPT-4 completeness check

    Returns a score and identifies gaps for potential expansion.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.openai_client = AsyncOpenAI(api_key=config["openai_api_key"])

        # Scoring weights
        self.weights = {
            "entity_coverage": 0.3,
            "temporal_relevance": 0.2,
            "gpt4_completeness": 0.4,
            "platform_coverage": 0.1,
        }

        # Sufficiency threshold
        self.sufficiency_threshold = config.get("sufficiency_threshold", 0.7)

    async def evaluate(
        self, query: str, context: dict[str, Any], information_needs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Evaluate if the retrieved context is sufficient to answer the query.

        Returns:
            Dict containing:
            - score: Overall sufficiency score (0-1)
            - gaps: List of identified gaps
            - dimension_scores: Individual dimension scores
            - recommendations: Suggestions for improvement
        """

        # Extract results from context
        all_results = context.get("all_results", [])

        if not all_results:
            return {
                "score": 0.0,
                "gaps": ["no_context_retrieved"],
                "dimension_scores": {},
                "recommendations": ["expand_search_criteria"],
            }

        # Calculate individual dimension scores
        entity_score = self._calculate_entity_coverage(all_results, information_needs)
        temporal_score = self._calculate_temporal_relevance(
            all_results, information_needs
        )
        platform_score = self._calculate_platform_coverage(
            all_results, information_needs
        )

        # GPT-4 completeness check (most important)
        gpt4_score = await self._gpt4_completeness_check(
            query, all_results, information_needs
        )

        # Calculate weighted overall score
        dimension_scores = {
            "entity_coverage": entity_score,
            "temporal_relevance": temporal_score,
            "platform_coverage": platform_score,
            "gpt4_completeness": gpt4_score,
        }

        overall_score = sum(
            score * self.weights[dimension]
            for dimension, score in dimension_scores.items()
        )

        # Identify gaps
        gaps = self._identify_gaps(dimension_scores, information_needs, all_results)

        # Generate recommendations
        recommendations = self._generate_recommendations(gaps, dimension_scores)

        logger.info(
            f"Sufficiency evaluation - Score: {overall_score:.2f}, Gaps: {gaps}"
        )

        return {
            "score": overall_score,
            "gaps": gaps,
            "dimension_scores": dimension_scores,
            "recommendations": recommendations,
            "context_size": len(all_results),
            "evaluation_timestamp": datetime.utcnow().isoformat(),
        }

    def _calculate_entity_coverage(
        self, results: list[Any], information_needs: dict[str, Any]
    ) -> float:
        """
        Calculate how well the retrieved context covers mentioned entities.
        """

        entities = information_needs.get("entities", {})
        if not entities:
            return 1.0  # No specific entities requested

        # Flatten all entity lists
        all_entities = []
        for _entity_type, entity_list in entities.items():
            all_entities.extend(entity_list)

        if not all_entities:
            return 1.0

        # Check coverage in results
        covered_entities = set()

        for result in results:
            content_lower = result.content.lower()
            metadata_str = str(result.metadata).lower()

            for entity in all_entities:
                if entity.lower() in content_lower or entity.lower() in metadata_str:
                    covered_entities.add(entity.lower())

        # Calculate coverage ratio
        coverage = len(covered_entities) / len({e.lower() for e in all_entities})

        logger.debug(
            f"Entity coverage: {len(covered_entities)}/{len(all_entities)} = {coverage:.2f}"
        )

        return coverage

    def _calculate_temporal_relevance(
        self, results: list[Any], information_needs: dict[str, Any]
    ) -> float:
        """
        Calculate temporal relevance of retrieved context.
        """

        time_range = information_needs.get("time_range", {})
        if not time_range or "start" not in time_range:
            return 1.0  # No specific time requirements

        start_time = time_range["start"]
        end_time = time_range.get("end", datetime.utcnow())

        # Check how many results fall within the requested time range
        relevant_count = 0
        total_with_timestamp = 0

        for result in results:
            if hasattr(result, "timestamp") and result.timestamp:
                total_with_timestamp += 1
                if start_time <= result.timestamp <= end_time:
                    relevant_count += 1

        if total_with_timestamp == 0:
            return 0.5  # No temporal information available

        relevance = relevant_count / total_with_timestamp

        # Boost score if we have good coverage of the time range
        if relevant_count >= 3:  # At least 3 relevant results
            relevance = min(relevance * 1.2, 1.0)

        logger.debug(
            f"Temporal relevance: {relevant_count}/{total_with_timestamp} = {relevance:.2f}"
        )

        return relevance

    def _calculate_platform_coverage(
        self, results: list[Any], information_needs: dict[str, Any]
    ) -> float:
        """
        Calculate platform coverage in retrieved context.
        """

        requested_platforms = information_needs.get("platforms", [])
        if not requested_platforms:
            return 1.0  # No specific platforms requested

        # Check which platforms are represented in results
        covered_platforms = set()

        for result in results:
            platform = result.metadata.get("platform", "").lower()
            if platform in [p.lower() for p in requested_platforms]:
                covered_platforms.add(platform)

        coverage = len(covered_platforms) / len(requested_platforms)

        logger.debug(f"Platform coverage: {covered_platforms} = {coverage:.2f}")

        return coverage

    async def _gpt4_completeness_check(
        self, query: str, results: list[Any], information_needs: dict[str, Any]
    ) -> float:
        """
        Use GPT-4 to evaluate if the context can answer the query.
        """

        # Prepare context summary
        context_summary = self._prepare_context_summary(results[:10])  # Top 10 results

        system_prompt = """You are evaluating whether the provided context is sufficient to answer a user's query.

        Score the completeness on a scale of 0-1:
        - 1.0: Context fully answers the query with all necessary details
        - 0.8: Context mostly answers the query, minor details might be missing
        - 0.6: Context partially answers the query, some important information missing
        - 0.4: Context has relevant information but major gaps
        - 0.2: Context is somewhat related but insufficient
        - 0.0: Context cannot answer the query

        Also identify what's missing if the score is below 0.8.

        Return a JSON object with 'score' and 'missing_elements' fields."""

        user_prompt = f"""
        User Query: "{query}"

        Query Intent: {information_needs.get('intent', 'unknown')}
        Looking for: {json.dumps(information_needs.get('entities', {}))}

        Retrieved Context:
        {context_summary}

        Can this context sufficiently answer the user's query?
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

            result = json.loads(response.choices[0].message.content)
            return result.get("score", 0.5)

        except Exception as e:
            logger.error(f"GPT-4 completeness check failed: {str(e)}")
            return 0.5  # Default middle score on error

    def _prepare_context_summary(self, results: list[Any]) -> str:
        """Prepare a summary of context for GPT-4 evaluation"""

        summary_parts = []

        for i, result in enumerate(results, 1):
            # Include source, timestamp, and content preview
            timestamp_str = ""
            if hasattr(result, "timestamp") and result.timestamp:
                timestamp_str = f" [{result.timestamp.strftime('%Y-%m-%d %H:%M')}]"

            platform = result.metadata.get("platform", "unknown")
            content_preview = (
                result.content[:200] + "..."
                if len(result.content) > 200
                else result.content
            )

            summary_parts.append(f"{i}. {platform}{timestamp_str}: {content_preview}")

        return "\n".join(summary_parts)

    def _identify_gaps(
        self,
        dimension_scores: dict[str, float],
        information_needs: dict[str, Any],
        results: list[Any],
    ) -> list[str]:
        """Identify specific gaps in context coverage"""

        gaps = []

        # Entity coverage gaps
        if dimension_scores["entity_coverage"] < 0.6:
            gaps.append("entity_coverage")

        # Temporal coverage gaps
        if dimension_scores["temporal_relevance"] < 0.6:
            gaps.append("temporal_coverage")

        # Platform diversity gaps
        if dimension_scores["platform_coverage"] < 0.6:
            gaps.append("platform_diversity")

        # Overall completeness gaps
        if dimension_scores["gpt4_completeness"] < 0.6:
            gaps.append("content_completeness")

        # Check for specific missing elements
        if information_needs.get("intent") == "query_actions" and not self._has_actions(
            results
        ):
            gaps.append("missing_actions")

        if information_needs.get("intent") == "query_events" and len(results) < 3:
            gaps.append("insufficient_events")

        return gaps

    def _has_actions(self, results: list[Any]) -> bool:
        """Check if results contain action items"""
        for result in results:
            if result.source == "action" or "action" in result.metadata.get("type", ""):
                return True
        return False

    def _generate_recommendations(
        self, gaps: list[str], dimension_scores: dict[str, float]
    ) -> list[str]:
        """Generate recommendations based on identified gaps"""

        recommendations = []

        if "entity_coverage" in gaps:
            recommendations.append("expand_entity_search")

        if "temporal_coverage" in gaps:
            recommendations.append("extend_time_range")

        if "platform_diversity" in gaps:
            recommendations.append("search_additional_platforms")

        if "content_completeness" in gaps:
            recommendations.append("broaden_search_terms")

        if "missing_actions" in gaps:
            recommendations.append("include_action_items")

        if "insufficient_events" in gaps:
            recommendations.append("retrieve_more_events")

        # If everything looks good but score is still low
        if not recommendations and dimension_scores.get("gpt4_completeness", 0) < 0.7:
            recommendations.append("refine_query_understanding")

        return recommendations
