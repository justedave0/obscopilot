"""
Twitch triggers for OBSCopilot workflow engine.

This module implements Twitch-specific workflow triggers.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Pattern

from obscopilot.workflows.models import TriggerType, WorkflowTrigger
from obscopilot.workflows.triggers.base import BaseTrigger, RegexPatternMixin

logger = logging.getLogger(__name__)


class BaseTwitchTrigger(BaseTrigger):
    """Base class for Twitch triggers."""
    pass


class TwitchChatMessageTrigger(BaseTwitchTrigger, RegexPatternMixin):
    """Trigger for Twitch chat messages."""
    
    trigger_type = TriggerType.TWITCH_CHAT_MESSAGE
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Compiles regex patterns for message and user.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Compile message pattern
        if "message_pattern" in config:
            config["_compiled_message_pattern"] = cls.compile_pattern(config["message_pattern"])
        
        # Compile user pattern
        if "user_pattern" in config:
            config["_compiled_user_pattern"] = cls.compile_pattern(config["user_pattern"])
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches chat message data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches chat message, False otherwise
        """
        # Extract message data
        message = event_data.get("message", "")
        username = event_data.get("username", "")
        channel = event_data.get("channel", "")
        is_mod = event_data.get("is_mod", False)
        is_sub = event_data.get("is_sub", False)
        is_broadcaster = event_data.get("is_broadcaster", False)
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        # Check message pattern
        message_pattern = config.get("_compiled_message_pattern")
        if message_pattern and not cls.matches_pattern(message_pattern, message):
            return False
        
        # Check user pattern
        user_pattern = config.get("_compiled_user_pattern")
        if user_pattern and not cls.matches_pattern(user_pattern, username):
            return False
        
        # Check mod/sub/broadcaster flags
        if config.get("is_mod_only", False) and not is_mod:
            return False
        
        if config.get("is_sub_only", False) and not is_sub:
            return False
        
        if config.get("is_broadcaster_only", False) and not is_broadcaster:
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "message_pattern": {
                "type": "string",
                "description": "Regex pattern to match messages",
                "required": False
            },
            "user_pattern": {
                "type": "string",
                "description": "Regex pattern to match usernames",
                "required": False
            },
            "is_mod_only": {
                "type": "boolean",
                "description": "Only trigger on moderator messages",
                "default": False,
                "required": False
            },
            "is_sub_only": {
                "type": "boolean",
                "description": "Only trigger on subscriber messages",
                "default": False,
                "required": False
            },
            "is_broadcaster_only": {
                "type": "boolean",
                "description": "Only trigger on broadcaster messages",
                "default": False,
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        }


class TwitchFollowTrigger(BaseTwitchTrigger, RegexPatternMixin):
    """Trigger for Twitch follows."""
    
    trigger_type = TriggerType.TWITCH_FOLLOW
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Compiles regex pattern for username.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Compile user pattern
        if "user_pattern" in config:
            config["_compiled_user_pattern"] = cls.compile_pattern(config["user_pattern"])
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches follow event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches follow event, False otherwise
        """
        # Extract follow data
        username = event_data.get("username", "")
        channel = event_data.get("channel", "")
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        # Check user pattern
        user_pattern = config.get("_compiled_user_pattern")
        if user_pattern and not cls.matches_pattern(user_pattern, username):
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "user_pattern": {
                "type": "string",
                "description": "Regex pattern to match usernames",
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        }


class TwitchSubscriptionTrigger(BaseTwitchTrigger, RegexPatternMixin):
    """Trigger for Twitch subscriptions."""
    
    trigger_type = TriggerType.TWITCH_SUBSCRIPTION
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Compiles regex pattern for username.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Compile user pattern
        if "user_pattern" in config:
            config["_compiled_user_pattern"] = cls.compile_pattern(config["user_pattern"])
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches subscription event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches subscription event, False otherwise
        """
        # Extract subscription data
        username = event_data.get("username", "")
        channel = event_data.get("channel", "")
        is_gift = event_data.get("is_gift", False)
        is_resub = event_data.get("is_resub", False)
        tier = event_data.get("tier", "1000")  # Default to Tier 1
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        # Check user pattern
        user_pattern = config.get("_compiled_user_pattern")
        if user_pattern and not cls.matches_pattern(user_pattern, username):
            return False
        
        # Check subscription type
        if config.get("is_gift_only", False) and not is_gift:
            return False
        
        if config.get("is_resub_only", False) and not is_resub:
            return False
        
        # Check tier
        if config.get("tier") and config["tier"] != tier:
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "user_pattern": {
                "type": "string",
                "description": "Regex pattern to match usernames",
                "required": False
            },
            "is_gift_only": {
                "type": "boolean",
                "description": "Only trigger on gift subscriptions",
                "default": False,
                "required": False
            },
            "is_resub_only": {
                "type": "boolean",
                "description": "Only trigger on resubscriptions",
                "default": False,
                "required": False
            },
            "tier": {
                "type": "string",
                "description": "Subscription tier (1000, 2000, 3000)",
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        }


class TwitchBitsTrigger(BaseTwitchTrigger, RegexPatternMixin):
    """Trigger for Twitch bits/cheers."""
    
    trigger_type = TriggerType.TWITCH_BITS
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Compiles regex pattern for username.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Compile user pattern
        if "user_pattern" in config:
            config["_compiled_user_pattern"] = cls.compile_pattern(config["user_pattern"])
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches bits event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches bits event, False otherwise
        """
        # Extract bits data
        username = event_data.get("username", "")
        channel = event_data.get("channel", "")
        bits = event_data.get("bits", 0)
        message = event_data.get("message", "")
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        # Check user pattern
        user_pattern = config.get("_compiled_user_pattern")
        if user_pattern and not cls.matches_pattern(user_pattern, username):
            return False
        
        # Check bits amount
        if config.get("min_bits") is not None and bits < config["min_bits"]:
            return False
        
        if config.get("max_bits") is not None and bits > config["max_bits"]:
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "user_pattern": {
                "type": "string",
                "description": "Regex pattern to match usernames",
                "required": False
            },
            "min_bits": {
                "type": "integer",
                "description": "Minimum bits amount",
                "required": False
            },
            "max_bits": {
                "type": "integer",
                "description": "Maximum bits amount",
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        }


class TwitchRaidTrigger(BaseTwitchTrigger, RegexPatternMixin):
    """Trigger for Twitch raids."""
    
    trigger_type = TriggerType.TWITCH_RAID
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Compiles regex pattern for raider username.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Compile raider pattern
        if "raider_pattern" in config:
            config["_compiled_raider_pattern"] = cls.compile_pattern(config["raider_pattern"])
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches raid event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches raid event, False otherwise
        """
        # Extract raid data
        raider = event_data.get("raider", "")
        channel = event_data.get("channel", "")
        viewers = event_data.get("viewers", 0)
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        # Check raider pattern
        raider_pattern = config.get("_compiled_raider_pattern")
        if raider_pattern and not cls.matches_pattern(raider_pattern, raider):
            return False
        
        # Check viewers count
        if config.get("min_viewers") is not None and viewers < config["min_viewers"]:
            return False
        
        if config.get("max_viewers") is not None and viewers > config["max_viewers"]:
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "raider_pattern": {
                "type": "string",
                "description": "Regex pattern to match raider usernames",
                "required": False
            },
            "min_viewers": {
                "type": "integer",
                "description": "Minimum viewers count",
                "required": False
            },
            "max_viewers": {
                "type": "integer",
                "description": "Maximum viewers count",
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        }


class TwitchChannelPointsRedeemTrigger(BaseTwitchTrigger, RegexPatternMixin):
    """Trigger for Twitch channel points redemptions."""
    
    trigger_type = TriggerType.TWITCH_CHANNEL_POINTS_REDEEM
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Compiles regex patterns for username and reward title.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Compile user pattern
        if "user_pattern" in config:
            config["_compiled_user_pattern"] = cls.compile_pattern(config["user_pattern"])
        
        # Compile reward pattern
        if "reward_pattern" in config:
            config["_compiled_reward_pattern"] = cls.compile_pattern(config["reward_pattern"])
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches channel points redemption data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches redemption, False otherwise
        """
        # Extract redemption data
        username = event_data.get("username", "")
        channel = event_data.get("channel", "")
        reward_title = event_data.get("reward_title", "")
        reward_cost = event_data.get("reward_cost", 0)
        user_input = event_data.get("user_input", "")
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        # Check user pattern
        user_pattern = config.get("_compiled_user_pattern")
        if user_pattern and not cls.matches_pattern(user_pattern, username):
            return False
        
        # Check reward title pattern
        reward_pattern = config.get("_compiled_reward_pattern")
        if reward_pattern and not cls.matches_pattern(reward_pattern, reward_title):
            return False
        
        # Check exact reward title
        if config.get("reward_title") and config["reward_title"] != reward_title:
            return False
        
        # Check reward cost
        if config.get("min_cost") is not None and reward_cost < config["min_cost"]:
            return False
        
        if config.get("max_cost") is not None and reward_cost > config["max_cost"]:
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "user_pattern": {
                "type": "string",
                "description": "Regex pattern to match usernames",
                "required": False
            },
            "reward_pattern": {
                "type": "string",
                "description": "Regex pattern to match reward titles",
                "required": False
            },
            "reward_title": {
                "type": "string",
                "description": "Exact reward title to match",
                "required": False
            },
            "min_cost": {
                "type": "integer",
                "description": "Minimum reward cost",
                "required": False
            },
            "max_cost": {
                "type": "integer",
                "description": "Maximum reward cost",
                "required": False
            },
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        }


class TwitchStreamOnlineTrigger(BaseTwitchTrigger):
    """Trigger for Twitch stream going online."""
    
    trigger_type = TriggerType.TWITCH_STREAM_ONLINE
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches stream online event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches stream online event, False otherwise
        """
        # Extract stream data
        channel = event_data.get("channel", "")
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        }


class TwitchStreamOfflineTrigger(BaseTwitchTrigger):
    """Trigger for Twitch stream going offline."""
    
    trigger_type = TriggerType.TWITCH_STREAM_OFFLINE
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches stream offline event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches stream offline event, False otherwise
        """
        # Extract stream data
        channel = event_data.get("channel", "")
        
        # Check channel
        if config.get("channel") and channel and config["channel"].lower() != channel.lower():
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "channel": {
                "type": "string",
                "description": "Channel to listen to",
                "required": False
            }
        } 