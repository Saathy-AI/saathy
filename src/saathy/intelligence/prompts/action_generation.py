"""GPT-4 prompt templates for generating specific, actionable recommendations."""

from typing import Dict, Any, List

def get_action_generation_prompt(context_bundle: Dict[str, Any]) -> str:
    """Generate the main prompt for GPT-4 action generation."""
    
    prompt = f"""You are Saathy, an AI assistant that helps knowledge workers be more productive by analyzing their cross-platform activity and suggesting specific, actionable next steps.

CONTEXT:
The user has recent activity across multiple platforms that appears to be related. Based on this activity, I need you to suggest 1-3 specific actions they should take next.

PRIMARY ACTIVITY:
- Platform: {context_bundle['primary_event']['platform']}
- Type: {context_bundle['primary_event'].get('event_type', 'activity')}
- Time: {context_bundle['primary_event']['timestamp']}
- Context: {context_bundle['primary_event'].get('project_context', 'General')}

RELATED ACTIVITIES:
{_format_related_events(context_bundle['related_events'])}

SYNTHESIZED CONTEXT:
{context_bundle['synthesized_context']}

KEY INSIGHTS:
{_format_insights(context_bundle['key_insights'])}

URGENCY SIGNALS:
{_format_urgency_signals(context_bundle['urgency_signals'])}

PLATFORM DATA:
{_format_platform_data(context_bundle['platform_data'])}

CORRELATION STRENGTH: {context_bundle.get('correlation_strength', 0.0):.2f}

YOUR TASK:
Generate 1-3 specific, actionable recommendations for what the user should do next. Each action should be:

1. SPECIFIC: Not generic advice, but concrete next steps based on the actual events
2. ACTIONABLE: Something they can complete in 5-30 minutes
3. CONTEXTUAL: Directly related to the events that happened
4. VALUABLE: Worth their time and attention
5. URGENT: Prioritized by the urgency signals and timing

RESPONSE FORMAT (JSON):
{{
  "actions": [
    {{
      "title": "Clear, specific title (max 60 characters)",
      "description": "Detailed description with context from the events (2-3 sentences)",
      "priority": "urgent|high|medium|low|fyi",
      "action_type": "review|respond|update|meeting|follow_up|create|fix",
      "estimated_time_minutes": 15,
      "reasoning": "Why this action is suggested based on the specific events (1-2 sentences)",
      "related_people": ["username1", "username2"],
      "action_links": [
        {{
          "platform": "slack|github|notion",
          "url": "direct_link_if_available",
          "label": "What this link does",
          "action_type": "view|edit|comment|reply"
        }}
      ]
    }}
  ]
}}

EXAMPLES OF GOOD ACTIONS:
- "Review PR #123 for security vulnerability in auth module" (not "review code")
- "Reply to Sarah's question about API deployment timeline in #eng-alerts" (not "respond to message")  
- "Update project status in Notion doc to reflect completed GitHub milestones" (not "update documentation")
- "Follow up on blocked deployment mentioned in Slack after commit abc123" (not "follow up on issue")

EXAMPLES OF BAD ACTIONS (NEVER DO THESE):
- "Check your messages" (too generic)
- "Review the code" (no specific context)
- "Follow up on the project" (no specific action)
- "Update the status" (no specific target)

CRITICAL RULES:
1. Every action MUST reference specific events, names, numbers, or content from the provided context
2. If there are PR numbers, issue numbers, channel names, or page titles - USE THEM in the action title/description
3. If there are user names mentioned - include them in related_people
4. Priority should reflect the urgency signals - urgent events get urgent actions
5. Action type should match what the user actually needs to do
6. Estimated time should be realistic for the specific task

Generate actions now based on the provided context:"""

    return prompt

def _format_related_events(related_events: List[Dict[str, Any]]) -> str:
    """Format related events for the prompt."""
    if not related_events:
        return "None"
    
    formatted = []
    for i, event in enumerate(related_events[:5]):  # Max 5 events
        platform = event['platform']
        timestamp = event['timestamp']
        event_type = event.get('event_type', 'activity')
        
        # Add more specific details for each platform
        details = ""
        if platform == "slack":
            channel = event.get('channel_name', 'unknown')
            details = f" in #{channel}"
            if event.get('message_text'):
                preview = event['message_text'][:50] + "..." if len(event['message_text']) > 50 else event['message_text']
                details += f" - \"{preview}\""
        elif platform == "github":
            repo = event.get('repository', 'unknown')
            if event.get('pr_number'):
                details = f" PR #{event['pr_number']} in {repo}"
            elif event.get('commit_sha'):
                details = f" commit {event['commit_sha'][:8]} in {repo}"
            else:
                details = f" in {repo}"
        elif platform == "notion":
            title = event.get('page_title', 'unknown')
            details = f" page \"{title}\""
            
        formatted.append(f"{i+1}. {platform} {event_type}{details} at {timestamp}")
    
    return "\n".join(formatted)

def _format_insights(insights: List[str]) -> str:
    """Format insights for the prompt."""
    if not insights:
        return "None identified"
    return "\n".join(f"- {insight}" for insight in insights)

def _format_urgency_signals(urgency_signals: List[str]) -> str:
    """Format urgency signals for the prompt."""
    if not urgency_signals:
        return "None detected"
    return "\n".join(f"- {signal}" for signal in urgency_signals)

def _format_platform_data(platform_data: Dict[str, Any]) -> str:
    """Format platform-specific data for the prompt."""
    formatted = []
    
    for platform, data in platform_data.items():
        if not data.get('events'):
            continue
            
        platform_info = f"{platform.upper()}:\n"
        
        if platform == "slack":
            channels = data.get('channels', [])
            messages = data.get('messages', [])
            if channels:
                platform_info += f"  Channels: {', '.join(channels)}\n"
            if messages:
                recent_messages = messages[-2:]  # Last 2 messages
                for msg in recent_messages:
                    preview = msg['text'][:100] + "..." if len(msg['text']) > 100 else msg['text']
                    platform_info += f"  Message in #{msg['channel']}: \"{preview}\"\n"
        
        elif platform == "github":
            repos = data.get('repos', [])
            prs = data.get('prs', [])
            commits = data.get('commits', [])
            issues = data.get('issues', [])
            
            if repos:
                platform_info += f"  Repositories: {', '.join(repos)}\n"
            if prs:
                pr_info = [f"PR #{pr['number']} ({pr['action']}) in {pr['repo']}" for pr in prs]
                platform_info += f"  Pull Requests: {', '.join(pr_info)}\n"
            if commits:
                commit_info = [f"{commit['sha']} in {commit['repo']}" for commit in commits]
                platform_info += f"  Commits: {', '.join(commit_info)}\n"
            if issues:
                issue_info = [f"Issue #{issue['number']} ({issue['action']}) in {issue['repo']}" for issue in issues]
                platform_info += f"  Issues: {', '.join(issue_info)}\n"
        
        elif platform == "notion":
            pages = data.get('pages', [])
            changes = data.get('changes', [])
            if pages:
                page_info = [f"\"{page['title']}\" ({page['change_type']})" for page in pages]
                platform_info += f"  Pages: {', '.join(page_info)}\n"
            if changes:
                unique_changes = list(set(changes))
                platform_info += f"  Property changes: {', '.join(unique_changes)}\n"
        
        formatted.append(platform_info)
    
    return "\n".join(formatted) if formatted else "No detailed platform data available"


def get_action_refinement_prompt(initial_actions: List[Dict], context: Dict[str, Any]) -> str:
    """Prompt to refine actions if they're too generic."""
    
    prompt = f"""The following actions were generated but may be too generic. Please refine them to be more specific and actionable based on the context:

CONTEXT REMINDER:
{context['synthesized_context']}

KEY INSIGHTS:
{_format_insights(context['key_insights'])}

CURRENT ACTIONS:
{_format_actions_for_refinement(initial_actions)}

REFINEMENT REQUIREMENTS:
1. More specific (include exact names, numbers, locations from the context)
2. More actionable (clear next steps that can be completed immediately)  
3. More contextual (reference the specific events that happened)
4. Include direct links where possible

EXAMPLES OF GOOD REFINEMENTS:
- "Review code" → "Review PR #123 security changes in auth.py for XSS vulnerability"
- "Update status" → "Update project status in Notion 'Q4 Roadmap' page to reflect PR #123 completion"
- "Follow up" → "Follow up with @sarah in #eng-alerts about deployment blocker mentioned 2 hours ago"

Return the refined actions in the same JSON format, but with improved specificity and actionability."""

    return prompt

def _format_actions_for_refinement(actions: List[Dict]) -> str:
    """Format actions for refinement prompt."""
    formatted = []
    for i, action in enumerate(actions, 1):
        formatted.append(f"{i}. {action.get('title', 'No title')}: {action.get('description', 'No description')}")
    return "\n".join(formatted)

def get_context_validation_prompt(context_bundle: Dict[str, Any]) -> str:
    """Prompt to validate if context is sufficient for action generation."""
    
    prompt = f"""Analyze the following context and determine if it's sufficient to generate useful, specific actions for the user.

CONTEXT:
{context_bundle['synthesized_context']}

EVENTS: {len(context_bundle['related_events']) + 1} total events
PLATFORMS: {', '.join(set(e['platform'] for e in [context_bundle['primary_event']] + context_bundle['related_events']))}
CORRELATION STRENGTH: {context_bundle.get('correlation_strength', 0.0):.2f}

URGENCY SIGNALS:
{_format_urgency_signals(context_bundle['urgency_signals'])}

Respond with JSON:
{{
  "sufficient": true/false,
  "reasoning": "Why the context is or isn't sufficient",
  "missing_elements": ["what would make this context more actionable"],
  "confidence": 0.8
}}

Context is sufficient if:
- There are specific events with clear actionable outcomes
- Users are mentioned or specific items need attention
- There's enough detail to suggest concrete next steps
- The correlation makes logical sense

Context is insufficient if:
- Events are too vague or disconnected
- No clear action items emerge from the activity
- Correlation is weak and events seem unrelated
- Missing key details like names, numbers, or specific content"""

    return prompt