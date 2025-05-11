"""
OBS WebSocket client for OBSCopilot.

This module provides integration with OBS Studio via the WebSocket protocol.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Union

from obswebsocket import obsws, requests, events
from obswebsocket.exceptions import ConnectionFailure

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class OBSClient:
    """OBS WebSocket client for controlling OBS Studio."""
    
    def __init__(self, config: Config):
        """Initialize OBS client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.event_bus = event_bus
        self.client: Optional[obsws] = None
        self.connected = False
        self.event_handlers = {}
        self._setup_event_handlers()
    
    def _setup_event_handlers(self) -> None:
        """Set up event handlers for OBS WebSocket events."""
        # Scene events
        self.event_handlers[events.SwitchScenes] = self._on_scene_changed
        self.event_handlers[events.TransitionBegin] = self._on_transition_begin
        
        # Streaming events
        self.event_handlers[events.StreamStarted] = self._on_stream_started
        self.event_handlers[events.StreamStopped] = self._on_stream_stopped
        
        # Recording events
        self.event_handlers[events.RecordingStarted] = self._on_recording_started
        self.event_handlers[events.RecordingStopped] = self._on_recording_stopped
        
        # Source events
        self.event_handlers[events.SourceVisibilityChanged] = self._on_source_visibility_changed
    
    async def connect(self) -> bool:
        """Connect to OBS WebSocket.
        
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            logger.info("Connecting to OBS WebSocket...")
            
            # Get connection info from config
            host = self.config.get('obs', 'host', 'localhost')
            port = self.config.get('obs', 'port', 4455)
            password = self.config.get('obs', 'password', '')
            
            # Create client instance
            self.client = obsws(host, port, password)
            
            # Register event handlers
            for event_type, handler in self.event_handlers.items():
                self.client.register(event_type, handler)
            
            # Connect to OBS
            self.client.connect()
            
            # Get OBS version
            version = self.client.call(requests.GetVersion())
            logger.info(f"Connected to OBS {version.getObsVersion()} with WebSocket {version.getObsWebSocketVersion()}")
            
            self.connected = True
            await event_bus.emit(Event(EventType.OBS_CONNECTED, {
                'obs_version': version.getObsVersion(),
                'websocket_version': version.getObsWebSocketVersion()
            }))
            
            return True
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to OBS: {e}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to OBS: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from OBS WebSocket."""
        if self.client and self.connected:
            try:
                logger.info("Disconnecting from OBS WebSocket...")
                self.client.disconnect()
                self.connected = False
                event_bus.emit_sync(Event(EventType.OBS_DISCONNECTED))
                logger.info("Disconnected from OBS WebSocket")
            except Exception as e:
                logger.error(f"Error disconnecting from OBS: {e}")
    
    def _check_connection(func):
        """Decorator to check if client is connected before executing function."""
        def wrapper(self, *args, **kwargs):
            if not self.client or not self.connected:
                logger.error(f"Cannot execute {func.__name__}, not connected to OBS")
                return None
            return func(self, *args, **kwargs)
        return wrapper
    
    @_check_connection
    def get_current_scene(self) -> Optional[str]:
        """Get the current scene in OBS.
        
        Returns:
            Current scene name or None on error
        """
        try:
            response = self.client.call(requests.GetCurrentScene())
            return response.getName()
        except Exception as e:
            logger.error(f"Error getting current scene: {e}")
            return None
    
    @_check_connection
    def get_scenes(self) -> List[str]:
        """Get all available scenes in OBS.
        
        Returns:
            List of scene names
        """
        try:
            response = self.client.call(requests.GetSceneList())
            return [scene['name'] for scene in response.getScenes()]
        except Exception as e:
            logger.error(f"Error getting scene list: {e}")
            return []
    
    @_check_connection
    def switch_scene(self, scene_name: str) -> bool:
        """Switch to a specific scene in OBS.
        
        Args:
            scene_name: Name of the scene to switch to
            
        Returns:
            True if scene switch was successful, False otherwise
        """
        try:
            logger.info(f"Switching to scene: {scene_name}")
            self.client.call(requests.SetCurrentScene(scene_name))
            return True
        except Exception as e:
            logger.error(f"Error switching to scene {scene_name}: {e}")
            return False
    
    @_check_connection
    def get_source_visibility(self, source_name: str, scene_name: Optional[str] = None) -> Optional[bool]:
        """Get the visibility state of a source.
        
        Args:
            source_name: Name of the source
            scene_name: Name of the scene containing the source (current scene if None)
            
        Returns:
            True if source is visible, False if hidden, None on error
        """
        try:
            scene = scene_name or self.get_current_scene()
            if not scene:
                return None
            
            response = self.client.call(requests.GetSceneItemProperties(source_name, scene_name=scene))
            return response.getVisible()
        except Exception as e:
            logger.error(f"Error getting source visibility for {source_name}: {e}")
            return None
    
    @_check_connection
    def set_source_visibility(self, source_name: str, visible: bool, scene_name: Optional[str] = None) -> bool:
        """Set the visibility state of a source.
        
        Args:
            source_name: Name of the source
            visible: True to show, False to hide
            scene_name: Name of the scene containing the source (current scene if None)
            
        Returns:
            True if visibility change was successful, False otherwise
        """
        try:
            scene = scene_name or self.get_current_scene()
            if not scene:
                return False
            
            logger.info(f"Setting source {source_name} visibility to {visible} in scene {scene}")
            self.client.call(requests.SetSceneItemProperties(
                item=source_name,
                visible=visible,
                scene_name=scene
            ))
            return True
        except Exception as e:
            logger.error(f"Error setting source visibility for {source_name}: {e}")
            return False
    
    @_check_connection
    def start_streaming(self) -> bool:
        """Start streaming in OBS.
        
        Returns:
            True if streaming started successfully, False otherwise
        """
        try:
            logger.info("Starting stream in OBS")
            self.client.call(requests.StartStreaming())
            return True
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return False
    
    @_check_connection
    def stop_streaming(self) -> bool:
        """Stop streaming in OBS.
        
        Returns:
            True if streaming stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping stream in OBS")
            self.client.call(requests.StopStreaming())
            return True
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
            return False
    
    @_check_connection
    def start_recording(self) -> bool:
        """Start recording in OBS.
        
        Returns:
            True if recording started successfully, False otherwise
        """
        try:
            logger.info("Starting recording in OBS")
            self.client.call(requests.StartRecording())
            return True
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False
    
    @_check_connection
    def stop_recording(self) -> bool:
        """Stop recording in OBS.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping recording in OBS")
            self.client.call(requests.StopRecording())
            return True
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False
    
    # OBS WebSocket event handlers
    
    def _on_scene_changed(self, message):
        """Handle scene changed event."""
        scene_name = message.getSceneName()
        logger.debug(f"Scene changed to: {scene_name}")
        event_bus.emit_sync(Event(EventType.OBS_SCENE_CHANGED, {
            'scene_name': scene_name
        }))
    
    def _on_transition_begin(self, message):
        """Handle transition begin event."""
        source_name = message.getFromScene()
        destination_name = message.getToScene()
        logger.debug(f"Transition from {source_name} to {destination_name}")
    
    def _on_stream_started(self, message):
        """Handle stream started event."""
        logger.info("Streaming started in OBS")
        event_bus.emit_sync(Event(EventType.OBS_STREAMING_STARTED))
    
    def _on_stream_stopped(self, message):
        """Handle stream stopped event."""
        logger.info("Streaming stopped in OBS")
        event_bus.emit_sync(Event(EventType.OBS_STREAMING_STOPPED))
    
    def _on_recording_started(self, message):
        """Handle recording started event."""
        logger.info("Recording started in OBS")
        event_bus.emit_sync(Event(EventType.OBS_RECORDING_STARTED))
    
    def _on_recording_stopped(self, message):
        """Handle recording stopped event."""
        logger.info("Recording stopped in OBS")
        path = message.getRecordingFilename()
        event_bus.emit_sync(Event(EventType.OBS_RECORDING_STOPPED, {
            'path': path
        }))
    
    def _on_source_visibility_changed(self, message):
        """Handle source visibility changed event."""
        source_name = message.getSourceName()
        visible = message.getSourceVisible()
        scene_name = message.getSceneName()
        logger.debug(f"Source {source_name} visibility changed to {visible} in scene {scene_name}")
        event_bus.emit_sync(Event(EventType.OBS_SOURCE_VISIBILITY_CHANGED, {
            'source_name': source_name,
            'visible': visible,
            'scene_name': scene_name
        })) 