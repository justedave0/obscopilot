import asyncio
import pytest
import threading
import time
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock

from services.obs_websocket import OBSWebSocketService
from tests.mock_obsws_server import MockOBSWebSocketServer

# Test constants
TEST_HOST = "localhost"
TEST_PORT = 4455
TEST_PASSWORD = "testpassword"
TEST_SCENE_NAME = "Scene 1"

class TestOBSWebSocketService:
    @pytest.fixture
    async def mock_server(self):
        """Fixture that provides a mock OBS WebSocket server."""
        server = MockOBSWebSocketServer(TEST_HOST, TEST_PORT, TEST_PASSWORD)
        await server.start()
        yield server
        await server.stop()
    
    @pytest.fixture
    def obs_service(self):
        """Fixture that provides an OBS WebSocket service."""
        return OBSWebSocketService()
    
    @pytest.mark.asyncio
    async def test_connect_success(self, obs_service):
        """Test connecting to the WebSocket server successfully."""
        # Create a mock client with the needed methods and properties
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.wait_until_identified = AsyncMock()
        mock_client.is_identified = MagicMock(return_value=True)
        
        with patch("services.obs_websocket.FixedWebSocketClient", return_value=mock_client), \
             patch("simpleobsws.IdentificationParameters", return_value=MagicMock()):
            # Connect to the server
            result = await obs_service.connect(TEST_HOST, TEST_PORT, TEST_PASSWORD)
            
            # Check that the connection was successful
            assert result is True
            assert obs_service.connected is True
            # client can be different than our mock since connect clears and recreates it
            # just verify it exists
            assert obs_service.client is not None
            assert obs_service.connection_params["host"] == TEST_HOST
            assert obs_service.connection_params["port"] == TEST_PORT
            assert obs_service.connection_params["password"] == TEST_PASSWORD
            
            # Verify wait_until_identified was called
            mock_client.wait_until_identified.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_already_connected(self, obs_service):
        """Test connecting when already connected."""
        # Manually set connected to True
        obs_service.connected = True
        obs_service.client = MagicMock()  # Need to set client too
        
        # Try to connect again
        with patch("services.obs_websocket.logger.warning") as mock_warning:
            result = await obs_service.connect(TEST_HOST, TEST_PORT, TEST_PASSWORD)
            
            # Check that a warning was logged
            mock_warning.assert_called_once_with("Already connected to OBS WebSocket")
        
        # Check that the connection was successful (reused the existing connection)
        assert result is True
        assert obs_service.connected is True
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, obs_service):
        """Test connecting to a server that doesn't exist."""
        # Mock simpleobsws to raise an exception
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=Exception("Failed to connect"))
        
        with patch("services.obs_websocket.FixedWebSocketClient", return_value=mock_client), \
             patch("simpleobsws.IdentificationParameters", return_value=MagicMock()):
            # Try to connect to a non-existent server
            result = await obs_service.connect(TEST_HOST, TEST_PORT, TEST_PASSWORD)
            
            # Check that the connection failed
            assert result is False
            assert obs_service.connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect_success(self, obs_service):
        """Test disconnecting from the WebSocket server successfully."""
        # Create a mock client
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        
        # Set up the service with the mock client
        obs_service.client = mock_client
        obs_service.connected = True
        
        # Disconnect from the server
        result = await obs_service.disconnect()
        
        # Check that the disconnection was successful
        assert result is True
        assert obs_service.connected is False
        
        # Verify that disconnect was called
        mock_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self, obs_service):
        """Test disconnecting when not connected."""
        # Make sure connected is False
        obs_service.connected = False
        obs_service.client = None
        
        # Try to disconnect when not connected
        with patch("services.obs_websocket.logger") as mock_logger:
            result = await obs_service.disconnect()
            
            # Check that a warning was logged
            mock_logger.warning.assert_called_once_with("Not connected to OBS WebSocket")
        
        # Check that the disconnection was "successful" (since we weren't connected)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_disconnect_failure(self, obs_service):
        """Test disconnecting failure."""
        # Create a mock client that raises an exception on disconnect
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock(side_effect=Exception("Test exception"))
        
        # Set up the service with the mock client
        obs_service.client = mock_client
        obs_service.connected = True
        
        # Try to disconnect
        with patch("services.obs_websocket.logger") as mock_logger:
            result = await obs_service.disconnect()
            
            # Check that an error was logged
            mock_logger.error.assert_called_once()
        
        # Check that the disconnection failed
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_request_not_connected(self, obs_service):
        """Test sending a request when not connected."""
        # Make sure connected is False
        obs_service.connected = False
        obs_service.client = None
        
        # Try to send a request when not connected
        with pytest.raises(RuntimeError, match="Not connected to OBS WebSocket"):
            await obs_service.send_request("GetVersion")
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, obs_service):
        """Test sending a request successfully."""
        # Create a mock request object and response
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.ok.return_value = True
        mock_response.responseData = {"obsVersion": "30.0.0"}
        
        # Create a mock client
        mock_client = MagicMock()
        mock_client.call = AsyncMock(return_value=mock_response)
        
        # Set up the service with the mock client
        obs_service.client = mock_client
        obs_service.connected = True
        
        # Mock the simpleobsws.Request class
        with patch("simpleobsws.Request", return_value=mock_request):
            # Send a request
            response = await obs_service.send_request("GetVersion")
            
            # Check that the response contains the expected data
            assert "obsVersion" in response
            assert response["obsVersion"] == "30.0.0"
            
            # Verify that call was called with the mock request
            mock_client.call.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_send_request_failure(self, obs_service):
        """Test sending a request that fails."""
        # Create a mock request object and response
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.ok.return_value = False
        mock_response.requestStatus.code = 404
        mock_response.requestStatus.comment = "Not found"
        
        # Create a mock client
        mock_client = MagicMock()
        mock_client.call = AsyncMock(return_value=mock_response)
        
        # Set up the service with the mock client
        obs_service.client = mock_client
        obs_service.connected = True
        
        # Mock the simpleobsws.Request class
        with patch("simpleobsws.Request", return_value=mock_request):
            # Try to send a request
            with pytest.raises(Exception, match="Request failed: 404 Not found"):
                await obs_service.send_request("GetVersion")
                
            # Verify that call was called with the mock request
            mock_client.call.assert_called_once_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_get_version(self, obs_service):
        """Test the get_version convenience method."""
        # Mock the send_request method
        response_data = {"obsVersion": "30.0.0"}
        obs_service.send_request = AsyncMock(return_value=response_data)
        
        # Call get_version
        response = await obs_service.get_version()
        
        # Check that the response contains the expected data
        assert "obsVersion" in response
        assert response["obsVersion"] == "30.0.0"
        
        # Verify that send_request was called with the correct request type
        obs_service.send_request.assert_called_once_with("GetVersion")
    
    @pytest.mark.asyncio
    async def test_get_scene_list(self, obs_service):
        """Test the get_scene_list convenience method."""
        # Mock the send_request method
        response_data = {
            "currentProgramSceneName": "Scene 1",
            "scenes": [
                {"sceneName": "Scene 1", "sceneIndex": 0},
                {"sceneName": "Scene 2", "sceneIndex": 1},
                {"sceneName": "Scene 3", "sceneIndex": 2}
            ]
        }
        obs_service.send_request = AsyncMock(return_value=response_data)
        
        # Call get_scene_list
        response = await obs_service.get_scene_list()
        
        # Check that the response contains the expected data
        assert "scenes" in response
        assert len(response["scenes"]) == 3
        assert response["scenes"][0]["sceneName"] == "Scene 1"
        
        # Verify that send_request was called with the correct request type
        obs_service.send_request.assert_called_once_with("GetSceneList")
    
    @pytest.mark.asyncio
    async def test_set_current_scene(self, obs_service):
        """Test the set_current_scene convenience method."""
        # Mock the send_request method
        response_data = {}
        obs_service.send_request = AsyncMock(return_value=response_data)
        
        # Call set_current_scene
        response = await obs_service.set_current_scene(TEST_SCENE_NAME)
        
        # Check that the response is empty (success)
        assert response == {}
        
        # Verify that send_request was called with the correct request type and data
        obs_service.send_request.assert_called_once_with("SetCurrentProgramScene", {"sceneName": TEST_SCENE_NAME})
    
    @pytest.mark.asyncio
    async def test_start_streaming(self, obs_service):
        """Test the start_streaming convenience method."""
        # Mock the send_request method
        response_data = {}
        obs_service.send_request = AsyncMock(return_value=response_data)
        
        # Call start_streaming
        response = await obs_service.start_streaming()
        
        # Check that the response is empty (success)
        assert response == {}
        
        # Verify that send_request was called with the correct request type
        obs_service.send_request.assert_called_once_with("StartStreaming")
    
    @pytest.mark.asyncio
    async def test_stop_streaming(self, obs_service):
        """Test the stop_streaming convenience method."""
        # Mock the send_request method
        response_data = {}
        obs_service.send_request = AsyncMock(return_value=response_data)
        
        # Call stop_streaming
        response = await obs_service.stop_streaming()
        
        # Check that the response is empty (success)
        assert response == {}
        
        # Verify that send_request was called with the correct request type
        obs_service.send_request.assert_called_once_with("StopStreaming")
    
    def test_event_callbacks(self, obs_service):
        """Test registering and unregistering event callbacks."""
        # Define a test callback
        def test_callback(data):
            pass
        
        # Register the callback
        obs_service.register_event_callback("SceneChanged", test_callback)
        
        # Check that the callback was registered
        assert "SceneChanged" in obs_service.event_callbacks
        assert test_callback in obs_service.event_callbacks["SceneChanged"]
        
        # Unregister the callback
        result = obs_service.unregister_event_callback("SceneChanged", test_callback)
        
        # Check that the callback was unregistered
        assert result is True
        assert test_callback not in obs_service.event_callbacks["SceneChanged"]
    
    def test_unregister_nonexistent_event(self, obs_service):
        """Test unregistering a callback for a nonexistent event."""
        # Define a test callback
        def test_callback(data):
            pass
        
        # Try to unregister a callback for a nonexistent event
        result = obs_service.unregister_event_callback("NonexistentEvent", test_callback)
        
        # Check that the unregistration failed
        assert result is False
    
    def test_unregister_nonexistent_callback(self, obs_service):
        """Test unregistering a nonexistent callback."""
        # Define test callbacks
        def test_callback1(data):
            pass
        
        def test_callback2(data):
            pass
        
        # Register callback1
        obs_service.register_event_callback("SceneChanged", test_callback1)
        
        # Try to unregister callback2
        result = obs_service.unregister_event_callback("SceneChanged", test_callback2)
        
        # Check that the unregistration failed
        assert result is False

    @pytest.mark.asyncio
    async def test_fixed_websocket_client_disconnect(self):
        """Test the FixedWebSocketClient's disconnect method."""
        from services.obs_websocket import FixedWebSocketClient
        
        # Create a mock connection
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connection.close = AsyncMock()
        
        # Create a FixedWebSocketClient with the mock connection
        client = FixedWebSocketClient("ws://localhost:4455")
        client._connection = mock_connection
        
        # Call the disconnect method
        result = await client.disconnect()
        
        # Check that the result is True
        assert result is True
        
        # Check that close was called on the connection
        mock_connection.close.assert_called_once_with(code=1000, reason="Disconnect")
        
        # Check that the connection state was cleared
        assert client._connection is None
        assert client._identified is False
    
    @pytest.mark.asyncio
    async def test_fixed_websocket_client_disconnect_no_connection(self):
        """Test the FixedWebSocketClient's disconnect method with no connection."""
        from services.obs_websocket import FixedWebSocketClient
        
        # Create a FixedWebSocketClient with no connection
        client = FixedWebSocketClient("ws://localhost:4455")
        client._connection = None
        
        # Call the disconnect method
        result = await client.disconnect()
        
        # Check that the result is True
        assert result is True
        
        # Check that the connection state was cleared
        assert client._connection is None
        assert client._identified is False
    
    @pytest.mark.asyncio
    async def test_fixed_websocket_client_disconnect_closed_connection(self):
        """Test the FixedWebSocketClient's disconnect method with a closed connection."""
        from services.obs_websocket import FixedWebSocketClient
        
        # Create a mock connection that's already closed
        mock_connection = MagicMock()
        mock_connection.closed = True
        
        # Create a FixedWebSocketClient with the mock connection
        client = FixedWebSocketClient("ws://localhost:4455")
        client._connection = mock_connection
        
        # Call the disconnect method
        result = await client.disconnect()
        
        # Check that the result is True
        assert result is True
        
        # Check that the connection state was cleared
        assert client._connection is None
        assert client._identified is False
    
    @pytest.mark.asyncio
    async def test_fixed_websocket_client_disconnect_error(self):
        """Test the FixedWebSocketClient's disconnect method with an error."""
        from services.obs_websocket import FixedWebSocketClient
        
        # Create a mock connection that raises an exception
        mock_connection = MagicMock()
        mock_connection.closed = False
        mock_connection.close = AsyncMock(side_effect=Exception("Test exception"))
        
        # Create a FixedWebSocketClient with the mock connection
        client = FixedWebSocketClient("ws://localhost:4455")
        client._connection = mock_connection
        
        # Call the disconnect method
        result = await client.disconnect()
        
        # Check that the result is True (it always returns True)
        assert result is True
        
        # Check that the connection state was cleared
        assert client._connection is None
        assert client._identified is False
    
    @pytest.mark.asyncio
    async def test_force_disconnect(self, obs_service):
        """Test forcing a disconnect."""
        # Set up the service with a mock client
        mock_client = MagicMock()
        mock_connection = MagicMock()
        mock_client._connection = mock_connection
        
        obs_service.client = mock_client
        obs_service.connected = True
        obs_service._event_listener_task = MagicMock()
        obs_service._event_listener_task.cancel = MagicMock()
        
        # Force disconnect
        result = await obs_service.force_disconnect()
        
        # Check that the result is True
        assert result is True
        
        # Check that the connection state was cleared
        assert obs_service.connected is False
        assert obs_service.client is None
        assert obs_service._event_listener_task is None
    
    def test_reset_connection(self, obs_service):
        """Test resetting the connection state."""
        # Set up the service with a mock client
        mock_client = MagicMock()
        mock_connection = MagicMock()
        mock_client._connection = mock_connection
        
        obs_service.client = mock_client
        obs_service.connected = True
        obs_service._event_listener_task = MagicMock()
        obs_service._event_listener_task.cancel = MagicMock()
        
        # Reset the connection
        obs_service.reset_connection()
        
        # Check that the connection state was cleared
        assert obs_service.connected is False
        assert obs_service.client is None
        assert obs_service._event_listener_task is None
    
    def test_force_disconnect_and_destroy(self, obs_service):
        """Test forcibly terminating and destroying the connection state."""
        # Set up the service with a mock client
        mock_client = MagicMock()
        obs_service.client = mock_client
        obs_service.connected = True
        
        # Mock the reset_connection method
        obs_service.reset_connection = MagicMock()
        
        # Force disconnect and destroy
        result = obs_service.force_disconnect_and_destroy()
        
        # Check that reset_connection was called
        obs_service.reset_connection.assert_called_once()
        
        # Check that the result is True
        assert result is True
    
    @pytest.mark.asyncio
    async def test_process_event(self, obs_service):
        """Test processing an event."""
        # Define a test callback
        callback_called = False
        def test_callback(data):
            nonlocal callback_called
            callback_called = True
            assert data == {"test": "data"}
        
        # Register the callback
        obs_service.register_event_callback("TestEvent", test_callback)
        
        # Create a test event
        class TestEvent:
            def __init__(self):
                self.eventType = "TestEvent"
                self.eventData = {"test": "data"}
        
        # Process the event
        await obs_service._process_event(TestEvent())
        
        # Check that the callback was called
        assert callback_called
    
    @pytest.mark.asyncio
    async def test_process_event_dict(self, obs_service):
        """Test processing an event that's a dictionary."""
        # Define a test callback
        callback_called = False
        def test_callback(data):
            nonlocal callback_called
            callback_called = True
            assert data == {"test": "data"}
        
        # Register the callback
        obs_service.register_event_callback("TestEvent", test_callback)
        
        # Create a test event as a dictionary
        event = {
            "eventType": "TestEvent",
            "eventData": {"test": "data"}
        }
        
        # Process the event
        await obs_service._process_event(event)
        
        # Check that the callback was called
        assert callback_called
    
    @pytest.mark.asyncio
    async def test_process_event_websocket_format(self, obs_service):
        """Test processing an event in direct WebSocket format."""
        # Define a test callback
        callback_called = False
        def test_callback(data):
            nonlocal callback_called
            callback_called = True
            assert data == {"test": "data"}
        
        # Register the callback
        obs_service.register_event_callback("TestEvent", test_callback)
        
        # Create a test event in WebSocket format
        event = {
            "op": 5,
            "d": {
                "eventType": "TestEvent",
                "eventData": {"test": "data"}
            }
        }
        
        # Process the event
        await obs_service._process_event(event)
        
        # Check that the callback was called
        assert callback_called
    
    @pytest.mark.asyncio
    async def test_process_event_no_callbacks(self, obs_service):
        """Test processing an event with no callbacks registered."""
        # Create a test event
        class TestEvent:
            def __init__(self):
                self.eventType = "TestEvent"
                self.eventData = {"test": "data"}
        
        # Process the event
        await obs_service._process_event(TestEvent())
        
        # No assertion needed - just checking that it doesn't raise an exception
    
    @pytest.mark.asyncio
    async def test_process_event_empty(self, obs_service):
        """Test processing an empty event."""
        # Process an empty event
        await obs_service._process_event(None)
        
        # No assertion needed - just checking that it doesn't raise an exception
    
    @pytest.mark.asyncio
    async def test_process_event_callback_error(self, obs_service):
        """Test processing an event where the callback raises an error."""
        # Define a test callback that raises an exception
        def test_callback(data):
            raise Exception("Test exception")
        
        # Register the callback
        obs_service.register_event_callback("TestEvent", test_callback)
        
        # Create a test event
        class TestEvent:
            def __init__(self):
                self.eventType = "TestEvent"
                self.eventData = {"test": "data"}
        
        # Process the event
        await obs_service._process_event(TestEvent())
        
        # No assertion needed - just checking that it doesn't raise an exception
    
    @pytest.mark.asyncio
    async def test_process_event_unknown_format(self, obs_service):
        """Test processing an event with an unknown format."""
        # Create a test event with no recognizable format
        event = {"unknown": "format"}
        
        # Process the event
        await obs_service._process_event(event)
        
        # No assertion needed - just checking that it doesn't raise an exception
    
    @pytest.mark.asyncio
    async def test_dummy_listener(self, obs_service):
        """Test the dummy event listener."""
        # Set up the service
        obs_service.connected = True
        obs_service.client = MagicMock()
        
        # Create an asyncio Future to signal when the dummy listener has run
        import asyncio
        done = asyncio.Future()
        
        # Override asyncio.sleep to immediately set the Future
        async def mock_sleep(seconds):
            if not done.done():
                done.set_result(None)
            raise asyncio.CancelledError()
            
        # Start the dummy listener with patched sleep
        with patch('asyncio.sleep', side_effect=mock_sleep):
            task = asyncio.create_task(obs_service._dummy_listener())
            
            # Wait for the sleep to be called
            await asyncio.wait_for(done, timeout=1.0)
            
            # Cancel the task
            task.cancel()
            
            # Wait for the task to complete
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_start_event_listener_already_running(self, obs_service):
        """Test starting the event listener when it's already running."""
        # Set up the service with a mock task
        obs_service._event_listener_task = MagicMock()
        obs_service.client = MagicMock()
        
        # Start the event listener
        obs_service._start_event_listener()
        
        # Check that the task wasn't recreated
        assert obs_service._event_listener_task is not None
    
    @pytest.mark.asyncio
    async def test_start_event_listener_with_callback_registration(self, obs_service):
        """Test starting the event listener with callback registration."""
        # Create a mock client with register_event_callback method
        mock_client = MagicMock()
        mock_client.register_event_callback = MagicMock()
        
        # Set up the service with the mock client
        obs_service.client = mock_client
        obs_service._event_listener_task = None
        
        # Mock asyncio.create_task
        with patch('asyncio.create_task') as mock_create_task:
            # Start the event listener
            obs_service._start_event_listener()
            
            # Check that register_event_callback was called
            mock_client.register_event_callback.assert_called_once()
            
            # Check that create_task was called
            mock_create_task.assert_called_once()
            
            # Check that _event_listener_task was set
            assert obs_service._event_callback is not None
    
    @pytest.mark.asyncio
    async def test_start_event_listener_registration_error(self, obs_service):
        """Test starting the event listener with an error during registration."""
        # Create a mock client that raises an exception on register_event_callback
        mock_client = MagicMock()
        mock_client.register_event_callback = MagicMock(side_effect=Exception("Test exception"))
        
        # Set up the service with the mock client
        obs_service.client = mock_client
        obs_service._event_listener_task = None
        
        # Start the event listener
        obs_service._start_event_listener()
        
        # Check that _event_callback was not set
        assert obs_service._event_callback is None
    
    @pytest.mark.asyncio
    async def test_start_event_listener_no_suitable_method(self, obs_service):
        """Test starting the event listener with no suitable method."""
        # Create a mock client with no register_event_callback method
        mock_client = MagicMock()
        
        # Set up the service with the mock client
        obs_service.client = mock_client
        obs_service._event_listener_task = None
        
        # Start the event listener
        with patch('services.obs_websocket.logger.warning') as mock_warning, \
             patch('services.obs_websocket.logger.error') as mock_error:
            obs_service._start_event_listener()
            
            # Check that errors were logged
            mock_error.assert_called_once_with("Could not start event listener: no appropriate event method found")
    
    @pytest.mark.asyncio
    async def test_set_source_visibility(self, obs_service):
        """Test setting a source's visibility."""
        # Mock _get_scene_item_id and send_request
        obs_service._get_scene_item_id = AsyncMock(return_value=123)
        obs_service.send_request = AsyncMock(return_value={"result": True})
        
        # Set the source visibility
        result = await obs_service.set_source_visibility("Scene 1", "Source 1", True)
        
        # Check that _get_scene_item_id was called with the correct arguments
        obs_service._get_scene_item_id.assert_called_once_with("Scene 1", "Source 1")
        
        # Check that send_request was called with the correct arguments
        obs_service.send_request.assert_called_once_with("SetSceneItemEnabled", {
            "sceneName": "Scene 1",
            "sceneItemId": 123,
            "sceneItemEnabled": True
        })
        
        # Check that the result is correct
        assert result == {"result": True}
    
    @pytest.mark.asyncio
    async def test_set_browser_source_url(self, obs_service):
        """Test setting a browser source's URL."""
        # Mock set_source_settings
        obs_service.set_source_settings = AsyncMock(return_value={"result": True})
        
        # Set the browser source URL
        result = await obs_service.set_browser_source_url("BrowserSource", "https://example.com")
        
        # Check that set_source_settings was called with the correct arguments
        obs_service.set_source_settings.assert_called_once_with("BrowserSource", {
            "url": "https://example.com"
        })
        
        # Check that the result is correct
        assert result == {"result": True}
    
    @pytest.mark.asyncio
    async def test_refresh_browser_source(self, obs_service):
        """Test refreshing a browser source."""
        # Mock send_request
        obs_service.send_request = AsyncMock(return_value={"result": True})
        
        # Refresh the browser source
        result = await obs_service.refresh_browser_source("BrowserSource")
        
        # Check that send_request was called with the correct arguments
        obs_service.send_request.assert_called_once_with("PressInputPropertiesButton", {
            "inputName": "BrowserSource",
            "propertyName": "refreshnocache"
        })
        
        # Check that the result is correct
        assert result == {"result": True} 