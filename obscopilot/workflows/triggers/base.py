"""
Base trigger classes for OBSCopilot workflow engine.

This module contains the base classes for all workflow triggers.
"""

import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Pattern, Type, TypeVar, Union, Set, Callable

from obscopilot.workflows.models import TriggerType, TriggerCondition, WorkflowTrigger

logger = logging.getLogger(__name__)


class BaseTrigger(ABC):
    """Base class for all workflow triggers."""
    
    trigger_type: TriggerType = None
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate the trigger configuration.
        
        Args:
            config: Trigger configuration
            
        Returns:
            List of validation errors, empty if valid
        """
        return []  # No validation by default
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        This is called when a trigger is registered with the workflow engine.
        Subclasses can use this to compile regex patterns, create cached data, etc.
        
        Args:
            trigger: Trigger to prepare
        """
        pass
    
    @classmethod
    def matches_event(cls, trigger: WorkflowTrigger, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if this trigger matches an event.
        
        Args:
            trigger: Trigger configuration
            event_type: Type of the event
            event_data: Event data payload
            
        Returns:
            True if trigger matches the event, False otherwise
        """
        # Basic type check
        if event_type != trigger.type:
            return False
        
        # If no conditions, always match for same type
        if not trigger.conditions:
            return cls._matches_config(trigger.config, event_data)
        
        # Check all conditions
        for condition in trigger.conditions:
            if not condition.evaluate(event_data):
                return False
        
        # Check trigger config specific matching
        return cls._matches_config(trigger.config, event_data)
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches event data.
        
        Subclasses should override this method to implement
        trigger-specific matching logic based on the config.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches event data, False otherwise
        """
        return True  # Match by default if no special config
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration by default


class RegexPatternMixin:
    """Mixin for triggers that use regex patterns."""
    
    @staticmethod
    def compile_pattern(pattern: Optional[str]) -> Optional[Pattern]:
        """Compile a regex pattern if provided.
        
        Args:
            pattern: Pattern to compile
            
        Returns:
            Compiled pattern or None
        """
        if not pattern:
            return None
        
        try:
            return re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            return None
    
    @staticmethod
    def matches_pattern(pattern: Optional[Pattern], text: str) -> bool:
        """Check if text matches pattern.
        
        Args:
            pattern: Compiled pattern
            text: Text to match
            
        Returns:
            True if matches, False otherwise
        """
        if not pattern:
            return True  # No pattern means always match
            
        return bool(pattern.search(text))


class ScheduleableTriggerMixin:
    """Mixin for triggers that can be scheduled."""
    
    @staticmethod
    def parse_cron_expression(cron_expr: str) -> Union[Dict[str, Any], None]:
        """Parse a cron expression into a dict of scheduled times.
        
        Args:
            cron_expr: Cron expression (e.g., "0 9 * * 1-5")
            
        Returns:
            Dict with schedule info or None if invalid
        """
        try:
            from croniter import croniter
            
            if not croniter.is_valid(cron_expr):
                logger.warning(f"Invalid cron expression: {cron_expr}")
                return None
                
            return {"cron": cron_expr}
        except ImportError:
            logger.warning("croniter package not installed, cron scheduling not available")
            return None
        except Exception as e:
            logger.warning(f"Error parsing cron expression '{cron_expr}': {e}")
            return None


class EventEmitterMixin:
    """Mixin for triggers that can emit events."""
    
    @staticmethod
    async def emit_event(event_bus, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event on the event bus.
        
        Args:
            event_bus: Event bus to use
            event_type: Type of event to emit
            data: Event data
        """
        from obscopilot.core.events import Event
        
        await event_bus.emit(Event(event_type, data)) 