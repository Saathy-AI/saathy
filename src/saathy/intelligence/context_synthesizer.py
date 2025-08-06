"""Context synthesizer for combining cross-platform events into actionable insights."""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import redis.asyncio as redis

from .models.actions import ContextBundle

logger = logging.getLogger(__name__)

class ContextSynthesizer:
    """Synthesizes context from correlated events across platforms."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", redis_password: Optional[str] = None):
        """Initialize the context synthesizer."""
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.redis: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            if self.redis_password:
                self.redis = redis.from_url(self.redis_url, password=self.redis_password)
            else:
                self.redis = redis.from_url(self.redis_url)
            
            await self.redis.ping()
            logger.info("Context synthesizer Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize ContextSynthesizer: {e}")
            raise
    
    async def synthesize_context(self, correlation_id: str) -> Optional[ContextBundle]:
        """Synthesize context from a correlation group."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            # Get correlation data
            correlation_key = f"correlation:{correlation_id}"
            correlation_data = await self.redis.get(correlation_key)
            
            if not correlation_data:
                logger.error(f"No correlation data found for {correlation_id}")
                return None
            
            correlation = json.loads(correlation_data)
            primary_event = correlation["primary_event"]
            related_events = correlation["related_events"]
            
            logger.info(f"Synthesizing context for correlation {correlation_id} with {len(related_events)} related events")
            
            # Organize events by platform
            platform_data = self.organize_by_platform(primary_event, related_events)
            
            # Extract key insights
            key_insights = self.extract_insights(primary_event, related_events, platform_data)
            
            # Identify urgency signals
            urgency_signals = self.identify_urgency_signals(primary_event, related_events)
            
            # Generate synthesized context narrative
            context_narrative = self.generate_context_narrative(
                primary_event, related_events, platform_data, key_insights
            )
            
            # Calculate correlation strength
            correlation_strength = correlation.get("correlation_strength", 0.0)
            
            context_bundle = ContextBundle(
                correlation_id=correlation_id,
                user_id=primary_event["user_id"],
                primary_event=primary_event,
                related_events=related_events,
                synthesized_context=context_narrative,
                key_insights=key_insights,
                urgency_signals=urgency_signals,
                platform_data=platform_data,
                correlation_strength=correlation_strength
            )
            
            # Store synthesized context
            await self.store_context_bundle(context_bundle)
            
            logger.debug(f"Successfully synthesized context for correlation {correlation_id}")
            return context_bundle
            
        except Exception as e:
            logger.error(f"Error synthesizing context for correlation {correlation_id}: {e}")
            return None
    
    def organize_by_platform(self, primary_event: Dict[str, Any], related_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Organize events by platform for easier analysis."""
        platforms = {
            "slack": {"events": [], "channels": set(), "messages": [], "reactions": []},
            "github": {"events": [], "repos": set(), "prs": [], "commits": [], "issues": []},
            "notion": {"events": [], "pages": [], "databases": set(), "changes": []}
        }
        
        all_events = [primary_event] + related_events
        
        for event in all_events:
            platform = event["platform"]
            
            if platform == "slack":
                self._process_slack_event(event, platforms["slack"])
            elif platform == "github":
                self._process_github_event(event, platforms["github"])
            elif platform == "notion":
                self._process_notion_event(event, platforms["notion"])
        
        # Convert sets to lists for JSON serialization
        for platform in platforms:
            for key, value in platforms[platform].items():
                if isinstance(value, set):
                    platforms[platform][key] = list(value)
        
        return platforms
    
    def _process_slack_event(self, event: Dict[str, Any], slack_data: Dict[str, Any]):
        """Process a Slack event into organized data."""
        slack_data["events"].append(event)
        
        if "channel_name" in event:
            slack_data["channels"].add(event["channel_name"])
            
        if "message_text" in event and event["message_text"]:
            slack_data["messages"].append({
                "text": event["message_text"],
                "timestamp": event["timestamp"],
                "user": event["user_id"],
                "channel": event.get("channel_name", "unknown"),
                "urgency": event.get("urgency_score", 0)
            })
            
        if event.get("event_type") == "slack_reaction" and "reactions" in event:
            for reaction in event["reactions"]:
                slack_data["reactions"].append({
                    "reaction": reaction,
                    "user": event["user_id"],
                    "timestamp": event["timestamp"]
                })
    
    def _process_github_event(self, event: Dict[str, Any], github_data: Dict[str, Any]):
        """Process a GitHub event into organized data."""
        github_data["events"].append(event)
        
        if "repository" in event:
            github_data["repos"].add(event["repository"])
            
        if "pr_number" in event and event["pr_number"]:
            github_data["prs"].append({
                "number": event["pr_number"],
                "action": event.get("action", "unknown"),
                "repo": event.get("repository"),
                "user": event["user_id"],
                "timestamp": event["timestamp"]
            })
            
        if "commit_sha" in event and event["commit_sha"]:
            github_data["commits"].append({
                "sha": event["commit_sha"][:8],
                "message": event.get("commit_message", ""),
                "repo": event.get("repository"),
                "user": event["user_id"],
                "branch": event.get("branch"),
                "files_changed": event.get("files_changed", [])
            })
            
        if "issue_number" in event and event["issue_number"]:
            github_data["issues"].append({
                "number": event["issue_number"],
                "action": event.get("action", "unknown"),
                "repo": event.get("repository"),
                "user": event["user_id"],
                "timestamp": event["timestamp"]
            })
    
    def _process_notion_event(self, event: Dict[str, Any], notion_data: Dict[str, Any]):
        """Process a Notion event into organized data."""
        notion_data["events"].append(event)
        
        if "page_title" in event:
            notion_data["pages"].append({
                "title": event["page_title"],
                "change_type": event.get("change_type"),
                "timestamp": event["timestamp"],
                "user": event["user_id"],
                "url": event.get("page_url"),
                "properties_changed": event.get("properties_changed", [])
            })
            
        if "database_id" in event and event["database_id"]:
            notion_data["databases"].add(event["database_id"])
            
        notion_data["changes"].extend(event.get("properties_changed", []))
    
    def extract_insights(self, primary_event: Dict[str, Any], related_events: List[Dict[str, Any]], 
                        platform_data: Dict[str, Any]) -> List[str]:
        """Extract key insights from the event group."""
        insights = []
        all_events = [primary_event] + related_events
        
        # Cross-platform activity insight
        platforms = set(event["platform"] for event in all_events)
        if len(platforms) > 1:
            platform_names = ", ".join(platforms)
            insights.append(f"Cross-platform activity detected across {platform_names}")
        
        # Project context insight
        projects = set(event.get("project_context") for event in all_events if event.get("project_context"))
        if projects:
            project_names = ", ".join(projects)
            insights.append(f"Related to project(s): {project_names}")
        
        # Keyword concentration analysis
        all_keywords = []
        for event in all_events:
            all_keywords.extend(event.get("keywords", []))
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Find keywords that appear multiple times
        frequent_keywords = [k for k, v in keyword_counts.items() if v >= 2]
        if frequent_keywords:
            insights.append(f"Key themes: {', '.join(frequent_keywords[:5])}")
        
        # Time pattern insight
        timestamps = [datetime.fromisoformat(event["timestamp"]) for event in all_events]
        if timestamps:
            time_span = max(timestamps) - min(timestamps)
            if time_span.total_seconds() < 300:  # 5 minutes
                insights.append("Events occurred in rapid succession (< 5 minutes)")
            elif time_span.total_seconds() < 1800:  # 30 minutes
                insights.append("Events occurred within a short time window (< 30 minutes)")
        
        # Platform-specific insights
        insights.extend(self._extract_platform_specific_insights(platform_data))
        
        # User involvement insight
        users = set(event["user_id"] for event in all_events)
        if len(users) > 1:
            insights.append(f"Multiple users involved: {', '.join(list(users)[:3])}")
        
        return insights[:10]  # Limit to top 10 insights
    
    def _extract_platform_specific_insights(self, platform_data: Dict[str, Any]) -> List[str]:
        """Extract platform-specific insights."""
        insights = []
        
        # Slack insights
        slack_data = platform_data.get("slack", {})
        if slack_data.get("messages"):
            message_count = len(slack_data["messages"])
            if message_count > 3:
                insights.append(f"Active Slack discussion with {message_count} messages")
            
            channels = slack_data.get("channels", [])
            if len(channels) > 1:
                insights.append(f"Discussion spans multiple Slack channels: {', '.join(channels[:3])}")
        
        # GitHub insights
        github_data = platform_data.get("github", {})
        if github_data.get("prs"):
            pr_count = len(github_data["prs"])
            if pr_count > 1:
                insights.append(f"Multiple PRs involved ({pr_count} PRs)")
            
            pr_actions = [pr["action"] for pr in github_data["prs"]]
            if "opened" in pr_actions and "review_requested" in pr_actions:
                insights.append("PR workflow progression: opened → review requested")
        
        if github_data.get("commits"):
            commit_count = len(github_data["commits"])
            if commit_count > 1:
                insights.append(f"Multiple commits detected ({commit_count} commits)")
        
        # Notion insights
        notion_data = platform_data.get("notion", {})
        if notion_data.get("pages"):
            page_count = len(notion_data["pages"])
            if page_count > 1:
                insights.append(f"Multiple Notion pages updated ({page_count} pages)")
            
            changes = notion_data.get("changes", [])
            if "status" in [c.lower() for c in changes]:
                insights.append("Task status changes detected in Notion")
        
        return insights
    
    def identify_urgency_signals(self, primary_event: Dict[str, Any], related_events: List[Dict[str, Any]]) -> List[str]:
        """Identify signals that indicate urgency."""
        signals = []
        all_events = [primary_event] + related_events
        
        # Check urgency scores
        high_urgency_events = [e for e in all_events if e.get("urgency_score", 0) > 0.5]
        if high_urgency_events:
            signals.append(f"{len(high_urgency_events)} high-urgency events detected")
        
        # Check for urgent keywords
        urgent_keywords = ['urgent', 'critical', 'asap', 'emergency', 'hotfix', 'deadline', 'blocking']
        urgent_found = set()
        for event in all_events:
            event_keywords = event.get("keywords", [])
            for keyword in event_keywords:
                if keyword.lower() in urgent_keywords:
                    urgent_found.add(keyword.lower())
        
        if urgent_found:
            signals.append(f"Urgent indicators: {', '.join(urgent_found)}")
        
        # Check for PR/review activity
        pr_events = [e for e in all_events if e.get("platform") == "github" and "pr" in e.get("keywords", [])]
        if pr_events:
            pr_actions = [e.get("action", "") for e in pr_events]
            if "review_requested" in pr_actions:
                signals.append("Pull request review requested (time-sensitive)")
            elif "opened" in pr_actions:
                signals.append("New pull request requires attention")
        
        # Check for direct mentions/assignments
        total_mentions = sum(len(event.get("mentioned_users", [])) for event in all_events)
        if total_mentions > 0:
            signals.append(f"You were mentioned {total_mentions} time(s)")
        
        # Check for production/incident keywords
        prod_keywords = ['production', 'prod', 'outage', 'down', 'incident', 'broken']
        prod_found = set()
        for event in all_events:
            event_keywords = event.get("keywords", [])
            for keyword in event_keywords:
                if keyword.lower() in prod_keywords:
                    prod_found.add(keyword.lower())
        
        if prod_found:
            signals.append(f"Production-related activity: {', '.join(prod_found)}")
        
        # Check for status changes in Notion
        notion_events = [e for e in all_events if e.get("platform") == "notion"]
        status_changes = []
        for event in notion_events:
            changes = event.get("properties_changed", [])
            status_changes.extend([c for c in changes if 'status' in c.lower()])
        
        if status_changes:
            signals.append("Task status changes require follow-up")
        
        return signals
    
    def generate_context_narrative(self, primary_event: Dict[str, Any], related_events: List[Dict[str, Any]], 
                                  platform_data: Dict[str, Any], key_insights: List[str]) -> str:
        """Generate a narrative description of the context."""
        try:
            narrative_parts = []
            
            # Start with the primary event
            primary_platform = primary_event["platform"]
            primary_time = datetime.fromisoformat(primary_event["timestamp"])
            
            # Describe the trigger event
            if primary_platform == "slack":
                channel = primary_event.get("channel_name", "unknown")
                narrative_parts.append(f"Started with a Slack message in #{channel}")
            elif primary_platform == "github":
                action = primary_event.get("action", "activity")
                repo = primary_event.get("repository", "unknown")
                if primary_event.get("pr_number"):
                    narrative_parts.append(f"Started with GitHub PR #{primary_event['pr_number']} {action} in {repo}")
                elif primary_event.get("commit_sha"):
                    narrative_parts.append(f"Started with Git commit in {repo}")
                else:
                    narrative_parts.append(f"Started with GitHub {action} in {repo}")
            elif primary_platform == "notion":
                change = primary_event.get("change_type", "change")
                title = primary_event.get("page_title", "unknown")
                narrative_parts.append(f"Started with Notion page {change}: '{title}'")
            
            # Add related activity summary
            if related_events:
                platforms_mentioned = set()
                activity_summary = []
                
                for event in related_events:
                    platforms_mentioned.add(event["platform"])
                
                if len(platforms_mentioned) == 1:
                    platform_name = list(platforms_mentioned)[0]
                    activity_summary.append(f"{len(related_events)} related {platform_name} events")
                else:
                    activity_summary.append(f"related activity across {', '.join(platforms_mentioned)}")
                
                narrative_parts.append("followed by " + " and ".join(activity_summary))
            
            # Add specific platform details
            platform_details = self._generate_platform_details(platform_data)
            if platform_details:
                narrative_parts.extend(platform_details)
            
            # Add key insights
            if key_insights:
                insight_text = ". ".join(key_insights[:3])  # Top 3 insights
                narrative_parts.append(f"Key context: {insight_text}")
            
            return ". ".join(narrative_parts) + "."
            
        except Exception as e:
            logger.error(f"Error generating context narrative: {e}")
            return "Related activity detected across multiple platforms."
    
    def _generate_platform_details(self, platform_data: Dict[str, Any]) -> List[str]:
        """Generate specific details for each platform."""
        details = []
        
        # Slack details
        slack_data = platform_data.get("slack", {})
        if slack_data.get("messages"):
            messages = slack_data["messages"]
            if len(messages) > 1:
                details.append(f"Slack discussion includes {len(messages)} messages")
        
        # GitHub details
        github_data = platform_data.get("github", {})
        if github_data.get("prs"):
            prs = github_data["prs"]
            if len(prs) == 1:
                pr = prs[0]
                details.append(f"GitHub PR #{pr['number']} {pr['action']}")
            elif len(prs) > 1:
                details.append(f"{len(prs)} GitHub PRs involved")
        
        if github_data.get("commits"):
            commits = github_data["commits"]
            if len(commits) == 1:
                commit = commits[0]
                details.append(f"Git commit {commit['sha']} on {commit.get('branch', 'unknown')}")
            elif len(commits) > 1:
                details.append(f"{len(commits)} commits across repositories")
        
        # Notion details
        notion_data = platform_data.get("notion", {})
        if notion_data.get("pages"):
            pages = notion_data["pages"]
            if len(pages) == 1:
                page = pages[0]
                details.append(f"Notion page '{page['title']}' {page['change_type']}")
            elif len(pages) > 1:
                details.append(f"{len(pages)} Notion pages updated")
        
        return details
    
    async def store_context_bundle(self, context_bundle: ContextBundle):
        """Store the synthesized context bundle."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            context_key = f"context:{context_bundle.correlation_id}"
            context_data = context_bundle.model_dump_json()
            
            # Store with 24 hour expiration
            await self.redis.setex(context_key, 24 * 60 * 60, context_data)
            
            logger.debug(f"Stored context bundle for correlation {context_bundle.correlation_id}")
            
        except Exception as e:
            logger.error(f"Error storing context bundle: {e}")
    
    async def get_context_bundle(self, correlation_id: str) -> Optional[ContextBundle]:
        """Retrieve a context bundle by correlation ID."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")
                
            context_key = f"context:{correlation_id}"
            context_data = await self.redis.get(context_key)
            
            if context_data:
                context_dict = json.loads(context_data)
                return ContextBundle(**context_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving context bundle: {e}")
            return None
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Context synthesizer Redis connection closed")