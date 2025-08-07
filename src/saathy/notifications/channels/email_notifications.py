import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self, 
                 smtp_server: str = None,
                 smtp_port: int = 587,
                 username: str = None,
                 password: str = None):
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.username = username or os.getenv('SMTP_USERNAME')
        self.password = password or os.getenv('SMTP_PASSWORD')

    async def send_action_notification(self, 
                                     user_id: str, 
                                     action_data: Dict[str, Any], 
                                     content: Dict[str, str]) -> bool:
        """Send single action notification email"""
        try:
            user_email = await self.get_user_email(user_id)
            if not user_email:
                logger.error(f"No email found for user {user_id}")
                return False

            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = user_email
            msg['Subject'] = content['subject']
            
            # Create email body
            body = self.create_single_action_email_body(action_data, content)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            return await self.send_email(msg)
            
        except Exception as e:
            logger.error(f"Error sending action notification email: {e}")
            return False

    async def send_batch_notification(self, user_id: str, actions: List[Dict[str, Any]]) -> bool:
        """Send batch notification email with multiple actions"""
        try:
            user_email = await self.get_user_email(user_id)
            if not user_email:
                return False

            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = user_email
            msg['Subject'] = f"⚡ {len(actions)} actions need your attention"
            
            # Create batch email body
            body = self.create_batch_email_body(actions)
            msg.attach(MIMEText(body, 'html'))
            
            return await self.send_email(msg)
            
        except Exception as e:
            logger.error(f"Error sending batch notification email: {e}")
            return False

    def create_single_action_email_body(self, action_data: Dict[str, Any], content: Dict[str, str]) -> str:
        """Create HTML email body for single action"""
        
        action_links_html = ""
        for link in content.get('action_links', []):
            platform_emoji = {'slack': '💬', 'github': '🐙', 'notion': '📝'}.get(link['platform'], '🔗')
            action_links_html += f"""
            <tr>
                <td style="padding: 8px 0;">
                    <a href="{link['url']}" style="display: inline-block; padding: 10px 20px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px;">
                        {platform_emoji} {link['label']}
                    </a>
                </td>
            </tr>
            """

        priority_color = {
            'urgent': '#dc3545',
            'high': '#fd7e14', 
            'medium': '#ffc107',
            'low': '#17a2b8',
            'fyi': '#6c757d'
        }.get(action_data.get('priority', 'medium'), '#ffc107')

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .action-card {{ background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
                .priority-badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
                .time-badge {{ display: inline-block; padding: 5px 12px; background-color: #e9ecef; border-radius: 20px; font-size: 12px; color: #495057; margin-left: 10px; }}
                .reason-box {{ background-color: #f1f3f5; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🤖 Saathy Action Alert</h1>
                </div>
                <div class="content">
                    <div class="action-card">
                        <h2 style="margin-top: 0; color: #212529;">{action_data.get('title', 'Action Required')}</h2>
                        <div style="margin-bottom: 20px;">
                            <span class="priority-badge" style="background-color: {priority_color}; color: white;">
                                {action_data.get('priority', 'medium').upper()}
                            </span>
                            <span class="time-badge">
                                ~{action_data.get('estimated_time_minutes', 15)} minutes
                            </span>
                        </div>
                        
                        <p style="color: #495057; margin-bottom: 20px;">
                            {action_data.get('description', '')}
                        </p>
                        
                        <div class="reason-box">
                            <strong>Why now:</strong> {action_data.get('reasoning', '')}
                        </div>
                        
                        <table style="margin-top: 20px;">
                            {action_links_html}
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
                    <p><a href="#" style="color: #4F46E5;">Manage notification preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body

    def create_batch_email_body(self, actions: List[Dict[str, Any]]) -> str:
        """Create HTML email body for batch actions"""
        
        actions_html = ""
        total_time = 0
        
        for i, action in enumerate(actions[:5], 1):  # Max 5 actions in email
            priority_color = {
                'urgent': '#dc3545', 'high': '#fd7e14', 'medium': '#ffc107', 
                'low': '#17a2b8', 'fyi': '#6c757d'
            }.get(action.get('priority', 'medium'), '#ffc107')
            
            time_estimate = action.get('estimated_time_minutes', 15)
            total_time += time_estimate
            
            actions_html += f"""
            <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid {priority_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="display: inline-block; padding: 4px 10px; background-color: {priority_color}; color: white; border-radius: 15px; font-size: 11px; font-weight: bold;">
                        {action.get('priority', 'medium').upper()}
                    </span>
                    <span style="color: #6c757d; font-size: 12px;">~{time_estimate} min</span>
                </div>
                <h3 style="margin: 0 0 10px 0; color: #212529;">{action.get('title', 'Action Required')}</h3>
                <p style="margin: 0; color: #495057; font-size: 14px;">
                    {action.get('description', '')[:150]}...
                </p>
            </div>
            """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .summary-box {{ background-color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
                .cta-button {{ display: inline-block; padding: 15px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; }}
                .footer {{ text-align: center; padding: 20px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🤖 Saathy Daily Summary</h1>
                </div>
                <div class="content">
                    <div class="summary-box">
                        <h2 style="margin: 0; color: #212529;">{len(actions)} actions need your attention</h2>
                        <p style="margin: 10px 0 0 0; color: #6c757d;">Estimated total time: {total_time} minutes</p>
                    </div>
                    
                    {actions_html}
                    
                    <div style="text-align: center;">
                        <a href="#" class="cta-button">View All Actions in Dashboard</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
                    <p><a href="#" style="color: #4F46E5;">Manage notification preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body

    async def send_email(self, msg: MIMEMultipart) -> bool:
        """Send email via SMTP"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {msg['To']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def get_user_email(self, user_id: str) -> str:
        """Get user's email address"""
        # This would typically fetch from user database
        # For now, return a placeholder or configuration-based email
        return f"{user_id}@company.com"  # Replace with actual user email lookup