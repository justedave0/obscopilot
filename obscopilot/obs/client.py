"""
OBS WebSocket client for OBSCopilot.

This module provides integration with OBS Studio via the WebSocket protocol v5 (OBS 28+).
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union

import simpleobsws

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
        self.client: Optional[simpleobsws.WebSocketClient] = None
        self.connected = False
        self._connecting = False
        self._event_task = None
    
    async def connect(self) -> bool:
        """Connect to OBS WebSocket.
        
        Returns:
            True if connection was successful, False otherwise
        """
        if self._connecting:
            logger.warning("Connection attempt already in progress")
            return False
            
        if self.connected:
            logger.warning("Already connected to OBS")
            return True
            
        self._connecting = True
        
        try:
            logger.info("Connecting to OBS WebSocket...")
            
            # Get connection info from config
            host = self.config.get('obs', 'host', 'localhost')
            port = self.config.get('obs', 'port', 4455)
            password = self.config.get('obs', 'password', '')
            
            # Create connection parameters
            parameters = simpleobsws.IdentificationParameters(ignoreNonFatalRequestStatus=False)
            
            # Create client instance
            self.client = simpleobsws.WebSocketClient(
                url=f"ws://{host}:{port}",
                password=password,
                identification_parameters=parameters
            )
            
            # Connect to OBS
            await self.client.connect()
            await self.client.wait_until_identified()
            
            # Get OBS version to verify connection is working
            request = simpleobsws.Request('GetVersion')
            response = await self.client.call(request)
            
            if not response.ok():
                raise ConnectionError(f"Failed to get OBS version: {response.error()}")
                
            data = response.responseData
            obs_version = data.get('obsVersion', 'Unknown')
            websocket_version = data.get('obsWebSocketVersion', 'Unknown')
            
            logger.info(f"Connected to OBS {obs_version} with WebSocket {websocket_version}")
            
            # Start event listener
            self._event_task = asyncio.create_task(self._event_listener())
            
            self.connected = True
            await event_bus.emit(Event(EventType.OBS_CONNECTED, {
                'obs_version': obs_version,
                'websocket_version': websocket_version
            }))
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to OBS: {e}")
            self.connected = False
            return False
        finally:
            self._connecting = False
    
    async def is_actually_connected(self) -> bool:
        """Verify if the connection to OBS is actually active.
        
        Returns:
            True if connection is active, False otherwise
        """
        if not self.client or not self.connected:
            return False
            
        try:
            # Try to get OBS version to verify connection
            request = simpleobsws.Request('GetVersion')
            response = await self.client.call(request)
            
            if not response.ok():
                # Connection is not working properly
                logger.warning(f"OBS connection check failed: {response.error()}")
                self.connected = False
                return False
                
            # Connection is working
            return True
        except Exception as e:
            logger.error(f"Error checking OBS connection: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from OBS WebSocket."""
        if self.client and self.connected:
            try:
                logger.info("Disconnecting from OBS WebSocket...")
                
                # Cancel event listener task
                if self._event_task and not self._event_task.done():
                    self._event_task.cancel()
                    try:
                        await self._event_task
                    except asyncio.CancelledError:
                        pass
                    
                # Disconnect from WebSocket
                await self.client.disconnect()
                self.connected = False
                await event_bus.emit(Event(EventType.OBS_DISCONNECTED))
                logger.info("Disconnected from OBS WebSocket")
            except Exception as e:
                logger.error(f"Error disconnecting from OBS: {e}")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.disconnect()
    
    async def _event_listener(self) -> None:
        """Listen for events from OBS WebSocket."""
        if not self.client:
            return
            
        while self.connected:
            try:
                event = await self.client.wait_for_event()
                
                if not event:
                    continue
                    
                event_type = event.eventType
                event_data = event.eventData
                
                logger.debug(f"Received OBS event: {event_type}")
                
                # Handle specific events
                if event_type == 'CurrentProgramSceneChanged':
                    await self._handle_scene_changed(event_data)
                elif event_type == 'SceneTransitionStarted':
                    await self._handle_transition_begin(event_data)
                elif event_type == 'StreamStateChanged':
                    if event_data.get('outputActive', False):
                        await self._handle_stream_started(event_data)
                    else:
                        await self._handle_stream_stopped(event_data)
                elif event_type == 'RecordStateChanged':
                    if event_data.get('outputActive', False):
                        await self._handle_recording_started(event_data)
                    else:
                        await self._handle_recording_stopped(event_data)
                elif event_type == 'SceneItemEnableStateChanged':
                    await self._handle_source_visibility_changed(event_data)
                
            except asyncio.CancelledError:
                logger.debug("Event listener task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in OBS event listener: {e}")
                await asyncio.sleep(1)  # Prevent excessive CPU usage in case of repeated errors
    
    def _check_connection(func):
        """Decorator to check if client is connected before executing function."""
        async def wrapper(self, *args, **kwargs):
            if not self.client or not self.connected:
                logger.error(f"Cannot execute {func.__name__}, not connected to OBS")
                return None
            return await func(self, *args, **kwargs)
        return wrapper
    
    @_check_connection
    async def get_current_scene(self) -> Optional[str]:
        """Get the current scene in OBS.
        
        Returns:
            Current scene name or None on error
        """
        try:
            request = simpleobsws.Request('GetCurrentProgramScene')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error getting current scene: {response.error()}")
                return None
                
            return response.responseData.get('currentProgramSceneName')
        except Exception as e:
            logger.error(f"Error getting current scene: {e}")
            return None
    
    @_check_connection
    async def get_scenes(self) -> List[str]:
        """Get all available scenes in OBS.
        
        Returns:
            List of scene names
        """
        try:
            request = simpleobsws.Request('GetSceneList')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error getting scene list: {response.error()}")
                return []
                
            scenes = response.responseData.get('scenes', [])
            return [scene.get('sceneName') for scene in scenes]
        except Exception as e:
            logger.error(f"Error getting scene list: {e}")
            return []
    
    @_check_connection
    async def switch_scene(self, scene_name: str) -> bool:
        """Switch to a specific scene in OBS.
        
        Args:
            scene_name: Name of the scene to switch to
            
        Returns:
            True if scene switch was successful, False otherwise
        """
        try:
            logger.info(f"Switching to scene: {scene_name}")
            request = simpleobsws.Request('SetCurrentProgramScene', {'sceneName': scene_name})
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error switching to scene {scene_name}: {response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error switching to scene {scene_name}: {e}")
            return False
    
    @_check_connection
    async def get_source_visibility(self, source_name: str, scene_name: Optional[str] = None) -> Optional[bool]:
        """Get the visibility state of a source.
        
        Args:
            source_name: Name of the source
            scene_name: Name of the scene containing the source (current scene if None)
            
        Returns:
            True if source is visible, False if hidden, None on error
        """
        try:
            scene = scene_name or await self.get_current_scene()
            if not scene:
                return None
            
            # First, get the scene item ID for the source
            request = simpleobsws.Request('GetSceneItemList', {'sceneName': scene})
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error getting scene items: {response.error()}")
                return None
                
            scene_items = response.responseData.get('sceneItems', [])
            item_id = None
            
            for item in scene_items:
                if item.get('sourceName') == source_name:
                    item_id = item.get('sceneItemId')
                    break
            
            if item_id is None:
                logger.error(f"Source {source_name} not found in scene {scene}")
                return None
            
            # Now get the source properties
            request = simpleobsws.Request('GetSceneItemEnabled', {
                'sceneName': scene,
                'sceneItemId': item_id
            })
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error getting source visibility: {response.error()}")
                return None
                
            return response.responseData.get('sceneItemEnabled', False)
        except Exception as e:
            logger.error(f"Error getting source visibility for {source_name}: {e}")
            return None
    
    @_check_connection
    async def set_source_visibility(self, source_name: str, visible: bool, scene_name: Optional[str] = None) -> bool:
        """Set the visibility state of a source.
        
        Args:
            source_name: Name of the source
            visible: True to show, False to hide
            scene_name: Name of the scene containing the source (current scene if None)
            
        Returns:
            True if visibility change was successful, False otherwise
        """
        try:
            scene = scene_name or await self.get_current_scene()
            if not scene:
                return False
            
            # First, get the scene item ID for the source
            request = simpleobsws.Request('GetSceneItemList', {'sceneName': scene})
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error getting scene items: {response.error()}")
                return False
                
            scene_items = response.responseData.get('sceneItems', [])
            item_id = None
            
            for item in scene_items:
                if item.get('sourceName') == source_name:
                    item_id = item.get('sceneItemId')
                    break
            
            if item_id is None:
                logger.error(f"Source {source_name} not found in scene {scene}")
                return False
            
            # Now set the source visibility
            logger.info(f"Setting source {source_name} visibility to {visible} in scene {scene}")
            request = simpleobsws.Request('SetSceneItemEnabled', {
                'sceneName': scene,
                'sceneItemId': item_id,
                'sceneItemEnabled': visible
            })
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error setting source visibility: {response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error setting source visibility for {source_name}: {e}")
            return False
    
    @_check_connection
    async def start_streaming(self) -> bool:
        """Start streaming in OBS.
        
        Returns:
            True if streaming started successfully, False otherwise
        """
        try:
            logger.info("Starting stream in OBS")
            request = simpleobsws.Request('StartStream')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error starting stream: {response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return False
    
    @_check_connection
    async def stop_streaming(self) -> bool:
        """Stop streaming in OBS.
        
        Returns:
            True if streaming stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping stream in OBS")
            request = simpleobsws.Request('StopStream')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error stopping stream: {response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
            return False
    
    @_check_connection
    async def start_recording(self) -> bool:
        """Start recording in OBS.
        
        Returns:
            True if recording started successfully, False otherwise
        """
        try:
            logger.info("Starting recording in OBS")
            request = simpleobsws.Request('StartRecord')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error starting recording: {response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False
    
    @_check_connection
    async def stop_recording(self) -> bool:
        """Stop recording in OBS.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping recording in OBS")
            request = simpleobsws.Request('StopRecord')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error stopping recording: {response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False
    
    # OBS WebSocket event handlers
    
    async def _handle_scene_changed(self, data):
        """Handle scene changed event."""
        scene_name = data.get('sceneName', '')
        logger.debug(f"Scene changed to: {scene_name}")
        await event_bus.emit(Event(EventType.OBS_SCENE_CHANGED, {
            'scene_name': scene_name
        }))
    
    async def _handle_transition_begin(self, data):
        """Handle transition begin event."""
        from_scene = data.get('fromScene', '')
        to_scene = data.get('toScene', '')
        logger.debug(f"Transition from {from_scene} to {to_scene}")
    
    async def _handle_stream_started(self, data):
        """Handle stream started event.
        
        Args:
            data: Event data
        """
        logger.info("OBS Stream started")
        session_id = str(uuid.uuid4())
        await event_bus.emit(Event(EventType.OBS_STREAM_STARTED, {
            'session_id': session_id,
            'timestamp': time.time(),
            'output_path': data.get('outputPath', '')
        }))
    
    async def _handle_stream_stopped(self, data):
        """Handle stream stopped event.
        
        Args:
            data: Event data
        """
        logger.info("OBS Stream stopped")
        await event_bus.emit(Event(EventType.OBS_STREAM_STOPPED, {
            'timestamp': time.time(),
            'output_path': data.get('outputPath', ''),
            'bytes_sent': data.get('bytesSent', 0),
            'duration': data.get('outputDuration', 0),
            'frames': data.get('outputTotalFrames', 0),
            'skipped_frames': data.get('outputSkippedFrames', 0)
        }))
    
    async def _handle_recording_started(self, data):
        """Handle recording started event."""
        logger.info("Recording started in OBS")
        await event_bus.emit(Event(EventType.OBS_RECORDING_STARTED))
    
    async def _handle_recording_stopped(self, data):
        """Handle recording stopped event."""
        logger.info("Recording stopped in OBS")
        output_path = data.get('outputPath', '')
        await event_bus.emit(Event(EventType.OBS_RECORDING_STOPPED, {
            'path': output_path
        }))
    
    @_check_connection
    async def _handle_source_visibility_changed(self, data):
        """Handle source visibility changed event."""
        scene_name = data.get('sceneName', '')
        source_name = data.get('sourceName', '')
        visible = data.get('sceneItemEnabled', False)
        
        logger.debug(f"Source {source_name} visibility changed to {visible} in scene {scene_name}")
        await event_bus.emit(Event(EventType.OBS_SOURCE_VISIBILITY_CHANGED, {
            'source_name': source_name,
            'visible': visible,
            'scene_name': scene_name
        }))
        
    @_check_connection
    async def get_source_settings(self, source_name: str, source_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the settings of a source.
        
        Args:
            source_name: Name of the source
            source_type: Type of the source (optional)
            
        Returns:
            Source settings if found, None otherwise
        """
        try:
            request = simpleobsws.Request('GetInputSettings', {
                'inputName': source_name
            })
            response = await self.client.call(request)
            
            if not response.ok():
                logger.debug(f"Source {source_name} not found or error: {response.error()}")
                return None
                
            return response.responseData
        except Exception as e:
            logger.error(f"Error getting source settings: {e}")
            return None
    
    @_check_connection
    async def create_text_source(self, source_name: str, scene_name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Create a text source in OBS.
        
        Args:
            source_name: Name of the source
            scene_name: Name of the scene to add the source to (optional, uses current scene if None)
            settings: Initial settings for the source (optional)
            
        Returns:
            True if source was created successfully, False otherwise
        """
        try:
            # Default settings
            default_settings = {
                "text": "",
                "font": {
                    "face": "Arial",
                    "size": 24,
                    "style": "Regular"
                },
                "color": 4294967295,  # White
                "bgcolor": 0,  # Transparent
                "align": "center"
            }
            
            # Merge with provided settings
            if settings:
                default_settings.update(settings)
            
            # Create the source
            logger.info(f"Creating text source: {source_name}")
            create_request = simpleobsws.Request('CreateInput', {
                'sceneName': scene_name or await self.get_current_scene(),
                'inputName': source_name,
                'inputKind': 'text_gdiplus_v2',
                'inputSettings': default_settings,
                'sceneItemEnabled': False
            })
            create_response = await self.client.call(create_request)
            
            if not create_response.ok():
                logger.error(f"Error creating text source: {create_response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error creating text source: {e}")
            return False
    
    @_check_connection
    async def set_source_text(self, source_name: str, text: str, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Set the text of a text source.
        
        Args:
            source_name: Name of the source
            text: Text to set
            settings: Additional settings to update (optional)
            
        Returns:
            True if text was set successfully, False otherwise
        """
        try:
            # Get current settings
            current_settings = await self.get_source_settings(source_name)
            if not current_settings:
                logger.error(f"Source {source_name} not found")
                return False
            
            # Update text
            input_settings = current_settings.get('inputSettings', {})
            input_settings['text'] = text
            
            # Update additional settings if provided
            if settings:
                input_settings.update(settings)
            
            # Apply settings
            request = simpleobsws.Request('SetInputSettings', {
                'inputName': source_name,
                'inputSettings': input_settings
            })
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error setting source text: {response.error()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error setting source text: {e}")
            return False
    
    @_check_connection
    async def get_stream_status(self) -> Optional[Dict[str, Any]]:
        """Get the current streaming status.
        
        Returns:
            Dictionary with stream status info or None on error
        """
        try:
            request = simpleobsws.Request('GetStreamStatus')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error getting stream status: {response.error()}")
                return None
                
            return response.responseData
        except Exception as e:
            logger.error(f"Error getting stream status: {e}")
            return None
    
    @_check_connection
    async def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get OBS statistics including CPU usage, memory usage, frames, etc.
        
        Returns:
            Dictionary with OBS statistics or None on error
        """
        try:
            request = simpleobsws.Request('GetStats')
            response = await self.client.call(request)
            
            if not response.ok():
                logger.error(f"Error getting OBS stats: {response.error()}")
                return None
                
            return response.responseData
        except Exception as e:
            logger.error(f"Error getting OBS stats: {e}")
            return None
    
    @_check_connection
    async def get_stream_health(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive stream health information by combining multiple API calls.
        
        Returns:
            Dictionary with combined stream health metrics or None on error
        """
        try:
            # Get general OBS stats (CPU, memory, etc.)
            stats = await self.get_stats()
            if not stats:
                return None
                
            # Get stream status (bitrate, dropped frames, etc.)
            stream_status = await self.get_stream_status()
            if not stream_status:
                return None
                
            # Combine data into a comprehensive health report
            health_data = {
                # OBS statistics
                'fps': stats.get('activeFps'),
                'render_total_frames': stats.get('renderTotalFrames'),
                'render_missed_frames': stats.get('renderMissedFrames'),
                'output_total_frames': stats.get('outputTotalFrames'),
                'output_skipped_frames': stats.get('outputSkippedFrames'),
                'average_frame_time': stats.get('averageFrameRenderTime'),
                'cpu_usage': stats.get('cpuUsage'),
                'memory_usage': stats.get('memoryUsage'),
                'free_disk_space': stats.get('availableDiskSpace'),
                
                # Stream statistics
                'bitrate': stream_status.get('outputBytes') / 128 / (stream_status.get('outputDuration', 1) / 1000) if stream_status.get('outputBytes') else 0,
                'num_dropped_frames': stream_status.get('outputSkippedFrames', 0),
                'num_total_frames': stream_status.get('outputTotalFrames', 0),
                'strain': None,  # Not directly available
                'stream_duration': stream_status.get('outputDuration', 0) / 1000 if stream_status.get('outputDuration') else 0,
                
                # Network statistics
                'kbits_per_sec': stream_status.get('kbitsPerSec', 0),
                'ping': None,  # Not directly available
                
                # Raw data for reference
                'raw_stats': stats,
                'raw_stream_status': stream_status
            }
            
            # Calculate drop percentage
            total_frames = health_data['num_total_frames']
            dropped_frames = health_data['num_dropped_frames']
            
            if total_frames > 0:
                health_data['drop_percentage'] = (dropped_frames / total_frames) * 100
            else:
                health_data['drop_percentage'] = 0
                
            return health_data
        except Exception as e:
            logger.error(f"Error getting stream health: {e}")
            return None 