from slack_sdk.web.async_client import AsyncWebClient
from typing import Dict, Any, List
import logging
import os

logger = logging.getLogger(__name__)

class SlackNotifier:
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.client = AsyncWebClient(token=self.bot_token) if self.bot_token else None

    async def send_dm_notification(self, 
                                 user_id: str, 
                                 action_data: Dict[str, Any], 
                                 content: Dict[str, str]) -> bool:
        """Send direct message notification to user"""
        try:
            if not self.client:
                logger.error("Slack client not initialized")
                return False

            # Get user's Slack ID
            slack_user_id = await self.get_slack_user_id(user_id)
            if not slack_user_id:
                logger.error(f"No Slack user ID found for {user_id}")
                return False

            # Create message blocks
            blocks = self.create_action_message_blocks(action_data, content)
            
            # Send DM
            response = await self.client.chat_postMessage(
                channel=slack_user_id,
                text=content['short_text'],  # Fallback text
                blocks=blocks
            )
            
            if response['ok']:
                logger.info(f"Slack notification sent to {user_id}")
                return True
            else:
                logger.error(f"Failed to send Slack notification: {response['error']}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    async def send_batch_dm(self, user_id: str, actions: List[Dict[str, Any]]) -> bool:
        """Send batch DM with multiple actions"""
        try:
            if not self.client:
                logger.error("Slack client not initialized")
                return False

            slack_user_id = await self.get_slack_user_id(user_id)
            if not slack_user_id:
                return False

            blocks = self.create_batch_message_blocks(actions)
            
            response = await self.client.chat_postMessage(
                channel=slack_user_id,
                text=f"🤖 {len(actions)} actions need your attention",
                blocks=blocks
            )
            
            return response['ok']
            
        except Exception as e:
            logger.error(f"Error sending batch Slack notification: {e}")
            return False

    def create_action_message_blocks(self, action_data: Dict[str, Any], content: Dict[str, str]) -> List[Dict]:
        """Create Slack message blocks for single action"""
        
        priority_emoji = {
            'urgent': '🚨',
            'high': '⚡',
            'medium': '📋',
            'low': '📝',
            'fyi': 'ℹ️'
        }
        
        priority = action_data.get('priority', 'medium')
        emoji = priority_emoji.get(priority, '📋')
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Action: {action_data.get('title', 'New Action')}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:* {priority.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:* ~{action_data.get('estimated_time_minutes', 15)} min"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": action_data.get('description', '')
                }
            }
        ]
        
        # Add context/reasoning
        if action_data.get('reasoning'):
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"💡 *Why now:* {action_data['reasoning']}"
                    }
                ]
            })
        
        # Add action buttons
        if content.get('action_links'):
            elements = []
            for link in content['action_links'][:3]:  # Max 3 buttons
                platform_emoji = {'slack': '💬', 'github': '🐙', 'notion': '📝'}.get(link['platform'], '🔗')
                elements.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": f"{platform_emoji} {link['label']}"
                    },
                    "url": link['url'],
                    "action_id": f"action_link_{link['platform']}"
                })
            
            if elements:
                blocks.append({
                    "type": "actions",
                    "elements": elements
                })
        
        # Add completion buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Mark Complete"
                    },
                    "style": "primary",
                    "action_id": f"complete_{action_data.get('action_id')}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 View Dashboard"
                    },
                    "url": os.getenv('DASHBOARD_URL', 'https://saathy.example.com/actions'),
                    "action_id": "view_dashboard"
                }
            ]
        })
        
        return blocks

    def create_batch_message_blocks(self, actions: List[Dict[str, Any]]) -> List[Dict]:
        """Create Slack message blocks for batch actions"""
        
        total_time = sum(action.get('estimated_time_minutes', 15) for action in actions)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🤖 Daily Summary: {len(actions)} actions need attention",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total actions:* {len(actions)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Estimated time:* {total_time} minutes"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        # Add top 3 actions
        for action in actions[:3]:
            priority_emoji = {
                'urgent': '🚨', 'high': '⚡', 'medium': '📋', 
                'low': '📝', 'fyi': 'ℹ️'
            }
            
            priority = action.get('priority', 'medium')
            emoji = priority_emoji.get(priority, '📋')
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{action.get('title', 'Action')}*\n{action.get('description', '')[:100]}..."
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:* {priority.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:* ~{action.get('estimated_time_minutes', 15)} min"
                    }
                ]
            })
        
        if len(actions) > 3:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"... and {len(actions) - 3} more actions"
                    }
                ]
            })
        
        # Add dashboard button
        blocks.extend([
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📋 View All Actions"
                        },
                        "style": "primary",
                        "url": os.getenv('DASHBOARD_URL', 'https://saathy.example.com/actions'),
                        "action_id": "view_all_actions"
                    }
                ]
            }
        ])
        
        return blocks

    async def get_slack_user_id(self, user_id: str) -> str:
        """Get Slack user ID for internal user ID"""
        # This would typically look up the mapping in your user database
        # For now, return the user_id assuming it's already a Slack ID
        return user_id  # Replace with actual lookup logic