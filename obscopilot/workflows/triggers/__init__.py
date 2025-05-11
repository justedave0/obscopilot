"""
Workflow triggers package for OBSCopilot.

This package contains all the trigger implementations for the workflow engine.
"""

from obscopilot.workflows.models import TriggerType

# Import trigger implementations
from .twitch_triggers import (
    TwitchChatMessageTrigger,
    TwitchFollowTrigger,
    TwitchSubscriptionTrigger,
    TwitchBitsTrigger,
    TwitchRaidTrigger,
    TwitchChannelPointsRedeemTrigger,
    TwitchStreamOnlineTrigger,
    TwitchStreamOfflineTrigger
)
from .obs_triggers import (
    ObsSceneChangedTrigger,
    ObsStreamingStartedTrigger,
    ObsStreamingStoppedTrigger,
    ObsRecordingStartedTrigger,
    ObsRecordingStoppedTrigger
)
from .time_triggers import (
    ScheduleTrigger,
    IntervalTrigger
)
from .manual_triggers import (
    ManualTrigger,
    HotkeyTrigger
)
from .chat_triggers import ChatCommandTrigger

# Register all triggers
TRIGGER_REGISTRY = {
    # Twitch triggers
    TriggerType.TWITCH_CHAT_MESSAGE: TwitchChatMessageTrigger,
    TriggerType.TWITCH_FOLLOW: TwitchFollowTrigger,
    TriggerType.TWITCH_SUBSCRIPTION: TwitchSubscriptionTrigger,
    TriggerType.TWITCH_BITS: TwitchBitsTrigger,
    TriggerType.TWITCH_RAID: TwitchRaidTrigger,
    TriggerType.TWITCH_CHANNEL_POINTS_REDEEM: TwitchChannelPointsRedeemTrigger,
    TriggerType.TWITCH_STREAM_ONLINE: TwitchStreamOnlineTrigger,
    TriggerType.TWITCH_STREAM_OFFLINE: TwitchStreamOfflineTrigger,
    
    # Chat command triggers
    TriggerType.CHAT_COMMAND: ChatCommandTrigger,
    
    # OBS triggers
    TriggerType.OBS_SCENE_CHANGED: ObsSceneChangedTrigger,
    TriggerType.OBS_STREAMING_STARTED: ObsStreamingStartedTrigger,
    TriggerType.OBS_STREAMING_STOPPED: ObsStreamingStoppedTrigger,
    TriggerType.OBS_RECORDING_STARTED: ObsRecordingStartedTrigger,
    TriggerType.OBS_RECORDING_STOPPED: ObsRecordingStoppedTrigger,
    
    # Time triggers
    TriggerType.SCHEDULE: ScheduleTrigger,
    TriggerType.INTERVAL: IntervalTrigger,
    
    # Manual triggers
    TriggerType.MANUAL: ManualTrigger,
    TriggerType.HOTKEY: HotkeyTrigger
}

# Define metadata for triggers
TRIGGER_METADATA = {
    # Twitch triggers
    TriggerType.TWITCH_CHAT_MESSAGE: {
        "name": "Twitch Chat Message",
        "description": "Triggered when a message is sent in Twitch chat",
        "icon": "chat",
        "category": "Twitch",
        "config_schema": {
            "channel": {"type": "string", "description": "Channel name (leave empty for any channel)"},
            "username": {"type": "string", "description": "Username (leave empty for any user)"},
            "message_pattern": {"type": "string", "description": "Regex pattern to match message content"}
        }
    },
    
    # Add metadata for other trigger types as needed
    
    # Chat command triggers
    TriggerType.CHAT_COMMAND: {
        "name": "Chat Command",
        "description": "Triggered when a specific chat command is used",
        "icon": "bolt",
        "category": "Twitch",
        "config_schema": {
            "command_name": {"type": "string", "description": "Command name (without prefix)", "required": True},
            "arg_pattern": {"type": "string", "description": "Regex pattern to match command arguments"},
            "required_permission": {
                "type": "string", 
                "description": "Required permission to use command", 
                "enum": ["broadcaster", "mod", "vip", "sub", ""]
            }
        }
    },
}

def get_trigger_class(trigger_type: TriggerType):
    """Get the trigger class for a given trigger type.
    
    Args:
        trigger_type: Type of trigger
        
    Returns:
        Trigger class or None if not found
    """
    return TRIGGER_REGISTRY.get(trigger_type)

def get_trigger_metadata(trigger_type: TriggerType):
    """Get metadata for a trigger type.
    
    Args:
        trigger_type: Type of trigger
        
    Returns:
        Trigger metadata or None if not found
    """
    return TRIGGER_METADATA.get(trigger_type)

def get_all_trigger_types():
    """Get all registered trigger types.
    
    Returns:
        List of trigger types
    """
    return list(TRIGGER_REGISTRY.keys()) 