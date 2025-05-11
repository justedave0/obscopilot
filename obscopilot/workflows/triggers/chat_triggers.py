"""
Chat command triggers for OBSCopilot workflow engine.

This module defines triggers for chat commands.
"""

import logging
import re
from typing import Dict, Any, Pattern, Optional

from obscopilot.workflows.models import TriggerType, WorkflowTrigger
from obscopilot.workflows.triggers.base import BaseTrigger
from obscopilot.twitch.commands import command_registry

logger = logging.getLogger(__name__)


class ChatCommandTrigger(BaseTrigger):
    """Trigger for chat commands."""
    
    trigger_type = TriggerType.CHAT_COMMAND
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare the trigger for use.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Get command pattern
        command_name = config.get("command_name", "")
        if not command_name:
            logger.warning(f"ChatCommandTrigger missing command_name: {trigger.id}")
            return
        
        # Compile regex pattern for argument parsing if provided
        arg_pattern_str = config.get("arg_pattern")
        if arg_pattern_str:
            try:
                arg_pattern = re.compile(arg_pattern_str)
                config["_compiled_arg_pattern"] = arg_pattern
            except re.error as e:
                logger.error(f"Invalid argument pattern for command trigger: {e}")
    
    @classmethod
    def matches_event(cls, trigger: WorkflowTrigger, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if the trigger matches an event.
        
        Args:
            trigger: Trigger to check
            event_type: Type of the event
            event_data: Event data
            
        Returns:
            True if trigger matches the event, False otherwise
        """
        # First check if this is a Twitch chat message event
        if event_type != TriggerType.TWITCH_CHAT_MESSAGE:
            return False
        
        # Then check if it's a command
        if not event_data.get("is_command", False):
            return False
        
        # Get command name from event
        command_name = event_data.get("command")
        if not command_name:
            return False
        
        # Get expected command name from trigger config
        expected_command = trigger.config.get("command_name", "").lower()
        if not expected_command:
            return False
        
        # Check if command names match
        if command_name.lower() != expected_command:
            return False
        
        # Check if arguments match the pattern (if provided)
        arg_pattern = trigger.config.get("_compiled_arg_pattern")
        if arg_pattern:
            args = event_data.get("command_args", "")
            if not args or not arg_pattern.match(args):
                return False
        
        # Check permission requirements
        required_permission = trigger.config.get("required_permission")
        if required_permission:
            # Check for specific permission
            has_permission = False
            if required_permission == "broadcaster" and event_data.get("is_broadcaster", False):
                has_permission = True
            elif required_permission == "mod" and (event_data.get("is_mod", False) or event_data.get("is_broadcaster", False)):
                has_permission = True
            elif required_permission == "vip" and (event_data.get("is_vip", False) or event_data.get("is_mod", False) or event_data.get("is_broadcaster", False)):
                has_permission = True
            elif required_permission == "sub" and (event_data.get("is_sub", False) or event_data.get("is_mod", False) or event_data.get("is_broadcaster", False)):
                has_permission = True
            
            if not has_permission:
                return False
        
        # If we get here, the trigger matches
        return True
    
    @classmethod
    def extract_args(cls, trigger: WorkflowTrigger, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract arguments from the event data.
        
        Args:
            trigger: The trigger
            event_data: Event data
            
        Returns:
            Dictionary of extracted arguments
        """
        args = {}
        
        # Add basic command info
        args["command"] = event_data.get("command", "")
        args["args"] = event_data.get("command_args", "")
        
        # Extract named args if arg pattern is present
        arg_pattern = trigger.config.get("_compiled_arg_pattern")
        if arg_pattern and args["args"]:
            match = arg_pattern.match(args["args"])
            if match and match.groupdict():
                # Add named groups to args
                args.update(match.groupdict())
        
        return args 