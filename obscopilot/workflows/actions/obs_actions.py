"""
OBS actions for the workflow engine.

This module implements OBS-specific workflow actions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from obscopilot.obs.client import OBSClient
from obscopilot.workflows.models import WorkflowAction, WorkflowContext

logger = logging.getLogger(__name__)


class BaseObsAction:
    """Base class for OBS actions."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, obs_client: OBSClient) -> Any:
        """Execute the action.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            obs_client: OBS client instance
            
        Returns:
            Action result
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        raise NotImplementedError("Subclasses must implement get_config_schema()")


class ObsSwitchSceneAction(BaseObsAction):
    """Switch to a different scene in OBS."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, obs_client: OBSClient) -> bool:
        """Switch to a different scene in OBS.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            obs_client: OBS client instance
            
        Returns:
            True if scene was switched, False otherwise
        """
        try:
            # Get action config
            config = action.config
            
            # Get scene name
            scene_name = context.resolve_template(config.get('scene_name', ''))
            if not scene_name:
                logger.warning("No scene name provided")
                return False
            
            # Switch scene
            logger.info(f"Switching to scene: {scene_name}")
            result = await obs_client.set_current_scene(scene_name)
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error switching scene: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "scene_name": {
                "type": "string",
                "description": "Name of the scene to switch to",
                "required": True
            }
        }


class ObsSetSourceVisibilityAction(BaseObsAction):
    """Set the visibility of a source in OBS."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, obs_client: OBSClient) -> bool:
        """Set the visibility of a source in OBS.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            obs_client: OBS client instance
            
        Returns:
            True if visibility was set, False otherwise
        """
        try:
            # Get action config
            config = action.config
            
            # Get source name
            source_name = context.resolve_template(config.get('source_name', ''))
            if not source_name:
                logger.warning("No source name provided")
                return False
            
            # Get visibility
            visible = config.get('visible', True)
            
            # Get scene name (optional)
            scene_name = context.resolve_template(config.get('scene_name', ''))
            
            # Set source visibility
            logger.info(f"Setting source visibility: {source_name} to {'visible' if visible else 'hidden'}")
            result = await obs_client.set_source_visibility(source_name, visible, scene_name)
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error setting source visibility: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "source_name": {
                "type": "string",
                "description": "Name of the source",
                "required": True
            },
            "visible": {
                "type": "boolean",
                "description": "Whether the source should be visible",
                "default": True,
                "required": False
            },
            "scene_name": {
                "type": "string",
                "description": "Name of the scene containing the source (optional)",
                "required": False
            }
        }


class ObsStartStreamingAction(BaseObsAction):
    """Start streaming in OBS."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, obs_client: OBSClient) -> bool:
        """Start streaming in OBS.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            obs_client: OBS client instance
            
        Returns:
            True if streaming was started, False otherwise
        """
        try:
            logger.info("Starting streaming")
            result = await obs_client.start_streaming()
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error starting streaming: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration needed


class ObsStopStreamingAction(BaseObsAction):
    """Stop streaming in OBS."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, obs_client: OBSClient) -> bool:
        """Stop streaming in OBS.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            obs_client: OBS client instance
            
        Returns:
            True if streaming was stopped, False otherwise
        """
        try:
            logger.info("Stopping streaming")
            result = await obs_client.stop_streaming()
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration needed


class ObsStartRecordingAction(BaseObsAction):
    """Start recording in OBS."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, obs_client: OBSClient) -> bool:
        """Start recording in OBS.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            obs_client: OBS client instance
            
        Returns:
            True if recording was started, False otherwise
        """
        try:
            logger.info("Starting recording")
            result = await obs_client.start_recording()
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration needed


class ObsStopRecordingAction(BaseObsAction):
    """Stop recording in OBS."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, obs_client: OBSClient) -> bool:
        """Stop recording in OBS.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            obs_client: OBS client instance
            
        Returns:
            True if recording was stopped, False otherwise
        """
        try:
            logger.info("Stopping recording")
            result = await obs_client.stop_recording()
            
            # Store the result in context
            context.set_variable(f"action_result_{action.id}", result)
            
            return result
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration needed 