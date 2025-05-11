"""
Manual triggers for OBSCopilot workflow engine.

This module implements manually-activated workflow triggers.
"""

import logging
from typing import Any, Dict, List, Optional

from obscopilot.workflows.models import TriggerType, WorkflowTrigger
from obscopilot.workflows.triggers.base import BaseTrigger, EventEmitterMixin

logger = logging.getLogger(__name__)


class BaseManualTrigger(BaseTrigger):
    """Base class for manual triggers."""
    pass


class ManualTrigger(BaseManualTrigger, EventEmitterMixin):
    """Trigger that can be manually activated by the user."""
    
    trigger_type = TriggerType.MANUAL
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches manual event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches manual event, False otherwise
        """
        # Check for ID-based matching
        if "id" in config and "trigger_id" in event_data:
            return config["id"] == event_data["trigger_id"]
        
        return True  # No specific matching, will match any manual trigger event
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "id": {
                "type": "string",
                "description": "Optional identifier for this manual trigger",
                "required": False
            },
            "display_name": {
                "type": "string",
                "description": "Display name for the trigger in the UI",
                "required": False
            },
            "description": {
                "type": "string",
                "description": "Description of what the trigger does",
                "required": False
            },
            "group": {
                "type": "string",
                "description": "Grouping for the trigger in the UI",
                "required": False
            }
        }


class HotkeyTrigger(BaseManualTrigger):
    """Trigger activated by a keyboard hotkey."""
    
    trigger_type = TriggerType.HOTKEY
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate the trigger configuration.
        
        Args:
            config: Trigger configuration
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for key
        if "key" not in config:
            errors.append("Hotkey trigger requires 'key' config")
        
        return errors
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches hotkey event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches hotkey event, False otherwise
        """
        # Check key
        if "key" in config and "key" in event_data:
            config_key = config["key"].lower()
            event_key = event_data["key"].lower()
            
            if config_key != event_key:
                return False
            
            # Check modifiers
            config_modifiers = config.get("modifiers", [])
            event_modifiers = event_data.get("modifiers", [])
            
            # If config specifies modifiers, check them
            if config_modifiers:
                # Convert to lowercase for case-insensitive comparison
                config_modifiers = [m.lower() for m in config_modifiers]
                event_modifiers = [m.lower() for m in event_modifiers]
                
                # Check if all required modifiers are present
                for modifier in config_modifiers:
                    if modifier not in event_modifiers:
                        return False
                
                # Check if no extra modifiers are present when strict matching is enabled
                if config.get("strict_modifiers", False):
                    for modifier in event_modifiers:
                        if modifier not in config_modifiers:
                            return False
            
            return True
        
        return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "key": {
                "type": "string",
                "description": "Key code (e.g., 'A', 'F1', 'Space')",
                "required": True
            },
            "modifiers": {
                "type": "array",
                "description": "Modifier keys (e.g., ['Ctrl', 'Shift'])",
                "required": False,
                "items": {
                    "type": "string"
                }
            },
            "strict_modifiers": {
                "type": "boolean",
                "description": "If true, no additional modifiers are allowed",
                "required": False,
                "default": False
            },
            "display_name": {
                "type": "string",
                "description": "Display name for the hotkey in the UI",
                "required": False
            }
        } 