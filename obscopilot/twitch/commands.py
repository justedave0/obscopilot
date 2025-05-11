"""
Custom chat commands for OBSCopilot.

This module provides functionality for custom chat commands that can be triggered from Twitch chat.
"""

import re
import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any, Set, Tuple, Union, Pattern

from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.workflows.models import WorkflowAction, WorkflowTrigger, TriggerType, TriggerCondition, ConditionType

logger = logging.getLogger(__name__)


class ChatCommand:
    """Represents a custom chat command."""
    
    def __init__(
        self,
        name: str,
        handler: Optional[Callable] = None,
        description: str = "",
        aliases: List[str] = None,
        cooldown: int = 0,
        user_cooldown: int = 0,
        permissions: Set[str] = None,
        enabled: bool = True
    ):
        """Initialize a chat command.
        
        Args:
            name: Command name (without prefix)
            handler: Function to call when command is triggered
            description: Command description
            aliases: Alternative names for the command
            cooldown: Global cooldown in seconds
            user_cooldown: Per-user cooldown in seconds
            permissions: Required permissions (mod, vip, sub, broadcaster)
            enabled: Whether the command is enabled
        """
        self.name = name.lower()
        self.handler = handler
        self.description = description
        self.aliases = [alias.lower() for alias in (aliases or [])]
        self.cooldown = cooldown
        self.user_cooldown = user_cooldown
        self.permissions = permissions or set()
        self.enabled = enabled
        self.last_used = 0  # Timestamp of last use
        self.user_last_used: Dict[str, float] = {}  # User ID -> timestamp
    
    def matches(self, command_name: str) -> bool:
        """Check if the command matches a given name.
        
        Args:
            command_name: Command name to check
            
        Returns:
            True if the command name matches, False otherwise
        """
        command_name = command_name.lower()
        return command_name == self.name or command_name in self.aliases
    
    def check_cooldown(self, user_id: str, current_time: float) -> Tuple[bool, float]:
        """Check if the command is on cooldown.
        
        Args:
            user_id: ID of the user triggering the command
            current_time: Current timestamp
            
        Returns:
            Tuple of (on_cooldown, remaining_time)
        """
        # Check global cooldown
        global_remaining = 0
        if self.cooldown > 0:
            elapsed = current_time - self.last_used
            if elapsed < self.cooldown:
                global_remaining = self.cooldown - elapsed
        
        # Check user cooldown
        user_remaining = 0
        if self.user_cooldown > 0 and user_id in self.user_last_used:
            elapsed = current_time - self.user_last_used.get(user_id, 0)
            if elapsed < self.user_cooldown:
                user_remaining = self.user_cooldown - elapsed
        
        # Return the longer cooldown
        remaining = max(global_remaining, user_remaining)
        return remaining > 0, remaining
    
    def update_cooldown(self, user_id: str, current_time: float) -> None:
        """Update command cooldown timestamps.
        
        Args:
            user_id: ID of the user who triggered the command
            current_time: Current timestamp
        """
        self.last_used = current_time
        if self.user_cooldown > 0:
            self.user_last_used[user_id] = current_time
    
    def check_permissions(self, user_data: Dict[str, Any]) -> bool:
        """Check if a user has permission to use this command.
        
        Args:
            user_data: User data including permissions
            
        Returns:
            True if user has permission, False otherwise
        """
        # If no permissions required, anyone can use
        if not self.permissions:
            return True
        
        # Get user permissions
        user_permissions = set()
        if user_data.get("is_broadcaster", False):
            user_permissions.add("broadcaster")
        if user_data.get("is_mod", False):
            user_permissions.add("mod")
        if user_data.get("is_vip", False):
            user_permissions.add("vip")
        if user_data.get("is_subscriber", False):
            user_permissions.add("sub")
        
        # Check if user has any of the required permissions
        return bool(user_permissions.intersection(self.permissions))


class CommandRegistry:
    """Registry for chat commands."""
    
    def __init__(self, prefix: str = "!"):
        """Initialize command registry.
        
        Args:
            prefix: Command prefix
        """
        self.prefix = prefix
        self.commands: Dict[str, ChatCommand] = {}
        self.command_pattern: Pattern = self._build_command_pattern()
    
    def _build_command_pattern(self) -> Pattern:
        """Build a regex pattern for command parsing.
        
        Returns:
            Compiled regex pattern
        """
        # Escape prefix for regex
        escaped_prefix = re.escape(self.prefix)
        
        # Pattern: prefix + command + optional space + optional args
        return re.compile(f"^{escaped_prefix}([A-Za-z0-9_]+)(?:\\s+(.*))?$")
    
    def set_prefix(self, prefix: str) -> None:
        """Set the command prefix.
        
        Args:
            prefix: New command prefix
        """
        self.prefix = prefix
        self.command_pattern = self._build_command_pattern()
        logger.info(f"Command prefix set to: {prefix}")
    
    def register_command(self, command: ChatCommand) -> bool:
        """Register a chat command.
        
        Args:
            command: Command to register
            
        Returns:
            True if command was registered, False if already exists
        """
        # Check if command already exists
        if command.name in self.commands:
            logger.warning(f"Command already exists: {command.name}")
            return False
        
        # Check if any aliases conflict with existing commands
        for alias in command.aliases:
            if alias in self.commands:
                logger.warning(f"Command alias conflicts with existing command: {alias}")
                return False
        
        # Register command
        self.commands[command.name] = command
        logger.info(f"Registered command: {command.name}")
        
        # Register aliases
        for alias in command.aliases:
            self.commands[alias] = command
            logger.debug(f"Registered command alias: {alias} -> {command.name}")
        
        return True
    
    def unregister_command(self, command_name: str) -> bool:
        """Unregister a chat command.
        
        Args:
            command_name: Name of the command to unregister
            
        Returns:
            True if command was unregistered, False if not found
        """
        command_name = command_name.lower()
        
        if command_name not in self.commands:
            logger.warning(f"Command not found: {command_name}")
            return False
        
        # Get command
        command = self.commands[command_name]
        
        # Remove command and aliases
        del self.commands[command.name]
        for alias in command.aliases:
            if alias in self.commands:
                del self.commands[alias]
        
        logger.info(f"Unregistered command: {command_name}")
        return True
    
    def get_command(self, command_name: str) -> Optional[ChatCommand]:
        """Get a command by name.
        
        Args:
            command_name: Name of the command
            
        Returns:
            Command instance or None if not found
        """
        return self.commands.get(command_name.lower())
    
    def parse_command(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse a chat message to extract command and arguments.
        
        Args:
            message: Chat message to parse
            
        Returns:
            Tuple of (command_name, args) or (None, None) if not a command
        """
        match = self.command_pattern.match(message)
        if not match:
            return None, None
        
        command_name = match.group(1).lower()
        args = match.group(2) or ""
        
        return command_name, args
    
    def handle_message(self, message: str, user_data: Dict[str, Any], current_time: float) -> Optional[ChatCommand]:
        """Handle a chat message and execute command if found.
        
        Args:
            message: Chat message
            user_data: Data about the user who sent the message
            current_time: Current timestamp
            
        Returns:
            Executed command or None if no command was executed
        """
        # Parse command
        command_name, args = self.parse_command(message)
        if not command_name:
            return None
        
        # Find command
        command = self.get_command(command_name)
        if not command or not command.enabled:
            return None
        
        # Check permissions
        if not command.check_permissions(user_data):
            logger.debug(f"User {user_data.get('username')} lacks permission for command: {command_name}")
            return None
        
        # Check cooldown
        on_cooldown, remaining = command.check_cooldown(user_data.get("user_id", ""), current_time)
        if on_cooldown:
            logger.debug(f"Command {command_name} on cooldown for {remaining:.1f}s")
            return None
        
        # Update cooldown
        command.update_cooldown(user_data.get("user_id", ""), current_time)
        
        # Execute command handler if available
        if command.handler:
            try:
                asyncio.create_task(command.handler(args, user_data))
                logger.debug(f"Executed command: {command_name} with args: {args}")
            except Exception as e:
                logger.error(f"Error executing command {command_name}: {e}")
        
        return command


# Create global command registry
command_registry = CommandRegistry()


def register_command(
    name: str,
    handler: Optional[Callable] = None,
    description: str = "",
    aliases: List[str] = None,
    cooldown: int = 0,
    user_cooldown: int = 0,
    permissions: Set[str] = None,
    enabled: bool = True
) -> bool:
    """Register a new chat command.
    
    Args:
        name: Command name (without prefix)
        handler: Function to call when command is triggered
        description: Command description
        aliases: Alternative names for the command
        cooldown: Global cooldown in seconds
        user_cooldown: Per-user cooldown in seconds
        permissions: Required permissions (mod, vip, sub, broadcaster)
        enabled: Whether the command is enabled
        
    Returns:
        True if command was registered, False if already exists
    """
    command = ChatCommand(
        name=name,
        handler=handler,
        description=description,
        aliases=aliases,
        cooldown=cooldown,
        user_cooldown=user_cooldown,
        permissions=permissions,
        enabled=enabled
    )
    
    return command_registry.register_command(command)


def unregister_command(command_name: str) -> bool:
    """Unregister a chat command.
    
    Args:
        command_name: Name of the command to unregister
        
    Returns:
        True if command was unregistered, False if not found
    """
    return command_registry.unregister_command(command_name)


def get_command(command_name: str) -> Optional[ChatCommand]:
    """Get a command by name.
    
    Args:
        command_name: Name of the command
        
    Returns:
        Command instance or None if not found
    """
    return command_registry.get_command(command_name)


def create_workflow_trigger_for_command(
    command_name: str,
    name: str = None,
    description: str = "",
    exact_match: bool = True
) -> WorkflowTrigger:
    """Create a workflow trigger for a specific chat command.
    
    Args:
        command_name: Name of the command (without prefix)
        name: Name for the trigger (defaults to "Command: {command_name}")
        description: Description for the trigger
        exact_match: Whether to match the command name exactly
        
    Returns:
        WorkflowTrigger instance
    """
    if not name:
        name = f"Command: {command_name}"
    
    # Create conditions
    conditions = []
    
    # Match on message content
    prefix = command_registry.prefix
    if exact_match:
        pattern = f"^\\{prefix}{command_name}(\\s.*)?$"
        conditions.append(TriggerCondition(
            type=ConditionType.REGEX_MATCH,
            field="message",
            value=pattern
        ))
    else:
        # Match command with any args
        conditions.append(TriggerCondition(
            type=ConditionType.STARTS_WITH,
            field="message",
            value=f"{prefix}{command_name}"
        ))
    
    # Create trigger
    trigger = WorkflowTrigger(
        name=name,
        description=description,
        type=TriggerType.TWITCH_CHAT_MESSAGE,
        conditions=conditions,
        config={
            "command_name": command_name
        }
    )
    
    return trigger 