"""
Workflow data models for OBSCopilot.

This module defines the data structures used by the workflow engine.
"""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, Field

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


class WorkflowAction(BaseModel):
    """Action in a workflow."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    type: ActionType
    config: Dict[str, Any] = {}
    enabled: bool = True


class WorkflowNode(BaseModel):
    """Node in a workflow graph."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: WorkflowAction
    next_nodes: List[str] = []  # IDs of next nodes
    metadata: Dict[str, Any] = {}


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
            WorkflowNode if found, None otherwise
        """
        return self.nodes.get(node_id)
    
    def get_entry_node(self) -> Optional[WorkflowNode]:
        """Get the entry node of the workflow.
        
        Returns:
            Entry WorkflowNode if set, None otherwise
        """
        if self.entry_node_id:
            return self.get_node(self.entry_node_id)
        return None
    
    def add_node(self, action: WorkflowAction, next_nodes: List[str] = []) -> str:
        """Add a node to the workflow.
        
        Args:
            action: Action for the node
            next_nodes: IDs of next nodes
            
        Returns:
            ID of the created node
        """
        node = WorkflowNode(
            action=action,
            next_nodes=next_nodes
        )
        self.nodes[node.id] = node
        
        # If this is the first node, set it as entry node
        if not self.entry_node_id:
            self.entry_node_id = node.id
        
        return node.id
    
    def add_trigger(self, trigger_type: TriggerType, name: str, config: Dict[str, Any] = {}) -> str:
        """Add a trigger to the workflow.
        
        Args:
            trigger_type: Type of the trigger
            name: Name of the trigger
            config: Trigger configuration
            
        Returns:
            ID of the created trigger
        """
        trigger = WorkflowTrigger(
            type=trigger_type,
            name=name,
            config=config
        )
        self.triggers.append(trigger)
        return trigger.id
    
    def connect_nodes(self, source_id: str, target_id: str) -> bool:
        """Connect two nodes in the workflow.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            
        Returns:
            True if connection was successful, False otherwise
        """
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        
        if not source or not target:
            return False
        
        if target_id not in source.next_nodes:
            source.next_nodes.append(target_id)
        
        return True 