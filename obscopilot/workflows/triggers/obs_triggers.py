"""
OBS triggers for OBSCopilot workflow engine.

This module implements OBS-specific workflow triggers.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Pattern

from obscopilot.workflows.models import TriggerType, WorkflowTrigger
from obscopilot.workflows.triggers.base import BaseTrigger, RegexPatternMixin

logger = logging.getLogger(__name__)


class BaseObsTrigger(BaseTrigger):
    """Base class for OBS triggers."""
    pass


class ObsSceneChangedTrigger(BaseObsTrigger, RegexPatternMixin):
    """Trigger for OBS scene changes."""
    
    trigger_type = TriggerType.OBS_SCENE_CHANGED
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Compiles regex patterns for scenes.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Compile scene pattern
        if "scene_pattern" in config:
            config["_compiled_scene_pattern"] = cls.compile_pattern(config["scene_pattern"])
        
        # Compile previous scene pattern
        if "previous_scene_pattern" in config:
            config["_compiled_previous_scene_pattern"] = cls.compile_pattern(config["previous_scene_pattern"])
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches scene change event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches scene change, False otherwise
        """
        # Extract scene data
        scene_name = event_data.get("scene_name", "")
        previous_scene_name = event_data.get("previous_scene_name", "")
        
        # Check exact scene name
        if "scene_name" in config and scene_name:
            if config["scene_name"] != scene_name:
                return False
        
        # Check exact previous scene name
        if "previous_scene_name" in config and previous_scene_name:
            if config["previous_scene_name"] != previous_scene_name:
                return False
        
        # Check scene pattern
        scene_pattern = config.get("_compiled_scene_pattern")
        if scene_pattern and not cls.matches_pattern(scene_pattern, scene_name):
            return False
        
        # Check previous scene pattern
        previous_scene_pattern = config.get("_compiled_previous_scene_pattern")
        if previous_scene_pattern and not cls.matches_pattern(previous_scene_pattern, previous_scene_name):
            return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "scene_name": {
                "type": "string",
                "description": "Exact name of the scene to match",
                "required": False
            },
            "scene_pattern": {
                "type": "string",
                "description": "Regex pattern to match scene names",
                "required": False
            },
            "previous_scene_name": {
                "type": "string",
                "description": "Exact name of the previous scene to match",
                "required": False
            },
            "previous_scene_pattern": {
                "type": "string",
                "description": "Regex pattern to match previous scene names",
                "required": False
            }
        }


class ObsStreamingStartedTrigger(BaseObsTrigger):
    """Trigger for when OBS starts streaming."""
    
    trigger_type = TriggerType.OBS_STREAMING_STARTED
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches streaming started event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches streaming started event, False otherwise
        """
        return True  # No specific matching for this trigger
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration needed


class ObsStreamingStoppedTrigger(BaseObsTrigger):
    """Trigger for when OBS stops streaming."""
    
    trigger_type = TriggerType.OBS_STREAMING_STOPPED
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches streaming stopped event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches streaming stopped event, False otherwise
        """
        return True  # No specific matching for this trigger
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration needed


class ObsRecordingStartedTrigger(BaseObsTrigger):
    """Trigger for when OBS starts recording."""
    
    trigger_type = TriggerType.OBS_RECORDING_STARTED
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches recording started event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches recording started event, False otherwise
        """
        return True  # No specific matching for this trigger
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {}  # No configuration needed


class ObsRecordingStoppedTrigger(BaseObsTrigger):
    """Trigger for when OBS stops recording."""
    
    trigger_type = TriggerType.OBS_RECORDING_STOPPED
    
    @classmethod
    def _matches_config(cls, config: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if trigger config matches recording stopped event data.
        
        Args:
            config: Trigger configuration
            event_data: Event data payload
            
        Returns:
            True if config matches recording stopped event, False otherwise
        """
        # Check if we want to filter by recording duration
        if "min_duration" in config and "duration" in event_data:
            if event_data["duration"] < config["min_duration"]:
                return False
        
        return True
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "min_duration": {
                "type": "integer",
                "description": "Minimum recording duration in seconds",
                "required": False
            }
        } 