"""
Twitch actions for the workflow engine.

This module implements Twitch-specific workflow actions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from obscopilot.twitch.client import TwitchClient
from obscopilot.workflows.models import WorkflowAction, WorkflowContext

logger = logging.getLogger(__name__)


class BaseTwitchAction:
    """Base class for Twitch actions."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, twitch_client: TwitchClient) -> Any:
        """Execute the action.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            twitch_client: Twitch client instance
            
        Returns:
            Action result
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        raise NotImplementedError("Subclasses must implement get_config_schema()")


class TwitchSendChatMessageAction(BaseTwitchAction):
    """Send a message to Twitch chat."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, twitch_client: TwitchClient) -> bool:
        """Send a message to Twitch chat.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            twitch_client: Twitch client instance
            
        Returns:
            True if message was sent, False otherwise
        """
        try:
            # Get action config
            config = action.config
            
            # Resolve message template
            message = context.resolve_template(config.get('message', ''))
            if not message:
                logger.warning("No message to send")
                return False
            
            # Get channel (optional)
            channel = context.resolve_template(config.get('channel', ''))
            
            # Send message
            logger.info(f"Sending chat message: {message}")
            result = await twitch_client.send_chat_message(message, channel)
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "message": {
                "type": "string",
                "description": "Message to send",
                "required": True
            },
            "channel": {
                "type": "string",
                "description": "Channel to send message to (optional)",
                "required": False
            }
        }


class TwitchTimeoutUserAction(BaseTwitchAction):
    """Timeout a user in Twitch chat."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, twitch_client: TwitchClient) -> bool:
        """Timeout a user in Twitch chat.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            twitch_client: Twitch client instance
            
        Returns:
            True if user was timed out, False otherwise
        """
        try:
            # Get action config
            config = action.config
            
            # Get username
            username = context.resolve_template(config.get('username', ''))
            if not username:
                logger.warning("No username to timeout")
                return False
            
            # Get duration
            duration = config.get('duration', 300)  # Default 5 minutes
            
            # Get reason
            reason = context.resolve_template(config.get('reason', 'Timed out by OBSCopilot'))
            
            # Get channel (optional)
            channel = context.resolve_template(config.get('channel', ''))
            
            # Timeout user
            logger.info(f"Timing out user: {username} for {duration}s")
            result = await twitch_client.timeout_user(username, duration, reason, channel)
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error timing out user: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "username": {
                "type": "string",
                "description": "Username to timeout",
                "required": True
            },
            "duration": {
                "type": "integer",
                "description": "Timeout duration in seconds",
                "default": 300,
                "required": False
            },
            "reason": {
                "type": "string",
                "description": "Reason for timeout",
                "default": "Timed out by OBSCopilot",
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to timeout user in (optional)",
                "required": False
            }
        }


class TwitchBanUserAction(BaseTwitchAction):
    """Ban a user from Twitch chat."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, twitch_client: TwitchClient) -> bool:
        """Ban a user from Twitch chat.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            twitch_client: Twitch client instance
            
        Returns:
            True if user was banned, False otherwise
        """
        try:
            # Get action config
            config = action.config
            
            # Get username
            username = context.resolve_template(config.get('username', ''))
            if not username:
                logger.warning("No username to ban")
                return False
            
            # Get reason
            reason = context.resolve_template(config.get('reason', 'Banned by OBSCopilot'))
            
            # Get channel (optional)
            channel = context.resolve_template(config.get('channel', ''))
            
            # Ban user
            logger.info(f"Banning user: {username}")
            result = await twitch_client.ban_user(username, reason, channel)
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "username": {
                "type": "string",
                "description": "Username to ban",
                "required": True
            },
            "reason": {
                "type": "string",
                "description": "Reason for ban",
                "default": "Banned by OBSCopilot",
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to ban user in (optional)",
                "required": False
            }
        } 