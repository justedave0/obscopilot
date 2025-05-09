"""
OBSCopilot Configuration Module

This module manages the settings and configuration for the OBSCopilot plugin.
It provides classes for event actions and handles settings persistence.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union

# Configure logging
logger = logging.getLogger("OBSCopilot.Config")

class EventAction:
    """Represents an action to take when a Twitch event occurs"""
    
    def __init__(self, event_type: str, condition: str, action_type: str, action_data: Dict[str, Any]):
        self.event_type = event_type
        self.condition = condition
        self.action_type = action_type
        self.action_data = action_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "event_type": self.event_type,
            "condition": self.condition,
            "action_type": self.action_type,
            "action_data": self.action_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventAction':
        """Create from dictionary"""
        return cls(
            data["event_type"],
            data["condition"],
            data["action_type"],
            data["action_data"]
        )
    
    def check_condition(self, event_data: Any) -> bool:
        """Check if the condition matches the event data"""
        # Simple condition matching for now
        if not self.condition:
            return True
        
        # Parse condition (format: "key=value")
        if "=" in self.condition:
            key, value = self.condition.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Check if key exists in event data and matches value
            if hasattr(event_data, key) and str(getattr(event_data, key)) == value:
                return True
        
        return False

class Config:
    """Configuration manager for OBSCopilot"""
    
    # Default settings
    DEFAULT_SETTINGS = {
        "twitch_broadcaster_client_id": "",
        "twitch_broadcaster_client_secret": "",
        "twitch_broadcaster_access_token": "",
        "twitch_broadcaster_refresh_token": "",
        "twitch_bot_client_id": "",
        "twitch_bot_client_secret": "",
        "twitch_bot_access_token": "",
        "twitch_bot_refresh_token": "",
        "obsws_host": "localhost",
        "obsws_port": 4455,
        "obsws_password": "",
        "event_actions": []
    }
    
    # Twitch event types and related data
    TWITCH_EVENT_TYPES = [
        {
            "id": "follow",
            "name": "New Follower",
            "description": "Triggers when someone follows the channel"
        },
        {
            "id": "subscription",
            "name": "New Subscription",
            "description": "Triggers when someone subscribes to the channel"
        },
        {
            "id": "subscription_gift",
            "name": "Subscription Gift",
            "description": "Triggers when someone gifts a subscription"
        },
        {
            "id": "subscription_message",
            "name": "Resubscription Message",
            "description": "Triggers when a subscriber shares a resubscription message"
        },
        {
            "id": "cheer",
            "name": "Cheer/Bits",
            "description": "Triggers when someone cheers with bits"
        },
        {
            "id": "raid",
            "name": "Raid",
            "description": "Triggers when someone raids the channel"
        },
        {
            "id": "channel_point_redemption",
            "name": "Channel Point Redemption",
            "description": "Triggers when someone redeems channel points"
        },
        {
            "id": "stream_online",
            "name": "Stream Online",
            "description": "Triggers when the stream goes online"
        },
        {
            "id": "stream_offline",
            "name": "Stream Offline",
            "description": "Triggers when the stream goes offline"
        }
    ]
    
    # OBS action types and related data
    OBS_ACTION_TYPES = [
        {
            "id": "show_source",
            "name": "Show Source",
            "description": "Shows a source in a scene",
            "fields": [
                {"name": "scene_name", "description": "Scene name", "type": "string"},
                {"name": "source_name", "description": "Source name", "type": "string"}
            ]
        },
        {
            "id": "hide_source",
            "name": "Hide Source",
            "description": "Hides a source in a scene",
            "fields": [
                {"name": "scene_name", "description": "Scene name", "type": "string"},
                {"name": "source_name", "description": "Source name", "type": "string"}
            ]
        },
        {
            "id": "update_text",
            "name": "Update Text",
            "description": "Updates a text source with new content",
            "fields": [
                {"name": "source_name", "description": "Text source name", "type": "string"},
                {"name": "text", "description": "Text content (can use placeholders like {username})", "type": "string"}
            ]
        },
        {
            "id": "switch_scene",
            "name": "Switch Scene",
            "description": "Switches to a different scene",
            "fields": [
                {"name": "scene_name", "description": "Scene name to switch to", "type": "string"}
            ]
        },
        {
            "id": "play_media",
            "name": "Play Media",
            "description": "Play a media source",
            "fields": [
                {"name": "source_name", "description": "Media source name", "type": "string"}
            ]
        }
    ]
    
    def __init__(self):
        """Initialize configuration with default settings"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.obs_data = None  # Will hold OBS data object (set by the script)
    
    def set_obs_data(self, obs_data):
        """Set the OBS data object for saving/loading settings"""
        self.obs_data = obs_data
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self.settings[key] = value
    
    def add_event_action(self, event_action: EventAction) -> None:
        """Add an event action to the configuration"""
        if not isinstance(self.settings["event_actions"], list):
            self.settings["event_actions"] = []
        
        self.settings["event_actions"].append(event_action)
        logger.info(f"Added event action: {event_action.event_type} -> {event_action.action_type}")
    
    def remove_event_action(self, index: int) -> Optional[EventAction]:
        """Remove an event action at the specified index"""
        if 0 <= index < len(self.settings["event_actions"]):
            action = self.settings["event_actions"].pop(index)
            logger.info(f"Removed event action at index {index}")
            return action
        return None
    
    def get_event_actions(self) -> List[EventAction]:
        """Get all event actions"""
        if not self.settings["event_actions"]:
            return []
        
        # Convert dict objects to EventAction objects if needed
        actions = []
        for action in self.settings["event_actions"]:
            if isinstance(action, dict):
                actions.append(EventAction.from_dict(action))
            else:
                actions.append(action)
        
        return actions
    
    def save_to_obs(self) -> bool:
        """Save configuration to OBS data if available"""
        if not self.obs_data:
            logger.warning("No OBS data object available for saving")
            return False
        
        import obspython as obs
        
        try:
            # Save basic settings
            for key, value in self.settings.items():
                if key != "event_actions":
                    if isinstance(value, str):
                        obs.obs_data_set_string(self.obs_data, key, value)
                    elif isinstance(value, int):
                        obs.obs_data_set_int(self.obs_data, key, value)
                    elif isinstance(value, bool):
                        obs.obs_data_set_bool(self.obs_data, key, value)
            
            # Save event actions as JSON
            actions_data = []
            for action in self.settings["event_actions"]:
                if isinstance(action, EventAction):
                    actions_data.append(action.to_dict())
                else:
                    actions_data.append(action)
            
            actions_json = json.dumps(actions_data)
            obs.obs_data_set_string(self.obs_data, "saved_event_actions", actions_json)
            
            logger.info("Saved configuration to OBS data")
            return True
        
        except Exception as e:
            logger.error(f"Error saving configuration to OBS data: {e}")
            return False
    
    def load_from_obs(self) -> bool:
        """Load configuration from OBS data if available"""
        if not self.obs_data:
            logger.warning("No OBS data object available for loading")
            return False
        
        import obspython as obs
        
        try:
            # Load basic settings
            for key in self.DEFAULT_SETTINGS.keys():
                if key != "event_actions":
                    if isinstance(self.DEFAULT_SETTINGS[key], str):
                        self.settings[key] = obs.obs_data_get_string(self.obs_data, key)
                    elif isinstance(self.DEFAULT_SETTINGS[key], int):
                        self.settings[key] = obs.obs_data_get_int(self.obs_data, key)
                    elif isinstance(self.DEFAULT_SETTINGS[key], bool):
                        self.settings[key] = obs.obs_data_get_bool(self.obs_data, key)
            
            # Load event actions from JSON
            actions_json = obs.obs_data_get_string(self.obs_data, "saved_event_actions")
            if actions_json:
                try:
                    actions_data = json.loads(actions_json)
                    self.settings["event_actions"] = [EventAction.from_dict(action) for action in actions_data]
                    logger.info(f"Loaded {len(self.settings['event_actions'])} event actions from OBS data")
                except json.JSONDecodeError:
                    logger.error("Error decoding event actions JSON")
                    self.settings["event_actions"] = []
            else:
                self.settings["event_actions"] = []
            
            logger.info("Loaded configuration from OBS data")
            return True
        
        except Exception as e:
            logger.error(f"Error loading configuration from OBS data: {e}")
            return False
    
    def export_to_file(self, filename: str) -> bool:
        """Export configuration to a JSON file"""
        try:
            # Prepare config for export (convert objects to dicts)
            export_config = self.settings.copy()
            export_config["event_actions"] = [
                action.to_dict() if isinstance(action, EventAction) else action
                for action in export_config["event_actions"]
            ]
            
            with open(filename, 'w') as f:
                json.dump(export_config, f, indent=2)
            
            logger.info(f"Exported configuration to {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting configuration to {filename}: {e}")
            return False
    
    def import_from_file(self, filename: str) -> bool:
        """Import configuration from a JSON file"""
        try:
            with open(filename, 'r') as f:
                import_config = json.load(f)
            
            # Validate the imported config
            for key in self.DEFAULT_SETTINGS.keys():
                if key not in import_config and key != "event_actions":
                    import_config[key] = self.DEFAULT_SETTINGS[key]
            
            # Convert event actions to objects
            if "event_actions" in import_config and isinstance(import_config["event_actions"], list):
                import_config["event_actions"] = [
                    EventAction.from_dict(action) for action in import_config["event_actions"]
                ]
            else:
                import_config["event_actions"] = []
            
            self.settings = import_config
            logger.info(f"Imported configuration from {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error importing configuration from {filename}: {e}")
            return False


# Create a global config instance
config = Config() 