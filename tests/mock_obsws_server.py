import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable

import websockets

# Set up logging
logger = logging.getLogger(__name__)

class MockOBSWebSocketServer:
    """A mock OBS WebSocket server for testing purposes."""
    
    def __init__(self, host: str = "localhost", port: int = 4455, password: str = ""):
        """
        Initialize the mock OBS WebSocket server.
        
        Args:
            host: The hostname to bind to
            port: The port to bind to
            password: The password to require for authentication (empty for no auth)
        """
        self.host = host
        self.port = port
        self.password = password
        self.server = None
        self.running = False
        self.clients = set()
        self.event_handlers = {}
        self.request_handlers = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    async def start(self):
        """Start the WebSocket server."""
        if self.running:
            logger.warning("Server is already running")
            return
        
        self.server = await websockets.serve(self._handle_client, self.host, self.port)
        self.running = True
        logger.info(f"Mock OBS WebSocket server started on ws://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the WebSocket server."""
        if not self.running:
            logger.warning("Server is not running")
            return
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        
        self.running = False
        logger.info("Mock OBS WebSocket server stopped")
    
    def register_request_handler(self, request_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Register a handler for a specific request type.
        
        Args:
            request_type: The type of request to handle
            handler: The handler function that takes a request and returns a response
        """
        self.request_handlers[request_type] = handler
        logger.debug(f"Registered handler for request type: {request_type}")
    
    def _register_default_handlers(self):
        """Register default handlers for common requests."""
        # GetVersion
        self.register_request_handler("GetVersion", self._handle_get_version)
        
        # GetSceneList
        self.register_request_handler("GetSceneList", self._handle_get_scene_list)
        
        # SetCurrentProgramScene
        self.register_request_handler("SetCurrentProgramScene", self._handle_set_current_program_scene)
    
    def _handle_get_version(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GetVersion request."""
        return {
            "obsVersion": "30.0.0",
            "obsWebSocketVersion": "5.0.0",
            "rpcVersion": 1,
            "platform": "windows",
            "platformDescription": "Windows 10.0.19042"
        }
    
    def _handle_get_scene_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GetSceneList request."""
        return {
            "currentProgramSceneName": "Scene 1",
            "currentPreviewSceneName": "Scene 2",
            "scenes": [
                {"sceneName": "Scene 1", "sceneIndex": 0},
                {"sceneName": "Scene 2", "sceneIndex": 1},
                {"sceneName": "Scene 3", "sceneIndex": 2}
            ]
        }
    
    def _handle_set_current_program_scene(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SetCurrentProgramScene request."""
        # Just return an empty response for success
        return {}
    
    async def _handle_client(self, websocket):
        """Handle a client connection."""
        try:
            # Add the client to the set
            self.clients.add(websocket)
            client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if hasattr(websocket, "remote_address") else "unknown"
            logger.info(f"Client connected from {client_addr}")
            
            # Handle the client's messages
            async for message in websocket:
                await self._handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if hasattr(websocket, "remote_address") else "unknown"
            logger.info(f"Client disconnected from {client_addr}")
        
        finally:
            # Remove the client from the set
            self.clients.remove(websocket)
    
    async def _handle_message(self, websocket, message):
        """Handle a message from a client."""
        try:
            data = json.loads(message)
            
            # Authentication request
            if "op" in data and data["op"] == 1:
                await self._handle_auth(websocket, data)
                return
            
            # Regular request
            if "op" in data and data["op"] == 6 and "d" in data:
                request_data = data["d"]
                request_id = request_data.get("requestId")
                request_type = request_data.get("requestType")
                
                if request_type:
                    await self._handle_request(websocket, request_id, request_type, request_data)
                    return
            
            # Unknown message type
            logger.warning(f"Unknown message type: {data}")
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    async def _handle_auth(self, websocket, data):
        """Handle an authentication request."""
        # Send authentication response with success
        response = {
            "op": 2,
            "d": {
                "negotiatedRpcVersion": 1
            }
        }
        
        await websocket.send(json.dumps(response))
        logger.info("Sent authentication response")
    
    async def _handle_request(self, websocket, request_id, request_type, request_data):
        """Handle a regular request."""
        response_data = {}
        
        # Call the handler for this request type if it exists
        if request_type in self.request_handlers:
            try:
                handler = self.request_handlers[request_type]
                response_data = handler(request_data)
            except Exception as e:
                logger.error(f"Error in request handler for {request_type}: {str(e)}")
                # Send an error response
                await self._send_error_response(websocket, request_id, 8, f"Error: {str(e)}")
                return
        else:
            logger.warning(f"No handler for request type: {request_type}")
            # Send an error response
            await self._send_error_response(websocket, request_id, 9, f"Unknown request type: {request_type}")
            return
        
        # Send the response
        response = {
            "op": 7,
            "d": {
                "requestType": request_type,
                "requestId": request_id,
                "requestStatus": {
                    "result": True,
                    "code": 100
                },
                "responseData": response_data
            }
        }
        
        await websocket.send(json.dumps(response))
        logger.debug(f"Sent response for request {request_type} ({request_id})")
    
    async def _send_error_response(self, websocket, request_id, code, comment):
        """Send an error response."""
        response = {
            "op": 7,
            "d": {
                "requestId": request_id,
                "requestStatus": {
                    "result": False,
                    "code": code,
                    "comment": comment
                }
            }
        }
        
        await websocket.send(json.dumps(response))
        logger.debug(f"Sent error response for request {request_id}: {code} - {comment}")
    
    async def send_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Send an event to all connected clients.
        
        Args:
            event_type: The type of event
            event_data: The event data
        """
        if not self.clients:
            logger.debug(f"No clients connected to send event {event_type}")
            return
        
        event = {
            "op": 5,
            "d": {
                "eventType": event_type,
                "eventData": event_data,
                "eventIntent": 1
            }
        }
        
        message = json.dumps(event)
        
        await asyncio.gather(*[client.send(message) for client in self.clients])
        logger.debug(f"Sent event {event_type} to {len(self.clients)} clients")


async def run_server(host="localhost", port=4455, password=""):
    """Run a standalone WebSocket server for testing."""
    server = MockOBSWebSocketServer(host, port, password)
    await server.start()
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run the server
    asyncio.run(run_server()) 