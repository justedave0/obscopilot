"""
Workflow execution engine for OBSCopilot.

This module provides the execution engine for running workflows.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union, Type

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventBus, EventType, event_bus
from obscopilot.twitch.client import TwitchClient
from obscopilot.obs.client import OBSClient
from obscopilot.workflows.models import (
    ActionType, 
    Workflow, 
    WorkflowAction, 
    WorkflowNode, 
    WorkflowTrigger, 
    TriggerType,
    WorkflowContext
)
from obscopilot.workflows.triggers import get_trigger_class, get_trigger_metadata
from obscopilot.workflows.actions import get_action_class

logger = logging.getLogger(__name__)


class WorkflowContext:
    """Context for a workflow execution."""
    
    def __init__(self, workflow: Workflow, trigger_data: Dict[str, Any]):
        """Initialize workflow context.
        
        Args:
            workflow: Workflow being executed
            trigger_data: Data from the trigger event
        """
        self.workflow = workflow
        self.trigger_data = trigger_data
        self.variables: Dict[str, Any] = {}
        self.execution_path: List[str] = []  # Node IDs in execution order
        self.start_time = time.time()
        self.current_node_id: Optional[str] = None
    
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
            template: Template string with {variable} placeholders
            
        Returns:
            Resolved string
        """
        try:
            # First try to format with context variables
            resolved = template.format(**self.variables)
            
            # Then try to format with trigger data
            resolved = resolved.format(**self.trigger_data)
            
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
        return time.time() - self.start_time


class WorkflowEngine:
    """Workflow execution engine."""
    
    def __init__(
        self, 
        config: Config, 
        twitch_client: TwitchClient, 
        obs_client: OBSClient
    ):
        """Initialize workflow engine.
        
        Args:
            config: Application configuration
            twitch_client: Twitch API client
            obs_client: OBS WebSocket client
        """
        self.config = config
        self.twitch_client = twitch_client
        self.obs_client = obs_client
        self.event_bus = event_bus
        self.workflows: Dict[str, Workflow] = {}
        self.event_mapping: Dict[EventType, List[str]] = {}  # Maps event types to workflow IDs
        self._register_event_handlers()
        self._setup_action_handlers()
    
    def _register_event_handlers(self) -> None:
        """Register event handlers for workflow triggers."""
        # Twitch events
        self.event_bus.subscribe(EventType.TWITCH_CHAT_MESSAGE, self._handle_event)
        self.event_bus.subscribe(EventType.TWITCH_FOLLOW, self._handle_event)
        self.event_bus.subscribe(EventType.TWITCH_SUBSCRIPTION, self._handle_event)
        self.event_bus.subscribe(EventType.TWITCH_BITS, self._handle_event)
        self.event_bus.subscribe(EventType.TWITCH_RAID, self._handle_event)
        self.event_bus.subscribe(EventType.TWITCH_CHANNEL_POINTS_REDEEM, self._handle_event)
        self.event_bus.subscribe(EventType.TWITCH_STREAM_ONLINE, self._handle_event)
        self.event_bus.subscribe(EventType.TWITCH_STREAM_OFFLINE, self._handle_event)
        
        # OBS events
        self.event_bus.subscribe(EventType.OBS_SCENE_CHANGED, self._handle_event)
        self.event_bus.subscribe(EventType.OBS_STREAMING_STARTED, self._handle_event)
        self.event_bus.subscribe(EventType.OBS_STREAMING_STOPPED, self._handle_event)
        self.event_bus.subscribe(EventType.OBS_RECORDING_STARTED, self._handle_event)
        self.event_bus.subscribe(EventType.OBS_RECORDING_STOPPED, self._handle_event)
    
    def _setup_action_handlers(self) -> None:
        """Set up action handlers for different action types."""
        self.action_handlers = {
            # Twitch actions
            ActionType.TWITCH_SEND_CHAT_MESSAGE: self._handle_twitch_send_chat_message,
            
            # OBS actions
            ActionType.OBS_SWITCH_SCENE: self._handle_obs_switch_scene,
            ActionType.OBS_SET_SOURCE_VISIBILITY: self._handle_obs_set_source_visibility,
            ActionType.OBS_START_STREAMING: self._handle_obs_start_streaming,
            ActionType.OBS_STOP_STREAMING: self._handle_obs_stop_streaming,
            ActionType.OBS_START_RECORDING: self._handle_obs_start_recording,
            ActionType.OBS_STOP_RECORDING: self._handle_obs_stop_recording,
            
            # Media actions
            ActionType.PLAY_SOUND: self._handle_play_sound,
            
            # AI actions
            ActionType.AI_GENERATE_RESPONSE: self._handle_ai_generate_response,
            
            # Control flow actions
            ActionType.DELAY: self._handle_delay,
            ActionType.CONDITIONAL: self._handle_conditional,
        }
    
    async def load_workflows(self, directory: Optional[Path] = None) -> int:
        """Load workflows from a directory.
        
        Args:
            directory: Directory containing workflow JSON files
            
        Returns:
            Number of workflows loaded
        """
        try:
            # Get workflow directory from config if not provided
            if not directory:
                workflow_dir = self.config.get('workflows', 'workflow_dir', '')
                if not workflow_dir:
                    workflow_dir = Path.home() / '.obscopilot' / 'workflows'
                else:
                    workflow_dir = Path(workflow_dir)
            else:
                workflow_dir = directory
            
            # Create directory if it doesn't exist
            workflow_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Loading workflows from {workflow_dir}")
            
            # Load all JSON files in the directory
            workflow_files = list(workflow_dir.glob('*.json'))
            count = 0
            
            for file_path in workflow_files:
                try:
                    with open(file_path, 'r') as f:
                        workflow_json = f.read()
                    
                    workflow = Workflow.from_json(workflow_json)
                    self.register_workflow(workflow)
                    count += 1
                    logger.info(f"Loaded workflow: {workflow.name} ({workflow.id})")
                except Exception as e:
                    logger.error(f"Error loading workflow from {file_path}: {e}")
            
            logger.info(f"Loaded {count} workflows")
            return count
        except Exception as e:
            logger.error(f"Error loading workflows: {e}")
            return 0
    
    async def save_workflow(self, workflow: Workflow, directory: Optional[Path] = None) -> bool:
        """Save a workflow to file.
        
        Args:
            workflow: Workflow to save
            directory: Directory to save the workflow in
            
        Returns:
            True if workflow was saved successfully, False otherwise
        """
        try:
            # Get workflow directory from config if not provided
            if not directory:
                workflow_dir = self.config.get('workflows', 'workflow_dir', '')
                if not workflow_dir:
                    workflow_dir = Path.home() / '.obscopilot' / 'workflows'
                else:
                    workflow_dir = Path(workflow_dir)
            else:
                workflow_dir = directory
            
            # Create directory if it doesn't exist
            workflow_dir.mkdir(parents=True, exist_ok=True)
            
            # Save workflow to file
            file_path = workflow_dir / f"{workflow.id}.json"
            with open(file_path, 'w') as f:
                f.write(workflow.to_json())
            
            logger.info(f"Saved workflow: {workflow.name} ({workflow.id}) to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving workflow: {e}")
            return False
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow with the engine.
        
        Args:
            workflow: Workflow to register
        """
        # Make sure the workflow is enabled
        if not workflow.enabled:
            logger.info(f"Skipping disabled workflow: {workflow.name} ({workflow.id})")
            return
        
        # Add workflow to registry
        self.workflows[workflow.id] = workflow
        
        # Register triggers
        for trigger in workflow.triggers:
            # Prepare the trigger
            trigger_class = get_trigger_class(trigger.type)
            if trigger_class:
                try:
                    # Call prepare method to set up any compiled patterns or caches
                    trigger_class.prepare(trigger)
                except Exception as e:
                    logger.error(f"Error preparing trigger {trigger.id} ({trigger.type}): {e}")
            
            # Map event type to workflow
            event_type = self._map_trigger_to_event_type(trigger.type)
            if event_type:
                if event_type not in self.event_mapping:
                    self.event_mapping[event_type] = []
                
                # Add workflow ID to the mapping if not already there
                if workflow.id not in self.event_mapping[event_type]:
                    self.event_mapping[event_type].append(workflow.id)
                    
        logger.info(f"Registered workflow: {workflow.name} ({workflow.id})")
    
    def unregister_workflow(self, workflow_id: str) -> bool:
        """Unregister a workflow from the engine.
        
        Args:
            workflow_id: ID of the workflow to unregister
            
        Returns:
            True if workflow was unregistered, False if not found
        """
        if workflow_id not in self.workflows:
            return False
        
        # Remove workflow from registry
        workflow = self.workflows.pop(workflow_id)
        
        # Remove workflow from event mapping
        for event_type in self.event_mapping:
            if workflow_id in self.event_mapping[event_type]:
                self.event_mapping[event_type].remove(workflow_id)
        
        logger.info(f"Unregistered workflow: {workflow.name} ({workflow.id})")
        return True
    
    def _map_trigger_to_event_type(self, trigger_type: TriggerType) -> Optional[EventType]:
        """Map a trigger type to an event type.
        
        Args:
            trigger_type: Trigger type to map
            
        Returns:
            Corresponding event type or None if no mapping
        """
        mapping = {
            TriggerType.TWITCH_CHAT_MESSAGE: EventType.TWITCH_CHAT_MESSAGE,
            TriggerType.TWITCH_FOLLOW: EventType.TWITCH_FOLLOW,
            TriggerType.TWITCH_SUBSCRIPTION: EventType.TWITCH_SUBSCRIPTION,
            TriggerType.TWITCH_BITS: EventType.TWITCH_BITS,
            TriggerType.TWITCH_RAID: EventType.TWITCH_RAID,
            TriggerType.TWITCH_CHANNEL_POINTS_REDEEM: EventType.TWITCH_CHANNEL_POINTS_REDEEM,
            TriggerType.TWITCH_STREAM_ONLINE: EventType.TWITCH_STREAM_ONLINE,
            TriggerType.TWITCH_STREAM_OFFLINE: EventType.TWITCH_STREAM_OFFLINE,
            TriggerType.OBS_SCENE_CHANGED: EventType.OBS_SCENE_CHANGED,
            TriggerType.OBS_STREAMING_STARTED: EventType.OBS_STREAMING_STARTED,
            TriggerType.OBS_STREAMING_STOPPED: EventType.OBS_STREAMING_STOPPED,
            TriggerType.OBS_RECORDING_STARTED: EventType.OBS_RECORDING_STARTED,
            TriggerType.OBS_RECORDING_STOPPED: EventType.OBS_RECORDING_STOPPED,
        }
        
        return mapping.get(trigger_type)
    
    def _map_event_type_to_trigger_type(self, event_type: EventType) -> Optional[TriggerType]:
        """Map an event type to a trigger type.
        
        Args:
            event_type: Event type to map
            
        Returns:
            Corresponding trigger type or None if no mapping
        """
        mapping = {
            EventType.TWITCH_CHAT_MESSAGE: TriggerType.TWITCH_CHAT_MESSAGE,
            EventType.TWITCH_FOLLOW: TriggerType.TWITCH_FOLLOW,
            EventType.TWITCH_SUBSCRIPTION: TriggerType.TWITCH_SUBSCRIPTION,
            EventType.TWITCH_BITS: TriggerType.TWITCH_BITS,
            EventType.TWITCH_RAID: TriggerType.TWITCH_RAID,
            EventType.TWITCH_CHANNEL_POINTS_REDEEM: TriggerType.TWITCH_CHANNEL_POINTS_REDEEM,
            EventType.TWITCH_STREAM_ONLINE: TriggerType.TWITCH_STREAM_ONLINE,
            EventType.TWITCH_STREAM_OFFLINE: TriggerType.TWITCH_STREAM_OFFLINE,
            EventType.OBS_SCENE_CHANGED: TriggerType.OBS_SCENE_CHANGED,
            EventType.OBS_STREAMING_STARTED: TriggerType.OBS_STREAMING_STARTED,
            EventType.OBS_STREAMING_STOPPED: TriggerType.OBS_STREAMING_STOPPED,
            EventType.OBS_RECORDING_STARTED: TriggerType.OBS_RECORDING_STARTED,
            EventType.OBS_RECORDING_STOPPED: TriggerType.OBS_RECORDING_STOPPED,
        }
        
        return mapping.get(event_type)
    
    async def _handle_event(self, event: Event) -> None:
        """Handle an event by checking if it triggers any workflows.
        
        Args:
            event: Event to handle
        """
        event_type = event.type
        event_data = event.data
        
        # Skip if no workflows registered for this event
        if event_type not in self.event_mapping or not self.event_mapping[event_type]:
            return
        
        # Get the corresponding trigger type
        trigger_type = self._map_event_type_to_trigger_type(event_type)
        if not trigger_type:
            logger.warning(f"No trigger type mapped for event type: {event_type}")
            return
        
        # Get the trigger class for this trigger type
        trigger_class = get_trigger_class(trigger_type)
        if not trigger_class:
            logger.warning(f"No trigger class found for trigger type: {trigger_type}")
            return
        
        # Check each workflow registered for this event
        triggered_workflows = []
        for workflow_id in self.event_mapping[event_type]:
            workflow = self.workflows.get(workflow_id)
            if not workflow or not workflow.enabled:
                continue
            
            # Check if any of the workflow's triggers match this event
            for trigger in workflow.triggers:
                if trigger.type != trigger_type:
                    continue
                
                # Use the specialized trigger class to check if the event matches
                if trigger_class.matches_event(trigger, event_type, event_data):
                    # This workflow should be triggered
                    triggered_workflows.append((workflow, trigger, event_data))
                    # Break after first matching trigger
                    break
        
        # Execute all triggered workflows
        for workflow, trigger, data in triggered_workflows:
            logger.info(f"Executing workflow '{workflow.name}' triggered by {trigger.type}")
            asyncio.create_task(self.execute_workflow(workflow, data, trigger))
    
    async def execute_workflow(
        self, 
        workflow: Workflow, 
        trigger_data: Dict[str, Any], 
        trigger: Optional[WorkflowTrigger] = None
    ) -> bool:
        """Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            trigger_data: Data from the trigger event
            trigger: The trigger that initiated this workflow (optional)
            
        Returns:
            True if workflow execution completed successfully, False otherwise
        """
        try:
            # Create workflow context
            context = workflow.create_context(trigger_data)
            
            # Record execution time for time-based triggers
            if trigger:
                if "_last_run" not in trigger.config:
                    trigger.config["_last_run"] = time.time()
                else:
                    trigger.config["_last_run"] = time.time()
            
            # Get entry node
            entry_node = workflow.get_entry_node()
            if not entry_node:
                logger.error(f"Workflow has no entry node: {workflow.name} ({workflow.id})")
                return False
            
            # Execute entry node and follow the execution path
            try:
                # Add entry node to execution path
                context.add_to_execution_path(entry_node.id)
                
                # Execute the entry node
                await self._execute_node(entry_node, context)
                
                logger.info(f"Workflow '{workflow.name}' executed successfully")
                return True
            except Exception as e:
                logger.error(f"Error executing workflow '{workflow.name}': {e}")
                return False
        except Exception as e:
            logger.error(f"Error setting up workflow execution for '{workflow.name}': {e}")
            return False
    
    async def _execute_node(self, node: WorkflowNode, context: WorkflowContext) -> Any:
        """Execute a workflow node.
        
        Args:
            node: Node to execute
            context: Workflow execution context
            
        Returns:
            Result of node execution
        """
        # Add node to execution path
        context.add_to_execution_path(node.id)
        
        # Check if node is enabled
        if not node.action.enabled:
            logger.info(f"Skipping disabled node: {node.action.name} ({node.id})")
            return None
        
        # Execute action
        action_handler = self.action_handlers.get(node.action.type)
        if not action_handler:
            logger.error(f"No handler for action type: {node.action.type}")
            return None
        
        try:
            logger.debug(f"Executing node: {node.action.name} ({node.id})")
            result = await action_handler(node.action, context)
            
            # Execute next nodes
            for next_node_id in node.next_nodes:
                next_node = context.workflow.get_node(next_node_id)
                if next_node:
                    await self._execute_node(next_node, context)
            
            return result
        except Exception as e:
            logger.error(f"Error executing node {node.action.name} ({node.id}): {e}")
            raise
    
    # Action handlers
    
    async def _handle_twitch_send_chat_message(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle TWITCH_SEND_CHAT_MESSAGE action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        channel = action.config.get('channel', '')
        message = action.config.get('message', '')
        
        # Resolve templates in channel and message
        channel = context.resolve_template(channel)
        message = context.resolve_template(message)
        
        if not channel:
            # Try to get channel from trigger data
            channel = context.trigger_data.get('channel', '')
        
        if not channel or not message:
            logger.error("Cannot send message: missing channel or message")
            return False
        
        # Send message
        return await self.twitch_client.send_chat_message(channel, message)
    
    async def _handle_obs_switch_scene(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle OBS_SWITCH_SCENE action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if scene was switched successfully, False otherwise
        """
        scene_name = action.config.get('scene_name', '')
        
        # Resolve template in scene name
        scene_name = context.resolve_template(scene_name)
        
        if not scene_name:
            logger.error("Cannot switch scene: missing scene name")
            return False
        
        # Switch scene
        return self.obs_client.switch_scene(scene_name)
    
    async def _handle_obs_set_source_visibility(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle OBS_SET_SOURCE_VISIBILITY action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if source visibility was set successfully, False otherwise
        """
        source_name = action.config.get('source_name', '')
        visible = action.config.get('visible', True)
        scene_name = action.config.get('scene_name', '')
        
        # Resolve templates
        source_name = context.resolve_template(source_name)
        scene_name = context.resolve_template(scene_name) if scene_name else None
        
        if not source_name:
            logger.error("Cannot set source visibility: missing source name")
            return False
        
        # Set source visibility
        return self.obs_client.set_source_visibility(source_name, visible, scene_name)
    
    async def _handle_obs_start_streaming(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle OBS_START_STREAMING action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if streaming was started successfully, False otherwise
        """
        return self.obs_client.start_streaming()
    
    async def _handle_obs_stop_streaming(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle OBS_STOP_STREAMING action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if streaming was stopped successfully, False otherwise
        """
        return self.obs_client.stop_streaming()
    
    async def _handle_obs_start_recording(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle OBS_START_RECORDING action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if recording was started successfully, False otherwise
        """
        return self.obs_client.start_recording()
    
    async def _handle_obs_stop_recording(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle OBS_STOP_RECORDING action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if recording was stopped successfully, False otherwise
        """
        return self.obs_client.stop_recording()
    
    async def _handle_play_sound(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle PLAY_SOUND action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if sound was played successfully, False otherwise
        """
        # Not implemented yet
        logger.warning("PLAY_SOUND action not implemented")
        return False
    
    async def _handle_ai_generate_response(self, action: WorkflowAction, context: WorkflowContext) -> Optional[str]:
        """Handle AI_GENERATE_RESPONSE action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            Generated response or None on error
        """
        # Not implemented yet
        logger.warning("AI_GENERATE_RESPONSE action not implemented")
        return None
    
    async def _handle_delay(self, action: WorkflowAction, context: WorkflowContext) -> None:
        """Handle DELAY action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
        """
        delay_seconds = action.config.get('delay_seconds', 1.0)
        try:
            delay_seconds = float(delay_seconds)
            logger.debug(f"Delaying workflow for {delay_seconds} seconds")
            await asyncio.sleep(delay_seconds)
        except ValueError:
            logger.error(f"Invalid delay value: {delay_seconds}")
    
    async def _handle_conditional(self, action: WorkflowAction, context: WorkflowContext) -> bool:
        """Handle CONDITIONAL action.
        
        Args:
            action: Action to execute
            context: Workflow execution context
            
        Returns:
            True if condition was met, False otherwise
        """
        # Not implemented yet
        logger.warning("CONDITIONAL action not implemented")
        return False 