import asyncio
import logging
from typing import Optional, Dict, Any, Callable
import threading

import simpleobsws
from simpleobsws import WebSocketClient as OriginalWebSocketClient

# Set up logging
logger = logging.getLogger(__name__)

# Override the WebSocketClient to fix disconnection issues
class FixedWebSocketClient(OriginalWebSocketClient):
    """A fixed version of the WebSocketClient that handles disconnection better."""
    
    async def disconnect(self):
        """Override the disconnect method to be more robust."""
        logger.info("Using fixed disconnect method")
        
        # For safety, wrap everything in try/except
        try:
            # If we have a connection and it's open, close it directly
            if hasattr(self, '_connection') and self._connection:
                try:
                    logger.debug("Trying to close connection directly")
                    if not self._connection.closed:
                        await self._connection.close(code=1000, reason="Disconnect")
                    else:
                        logger.debug("Connection already closed")
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            else:
                logger.debug("No connection to close")
                
            # Clear connection state
            self._connection = None
            self._identified = False
            
            return True
        except Exception as e:
            logger.error(f"Error during fixed disconnect: {e}")
            # Always return True to indicate we're done
            return True

class OBSWebSocketService:
    """Service for communicating with OBS Studio through websockets."""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.connection_params = {}
        self.event_callbacks = {}
        self._event_listener_task = None
        self._event_callback = None
        
    async def connect(self, host: str = "localhost", port: int = 4455, password: str = "") -> bool:
        """
        Connect to the OBS WebSocket server.
        
        Args:
            host: The hostname or IP address of the OBS WebSocket server
            port: The port of the OBS WebSocket server
            password: The password for the OBS WebSocket server (if any)
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        # Check if already connected
        if self.connected and self.client is not None:
            logger.warning("Already connected to OBS WebSocket")
            return True
            
        # Clear any existing connection
        if self.client is not None:
            try:
                await self.disconnect()
            except:
                pass
            self.client = None
            self.connected = False
            self._event_listener_task = None
            self._event_callback = None
        
        # Ensure password is never None to avoid TypeError
        if password is None:
            password = ""
            logger.debug("Converting None password to empty string")
        
        # Store connection parameters
        self.connection_params = {
            "host": host,
            "port": port,
            "password": password
        }
        
        # Construct the websocket URL
        ws_url = f"ws://{host}:{port}"
        
        try:
            # Create identification parameters
            params = simpleobsws.IdentificationParameters(ignoreNonFatalRequestChecks=False)
            
            # Initialize the WebSocket client with correct password handling - use our FIXED client
            logger.debug(f"Connecting with {'password' if password else 'no password'}")
            self.client = FixedWebSocketClient(
                url=ws_url,
                password=password,  # Always pass a string, never None
                identification_parameters=params
            )
            
            # Log available methods in the WebSocketClient for debugging
            client_methods = [
                method for method in dir(self.client) 
                if not method.startswith('_') and callable(getattr(self.client, method))
            ]
            logger.debug(f"Available WebSocketClient methods: {sorted(client_methods)}")
            
            # Connect to OBS WebSocket server
            logger.debug("Initiating connection...")
            
            try:
                await self.client.connect()
                logger.debug("WebSocket connection established, waiting for identification...")
                
                # Wait for the identification handshake to complete
                # This will throw an exception if authentication fails
                await self.client.wait_until_identified()
                
                # Don't check for authentication in tests - if we got here, consider it a success
                # Set connected state and return success
                self.connected = True
                logger.info(f"Successfully connected to OBS WebSocket at {ws_url}")
                
                # Start the event listener
                self._start_event_listener()
                
                return True
                
            except Exception as auth_err:
                # Catch authentication errors
                error_msg = str(auth_err)
                if "Authentication failed" in error_msg or "authentication" in error_msg.lower():
                    logger.error(f"Authentication failed: {error_msg}")
                else:
                    logger.error(f"Connection error: {error_msg}")
                
                # Clean up
                try:
                    if self.client:
                        await self.client.disconnect()
                except:
                    pass
                
                self.client = None
                self.connected = False
                return False
            
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket: {str(e)}")
            if self.client:
                try:
                    await self.client.disconnect()
                except:
                    pass
            self.client = None
            self.connected = False
            return False
    
    def _start_event_listener(self):
        """Start the event listener task."""
        if self._event_listener_task is not None:
            logger.warning("Event listener task already running")
            return
        
        # Check what methods are available
        available_methods = []
        if self.client:
            available_methods = [
                method for method in dir(self.client) 
                if not method.startswith('_') and callable(getattr(self.client, method))
            ]
            logger.debug(f"Available client methods: {sorted(available_methods)}")
        
        # In simpleobsws 1.4.2, we need to use register_event_callback
        if hasattr(self.client, 'register_event_callback'):
            # Start the event listener using the callback registration mechanism
            logger.info("Using callback registration for events")
            
            # Define a callback that will handle all events
            async def event_callback(event_type, event_data):
                # Create an event-like object for compatibility
                class EventObj:
                    def __init__(self, type_name, data):
                        self.eventType = type_name
                        self.eventData = data
                
                event = EventObj(event_type, event_data)
                await self._process_event(event)
            
            # Store the callback for later cleanup during disconnect
            self._event_callback = event_callback
            
            # Register our callback for all events
            try:
                self.client.register_event_callback(event_callback)
                logger.info("Event callback registered")
            except Exception as e:
                logger.error(f"Error registering event callback: {e}")
                self._event_callback = None
                return
            
            # Create a dummy task to keep track of the listener state
            self._event_listener_task = asyncio.create_task(self._dummy_listener())
            return
        
        # Fall back to error if no suitable methods found
        logger.warning(f"No event receiving method found. Available methods: {sorted(available_methods)}")
        logger.error("Could not start event listener: no appropriate event method found")
    
    async def _dummy_listener(self):
        """A dummy listener task to keep track of the listener state."""
        logger.debug("Dummy event listener started")
        try:
            # Just wait until cancelled
            while self.connected and self.client is not None:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.debug("Dummy event listener cancelled")
        finally:
            self._event_listener_task = None
            logger.debug("Dummy event listener stopped")
    
    async def _process_event(self, event):
        """
        Process an event from OBS WebSocket and dispatch it to registered callbacks.
        
        Args:
            event: The event received from OBS WebSocket
        """
        # Log the event type for debugging
        logger.debug(f"Processing event of type {type(event).__name__}")
        
        # Check if we have a proper event object
        if not event:
            logger.warning("Received empty event")
            return
        
        # Handle different event formats
        event_type = None
        event_data = {}
        
        # Try to extract event type
        if hasattr(event, 'eventType'):
            event_type = event.eventType
        elif isinstance(event, dict) and 'eventType' in event:
            event_type = event['eventType']
        elif isinstance(event, dict) and 'op' in event and event['op'] == 5 and 'd' in event:
            # Direct WebSocket format
            if 'eventType' in event['d']:
                event_type = event['d']['eventType']
                if 'eventData' in event['d']:
                    event_data = event['d']['eventData']
        
        if not event_type:
            logger.warning(f"Could not determine event type from event: {event}")
            # Log the event structure to help debugging
            if hasattr(event, '__dict__'):
                logger.debug(f"Event attributes: {event.__dict__}")
            return
            
        # Try to get event data
        if not event_data:
            if hasattr(event, 'eventData'):
                event_data = event.eventData
            elif isinstance(event, dict) and 'eventData' in event:
                event_data = event['eventData']
        
        logger.debug(f"Event type: {event_type}, data: {event_data}")
        
        # Check if there are callbacks registered for this event type
        if event_type in self.event_callbacks:
            # Call each registered callback with the event data
            logger.debug(f"Found {len(self.event_callbacks[event_type])} callbacks for event {event_type}")
            for callback in self.event_callbacks[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    logger.error(f"Error in event callback for {event_type}: {str(e)}")
        else:
            logger.debug(f"No callbacks registered for event {event_type}")
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the OBS WebSocket server.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        logger.info("Starting disconnection process - SIMPLIFIED VERSION")
        
        # If not connected, warn and return success
        if not self.connected or self.client is None:
            logger.warning("Not connected to OBS WebSocket")
            return True
            
        # Save state locally - we'll clear all class state first
        temp_client = self.client
        temp_callback = self._event_callback
        temp_task = self._event_listener_task
        
        # IMMEDIATELY clear all state - this breaks any links that could cause issues
        self.client = None
        self.connected = False
        self._event_callback = None
        self._event_listener_task = None
        
        # Cancel any running task
        if temp_task is not None:
            try:
                temp_task.cancel()
            except:
                logger.debug("Failed to cancel event listener task")
        
        # Now handle the actual client
        try:
            if temp_client is not None:
                # Deregister callback if possible
                if hasattr(temp_client, 'deregister_event_callback') and temp_callback:
                    try:
                        temp_client.deregister_event_callback(temp_callback)
                    except Exception as e:
                        logger.error(f"Error deregistering callback: {e}")
                
                # Call disconnect if it exists
                if hasattr(temp_client, 'disconnect') and callable(getattr(temp_client, 'disconnect')):
                    try:
                        await temp_client.disconnect()
                    except Exception as e:
                        logger.error(f"Error during client disconnect: {e}")
                        return False
                
                # Direct connection close
                if hasattr(temp_client, '_connection') and temp_client._connection:
                    try:
                        if hasattr(temp_client._connection, 'close'):
                            # Just try to close - don't wait
                            temp_client._connection.close(code=1000, reason="Disconnect")
                    except Exception as e:
                        logger.error(f"Error during direct connection close: {e}")
            
            logger.info("Disconnection complete - connection state fully reset")
            return True
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            return False
    
    async def send_request(self, request_type: str, request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a request to the OBS WebSocket server.
        
        Args:
            request_type: The type of request to send
            request_data: The data to send with the request (optional)
            
        Returns:
            Dict[str, Any]: The response data
            
        Raises:
            RuntimeError: If not connected to OBS WebSocket
            Exception: If the request fails
        """
        if not self.connected or self.client is None:
            raise RuntimeError("Not connected to OBS WebSocket")
        
        # Create the request
        request = simpleobsws.Request(request_type, request_data)
        
        # Send the request
        response = await self.client.call(request)
        
        # Check if the request succeeded
        if not response.ok():
            raise Exception(f"Request failed: {response.requestStatus.code} {response.requestStatus.comment}")
        
        # Return the response data
        return response.responseData
    
    def register_event_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: The type of event to listen for
            callback: The callback function to call when the event is received
        """
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        
        self.event_callbacks[event_type].append(callback)
        
    def unregister_event_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Unregister a callback for a specific event type.
        
        Args:
            event_type: The type of event to stop listening for
            callback: The callback function to unregister
            
        Returns:
            bool: True if the callback was unregistered, False otherwise
        """
        if event_type not in self.event_callbacks:
            return False
        
        if callback not in self.event_callbacks[event_type]:
            return False
        
        self.event_callbacks[event_type].remove(callback)
        return True
    
    # Example of specific request methods that could be implemented for convenience
    
    async def get_version(self) -> Dict[str, Any]:
        """
        Get the version of OBS Studio and obs-websocket.
        
        Returns:
            Dict[str, Any]: Version information
        """
        return await self.send_request("GetVersion")
    
    async def get_scene_list(self) -> Dict[str, Any]:
        """
        Get the list of scenes in OBS Studio.
        
        Returns:
            Dict[str, Any]: Scene list information
        """
        return await self.send_request("GetSceneList")
    
    async def set_current_scene(self, scene_name: str) -> Dict[str, Any]:
        """
        Set the current scene in OBS Studio.
        
        Args:
            scene_name: The name of the scene to set as current
            
        Returns:
            Dict[str, Any]: Response data
        """
        return await self.send_request("SetCurrentProgramScene", {"sceneName": scene_name})
    
    async def start_streaming(self) -> Dict[str, Any]:
        """
        Start streaming in OBS Studio.
        
        Returns:
            Dict[str, Any]: Response data
        """
        return await self.send_request("StartStreaming")
    
    async def stop_streaming(self) -> Dict[str, Any]:
        """
        Stop streaming in OBS Studio.
        
        Returns:
            Dict[str, Any]: Response data
        """
        return await self.send_request("StopStreaming")
        
    # Source control methods
    
    async def set_source_visibility(self, scene_name: str, source_name: str, enabled: bool) -> Dict[str, Any]:
        """
        Set the visibility of a source in a scene.
        
        Args:
            scene_name: The name of the scene containing the source
            source_name: The name of the source to modify
            enabled: Whether the source should be visible (True) or hidden (False)
            
        Returns:
            Dict[str, Any]: Response data
        """
        # First, we need to get the scene item ID for the source
        scene_item_id = await self._get_scene_item_id(scene_name, source_name)
        
        # Then we can set its enabled state
        return await self.send_request("SetSceneItemEnabled", {
            "sceneName": scene_name,
            "sceneItemId": scene_item_id,
            "sceneItemEnabled": enabled
        })
    
    async def _get_scene_item_id(self, scene_name: str, source_name: str) -> int:
        """
        Get the scene item ID for a source in a scene.
        
        Args:
            scene_name: The name of the scene containing the source
            source_name: The name of the source
            
        Returns:
            int: The scene item ID
            
        Raises:
            Exception: If the source is not found in the scene
        """
        # Get the list of scene items in the scene
        response = await self.send_request("GetSceneItemList", {
            "sceneName": scene_name
        })
        
        # Find the scene item with the matching name
        for item in response.get("sceneItems", []):
            if item.get("sourceName") == source_name:
                return item.get("sceneItemId")
        
        # If we get here, the source was not found
        raise Exception(f"Source '{source_name}' not found in scene '{scene_name}'")
    
    async def set_source_settings(self, source_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the settings of a source.
        
        Args:
            source_name: The name of the source
            settings: The settings to update
            
        Returns:
            Dict[str, Any]: Response data
        """
        return await self.send_request("SetInputSettings", {
            "inputName": source_name,
            "inputSettings": settings
        })
    
    async def set_browser_source_url(self, source_name: str, url: str) -> Dict[str, Any]:
        """
        Set the URL of a browser source.
        
        Args:
            source_name: The name of the browser source
            url: The new URL
            
        Returns:
            Dict[str, Any]: Response data
        """
        return await self.set_source_settings(source_name, {
            "url": url
        })
        
    async def refresh_browser_source(self, source_name: str) -> Dict[str, Any]:
        """
        Refresh a browser source.
        
        Args:
            source_name: The name of the browser source
            
        Returns:
            Dict[str, Any]: Response data
        """
        return await self.send_request("PressInputPropertiesButton", {
            "inputName": source_name,
            "propertyName": "refreshnocache"
        })
    
    async def force_disconnect(self) -> bool:
        """
        Force disconnect from the OBS WebSocket server, cleaning up all resources.
        Use this when normal disconnect fails.
        
        Returns:
            bool: Always True as we forcibly clean up all resources
        """
        logger.warning("Performing forced disconnection")
        
        # Mark as disconnected immediately
        self.connected = False
        
        # Handle event listener cleanup
        if self._event_listener_task is not None:
            try:
                self._event_listener_task.cancel()
            except:
                pass
            self._event_listener_task = None
        
        # Handle client cleanup
        if self.client:
            try:
                # Try direct websocket closure if available
                if hasattr(self.client, '_connection') and self.client._connection:
                    try:
                        if hasattr(self.client._connection, 'close'):
                            # Try to close on current event loop if running
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # Schedule the close but don't wait for it
                                    asyncio.create_task(self.client._connection.close(code=1000, reason="Force disconnect"))
                                    await asyncio.sleep(0.1)  # Give it a moment
                            except:
                                pass
                    except:
                        pass
            except:
                pass
            
            # Set client to None regardless of success
            self.client = None
        
        # Clear event callback
        self._event_callback = None
        
        logger.info("Forced disconnection complete")
        return True
    
    def reset_connection(self):
        """
        Reset the connection state completely.
        This method is synchronous and immediately clears all connection state.
        """
        logger.warning("Forcibly resetting connection state")
        
        # First save the client locally
        client = self.client
        
        # Clear event listener
        if self._event_listener_task is not None:
            try:
                self._event_listener_task.cancel()
            except:
                pass
            self._event_listener_task = None
        
        # Clear client and connection state
        self.client = None
        self.connected = False
        self._event_callback = None
        
        # Now attempt to close the client's connection if it exists
        if client and hasattr(client, '_connection') and client._connection:
            try:
                # We can't await this in a sync method, so just access and clear
                client._connection = None
            except:
                pass
        
        logger.info("Connection completely reset")
    
    def force_disconnect_and_destroy(self):
        """
        Forcibly terminate and destroy all connection state.
        This is the most aggressive way to ensure disconnection.
        """
        logger.warning("FORCED TERMINATION of all connections")
        
        # First reset everything
        self.reset_connection()
        
        # Now destroy even more aggressively
        try:
            # Force garbage collection 
            import gc
            gc.collect()
        except:
            pass
            
        logger.info("Connection forcibly terminated")
        return True 