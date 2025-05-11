"""
Base action classes for OBSCopilot workflow engine.

This module contains the base classes for all workflow actions.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable

from obscopilot.workflows.models import ActionType, WorkflowAction, WorkflowContext

logger = logging.getLogger(__name__)


class BaseAction(ABC):
    """Base class for all workflow actions."""
    
    action_type: ActionType = None
    
    @classmethod
    @abstractmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> Any:
        """Execute the action.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            **kwargs: Additional dependencies needed by the action
            
        Returns:
            Action result
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate the action configuration.
        
        Args:
            config: Action configuration
            
        Returns:
            List of validation errors, empty if valid
        """
        return []  # No validation by default
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration by default


class TemplateableMixin:
    """Mixin for actions that use templates."""
    
    @staticmethod
    def resolve_template(template: str, context: WorkflowContext) -> str:
        """Resolve a template string with context variables.
        
        Args:
            template: Template string with {variable} placeholders
            context: Workflow context with variables
            
        Returns:
            Resolved string
        """
        if not template:
            return template
            
        return context.resolve_template(template)


class RetryableMixin:
    """Mixin for actions that can be retried."""
    
    @staticmethod
    async def execute_with_retry(
        func: Callable,
        action: WorkflowAction,
        *args,
        **kwargs
    ) -> Any:
        """Execute a function with retry logic.
        
        Args:
            func: Function to execute
            action: Action configuration with retry settings
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function
        """
        retry_config = action.retry
        max_attempts = retry_config.get("max_attempts", 1)
        delay = retry_config.get("delay", 0)
        backoff = retry_config.get("backoff", 1.0)
        
        attempt = 0
        last_error = None
        
        while attempt < max_attempts:
            attempt += 1
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Action {action.name} failed (attempt {attempt}/{max_attempts}): {e}")
                last_error = e
                
                if attempt < max_attempts:
                    # Calculate delay for next attempt
                    current_delay = delay * (backoff ** (attempt - 1))
                    logger.debug(f"Retrying in {current_delay} seconds")
                    await asyncio.sleep(current_delay)
        
        # If we get here, all attempts failed
        logger.error(f"Action {action.name} failed after {max_attempts} attempts. Last error: {last_error}")
        raise last_error


class ConditionalMixin:
    """Mixin for actions with conditional execution."""
    
    @staticmethod
    def evaluate_condition(condition: Dict[str, Any], context: WorkflowContext) -> bool:
        """Evaluate a condition against workflow context.
        
        Args:
            condition: Condition to evaluate
            context: Workflow context
            
        Returns:
            True if condition is met, False otherwise
        """
        if not condition:
            return True  # No condition means always execute
            
        condition_type = condition.get("type", "equals")
        left = condition.get("left", "")
        right = condition.get("right", "")
        
        # Resolve templates in left and right
        if isinstance(left, str):
            left = context.resolve_template(left)
        if isinstance(right, str):
            right = context.resolve_template(right)
        
        # Convert types if needed
        if condition.get("convert_to_number", False):
            try:
                left = float(left)
                right = float(right)
            except (ValueError, TypeError):
                pass
        
        # Evaluate condition
        if condition_type == "equals":
            return left == right
        elif condition_type == "not_equals":
            return left != right
        elif condition_type == "contains":
            return right in left if isinstance(left, (str, list, dict)) else False
        elif condition_type == "not_contains":
            return right not in left if isinstance(left, (str, list, dict)) else True
        elif condition_type == "greater_than":
            return left > right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False
        elif condition_type == "less_than":
            return left < right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False
        elif condition_type == "regex_match":
            import re
            return bool(re.match(right, str(left))) if isinstance(right, str) and left is not None else False
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return False 