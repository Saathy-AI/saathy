"""
Context Retriever Agent - Advanced hybrid retrieval with Reciprocal Rank Fusion.
Orchestrates multiple retrieval strategies and intelligently fuses results.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np

from app.models.information_needs import InformationNeeds
from app.retrieval.hybrid_retriever import BasicHybridRetriever, SearchResult

logger = logging.getLogger(__name__)


class ContextRetrieverAgent:
    """
    Advanced context retrieval with:
    - Reciprocal Rank Fusion (RRF) for result merging
    - Temporal relevance weighting
    - Platform-specific boosting
    - Expansion-aware retrieval
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.basic_retriever = BasicHybridRetriever()
        self.rrf_k = config.get("rrf_k", 60)  # RRF constant
        self.initialized = False

    async def _ensure_initialized(self):
        """Ensure retriever is initialized"""
        if not self.initialized:
            await self.basic_retriever.initialize()
            self.initialized = True

    async def retrieve(
        self,
        information_needs: dict[str, Any],
        user_id: str,
        expansion_hints: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Retrieve context with advanced ranking and fusion.

        Args:
            information_needs: Analyzed query information
            user_id: User ID for personalization
            expansion_hints: Hints from sufficiency evaluator for expansion

        Returns:
            Retrieved and ranked context
        """

        await self._ensure_initialized()

        # Convert dict to InformationNeeds object for compatibility
        info_needs_obj = self._dict_to_info_needs(information_needs, user_id)

        # Apply expansion hints if provided
        if expansion_hints:
            info_needs_obj = self._apply_expansion_hints(
                info_needs_obj, expansion_hints
            )

        # Get results from multiple sources in parallel
        retrieval_results = await self.basic_retriever.retrieve_context(info_needs_obj)

        # Apply Reciprocal Rank Fusion
        fused_results = self._apply_rrf(retrieval_results, information_needs, user_id)

        # Apply additional boosting
        boosted_results = self._apply_relevance_boosting(
            fused_results, information_needs
        )

        # Structure final results
        return {
            "all_results": boosted_results[:20],  # Top 20 results
            "by_source": self._group_by_source(boosted_results[:20]),
            "by_platform": self._group_by_platform(boosted_results[:20]),
            "metadata": {
                "total_retrieved": sum(
                    len(results) for results in retrieval_results.values()
                ),
                "sources_used": list(retrieval_results.keys()),
                "expansion_applied": expansion_hints is not None,
                "retrieval_timestamp": datetime.utcnow().isoformat(),
            },
        }

    def _dict_to_info_needs(
        self, info_dict: dict[str, Any], user_id: str
    ) -> InformationNeeds:
        """Convert dictionary to InformationNeeds object"""
        return InformationNeeds(
            query=info_dict["query"],
            intent=info_dict.get("intent", "general_query"),
            entities=info_dict.get("entities", {}),
            time_range=info_dict.get("time_range", {}),
            platforms=info_dict.get("platforms", []),
            user_id=user_id,
        )

    def _apply_expansion_hints(
        self, info_needs: InformationNeeds, expansion_hints: list[str]
    ) -> InformationNeeds:
        """Apply expansion hints to information needs"""

        for hint in expansion_hints:
            if hint == "temporal_coverage":
                # Expand time range
                if hasattr(info_needs.time_range, "start"):
                    info_needs.time_range["start"] = info_needs.time_range[
                        "start"
                    ] - timedelta(days=7)

            elif hint == "platform_diversity":
                # Add more platforms if not specified
                if not info_needs.platforms:
                    info_needs.platforms = ["slack", "github", "notion"]

            elif hint == "entity_depth":
                # This would trigger deeper entity search in the retriever
                info_needs.metadata = info_needs.metadata or {}
                info_needs.metadata["expand_entities"] = True

        return info_needs

    def _apply_rrf(
        self,
        retrieval_results: dict[str, list[SearchResult]],
        information_needs: dict[str, Any],
        user_id: str,
    ) -> list[SearchResult]:
        """
        Apply Reciprocal Rank Fusion to merge results from different sources.

        RRF formula: score = Σ(1 / (rank + k)) for each ranking
        """

        rrf_scores = defaultdict(float)
        result_map = {}  # Store actual result objects

        # Process each source's results
        for _source, results in retrieval_results.items():
            for rank, result in enumerate(results, 1):
                # Calculate RRF contribution
                rrf_scores[result.id] += 1 / (rank + self.rrf_k)

                # Store result object (overwrite if duplicate)
                result_map[result.id] = result

        # Sort by RRF score
        sorted_ids = sorted(
            rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
        )

        # Create final result list with RRF scores
        fused_results = []
        for result_id in sorted_ids:
            result = result_map[result_id]
            # Update score with RRF score
            result.score = rrf_scores[result_id]
            fused_results.append(result)

        logger.info(
            f"RRF fusion: {len(retrieval_results)} sources -> {len(fused_results)} unique results"
        )

        return fused_results

    def _apply_relevance_boosting(
        self, results: list[SearchResult], information_needs: dict[str, Any]
    ) -> list[SearchResult]:
        """
        Apply additional relevance boosting based on:
        - Temporal relevance
        - Platform matching
        - Entity matching
        - Query-specific factors
        """

        boosted_results = []

        for result in results:
            boost_factor = 1.0

            # Temporal boosting
            temporal_boost = self._calculate_temporal_boost(
                result.timestamp, information_needs.get("time_range", {})
            )
            boost_factor *= temporal_boost

            # Platform boosting
            if information_needs.get("platforms"):
                platform_boost = self._calculate_platform_boost(
                    result.metadata.get("platform", ""), information_needs["platforms"]
                )
                boost_factor *= platform_boost

            # Entity matching boost
            entity_boost = self._calculate_entity_boost(
                result.content, result.metadata, information_needs.get("entities", {})
            )
            boost_factor *= entity_boost

            # Apply boost
            result.score *= boost_factor
            boosted_results.append(result)

        # Re-sort by boosted scores
        boosted_results.sort(key=lambda x: x.score, reverse=True)

        return boosted_results

    def _calculate_temporal_boost(
        self, item_timestamp: datetime, query_time_context: dict[str, Any]
    ) -> float:
        """
        Calculate temporal relevance boost.
        More recent items get higher scores for recency-sensitive queries.
        """

        if not query_time_context or not isinstance(item_timestamp, datetime):
            return 1.0

        # Calculate age in hours
        now = datetime.utcnow()
        age_hours = (now - item_timestamp).total_seconds() / 3600

        # Different decay rates based on query context
        reference = query_time_context.get("reference", "default_recent")

        if "hour" in reference or "today" in reference:
            # Very recent queries - steep decay
            decay_factor = 0.5
        elif "yesterday" in reference or "day" in reference:
            # Daily queries - moderate decay
            decay_factor = 0.1
        elif "week" in reference:
            # Weekly queries - gentle decay
            decay_factor = 0.05
        else:
            # Default gentle decay
            decay_factor = 0.02

        # Exponential decay
        temporal_score = np.exp(-decay_factor * age_hours)

        # Boost recent items, but don't penalize too much
        return 0.5 + (0.5 * temporal_score)

    def _calculate_platform_boost(
        self, item_platform: str, requested_platforms: list[str]
    ) -> float:
        """
        Boost items from explicitly requested platforms.
        """

        if not requested_platforms:
            return 1.0

        if item_platform.lower() in [p.lower() for p in requested_platforms]:
            return 1.5  # 50% boost for matching platform

        return 0.8  # Slight penalty for non-matching platform

    def _calculate_entity_boost(
        self, content: str, metadata: dict[str, Any], entities: dict[str, list[str]]
    ) -> float:
        """
        Boost items that contain mentioned entities.
        """

        if not entities:
            return 1.0

        boost = 1.0
        content_lower = content.lower()

        # Check each entity type
        for _entity_type, entity_list in entities.items():
            for entity in entity_list:
                if entity.lower() in content_lower:
                    boost *= 1.2  # 20% boost per matched entity

                # Also check metadata
                if entity.lower() in str(metadata).lower():
                    boost *= 1.1  # 10% boost for metadata match

        # Cap the boost to prevent over-weighting
        return min(boost, 2.0)

    def _group_by_source(
        self, results: list[SearchResult]
    ) -> dict[str, list[SearchResult]]:
        """Group results by their source (vector, event, action)"""
        grouped = defaultdict(list)
        for result in results:
            grouped[result.source].append(result)
        return dict(grouped)

    def _group_by_platform(
        self, results: list[SearchResult]
    ) -> dict[str, list[SearchResult]]:
        """Group results by platform"""
        grouped = defaultdict(list)
        for result in results:
            platform = result.metadata.get("platform", "unknown")
            grouped[platform].append(result)
        return dict(grouped)
