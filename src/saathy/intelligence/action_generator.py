"""GPT-4 powered action generator with validation and enhancement."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import redis.asyncio as redis
from openai import AsyncOpenAI

from .context_synthesizer import ContextSynthesizer
from .models.actions import ActionLink, ActionPriority, ActionType, GeneratedAction
from .prompts.action_generation import (
    get_action_generation_prompt,
    get_action_refinement_prompt,
    get_context_validation_prompt,
)

logger = logging.getLogger(__name__)


class ActionGenerator:
    """GPT-4 powered action generator with validation and enhancement."""

    def __init__(
        self,
        openai_api_key: str,
        redis_url: str = "redis://localhost:6379",
        redis_password: Optional[str] = None,
    ):
        """Initialize the action generator."""
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.redis: Optional[redis.Redis] = None
        self.context_synthesizer = ContextSynthesizer(redis_url, redis_password)

        # Configuration
        self.model = "gpt-4o"  # Using latest GPT-4 model
        self.max_actions_per_correlation = 3
        self.max_daily_actions_per_user = 20

    async def initialize(self):
        """Initialize Redis connection and context synthesizer."""
        try:
            if self.redis_password:
                self.redis = redis.from_url(
                    self.redis_url, password=self.redis_password
                )
            else:
                self.redis = redis.from_url(self.redis_url)

            await self.redis.ping()
            await self.context_synthesizer.initialize()
            logger.info("Action generator initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ActionGenerator: {e}")
            raise

    async def generate_actions_for_correlation(
        self, correlation_id: str
    ) -> list[GeneratedAction]:
        """Main entry point: generate actions for a correlation group."""
        try:
            logger.info(f"Generating actions for correlation {correlation_id}")

            # Get synthesized context
            context_bundle = await self.context_synthesizer.synthesize_context(
                correlation_id
            )
            if not context_bundle:
                logger.error(
                    f"No context bundle found for correlation {correlation_id}"
                )
                return []

            # Check daily limits for user
            if not await self.check_daily_limits(context_bundle.user_id):
                logger.info(
                    f"Daily action limit reached for user {context_bundle.user_id}"
                )
                return []

            # Validate context quality
            if not await self.validate_context_quality(context_bundle):
                logger.info(
                    f"Context quality insufficient for correlation {correlation_id}"
                )
                return []

            # Generate actions using GPT-4
            actions = await self.generate_actions_with_gpt4(context_bundle)

            # Store and return actions
            stored_actions = []
            for action_data in actions:
                generated_action = await self.create_and_store_action(
                    action_data, correlation_id, context_bundle.user_id
                )
                if generated_action:
                    stored_actions.append(generated_action)

            # Update correlation status
            await self.update_correlation_status(correlation_id, "actions_generated")

            logger.info(
                f"Generated {len(stored_actions)} actions for correlation {correlation_id}"
            )
            return stored_actions

        except Exception as e:
            logger.error(
                f"Error generating actions for correlation {correlation_id}: {e}"
            )
            return []

    async def check_daily_limits(self, user_id: str) -> bool:
        """Check if user hasn't exceeded daily action generation limits."""
        try:
            if not self.redis:
                return True  # Allow if Redis unavailable

            today_key = (
                f"user:{user_id}:actions:daily:{datetime.now().strftime('%Y-%m-%d')}"
            )
            daily_count = await self.redis.get(today_key)

            if daily_count:
                count = int(daily_count)
                if count >= self.max_daily_actions_per_user:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking daily limits: {e}")
            return True  # Allow on error

    async def validate_context_quality(self, context_bundle) -> bool:
        """Validate that context is sufficient for generating useful actions."""
        try:
            # Basic validation checks
            if not context_bundle.related_events:
                logger.debug("No related events - context may be too weak")
                return False

            if context_bundle.correlation_strength < 0.3:
                logger.debug(
                    f"Correlation strength too low: {context_bundle.correlation_strength}"
                )
                return False

            # Use GPT-4 for sophisticated context validation
            validation_prompt = get_context_validation_prompt(
                context_bundle.model_dump()
            )

            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a context validator. Analyze the provided context and determine if it's sufficient for generating useful actions.",
                    },
                    {"role": "user", "content": validation_prompt},
                ],
                temperature=0.2,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            validation_result = json.loads(response.choices[0].message.content)

            is_sufficient = validation_result.get("sufficient", False)
            reasoning = validation_result.get("reasoning", "No reasoning provided")

            logger.debug(
                f"Context validation for {context_bundle.correlation_id}: {is_sufficient} - {reasoning}"
            )

            return is_sufficient

        except Exception as e:
            logger.error(f"Error validating context quality: {e}")
            return True  # Allow on error to avoid blocking valid actions

    async def generate_actions_with_gpt4(self, context_bundle) -> list[dict[str, Any]]:
        """Use GPT-4 to generate actions from context."""
        try:
            # Prepare the context data for the prompt
            context_data = context_bundle.model_dump()

            # Generate the prompt
            prompt = get_action_generation_prompt(context_data)

            # Call GPT-4 with optimized parameters
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Saathy, a proactive AI assistant that helps knowledge workers by analyzing their cross-platform activity and suggesting specific, actionable next steps. Always respond with valid JSON containing concrete actions.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            # Parse response
            response_text = response.choices[0].message.content
            actions_data = json.loads(response_text)

            # Validate and clean actions
            actions = actions_data.get("actions", [])
            validated_actions = []

            for action in actions:
                if self.validate_action_data(action):
                    # Add platform-specific links
                    action = await self.enhance_action_links(action, context_data)
                    validated_actions.append(action)
                else:
                    logger.warning(f"Invalid action data: {action}")

            # Refine actions if they seem too generic
            if validated_actions and self.actions_seem_generic(validated_actions):
                logger.info("Actions seem generic, refining...")
                validated_actions = await self.refine_generic_actions(
                    validated_actions, context_data
                )

            # Limit number of actions
            return validated_actions[: self.max_actions_per_correlation]

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error calling GPT-4 for action generation: {e}")
            return []

    def validate_action_data(self, action: dict[str, Any]) -> bool:
        """Validate that action data has required fields and reasonable content."""
        required_fields = [
            "title",
            "description",
            "priority",
            "action_type",
            "reasoning",
        ]

        for field in required_fields:
            if not action.get(field):
                logger.warning(f"Action missing required field: {field}")
                return False

        # Validate priority
        valid_priorities = ["urgent", "high", "medium", "low", "fyi"]
        if action["priority"].lower() not in valid_priorities:
            logger.warning(f"Invalid priority: {action['priority']}")
            return False

        # Validate action_type
        valid_types = [
            "review",
            "respond",
            "update",
            "meeting",
            "follow_up",
            "create",
            "fix",
        ]
        if action["action_type"].lower() not in valid_types:
            logger.warning(f"Invalid action_type: {action['action_type']}")
            return False

        # Check for specificity
        title = action["title"].lower()
        description = action["description"].lower()

        # Generic action detection
        generic_indicators = [
            "check",
            "look at",
            "review the",
            "update the",
            "follow up on the",
        ]
        if any(
            indicator in title or indicator in description
            for indicator in generic_indicators
        ):
            logger.debug(f"Action may be too generic: {action['title']}")

        return True

    def actions_seem_generic(self, actions: list[dict[str, Any]]) -> bool:
        """Check if actions seem too generic and need refinement."""
        generic_keywords = [
            "check",
            "review",
            "update",
            "follow up",
            "look at",
            "consider",
        ]

        for action in actions:
            title = action["title"].lower()
            description = action["description"].lower()

            # If title is very short and uses generic words
            if len(title.split()) <= 3 and any(
                word in title for word in generic_keywords
            ):
                return True

            # If description doesn't contain specific references
            if not any(
                indicator in description
                for indicator in ["#", "pr", "issue", "@", "commit"]
            ):
                if any(word in description for word in generic_keywords):
                    return True

        return False

    async def refine_generic_actions(
        self, actions: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Refine actions that are too generic."""
        try:
            refinement_prompt = get_action_refinement_prompt(actions, context)

            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are refining actions to be more specific and actionable. Respond with valid JSON.",
                    },
                    {"role": "user", "content": refinement_prompt},
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            refined_data = json.loads(response.choices[0].message.content)
            refined_actions = refined_data.get("actions", [])

            # Validate refined actions
            validated_refined = []
            for action in refined_actions:
                if self.validate_action_data(action):
                    validated_refined.append(action)

            return validated_refined if validated_refined else actions

        except Exception as e:
            logger.error(f"Error refining actions: {e}")
            return actions

    async def enhance_action_links(
        self, action: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Add platform-specific action links to the action."""
        try:
            enhanced_links = []
            platform_data = context["platform_data"]

            # Add Slack links
            slack_data = platform_data.get("slack", {})
            if slack_data.get("messages"):
                for message in slack_data["messages"][-2:]:  # Last 2 messages
                    channel = message.get("channel", "unknown")
                    # Generate Slack deep link (simplified)
                    slack_url = (
                        f"slack://channel?team=T123456&id=C{hash(channel) % 1000000}"
                    )
                    enhanced_links.append(
                        {
                            "platform": "slack",
                            "url": slack_url,
                            "label": f"View discussion in #{channel}",
                            "action_type": "view",
                        }
                    )

            # Add GitHub links
            github_data = platform_data.get("github", {})
            if github_data.get("prs"):
                for pr in github_data["prs"][:2]:  # First 2 PRs
                    repo = pr.get("repo", "unknown")
                    pr_number = pr.get("number")
                    if pr_number:
                        github_url = f"https://github.com/{repo}/pull/{pr_number}"
                        enhanced_links.append(
                            {
                                "platform": "github",
                                "url": github_url,
                                "label": f"View PR #{pr_number}",
                                "action_type": "view",
                            }
                        )

            if github_data.get("commits"):
                for commit in github_data["commits"][:1]:  # First commit
                    repo = commit.get("repo", "unknown")
                    sha = commit.get("sha")
                    if sha:
                        github_url = f"https://github.com/{repo}/commit/{sha}"
                        enhanced_links.append(
                            {
                                "platform": "github",
                                "url": github_url,
                                "label": f"View commit {sha}",
                                "action_type": "view",
                            }
                        )

            if github_data.get("issues"):
                for issue in github_data["issues"][:1]:  # First issue
                    repo = issue.get("repo", "unknown")
                    issue_number = issue.get("number")
                    if issue_number:
                        github_url = f"https://github.com/{repo}/issues/{issue_number}"
                        enhanced_links.append(
                            {
                                "platform": "github",
                                "url": github_url,
                                "label": f"View Issue #{issue_number}",
                                "action_type": "view",
                            }
                        )

            # Add Notion links
            notion_data = platform_data.get("notion", {})
            if notion_data.get("pages"):
                for page in notion_data["pages"][:2]:  # First 2 pages
                    url = page.get("url")
                    title = page.get("title", "Untitled")
                    if url:
                        enhanced_links.append(
                            {
                                "platform": "notion",
                                "url": url,
                                "label": f'Edit "{title}"',
                                "action_type": "edit",
                            }
                        )

            # Add links to action (limit to 3 most relevant)
            action["action_links"] = enhanced_links[:3]

            return action

        except Exception as e:
            logger.error(f"Error enhancing action links: {e}")
            return action

    async def create_and_store_action(
        self, action_data: dict[str, Any], correlation_id: str, user_id: str
    ) -> Optional[GeneratedAction]:
        """Create and store a GeneratedAction."""
        try:
            # Generate unique action ID
            action_id = f"action_{user_id}_{int(datetime.now().timestamp())}_{hash(action_data['title']) % 1000}"

            # Convert action links
            action_links = []
            for link_data in action_data.get("action_links", []):
                action_links.append(ActionLink(**link_data))

            # Set expiration (actions expire after 24 hours by default)
            expires_at = datetime.now() + timedelta(hours=24)

            # Adjust expiration based on priority
            priority = action_data["priority"].lower()
            if priority == "urgent":
                expires_at = datetime.now() + timedelta(
                    hours=4
                )  # Urgent actions expire quickly
            elif priority == "high":
                expires_at = datetime.now() + timedelta(hours=12)
            elif priority in ["low", "fyi"]:
                expires_at = datetime.now() + timedelta(
                    days=3
                )  # Low priority actions last longer

            # Create GeneratedAction
            generated_action = GeneratedAction(
                action_id=action_id,
                title=action_data["title"],
                description=action_data["description"],
                priority=ActionPriority(action_data["priority"].lower()),
                action_type=ActionType(action_data["action_type"].lower()),
                reasoning=action_data["reasoning"],
                context_summary=action_data.get(
                    "context_summary", action_data["description"][:200]
                ),
                estimated_time_minutes=action_data.get("estimated_time_minutes", 15),
                action_links=action_links,
                related_people=action_data.get("related_people", []),
                user_id=user_id,
                correlation_id=correlation_id,
                expires_at=expires_at,
            )

            # Store in Redis
            await self.store_action(generated_action)

            # Add to user's action queue
            await self.add_to_user_queue(user_id, action_id)

            # Update daily counter
            await self.increment_daily_counter(user_id)

            logger.info(
                f"Created and stored action {action_id}: {generated_action.title}"
            )
            return generated_action

        except Exception as e:
            logger.error(f"Error creating action: {e}")
            return None

    async def store_action(self, action: GeneratedAction):
        """Store action in Redis."""
        try:
            if not self.redis:
                raise RuntimeError("Redis not initialized")

            action_key = f"action:{action.action_id}"
            action_data = action.model_dump_json()

            # Store with 7 day expiration
            await self.redis.setex(action_key, 7 * 24 * 60 * 60, action_data)

        except Exception as e:
            logger.error(f"Error storing action: {e}")

    async def add_to_user_queue(self, user_id: str, action_id: str):
        """Add action to user's priority queue."""
        try:
            if not self.redis:
                return

            user_queue_key = f"user:{user_id}:actions"

            # Use current timestamp as score for chronological ordering
            await self.redis.zadd(
                user_queue_key, {action_id: datetime.now().timestamp()}
            )

            # Keep only last 50 actions per user
            await self.redis.zremrangebyrank(user_queue_key, 0, -51)

        except Exception as e:
            logger.error(f"Error adding action to user queue: {e}")

    async def increment_daily_counter(self, user_id: str):
        """Increment daily action counter for user."""
        try:
            if not self.redis:
                return

            today_key = (
                f"user:{user_id}:actions:daily:{datetime.now().strftime('%Y-%m-%d')}"
            )
            await self.redis.incr(today_key)
            await self.redis.expire(today_key, 25 * 60 * 60)  # Expire after 25 hours

        except Exception as e:
            logger.error(f"Error incrementing daily counter: {e}")

    async def update_correlation_status(self, correlation_id: str, status: str):
        """Update correlation status after action generation."""
        try:
            if not self.redis:
                return

            correlation_key = f"correlation:{correlation_id}"
            correlation_data = await self.redis.get(correlation_key)

            if correlation_data:
                correlation = json.loads(correlation_data)
                correlation["status"] = status
                correlation["actions_generated_at"] = datetime.now().isoformat()

                await self.redis.setex(
                    correlation_key,
                    24 * 60 * 60,  # 24 hours
                    json.dumps(correlation),
                )

        except Exception as e:
            logger.error(f"Error updating correlation status: {e}")

    async def start_action_generation_processor(self):
        """Background processor for action generation queue."""
        action_queue_key = "saathy:action_generation"

        logger.info("Starting action generation processor...")

        while True:
            try:
                if not self.redis:
                    logger.error(
                        "Redis not initialized for action generation processor"
                    )
                    await asyncio.sleep(5)
                    continue

                # Get next correlation from queue
                result = await self.redis.brpop(action_queue_key, timeout=10)

                if result:
                    queue_name, correlation_id = result
                    correlation_id = correlation_id.decode()

                    logger.info(
                        f"Processing action generation for correlation {correlation_id}"
                    )

                    # Generate actions
                    actions = await self.generate_actions_for_correlation(
                        correlation_id
                    )

                    if actions:
                        logger.info(
                            f"Generated {len(actions)} actions for correlation {correlation_id}"
                        )

                        # Notify users about new actions (could integrate with Slack/email here)
                        await self.notify_user_of_actions(actions)
                    else:
                        logger.warning(
                            f"No actions generated for correlation {correlation_id}"
                        )

            except Exception as e:
                logger.error(f"Error in action generation processor: {e}")
                await asyncio.sleep(5)

    async def notify_user_of_actions(self, actions: list[GeneratedAction]):
        """Notify user about new actions (placeholder for future implementation)."""
        try:
            # This could send Slack messages, emails, or push notifications
            # For now, just log the actions
            user_id = actions[0].user_id if actions else "unknown"
            action_titles = [action.title for action in actions]

            logger.info(f"New actions for {user_id}: {', '.join(action_titles)}")

        except Exception as e:
            logger.error(f"Error notifying user of actions: {e}")

    async def get_user_actions(
        self, user_id: str, limit: int = 20
    ) -> list[GeneratedAction]:
        """Get recent actions for a user."""
        try:
            if not self.redis:
                return []

            user_queue_key = f"user:{user_id}:actions"

            # Get action IDs (most recent first)
            action_ids = await self.redis.zrevrange(user_queue_key, 0, limit - 1)

            actions = []
            for action_id in action_ids:
                action_key = f"action:{action_id.decode()}"
                action_data = await self.redis.get(action_key)

                if action_data:
                    action_dict = json.loads(action_data)
                    try:
                        action = GeneratedAction(**action_dict)
                        # Only return non-expired actions
                        if not action.expires_at or action.expires_at > datetime.now():
                            actions.append(action)
                    except Exception as e:
                        logger.warning(f"Error parsing action {action_id}: {e}")

            return actions

        except Exception as e:
            logger.error(f"Error getting user actions: {e}")
            return []

    async def close(self):
        """Close connections."""
        if self.redis:
            await self.redis.close()
        await self.context_synthesizer.close()
        logger.info("Action generator connections closed")
