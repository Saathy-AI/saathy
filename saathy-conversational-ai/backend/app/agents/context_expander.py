"""
Context Expander Agent - Intelligently expands context when sufficiency is low.
Plans and executes expansion strategies based on identified gaps.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ContextExpanderAgent:
    """
    Plans context expansion strategies when initial retrieval is insufficient.
    
    Strategies include:
    - Temporal expansion (extend time range)
    - Platform diversification (add more platforms)
    - Entity expansion (find related entities)
    - Query reformulation (broaden search terms)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Expansion strategies configuration
        self.expansion_config = {
            "temporal_extension_days": [1, 3, 7, 14, 30],  # Progressive expansion
            "additional_platforms": ["slack", "github", "notion", "jira"],
            "entity_expansion_methods": ["synonyms", "related", "hierarchical"],
            "query_broadening_levels": ["exact", "similar", "related", "general"]
        }
    
    async def plan_expansion(self, current_context: Dict[str, Any], 
                           information_needs: Dict[str, Any],
                           sufficiency_gaps: List[str],
                           attempt_number: int) -> Dict[str, Any]:
        """
        Plan expansion strategy based on current context and identified gaps.
        
        Returns expansion plan to modify information needs for next retrieval.
        """
        
        expansion_plan = {
            "strategy": self._determine_strategy(sufficiency_gaps, attempt_number),
            "modifications": {},
            "rationale": ""
        }
        
        # Apply different strategies based on gaps and attempt number
        for gap in sufficiency_gaps:
            if gap == "temporal_coverage":
                self._plan_temporal_expansion(expansion_plan, information_needs, attempt_number)
                
            elif gap == "platform_diversity":
                self._plan_platform_expansion(expansion_plan, information_needs, current_context)
                
            elif gap == "entity_coverage":
                self._plan_entity_expansion(expansion_plan, information_needs, current_context)
                
            elif gap == "content_completeness":
                self._plan_query_expansion(expansion_plan, information_needs, attempt_number)
                
            elif gap == "missing_actions":
                self._plan_action_expansion(expansion_plan, information_needs)
                
            elif gap == "insufficient_events":
                self._plan_event_expansion(expansion_plan, information_needs)
        
        # Add metadata about the expansion
        expansion_plan["metadata"] = {
            "attempt": attempt_number,
            "gaps_addressed": sufficiency_gaps,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Expansion plan (attempt {attempt_number}): {expansion_plan['strategy']}")
        
        return expansion_plan
    
    def _determine_strategy(self, gaps: List[str], attempt_number: int) -> str:
        """Determine overall expansion strategy"""
        
        if attempt_number == 1:
            # First expansion - be conservative
            if "temporal_coverage" in gaps:
                return "temporal_first"
            elif "platform_diversity" in gaps:
                return "platform_first"
            else:
                return "targeted_expansion"
                
        elif attempt_number == 2:
            # Second expansion - be more aggressive
            return "broad_expansion"
            
        else:
            # Final attempt - pull out all stops
            return "exhaustive_expansion"
    
    def _plan_temporal_expansion(self, plan: Dict[str, Any], 
                               information_needs: Dict[str, Any], 
                               attempt_number: int):
        """Plan temporal expansion strategy"""
        
        current_range = information_needs.get("time_range", {})
        
        # Progressive expansion based on attempt
        extension_days = self.expansion_config["temporal_extension_days"][
            min(attempt_number - 1, len(self.expansion_config["temporal_extension_days"]) - 1)
        ]
        
        # Expand both directions
        if "start" in current_range:
            new_start = current_range["start"] - timedelta(days=extension_days)
        else:
            new_start = datetime.utcnow() - timedelta(days=extension_days)
        
        if "end" in current_range:
            new_end = current_range["end"] + timedelta(days=extension_days // 2)
        else:
            new_end = datetime.utcnow()
        
        plan["modifications"]["time_range"] = {
            "start": new_start,
            "end": new_end,
            "reference": f"expanded_{extension_days}_days"
        }
        
        plan["rationale"] += f"Expanding time range by {extension_days} days. "
    
    def _plan_platform_expansion(self, plan: Dict[str, Any], 
                               information_needs: Dict[str, Any],
                               current_context: Dict[str, Any]):
        """Plan platform expansion strategy"""
        
        current_platforms = information_needs.get("platforms", [])
        
        # Find platforms not yet searched
        all_platforms = self.expansion_config["additional_platforms"]
        missing_platforms = [p for p in all_platforms if p not in current_platforms]
        
        if missing_platforms:
            # Add platforms based on query intent
            intent = information_needs.get("intent", "general_query")
            
            if intent == "query_actions":
                # Prioritize task management platforms
                new_platforms = [p for p in ["jira", "github"] if p in missing_platforms]
            elif intent == "query_events":
                # Prioritize communication platforms
                new_platforms = [p for p in ["slack", "notion"] if p in missing_platforms]
            else:
                # Add all missing platforms
                new_platforms = missing_platforms[:2]  # Add up to 2 new platforms
            
            plan["modifications"]["platforms"] = current_platforms + new_platforms
            plan["rationale"] += f"Adding platforms: {', '.join(new_platforms)}. "
    
    def _plan_entity_expansion(self, plan: Dict[str, Any], 
                             information_needs: Dict[str, Any],
                             current_context: Dict[str, Any]):
        """Plan entity expansion strategy"""
        
        current_entities = information_needs.get("entities", {})
        
        # Extract additional entities from current context
        expanded_entities = dict(current_entities)
        
        # Look for related entities in retrieved content
        all_results = current_context.get("all_results", [])
        
        for result in all_results[:5]:  # Check top 5 results
            # Simple entity extraction from content
            # In production, this would use NER or more sophisticated methods
            content_words = result.content.split()
            
            # Look for capitalized words that might be entities
            for word in content_words:
                if word[0].isupper() and len(word) > 2:
                    # Add to appropriate entity type
                    if "project" in word.lower():
                        expanded_entities.setdefault("projects", []).append(word)
                    elif any(name_indicator in word.lower() for name_indicator in ["@", "from", "by"]):
                        expanded_entities.setdefault("people", []).append(word)
        
        # Deduplicate
        for key in expanded_entities:
            expanded_entities[key] = list(set(expanded_entities[key]))
        
        plan["modifications"]["entities"] = expanded_entities
        plan["modifications"]["expand_related_entities"] = True
        plan["rationale"] += "Expanding to include related entities. "
    
    def _plan_query_expansion(self, plan: Dict[str, Any], 
                            information_needs: Dict[str, Any],
                            attempt_number: int):
        """Plan query expansion strategy"""
        
        # Broaden search terms based on attempt
        broadening_level = min(attempt_number, len(self.expansion_config["query_broadening_levels"]) - 1)
        
        plan["modifications"]["query_expansion_level"] = \
            self.expansion_config["query_broadening_levels"][broadening_level]
        
        # Add synonyms or related terms
        plan["modifications"]["include_synonyms"] = True
        plan["modifications"]["fuzzy_matching"] = attempt_number >= 2
        
        plan["rationale"] += f"Broadening query to '{plan['modifications']['query_expansion_level']}' level. "
    
    def _plan_action_expansion(self, plan: Dict[str, Any], 
                             information_needs: Dict[str, Any]):
        """Plan expansion specifically for action items"""
        
        plan["modifications"]["include_action_sources"] = True
        plan["modifications"]["action_time_window"] = timedelta(days=30)  # Look back 30 days for actions
        plan["modifications"]["include_completed_actions"] = True
        
        plan["rationale"] += "Expanding to include all action sources and completed actions. "
    
    def _plan_event_expansion(self, plan: Dict[str, Any], 
                            information_needs: Dict[str, Any]):
        """Plan expansion for event retrieval"""
        
        plan["modifications"]["event_limit_multiplier"] = 2  # Double the event limit
        plan["modifications"]["include_minor_events"] = True
        plan["modifications"]["correlation_threshold"] = 0.5  # Lower threshold for correlations
        
        plan["rationale"] += "Expanding event retrieval with lower thresholds. "