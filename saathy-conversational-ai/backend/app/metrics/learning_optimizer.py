"""
Learning Optimizer - Implements feedback loops for continuous system improvement.
Uses collected metrics to adjust system parameters and improve performance.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import json
import asyncio

logger = logging.getLogger(__name__)


class LearningOptimizer:
    """
    Implements learning loops to continuously improve the system based on:
    - User feedback
    - Performance metrics
    - Error patterns
    - Success patterns
    
    Adjusts:
    - Sufficiency thresholds
    - Retrieval weights
    - Expansion strategies
    - Cache policies
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Learning parameters
        self.learning_rate = config.get("learning_rate", 0.1)
        self.batch_size = config.get("batch_size", 100)
        self.update_interval = config.get("update_interval", 3600)  # 1 hour
        
        # Current system parameters (to be optimized)
        self.system_params = {
            "sufficiency_threshold": 0.7,
            "retrieval_weights": {
                "vector": 0.4,
                "structured": 0.3,
                "action": 0.3
            },
            "expansion_thresholds": {
                "temporal": 0.6,
                "platform": 0.5,
                "entity": 0.7
            },
            "cache_ttl_multipliers": {
                "high_satisfaction": 2.0,
                "medium_satisfaction": 1.0,
                "low_satisfaction": 0.5
            },
            "rrf_k": 60
        }
        
        # Parameter bounds
        self.param_bounds = {
            "sufficiency_threshold": (0.5, 0.9),
            "retrieval_weights": (0.1, 0.7),
            "expansion_thresholds": (0.3, 0.8),
            "cache_ttl_multipliers": (0.5, 3.0),
            "rrf_k": (30, 100)
        }
        
        # Learning history
        self.optimization_history = []
        self.performance_trends = defaultdict(list)
        
        # Lock for thread-safe parameter updates
        self.param_lock = asyncio.Lock()
    
    async def process_feedback_batch(self, feedback_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of feedback items to update system parameters.
        
        Args:
            feedback_items: List of feedback entries from quality metrics
            
        Returns:
            Updated parameters and optimization summary
        """
        
        if not feedback_items:
            return {"status": "no_feedback"}
        
        # Analyze feedback patterns
        analysis = self._analyze_feedback_patterns(feedback_items)
        
        # Calculate parameter adjustments
        adjustments = await self._calculate_adjustments(analysis)
        
        # Apply adjustments
        async with self.param_lock:
            old_params = self.system_params.copy()
            self._apply_adjustments(adjustments)
            new_params = self.system_params.copy()
        
        # Record optimization
        optimization_record = {
            "timestamp": datetime.utcnow(),
            "feedback_count": len(feedback_items),
            "analysis": analysis,
            "adjustments": adjustments,
            "old_params": old_params,
            "new_params": new_params
        }
        
        self.optimization_history.append(optimization_record)
        
        logger.info(f"Processed {len(feedback_items)} feedback items, "
                   f"adjusted {len(adjustments)} parameters")
        
        return {
            "status": "updated",
            "adjustments": adjustments,
            "new_params": new_params
        }
    
    def _analyze_feedback_patterns(self, feedback_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in feedback to identify areas for improvement"""
        
        analysis = {
            "issue_counts": defaultdict(int),
            "avg_scores": {
                "sufficiency": [],
                "satisfaction": [],
                "response_time": []
            },
            "intent_performance": defaultdict(lambda: {
                "success": 0,
                "failure": 0,
                "avg_sufficiency": []
            }),
            "expansion_patterns": {
                "needed": 0,
                "successful": 0,
                "excessive": 0
            }
        }
        
        for item in feedback_items:
            # Count issues
            for issue in item.get("issues", []):
                analysis["issue_counts"][issue] += 1
            
            metric_entry = item.get("metric_entry", {})
            
            # Collect scores
            if "sufficiency_score" in metric_entry:
                analysis["avg_scores"]["sufficiency"].append(
                    metric_entry["sufficiency_score"]
                )
            
            if "satisfaction_score" in metric_entry:
                analysis["avg_scores"]["satisfaction"].append(
                    metric_entry["satisfaction_score"]
                )
            
            if "response_time" in metric_entry:
                analysis["avg_scores"]["response_time"].append(
                    metric_entry["response_time"]
                )
            
            # Intent-specific performance
            intent = metric_entry.get("intent", "unknown")
            if "error" in metric_entry:
                analysis["intent_performance"][intent]["failure"] += 1
            else:
                analysis["intent_performance"][intent]["success"] += 1
                if "sufficiency_score" in metric_entry:
                    analysis["intent_performance"][intent]["avg_sufficiency"].append(
                        metric_entry["sufficiency_score"]
                    )
            
            # Expansion patterns
            expansions = metric_entry.get("expansion_attempts", 0)
            if expansions > 0:
                analysis["expansion_patterns"]["needed"] += 1
                if metric_entry.get("sufficiency_score", 0) > 0.7:
                    analysis["expansion_patterns"]["successful"] += 1
                if expansions > 2:
                    analysis["expansion_patterns"]["excessive"] += 1
        
        # Calculate averages
        for key in analysis["avg_scores"]:
            if analysis["avg_scores"][key]:
                analysis["avg_scores"][key] = np.mean(analysis["avg_scores"][key])
            else:
                analysis["avg_scores"][key] = None
        
        # Convert defaultdicts to regular dicts
        analysis["issue_counts"] = dict(analysis["issue_counts"])
        analysis["intent_performance"] = {
            k: dict(v) for k, v in analysis["intent_performance"].items()
        }
        
        return analysis
    
    async def _calculate_adjustments(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate parameter adjustments based on analysis"""
        
        adjustments = {}
        
        # Adjust sufficiency threshold based on expansion patterns
        if analysis["expansion_patterns"]["needed"] > 0:
            expansion_rate = (analysis["expansion_patterns"]["excessive"] / 
                            analysis["expansion_patterns"]["needed"])
            
            if expansion_rate > 0.3:  # Too many excessive expansions
                # Lower threshold to avoid unnecessary expansions
                adjustments["sufficiency_threshold"] = -0.05
            elif analysis["avg_scores"]["sufficiency"] and \
                 analysis["avg_scores"]["sufficiency"] < 0.6:
                # Raise threshold to ensure better context
                adjustments["sufficiency_threshold"] = 0.05
        
        # Adjust retrieval weights based on intent performance
        intent_adjustments = self._calculate_intent_based_adjustments(
            analysis["intent_performance"]
        )
        if intent_adjustments:
            adjustments["retrieval_weights"] = intent_adjustments
        
        # Adjust expansion thresholds based on issues
        if "low_sufficiency" in analysis["issue_counts"] and \
           analysis["issue_counts"]["low_sufficiency"] > 10:
            adjustments["expansion_thresholds"] = {
                "temporal": -0.05,
                "platform": -0.05,
                "entity": -0.05
            }
        
        # Adjust cache policies based on satisfaction
        if analysis["avg_scores"]["satisfaction"] is not None:
            if analysis["avg_scores"]["satisfaction"] < 0.5:
                # Reduce cache TTL for low satisfaction cases
                adjustments["cache_ttl_multipliers"] = {
                    "low_satisfaction": -0.1
                }
            elif analysis["avg_scores"]["satisfaction"] > 0.8:
                # Increase cache TTL for high satisfaction
                adjustments["cache_ttl_multipliers"] = {
                    "high_satisfaction": 0.2
                }
        
        # Adjust RRF parameter based on result quality
        if "high_expansion_rate" in analysis["issue_counts"] and \
           analysis["issue_counts"]["high_expansion_rate"] > 5:
            # Adjust RRF to improve initial ranking
            adjustments["rrf_k"] = -5
        
        return adjustments
    
    def _calculate_intent_based_adjustments(self, 
                                          intent_performance: Dict[str, Dict]) -> Optional[Dict[str, float]]:
        """Calculate retrieval weight adjustments based on intent performance"""
        
        # Analyze which intents are underperforming
        underperforming_intents = []
        
        for intent, perf in intent_performance.items():
            total = perf["success"] + perf["failure"]
            if total > 5:  # Minimum sample size
                success_rate = perf["success"] / total
                if success_rate < 0.7:
                    underperforming_intents.append(intent)
        
        if not underperforming_intents:
            return None
        
        # Adjust weights based on intent patterns
        adjustments = {}
        
        if "query_actions" in underperforming_intents:
            # Boost action retrieval for action queries
            adjustments["action"] = 0.05
            adjustments["vector"] = -0.05
        
        if "query_events" in underperforming_intents:
            # Boost structured retrieval for event queries
            adjustments["structured"] = 0.05
            adjustments["action"] = -0.05
        
        return adjustments
    
    def _apply_adjustments(self, adjustments: Dict[str, Any]):
        """Apply calculated adjustments to system parameters"""
        
        for param, adjustment in adjustments.items():
            if param == "sufficiency_threshold":
                new_value = self.system_params[param] + adjustment * self.learning_rate
                self.system_params[param] = self._clip_value(
                    new_value, *self.param_bounds[param]
                )
            
            elif param == "retrieval_weights":
                for weight_type, adj in adjustment.items():
                    if weight_type in self.system_params["retrieval_weights"]:
                        new_value = (self.system_params["retrieval_weights"][weight_type] + 
                                   adj * self.learning_rate)
                        self.system_params["retrieval_weights"][weight_type] = self._clip_value(
                            new_value, *self.param_bounds["retrieval_weights"]
                        )
                
                # Normalize weights to sum to 1
                self._normalize_weights(self.system_params["retrieval_weights"])
            
            elif param == "expansion_thresholds":
                for threshold_type, adj in adjustment.items():
                    if threshold_type in self.system_params["expansion_thresholds"]:
                        new_value = (self.system_params["expansion_thresholds"][threshold_type] + 
                                   adj * self.learning_rate)
                        self.system_params["expansion_thresholds"][threshold_type] = self._clip_value(
                            new_value, *self.param_bounds["expansion_thresholds"]
                        )
            
            elif param == "cache_ttl_multipliers":
                for mult_type, adj in adjustment.items():
                    if mult_type in self.system_params["cache_ttl_multipliers"]:
                        new_value = (self.system_params["cache_ttl_multipliers"][mult_type] + 
                                   adj * self.learning_rate)
                        self.system_params["cache_ttl_multipliers"][mult_type] = self._clip_value(
                            new_value, *self.param_bounds["cache_ttl_multipliers"]
                        )
            
            elif param == "rrf_k":
                new_value = self.system_params[param] + adjustment
                self.system_params[param] = int(self._clip_value(
                    new_value, *self.param_bounds[param]
                ))
    
    def _clip_value(self, value: float, min_val: float, max_val: float) -> float:
        """Clip value to specified bounds"""
        return max(min_val, min(max_val, value))
    
    def _normalize_weights(self, weights: Dict[str, float]):
        """Normalize weights to sum to 1"""
        total = sum(weights.values())
        if total > 0:
            for key in weights:
                weights[key] /= total
    
    async def get_optimized_parameters(self) -> Dict[str, Any]:
        """Get current optimized parameters"""
        async with self.param_lock:
            return self.system_params.copy()
    
    def get_optimization_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent optimization history"""
        return self.optimization_history[-limit:]
    
    async def analyze_performance_trends(self, metrics: Dict[str, Any]):
        """Analyze performance trends over time"""
        
        # Record current performance
        timestamp = datetime.utcnow()
        
        self.performance_trends["response_time"].append({
            "timestamp": timestamp,
            "value": metrics.get("avg_response_time", 0)
        })
        
        self.performance_trends["sufficiency"].append({
            "timestamp": timestamp,
            "value": metrics.get("avg_sufficiency_score", 0)
        })
        
        self.performance_trends["error_rate"].append({
            "timestamp": timestamp,
            "value": metrics.get("error_rate", 0)
        })
        
        # Keep only recent data (last 7 days)
        cutoff = timestamp - timedelta(days=7)
        for metric in self.performance_trends:
            self.performance_trends[metric] = [
                entry for entry in self.performance_trends[metric]
                if entry["timestamp"] > cutoff
            ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance trends"""
        
        summary = {}
        
        for metric, entries in self.performance_trends.items():
            if entries:
                values = [e["value"] for e in entries]
                summary[metric] = {
                    "current": values[-1],
                    "average": np.mean(values),
                    "trend": self._calculate_trend(values),
                    "improvement": values[-1] - values[0] if len(values) > 1 else 0
                }
        
        return summary
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        
        if len(values) < 2:
            return "stable"
        
        # Simple linear regression
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if abs(slope) < 0.01:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    async def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for analysis"""
        
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "current_parameters": await self.get_optimized_parameters(),
            "optimization_history": self.optimization_history,
            "performance_trends": dict(self.performance_trends),
            "performance_summary": self.get_performance_summary()
        }