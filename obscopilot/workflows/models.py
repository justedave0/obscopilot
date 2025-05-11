"""
Workflow data models for OBSCopilot.

This module defines the data structures used by the workflow engine.
"""

import json
import logging
import uuid
import re
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Set, Callable, ClassVar

from pydantic import BaseModel, Field, validator, root_validator

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """Types of workflow triggers."""
    
    # Twitch triggers
    TWITCH_CHAT_MESSAGE = "twitch_chat_message"
    TWITCH_FOLLOW = "twitch_follow"
    TWITCH_SUBSCRIPTION = "twitch_subscription"
    TWITCH_BITS = "twitch_bits"
    TWITCH_RAID = "twitch_raid"
    TWITCH_CHANNEL_POINTS_REDEEM = "twitch_channel_points_redeem"
    TWITCH_STREAM_ONLINE = "twitch_stream_online"
    TWITCH_STREAM_OFFLINE = "twitch_stream_offline"
    
    # OBS triggers
    OBS_SCENE_CHANGED = "obs_scene_changed"
    OBS_STREAMING_STARTED = "obs_streaming_started"
    OBS_STREAMING_STOPPED = "obs_streaming_stopped"
    OBS_RECORDING_STARTED = "obs_recording_started"
    OBS_RECORDING_STOPPED = "obs_recording_stopped"
    
    # Time triggers
    SCHEDULE = "schedule"
    INTERVAL = "interval"
    
    # Manual triggers
    MANUAL = "manual"
    HOTKEY = "hotkey"


class ActionType(str, Enum):
    """Types of workflow actions."""
    
    # Twitch actions
    TWITCH_SEND_CHAT_MESSAGE = "twitch_send_chat_message"
    TWITCH_TIMEOUT_USER = "twitch_timeout_user"
    TWITCH_BAN_USER = "twitch_ban_user"
    
    # OBS actions
    OBS_SWITCH_SCENE = "obs_switch_scene"
    OBS_SET_SOURCE_VISIBILITY = "obs_set_source_visibility"
    OBS_START_STREAMING = "obs_start_streaming"
    OBS_STOP_STREAMING = "obs_stop_streaming"
    OBS_START_RECORDING = "obs_start_recording"
    OBS_STOP_RECORDING = "obs_stop_recording"
    
    # Media actions
    PLAY_SOUND = "play_sound"
    SHOW_IMAGE = "show_image"
    
    # AI actions
    AI_GENERATE_RESPONSE = "ai_generate_response"
    
    # Control flow actions
    DELAY = "delay"
    CONDITIONAL = "conditional"
    WEBHOOK = "webhook"
    RUN_PROCESS = "run_process"
    SEND_EMAIL = "send_email"


class ConditionType(str, Enum):
    """Types of conditions for workflow conditionals."""
    
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX_MATCH = "regex_match"
    JAVASCRIPT = "javascript"
    PYTHON = "python"


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerCondition(BaseModel):
    """Condition for filtering trigger events."""
    
    type: ConditionType
    field: str
    value: Any
    
    def evaluate(self, data: Dict[str, Any]) -> bool:
        """Evaluate the condition against the provided data.
        
        Args:
            data: Event data to evaluate against
            
        Returns:
            True if condition matches, False otherwise
        """
        # Extract the field value from the data
        field_parts = self.field.split('.')
        current = data
        for part in field_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False  # Field doesn't exist
        
        field_value = current
        
        # Evaluate the condition
        if self.type == ConditionType.EQUALS:
            return field_value == self.value
        elif self.type == ConditionType.NOT_EQUALS:
            return field_value != self.value
        elif self.type == ConditionType.CONTAINS:
            return self.value in field_value if isinstance(field_value, (str, list, dict)) else False
        elif self.type == ConditionType.NOT_CONTAINS:
            return self.value not in field_value if isinstance(field_value, (str, list, dict)) else True
        elif self.type == ConditionType.STARTS_WITH:
            return field_value.startswith(self.value) if isinstance(field_value, str) else False
        elif self.type == ConditionType.ENDS_WITH:
            return field_value.endswith(self.value) if isinstance(field_value, str) else False
        elif self.type == ConditionType.GREATER_THAN:
            return field_value > self.value if isinstance(field_value, (int, float)) else False
        elif self.type == ConditionType.LESS_THAN:
            return field_value < self.value if isinstance(field_value, (int, float)) else False
        elif self.type == ConditionType.REGEX_MATCH:
            import re
            return bool(re.match(self.value, str(field_value)))
        elif self.type == ConditionType.JAVASCRIPT:
            # Not implemented for security reasons
            logger.warning("JavaScript condition evaluation not implemented")
            return False
        elif self.type == ConditionType.PYTHON:
            # Not implemented for security reasons
            logger.warning("Python condition evaluation not implemented")
            return False
        else:
            return False


class WorkflowTrigger(BaseModel):
    """Trigger for a workflow."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    type: TriggerType
    conditions: List[TriggerCondition] = []
    config: Dict[str, Any] = {}
    
    def matches_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if this trigger matches an event.
        
        Args:
            event_type: Type of the event
            event_data: Event data payload
            
        Returns:
            True if trigger matches the event, False otherwise
        """
        # Check if event type matches trigger type
        if event_type != self.type:
            return False
        
        # If no conditions, always match
        if not self.conditions:
            return True
        
        # Check all conditions
        for condition in self.conditions:
            if not condition.evaluate(event_data):
                return False
        
        return True


class VariableDefinition(BaseModel):
    """Definition of a workflow variable."""
    
    name: str
    description: str = ""
    type: str  # string, number, boolean, object, array
    default_value: Optional[Any] = None
    required: bool = False


class WorkflowAction(BaseModel):
    """Action in a workflow."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    type: ActionType
    config: Dict[str, Any] = {}
    enabled: bool = True
    timeout: Optional[int] = None  # Timeout in seconds
    retry: Dict[str, Any] = Field(default_factory=lambda: {
        "max_attempts": 1,
        "delay": 0,  # Seconds between retries
        "backoff": 1.0  # Multiplicative backoff factor
    })
    
    @validator('config')
    def validate_config(cls, config, values):
        """Validate action configuration based on action type."""
        action_type = values.get('type')
        
        # Validate based on action type
        if action_type == ActionType.TWITCH_SEND_CHAT_MESSAGE:
            if 'message' not in config:
                raise ValueError("Twitch chat message action requires 'message' config")
        elif action_type == ActionType.OBS_SWITCH_SCENE:
            if 'scene_name' not in config:
                raise ValueError("OBS switch scene action requires 'scene_name' config")
        # Add validation for other action types as needed
        
        return config


class ConditionGroup(BaseModel):
    """Group of conditions with logical operator."""
    
    operator: str = "and"  # "and" or "or"
    conditions: List[TriggerCondition] = []
    groups: List["ConditionGroup"] = []
    
    def evaluate(self, data: Dict[str, Any]) -> bool:
        """Evaluate the condition group against the provided data.
        
        Args:
            data: Data to evaluate against
            
        Returns:
            True if conditions match, False otherwise
        """
        # Evaluate all conditions in this group
        condition_results = [condition.evaluate(data) for condition in self.conditions]
        
        # Evaluate all nested groups
        for group in self.groups:
            condition_results.append(group.evaluate(data))
        
        # Apply the logical operator
        if self.operator == "and":
            return all(condition_results) if condition_results else True
        elif self.operator == "or":
            return any(condition_results) if condition_results else False
        else:
            logger.warning(f"Unknown operator: {self.operator}")
            return False


ConditionGroup.update_forward_refs()


class WorkflowNode(BaseModel):
    """Node in a workflow graph."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: WorkflowAction
    next_nodes: List[str] = []  # IDs of next nodes
    metadata: Dict[str, Any] = {}
    error_handler: Optional[str] = None  # ID of error handler node
    condition: Optional[ConditionGroup] = None  # Condition for conditional nodes


class WorkflowContext(BaseModel):
    """Context for a workflow execution."""
    
    workflow_id: str
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    execution_path: List[str] = Field(default_factory=list)  # Node IDs in execution order
    current_node_id: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.READY
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a context variable.
        
        Args:
            name: Variable name
            value: Variable value
        """
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a context variable.
        
        Args:
            name: Variable name
            default: Default value if variable not found
            
        Returns:
            Variable value or default if not found
        """
        return self.variables.get(name, default)
    
    def resolve_template(self, template: str) -> str:
        """Resolve a template string with context variables.
        
        Args:
            template: Template string with {variable} or {{variable}} placeholders
            
        Returns:
            Resolved string
        """
        if not template or not isinstance(template, str):
            return template
            
        # First, escape any double curly braces to handle them differently
        escaped = re.sub(r'{{(.*?)}}', lambda m: f"__DOUBLE_CURLY__{m.group(1)}__", template)
        
        # Process regular variable placeholders
        try:
            # Try to format with context variables
            all_variables = {**self.variables}
            
            # Add trigger data with flat structure for easier access
            if isinstance(self.trigger_data, dict):
                # Add trigger_data as a variable
                all_variables['trigger_data'] = self.trigger_data
                
                # Also flatten top-level trigger data for direct access
                for key, value in self.trigger_data.items():
                    if key not in all_variables:  # Don't overwrite existing variables
                        all_variables[key] = value
            
            # Perform the replacement
            resolved = escaped.format(**all_variables)
            
            # Now restore any double curly brace expressions
            resolved = re.sub(r'__DOUBLE_CURLY__(.*?)__', lambda m: "{" + m.group(1) + "}", resolved)
            
            return resolved
        except KeyError as e:
            logger.warning(f"Variable not found in template: {e}")
            return template
        except Exception as e:
            logger.error(f"Error resolving template: {e}")
            return template
    
    def add_to_execution_path(self, node_id: str) -> None:
        """Add a node to the execution path.
        
        Args:
            node_id: ID of the node
        """
        self.execution_path.append(node_id)
        self.current_node_id = node_id
    
    def get_execution_time(self) -> float:
        """Get the workflow execution time in seconds.
        
        Returns:
            Execution time in seconds
        """
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all data available in the context.
        
        Returns:
            Dictionary with all context data
        """
        return {
            "variables": self.variables,
            "trigger_data": self.trigger_data,
            "workflow_id": self.workflow_id,
            "execution_path": self.execution_path,
            "current_node_id": self.current_node_id,
            "status": self.status,
            "execution_time": self.get_execution_time()
        }


class Workflow(BaseModel):
    """Workflow definition."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True
    triggers: List[WorkflowTrigger] = []
    nodes: Dict[str, WorkflowNode] = {}
    entry_node_id: Optional[str] = None
    variables: List[VariableDefinition] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        """Convert workflow to JSON string.
        
        Returns:
            JSON string representation of the workflow
        """
        return self.json(exclude_unset=True, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Workflow":
        """Create a workflow from JSON string.
        
        Args:
            json_str: JSON string representation of a workflow
            
        Returns:
            Workflow instance
        """
        try:
            data = json.loads(json_str)
            return cls(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding workflow JSON: {e}")
            raise ValueError(f"Invalid workflow JSON: {e}")
        except Exception as e:
            logger.error(f"Error creating workflow from JSON: {e}")
            raise ValueError(f"Error creating workflow: {e}")
    
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID.
        
        Args:
            node_id: ID of the node to get
            
        Returns:
            Node instance or None if not found
        """
        return self.nodes.get(node_id)
    
    def get_entry_node(self) -> Optional[WorkflowNode]:
        """Get the entry node.
        
        Returns:
            Entry node instance or None if not set
        """
        if not self.entry_node_id:
            return None
        
        return self.get_node(self.entry_node_id)
    
    def add_node(self, action: WorkflowAction, next_nodes: List[str] = []) -> str:
        """Add a node to the workflow.
        
        Args:
            action: Action to add
            next_nodes: IDs of next nodes
            
        Returns:
            ID of the added node
        """
        node_id = str(uuid.uuid4())
        node = WorkflowNode(
            id=node_id,
            action=action,
            next_nodes=next_nodes
        )
        
        # Add node to workflow
        self.nodes[node_id] = node
        
        # If no entry node is set, use this one
        if not self.entry_node_id:
            self.entry_node_id = node_id
        
        # Update workflow
        self.updated_at = datetime.now()
        
        return node_id
    
    def add_trigger(self, trigger_type: TriggerType, name: str, config: Dict[str, Any] = {}) -> str:
        """Add a trigger to the workflow.
        
        Args:
            trigger_type: Type of trigger
            name: Name of the trigger
            config: Trigger configuration
            
        Returns:
            ID of the added trigger
        """
        trigger = WorkflowTrigger(
            id=str(uuid.uuid4()),
            name=name,
            type=trigger_type,
            config=config
        )
        
        # Add trigger to workflow
        self.triggers.append(trigger)
        
        # Update workflow
        self.updated_at = datetime.now()
        
        return trigger.id
    
    def connect_nodes(self, source_id: str, target_id: str) -> bool:
        """Connect two nodes.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            
        Returns:
            True if connection was made, False if nodes not found
        """
        # Get source node
        source_node = self.get_node(source_id)
        if not source_node:
            return False
        
        # Get target node
        target_node = self.get_node(target_id)
        if not target_node:
            return False
        
        # Add target to source's next_nodes if not already there
        if target_id not in source_node.next_nodes:
            source_node.next_nodes.append(target_id)
        
        # Update workflow
        self.updated_at = datetime.now()
        
        return True
    
    def create_context(self, trigger_data: Dict[str, Any]) -> WorkflowContext:
        """Create a new execution context for this workflow.
        
        Args:
            trigger_data: Data from the trigger event
            
        Returns:
            New workflow context
        """
        # Initialize variables with defaults
        variables = {}
        for var_def in self.variables:
            if var_def.default_value is not None:
                variables[var_def.name] = var_def.default_value
        
        # Create context
        context = WorkflowContext(
            workflow_id=self.id,
            trigger_data=trigger_data,
            variables=variables
        )
        
        return context
    
    def validate(self) -> List[str]:
        """Validate the workflow.
        
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check if entry node exists
        if not self.entry_node_id:
            errors.append("No entry node defined")
        elif self.entry_node_id not in self.nodes:
            errors.append(f"Entry node {self.entry_node_id} not found")
        
        # Check for required variables
        required_vars = [var.name for var in self.variables if var.required]
        
        # Check nodes
        reachable_nodes = set()
        if self.entry_node_id:
            self._mark_reachable_nodes(self.entry_node_id, reachable_nodes)
        
        # Find unreachable nodes
        unreachable = set(self.nodes.keys()) - reachable_nodes
        if unreachable:
            errors.append(f"Unreachable nodes: {', '.join(unreachable)}")
        
        # Check for cycles
        cycles = self._find_cycles()
        if cycles:
            cycle_paths = [' -> '.join(cycle) for cycle in cycles]
            errors.append(f"Workflow contains cycles: {'; '.join(cycle_paths)}")
        
        return errors
    
    def _mark_reachable_nodes(self, node_id: str, reachable: Set[str], visited: Set[str] = None) -> None:
        """Mark all nodes reachable from the given node.
        
        Args:
            node_id: ID of the node to start from
            reachable: Set to collect reachable node IDs
            visited: Set of already visited nodes (for cycle detection)
        """
        if visited is None:
            visited = set()
        
        # Mark as visited and reachable
        visited.add(node_id)
        reachable.add(node_id)
        
        # Get the node
        node = self.get_node(node_id)
        if not node:
            return
        
        # Visit all next nodes
        for next_id in node.next_nodes:
            if next_id not in visited:
                self._mark_reachable_nodes(next_id, reachable, visited)
    
    def _find_cycles(self) -> List[List[str]]:
        """Find cycles in the workflow graph.
        
        Returns:
            List of cycles, each cycle is a list of node IDs
        """
        cycles = []
        visited = set()
        path = []
        path_set = set()
        
        def dfs(node_id: str) -> None:
            nonlocal cycles, visited, path, path_set
            
            # Mark current node as visited
            visited.add(node_id)
            path.append(node_id)
            path_set.add(node_id)
            
            # Get node
            node = self.get_node(node_id)
            if node:
                # Visit all next nodes
                for next_id in node.next_nodes:
                    if next_id not in visited:
                        dfs(next_id)
                    elif next_id in path_set:
                        # Found a cycle
                        cycle_start = path.index(next_id)
                        cycles.append(path[cycle_start:] + [next_id])
            
            # Backtrack
            path_set.remove(node_id)
            path.pop()
        
        # Start DFS from entry node if defined
        if self.entry_node_id:
            dfs(self.entry_node_id)
        
        # Check any remaining nodes (might be unreachable)
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)
        
        return cycles


# Custom serialization helpers
def workflow_to_dict(workflow: Workflow) -> Dict[str, Any]:
    """Convert a workflow to a dictionary suitable for database storage.
    
    Args:
        workflow: Workflow to convert
        
    Returns:
        Dictionary representation
    """
    return json.loads(workflow.json(exclude_unset=True))


def workflow_from_dict(data: Dict[str, Any]) -> Workflow:
    """Create a workflow from a dictionary.
    
    Args:
        data: Dictionary representation of a workflow
        
    Returns:
        Workflow instance
    """
    return Workflow(**data) 