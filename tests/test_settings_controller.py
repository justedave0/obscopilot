import asyncio
import pytest
from unittest.mock import MagicMock, patch
import logging
import sys
import json

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QGroupBox, QFormLayout
from PyQt6.QtCore import Qt, QTimer

from ui.tabs.settings_controller import SettingsController, AsyncWorker

# Test constants
TEST_HOST = "localhost"
TEST_PORT = 4455
TEST_PASSWORD = "testpassword"

class TestSettingsController:
    @pytest.fixture
    def controller(self):
        """Fixture that provides a settings controller."""
        controller = SettingsController()
        return controller
    
    def test_init(self, controller):
        """Test initializing the controller."""
        assert controller.obs_service is not None
        assert isinstance(controller.threadpool, QThreadPool)
    
    @pytest.mark.asyncio
    async def test_connect_to_obs_success(self, controller):
        """Test connecting to OBS successfully."""
        # Mock the OBS service connect method
        controller.obs_service.connect = MagicMock(return_value=True)
        
        # Create mocks for the signal callbacks
        on_result_mock = MagicMock()
        on_error_mock = MagicMock()
        on_finished_mock = MagicMock()
        
        # Mock run_async to call the callbacks directly
        def mock_run_async(coro, host=None, port=None, password=None, on_result=None, on_error=None, on_finished=None):
            if on_result:
                on_result(True)
            if on_finished:
                on_finished()
        
        controller.run_async = MagicMock(side_effect=mock_run_async)
        
        # Connect to OBS
        controller.connect_to_obs(TEST_HOST, TEST_PORT, TEST_PASSWORD)
        
        # Check that run_async was called with the correct arguments
        controller.run_async.assert_called_once()
        args, kwargs = controller.run_async.call_args
        assert args[0] == controller.obs_service.connect
        assert kwargs["host"] == TEST_HOST
        assert kwargs["port"] == TEST_PORT
        assert kwargs["password"] == TEST_PASSWORD
    
    @pytest.mark.asyncio
    async def test_disconnect_from_obs_success(self, controller):
        """Test disconnecting from OBS successfully."""
        # Mock the OBS service disconnect method
        controller.obs_service.disconnect = MagicMock(return_value=True)
        
        # Create mocks for the signal callbacks
        on_result_mock = MagicMock()
        on_error_mock = MagicMock()
        on_finished_mock = MagicMock()
        
        # Mock run_async to call the callbacks directly
        def mock_run_async(coro, on_result=None, on_error=None, on_finished=None):
            if on_result:
                on_result(True)
            if on_finished:
                on_finished()
        
        controller.run_async = MagicMock(side_effect=mock_run_async)
        
        # Disconnect from OBS
        controller.disconnect_from_obs()
        
        # Check that run_async was called with the correct arguments
        controller.run_async.assert_called_once()
        args, kwargs = controller.run_async.call_args
        assert args[0] == controller.obs_service.disconnect
    
    def test_on_connect_result_success(self, controller):
        """Test handling a successful connect result."""
        # Mock the connection_successful signal
        controller.connection_successful = MagicMock()
        
        # Call _on_connect_result with True
        controller._on_connect_result(True)
        
        # Check that the signal was emitted
        controller.connection_successful.emit.assert_called_once()
    
    def test_on_connect_result_failure(self, controller):
        """Test handling a failed connect result."""
        # Mock the connection_failed signal
        controller.connection_failed = MagicMock()
        
        # Call _on_connect_result with False
        controller._on_connect_result(False)
        
        # Check that the signal was emitted
        controller.connection_failed.emit.assert_called_once_with("Failed to connect to OBS WebSocket. Please check your settings and try again.")
    
    def test_on_connect_error(self, controller):
        """Test handling an error during connect."""
        # Mock the connection_failed signal
        controller.connection_failed = MagicMock()
        
        # Call _on_connect_error with an error message
        error_message = "Test error"
        controller._on_connect_error(error_message)
        
        # Check that the signal was emitted
        controller.connection_failed.emit.assert_called_once_with(f"Error connecting to OBS WebSocket: {error_message}")
    
    def test_on_disconnect_result_success(self, controller):
        """Test handling a successful disconnect result."""
        # Mock the disconnection_successful signal
        controller.disconnection_successful = MagicMock()
        
        # Call _on_disconnect_result with True
        controller._on_disconnect_result(True)
        
        # Check that the signal was emitted
        controller.disconnection_successful.emit.assert_called_once()
    
    def test_on_disconnect_result_failure(self, controller):
        """Test handling a failed disconnect result."""
        # Mock the disconnection_failed signal
        controller.disconnection_failed = MagicMock()
        
        # Call _on_disconnect_result with False
        controller._on_disconnect_result(False)
        
        # Check that the signal was emitted
        controller.disconnection_failed.emit.assert_called_once_with("Failed to disconnect from OBS WebSocket")
    
    def test_on_disconnect_error(self, controller):
        """Test handling an error during disconnect."""
        # Mock the disconnection_failed signal
        controller.disconnection_failed = MagicMock()
        
        # Call _on_disconnect_error with an error message
        error_message = "Test error"
        controller._on_disconnect_error(error_message)
        
        # Check that the signal was emitted
        controller.disconnection_failed.emit.assert_called_once_with(f"Error disconnecting from OBS WebSocket: {error_message}")
    
    def test_is_connected(self, controller):
        """Test checking if connected."""
        # Set the connected state
        controller.obs_service.connected = True
        
        # Check that is_connected returns the correct value
        assert controller.is_connected() is True
        
        # Change the connected state
        controller.obs_service.connected = False
        
        # Check that is_connected returns the correct value
        assert controller.is_connected() is False
        
    def test_get_default_settings(self, controller):
        """Test getting default settings."""
        # Get default settings
        default_settings = controller._get_default_settings()
        
        # Check that the default settings are correct
        assert default_settings["obs_host"] == "localhost"
        assert default_settings["obs_port"] == 4455
        assert default_settings["obs_password"] == ""
        assert default_settings["auto_connect_enabled"] is False
    
    def test_load_settings_existing(self, controller):
        """Test loading settings from an existing file."""
        # Create a temp file with settings
        import tempfile
        import json
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create settings file
            settings_file = os.path.join(temp_dir, "settings.json")
            test_settings = {
                "obs_host": "example.com",
                "obs_port": 1234,
                "auto_connect_enabled": True
            }
            with open(settings_file, 'w') as f:
                json.dump(test_settings, f)
            
            # Patch settings file path and load_password_from_storage
            with patch('ui.tabs.settings_controller.SETTINGS_FILE', settings_file), \
                 patch.object(controller, '_load_password_from_storage', return_value="testpassword"), \
                 patch.object(controller, 'settings_loaded') as mock_signal:
                
                # Reset loaded flag
                controller._settings_loaded = False
                
                # Load settings
                controller.load_settings()
                
                # Check that settings were loaded correctly
                assert controller.settings["obs_host"] == "example.com"
                assert controller.settings["obs_port"] == 1234
                assert controller.settings["auto_connect_enabled"] is True
                assert controller.settings["obs_password"] == "testpassword"
                
                # Check that the signal was emitted
                mock_signal.emit.assert_called_once()
                
                # Check that the loaded flag was set
                assert controller._settings_loaded
    
    def test_load_settings_already_loaded(self, controller):
        """Test loading settings when they're already loaded."""
        # Set loaded flag
        controller._settings_loaded = True
        
        # Mock settings_loaded signal
        with patch.object(controller, 'settings_loaded') as mock_signal:
            # Load settings
            controller.load_settings()
            
            # Check that the signal was not emitted (settings were already loaded)
            mock_signal.emit.assert_not_called()
    
    def test_load_settings_nonexistent(self, controller):
        """Test loading settings from a non-existent file."""
        # Create a temp directory (without settings file)
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch settings file path and save_settings
            settings_file = os.path.join(temp_dir, "settings.json")
            with patch('ui.tabs.settings_controller.SETTINGS_FILE', settings_file), \
                 patch.object(controller, 'save_settings') as mock_save, \
                 patch.object(controller, 'settings_loaded') as mock_signal:
                
                # Reset loaded flag
                controller._settings_loaded = False
                
                # Load settings
                controller.load_settings()
                
                # Check that default settings were used
                default_settings = controller._get_default_settings()
                for key, value in default_settings.items():
                    if key != "obs_password":  # Password is loaded separately
                        assert controller.settings[key] == value
                
                # Check that save_settings was called
                mock_save.assert_called_once()
                
                # Check that the signal was emitted
                mock_signal.emit.assert_called_once()
    
    def test_load_settings_invalid_json(self, controller):
        """Test loading settings from a file with invalid JSON."""
        # Create a temp file with invalid JSON
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create settings file with invalid JSON
            settings_file = os.path.join(temp_dir, "settings.json")
            with open(settings_file, 'w') as f:
                f.write("invalid json")
            
            # Patch settings file path and save_settings
            with patch('ui.tabs.settings_controller.SETTINGS_FILE', settings_file), \
                 patch.object(controller, 'settings_loaded') as mock_signal:
                
                # Reset loaded flag
                controller._settings_loaded = False
                
                # Load settings
                controller.load_settings()
                
                # Check that default settings were used
                default_settings = controller._get_default_settings()
                for key, value in default_settings.items():
                    if key != "obs_password":  # Password is loaded separately
                        assert controller.settings[key] == value
                
                # Check that the signal was emitted
                mock_signal.emit.assert_called_once()
    
    def test_ensure_password_loaded_existing(self, controller):
        """Test ensuring password is loaded when it already exists."""
        # Set password in settings
        controller.settings["obs_password"] = "existing_password"
        
        # Ensure password is loaded
        controller._ensure_password_loaded()
        
        # Check that the password wasn't changed
        assert controller.settings["obs_password"] == "existing_password"
    
    def test_ensure_password_loaded_from_storage(self, controller):
        """Test ensuring password is loaded from storage."""
        # Remove password from settings
        if "obs_password" in controller.settings:
            del controller.settings["obs_password"]
        
        # Mock _load_password_from_storage
        with patch.object(controller, '_load_password_from_storage', return_value="loaded_password"):
            # Ensure password is loaded
            controller._ensure_password_loaded()
            
            # Check that the password was loaded
            assert controller.settings["obs_password"] == "loaded_password"
    
    def test_ensure_password_loaded_not_found(self, controller):
        """Test ensuring password is loaded when not found in storage."""
        # Remove password from settings
        if "obs_password" in controller.settings:
            del controller.settings["obs_password"]
        
        # Mock _load_password_from_storage to return None
        with patch.object(controller, '_load_password_from_storage', return_value=None):
            # Ensure password is loaded
            controller._ensure_password_loaded()
            
            # Check that an empty password was set
            assert controller.settings["obs_password"] == ""
    
    def test_load_password_from_storage_keyring(self, controller):
        """Test loading password from keyring."""
        # Mock keyring.get_password
        with patch('keyring.get_password', return_value="keyring_password"):
            # Load password
            password = controller._load_password_from_storage()
            
            # Check that the password was loaded from keyring
            assert password == "keyring_password"
    
    def test_load_password_from_storage_fallback(self, controller):
        """Test loading password from fallback file."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fallback file
            fallback_file = os.path.join(temp_dir, ".obspass")
            with open(fallback_file, 'w') as f:
                f.write("fallback_password")
            
            # Patch fallback file path and keyring
            with patch('ui.tabs.settings_controller.FALLBACK_PWD_FILE', fallback_file), \
                 patch('keyring.get_password', return_value=None), \
                 patch('keyring.set_password'):
                
                # Load password
                password = controller._load_password_from_storage()
                
                # Check that the password was loaded from fallback
                assert password == "fallback_password"
    
    def test_load_password_from_storage_not_found(self, controller):
        """Test loading password when not found anywhere."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch fallback file path and keyring
            fallback_file = os.path.join(temp_dir, ".obspass")
            with patch('ui.tabs.settings_controller.FALLBACK_PWD_FILE', fallback_file), \
                 patch('keyring.get_password', return_value=None):
                
                # Load password
                password = controller._load_password_from_storage()
                
                # Check that no password was loaded
                assert password is None
    
    def test_save_settings(self, controller):
        """Test saving settings to disk."""
        import tempfile
        import json
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch settings file path
            settings_file = os.path.join(temp_dir, "settings.json")
            with patch('ui.tabs.settings_controller.SETTINGS_FILE', settings_file):
                # Set some settings
                controller.settings = {
                    "obs_host": "example.com",
                    "obs_port": 1234,
                    "obs_password": "secret_password",
                    "auto_connect_enabled": True
                }
                
                # Save settings
                controller.save_settings()
                
                # Check that the file was created
                assert os.path.exists(settings_file)
                
                # Load and check saved settings
                with open(settings_file, 'r') as f:
                    saved_settings = json.load(f)
                
                # Check that settings were saved correctly
                assert saved_settings["obs_host"] == "example.com"
                assert saved_settings["obs_port"] == 1234
                assert saved_settings["auto_connect_enabled"] is True
                
                # Password should not be saved
                assert "obs_password" not in saved_settings
    
    def test_save_settings_debounce(self, controller):
        """Test debouncing rapid settings saves."""
        import tempfile
        import os
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch settings file path
            settings_file = os.path.join(temp_dir, "settings.json")
            with patch('ui.tabs.settings_controller.SETTINGS_FILE', settings_file):
                # Set _last_save_time to now
                controller._last_save_time = time.time()
                
                # Create mock for open to check if it's called
                with patch('builtins.open') as mock_open:
                    # Save settings
                    controller.save_settings()
                    
                    # Check that open was not called (debounced)
                    mock_open.assert_not_called()
    
    def test_save_password(self, controller):
        """Test saving password to settings."""
        # Directly set password in settings
        controller.save_password("new_password")
        
        # Check that the password was set in settings
        assert controller.settings["obs_password"] == "new_password"
    
    def test_save_password_to_keyring_success(self, controller):
        """Test saving password to keyring successfully."""
        # Mock keyring.set_password and keyring.get_password
        with patch('keyring.set_password'), \
             patch('keyring.get_password', return_value="test_password"):
            
            # Save password to keyring
            result = controller._save_password_to_keyring("test_password")
            
            # Check that the result is True
            assert result is True
    
    def test_save_password_to_keyring_empty(self, controller):
        """Test saving an empty password to keyring."""
        # Save empty password to keyring
        result = controller._save_password_to_keyring("")
        
        # Check that the result is False
        assert result is False
    
    def test_save_password_to_keyring_verification_failure(self, controller):
        """Test saving password to keyring with verification failure."""
        # Mock keyring.set_password and keyring.get_password to return a different password
        with patch('keyring.set_password'), \
             patch('keyring.get_password', return_value="wrong_password"), \
             patch('ui.tabs.settings_controller.logger.error') as mock_error, \
             patch('os.path.exists', return_value=False):  # Make fallback file not exist
            
            # Save password to keyring
            result = controller._save_password_to_keyring("test_password")
            
            # Based on the implementation, this returns False when verification fails
            assert result is False
            
            # Also check that the error was logged
            mock_error.assert_any_call("[FAIL] Password verification failed - stored value doesn't match")
    
    def test_save_password_to_keyring_exception(self, controller):
        """Test saving password to keyring with an exception."""
        # Mock keyring.set_password to raise an exception
        with patch('keyring.set_password', side_effect=Exception("Test exception")), \
             patch('ui.tabs.settings_controller.logger.error') as mock_error, \
             patch('os.path.exists', return_value=False):  # Make fallback file not exist
            
            # Save password to keyring
            result = controller._save_password_to_keyring("test_password")
            
            # Based on the implementation, it returns False when there's an exception
            assert result is False
            
            # Check error was logged
            mock_error.assert_any_call("[FAIL] Error saving password to keyring: Test exception")
    
    def test_set_auto_connect_enabled(self, controller):
        """Test enabling/disabling auto-connect."""
        import tempfile
        import json
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch settings file path
            settings_file = os.path.join(temp_dir, "settings.json")
            with patch('ui.tabs.settings_controller.SETTINGS_FILE', settings_file), \
                 patch.object(controller, 'save_settings'):
                
                # Set auto-connect to True
                result = controller.set_auto_connect_enabled(True)
                
                # Check that auto-connect was enabled
                assert controller.settings["auto_connect_enabled"] is True
                assert result is True
                
                # Set auto-connect to False
                result = controller.set_auto_connect_enabled(False)
                
                # Check that auto-connect was disabled
                assert controller.settings["auto_connect_enabled"] is False
                assert result is False
    
    def test_is_auto_connect_enabled(self, controller):
        """Test checking if auto-connect is enabled."""
        # Set auto-connect to True in memory
        controller.settings["auto_connect_enabled"] = True
        
        # Mock file operations to return the same value
        settings_file_data = {"auto_connect_enabled": True}
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(settings_file_data)
        mock_open.return_value = mock_file
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open), \
             patch('json.load', return_value=settings_file_data):
            
            # Check that is_auto_connect_enabled returns True
            assert controller.is_auto_connect_enabled() is True
        
        # Set auto-connect to False in memory
        controller.settings["auto_connect_enabled"] = False
        
        # Mock file operations to return the same value
        settings_file_data = {"auto_connect_enabled": False}
        mock_file.read.return_value = json.dumps(settings_file_data)
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open), \
             patch('json.load', return_value=settings_file_data):
            
            # Check that is_auto_connect_enabled returns False
            assert controller.is_auto_connect_enabled() is False
    
    def test_is_auto_connect_enabled_file_mismatch(self, controller):
        """Test checking auto-connect when memory and file settings disagree."""
        import tempfile
        import json
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create settings file with auto-connect enabled
            settings_file = os.path.join(temp_dir, "settings.json")
            with open(settings_file, 'w') as f:
                json.dump({"auto_connect_enabled": True}, f)
            
            # Patch settings file path
            with patch('ui.tabs.settings_controller.SETTINGS_FILE', settings_file):
                # Set auto-connect to False in memory
                controller.settings["auto_connect_enabled"] = False
                
                # Check that is_auto_connect_enabled returns True (from file)
                assert controller.is_auto_connect_enabled() is True
                
                # Check that memory setting was updated
                assert controller.settings["auto_connect_enabled"] is True
    
    def test_check_auto_connect_already_attempted(self, controller):
        """Test checking auto-connect when it's already been attempted."""
        # Set auto_connect_attempted flag
        controller.auto_connect_attempted = True
        
        # Mock connect_to_obs
        controller.connect_to_obs = MagicMock()
        
        # Check auto-connect
        controller._check_auto_connect()
        
        # Check that connect_to_obs was not called
        controller.connect_to_obs.assert_not_called()
    
    def test_check_auto_connect_already_connected(self, controller):
        """Test checking auto-connect when already connected."""
        # Reset auto_connect_attempted flag
        controller.auto_connect_attempted = False
        
        # Set connected state
        controller.obs_service.connected = True
        
        # Mock connect_to_obs
        controller.connect_to_obs = MagicMock()
        
        # Check auto-connect
        controller._check_auto_connect()
        
        # Check that connect_to_obs was not called
        controller.connect_to_obs.assert_not_called()
        
        # Check that the flag was set
        assert controller.auto_connect_attempted
    
    def test_check_auto_connect_disabled(self, controller):
        """Test checking auto-connect when disabled."""
        # Reset auto_connect_attempted flag
        controller.auto_connect_attempted = False
        
        # Set connected state and auto-connect setting
        controller.obs_service.connected = False
        controller.settings["auto_connect_enabled"] = False
        
        # Mock connect_to_obs
        controller.connect_to_obs = MagicMock()
        
        # Check auto-connect
        controller._check_auto_connect()
        
        # Check that connect_to_obs was not called
        controller.connect_to_obs.assert_not_called()
        
        # Check that the flag was set
        assert controller.auto_connect_attempted
    
    def test_check_auto_connect_missing_credentials(self, controller):
        """Test checking auto-connect with missing credentials."""
        # Reset auto_connect_attempted flag
        controller.auto_connect_attempted = False
        
        # Set connected state and auto-connect setting
        controller.obs_service.connected = False
        controller.settings["auto_connect_enabled"] = True
        controller.settings["obs_host"] = ""
        controller.settings["obs_port"] = 0
        
        # Mock connect_to_obs
        controller.connect_to_obs = MagicMock()
        
        # Check auto-connect
        controller._check_auto_connect()
        
        # Check that connect_to_obs was not called
        controller.connect_to_obs.assert_not_called()
        
        # Check that the flag was set
        assert controller.auto_connect_attempted
    
    def test_check_auto_connect_success(self, controller):
        """Test checking auto-connect successfully."""
        # Reset auto_connect_attempted flag
        controller.auto_connect_attempted = False
        
        # Set connected state and auto-connect setting
        controller.obs_service.connected = False
        controller.settings["auto_connect_enabled"] = True
        controller.settings["obs_host"] = "example.com"
        controller.settings["obs_port"] = 1234
        controller.settings["obs_password"] = "test_password"
        
        # Mock connect_to_obs and notify_auto_connect_started
        controller.connect_to_obs = MagicMock()
        controller.notify_auto_connect_started = MagicMock()
        
        # Check auto-connect
        controller._check_auto_connect()
        
        # Check that notify_auto_connect_started was emitted
        controller.notify_auto_connect_started.emit.assert_called_once_with("example.com", 1234)
        
        # Check that connect_to_obs was called
        controller.connect_to_obs.assert_called_once_with("example.com", 1234, "test_password")
        
        # Check that the flag was set
        assert controller.auto_connect_attempted
    
    def test_setup_event_listeners(self, controller):
        """Test setting up event listeners."""
        # Reset the controller
        controller = SettingsController()
        
        # Mock the event_manager.subscribe method and connection signals
        with patch('ui.tabs.settings_controller.event_manager.subscribe') as mock_subscribe, \
             patch.object(controller, 'connection_successful') as mock_conn_success, \
             patch.object(controller, 'disconnection_successful') as mock_disconn_success:
            
            # Call the method
            controller._setup_event_listeners()
            
            # Check that the signals were connected to event_manager.emit
            assert len(mock_conn_success.connect.call_args_list) == 1
            assert len(mock_disconn_success.connect.call_args_list) == 1
    
    def test_handle_app_started(self, controller):
        """Test handling app started event."""
        # Call the method
        controller._handle_app_started()
        
        # No assertion needed - just checking that it doesn't raise an exception
    
    def test_debug_password_status_with_password(self, controller):
        """Test debugging password status when password exists."""
        # Set password in settings
        controller.settings["obs_password"] = "existing_password"
        
        # Debug password status
        controller._debug_password_status()
        
        # No assertion needed - just checking that it doesn't raise an exception
    
    def test_debug_password_status_without_password(self, controller):
        """Test debugging password status when password doesn't exist."""
        # Remove password from settings
        if "obs_password" in controller.settings:
            del controller.settings["obs_password"]
        
        # Mock _load_password_from_storage
        with patch.object(controller, '_load_password_from_storage', return_value="loaded_password"):
            # Debug password status
            controller._debug_password_status()
            
            # No assertion needed - just checking that it doesn't raise an exception
    
    def test_run_sync_disconnect(self, controller):
        """Test running a synchronous disconnect."""
        # Mock the reset_connection method
        controller.obs_service.reset_connection = MagicMock()
        
        # Run sync disconnect
        controller.run_sync_disconnect()
        
        # Check that reset_connection was called
        controller.obs_service.reset_connection.assert_called_once()

class TestAsyncWorker:
    @pytest.fixture
    def worker(self):
        """Fixture that provides an async worker."""
        async def test_coro(*args, **kwargs):
            return "test_result"
        
        worker = AsyncWorker(test_coro, "arg1", "arg2", kwarg1="value1", kwarg2="value2")
        return worker
    
    def test_init(self, worker):
        """Test initializing the worker."""
        assert worker.args == ("arg1", "arg2")
        assert worker.kwargs == {"kwarg1": "value1", "kwarg2": "value2"}
        assert worker.signals is not None
    
    def test_run_success(self, worker):
        """Test running the worker successfully."""
        # Mock the signals
        worker.signals.result = MagicMock()
        worker.signals.error = MagicMock()
        worker.signals.finished = MagicMock()
        
        # Mock asyncio.new_event_loop and asyncio.set_event_loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete = MagicMock(return_value="test_result")
        
        with patch("asyncio.new_event_loop", return_value=mock_loop), \
             patch("asyncio.set_event_loop"):
            # Run the worker
            worker.run()
            
            # Check that the result was emitted with the expected value
            worker.signals.result.emit.assert_called_once_with("test_result")
            worker.signals.finished.emit.assert_called_once()
            
            # Verify run_until_complete was called (but don't check how many times)
            assert mock_loop.run_until_complete.called
    
    def test_run_error(self, worker):
        """Test running the worker with an error."""
        # Mock the signals
        worker.signals.result = MagicMock()
        worker.signals.error = MagicMock()
        worker.signals.finished = MagicMock()
        
        # Mock asyncio.new_event_loop and asyncio.set_event_loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete = MagicMock(side_effect=Exception("Test exception"))
        
        with patch("asyncio.new_event_loop", return_value=mock_loop), \
             patch("asyncio.set_event_loop"), \
             patch("ui.tabs.settings_controller.logger") as mock_logger:
            # Run the worker
            worker.run()
            
            # Check that the error was emitted (at least once)
            assert worker.signals.error.emit.called
            # Check that finished was called
            worker.signals.finished.emit.assert_called_once()
            
            # Verify run_until_complete was called
            assert mock_loop.run_until_complete.called 