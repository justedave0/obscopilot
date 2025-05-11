"""
Workflow actions package for OBSCopilot.

This package contains all the action implementations for the workflow engine.
"""

from obscopilot.workflows.models import ActionType

# Import action implementations
from .twitch_actions import (
    TwitchSendChatMessageAction,
    TwitchTimeoutUserAction,
    TwitchBanUserAction
)
from .obs_actions import (
    ObsSwitchSceneAction,
    ObsSetSourceVisibilityAction,
    ObsStartStreamingAction,
    ObsStopStreamingAction,
    ObsStartRecordingAction,
    ObsStopRecordingAction
)
from .media_actions import (
    PlaySoundAction,
    ShowImageAction,
    ShowAlertAction
)
from .ai_actions import AiGenerateResponseAction
from .control_actions import (
    DelayAction,
    ConditionalAction,
    WebhookAction,
    RunProcessAction,
    SendEmailAction
)

# Register all actions
ACTION_REGISTRY = {
    # Twitch actions
    ActionType.TWITCH_SEND_CHAT_MESSAGE: TwitchSendChatMessageAction,
    ActionType.TWITCH_TIMEOUT_USER: TwitchTimeoutUserAction,
    ActionType.TWITCH_BAN_USER: TwitchBanUserAction,
    
    # OBS actions
    ActionType.OBS_SWITCH_SCENE: ObsSwitchSceneAction,
    ActionType.OBS_SET_SOURCE_VISIBILITY: ObsSetSourceVisibilityAction,
    ActionType.OBS_START_STREAMING: ObsStartStreamingAction,
    ActionType.OBS_STOP_STREAMING: ObsStopStreamingAction,
    ActionType.OBS_START_RECORDING: ObsStartRecordingAction,
    ActionType.OBS_STOP_RECORDING: ObsStopRecordingAction,
    
    # Media actions
    ActionType.PLAY_SOUND: PlaySoundAction,
    ActionType.SHOW_IMAGE: ShowImageAction,
    ActionType.SHOW_ALERT: ShowAlertAction,
    
    # AI actions
    ActionType.AI_GENERATE_RESPONSE: AiGenerateResponseAction,
    
    # Control flow actions
    ActionType.DELAY: DelayAction,
    ActionType.CONDITIONAL: ConditionalAction,
    ActionType.WEBHOOK: WebhookAction,
    ActionType.RUN_PROCESS: RunProcessAction,
    ActionType.SEND_EMAIL: SendEmailAction
}

# Define metadata for actions
ACTION_METADATA = {
    # Twitch actions
    ActionType.TWITCH_SEND_CHAT_MESSAGE: {
        "name": "Send Chat Message",
        "description": "Send a message to Twitch chat",
        "category": "Twitch",
        "config_schema": {
            "message": {"type": "string", "description": "Message to send"},
            "channel": {"type": "string", "description": "Channel to send message to (optional)"}
        }
    },
    
    # Add metadata for other action types as needed...
}

def get_action_class(action_type: ActionType):
    """Get the action class for a given action type.
    
    Args:
        action_type: Type of action
        
    Returns:
        Action class or None if not found
    """
    return ACTION_REGISTRY.get(action_type)

def get_action_metadata(action_type: ActionType):
    """Get metadata for an action type.
    
    Args:
        action_type: Type of action
        
    Returns:
        Action metadata or None if not found
    """
    return ACTION_METADATA.get(action_type)

def get_all_action_types():
    """Get all registered action types.
    
    Returns:
        List of action types
    """
    return list(ACTION_REGISTRY.keys())
