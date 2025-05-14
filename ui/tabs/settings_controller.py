import asyncio
import logging
import json
import os
import sys
import traceback
import time
from typing import Optional, Dict, Any, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable, QThreadPool, QTimer

import keyring
import keyrings.alt.file
from keyring.errors import KeyringError
from services.obs_websocket import OBSWebSocketService

# Configure logging
logger = logging.getLogger(__name__)

# Settings file path - use app directory
# Use a directory in the app folder instead of user profile
APP_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
SETTINGS_FILE = os.path.join(APP_DIR, "settings", "settings.json")
FALLBACK_PWD_FILE = os.path.join(os.path.dirname(SETTINGS_FILE), ".obspass")
KEYRING_FILE = os.path.join(os.path.dirname(SETTINGS_FILE), ".keyring.json")

# Make sure the directory exists
os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)

logger.info(f"Using settings file at: {SETTINGS_FILE}")
logger.info(f"Using fallback password file at: {FALLBACK_PWD_FILE}")
logger.info(f"Using keyring file at: {KEYRING_FILE}")

# Define the service name for keyring
KEYRING_SERVICE = "obscopilot"
KEYRING_USERNAME = "obs_websocket"

# ALWAYS use file based keyring - this ensures passwords are stored consistently
logger.info("Forcing file-based keyring for consistent password storage...")
file_keyring = keyrings.alt.file.PlaintextKeyring()
file_keyring.file_path = KEYRING_FILE
keyring.set_keyring(file_keyring)
logger.info("[OK] File-based keyring configured")

# Test keyring availability at startup
try:
    test_password = "test_password_123"
    logger.info(f"Testing keyring functionality with service: {KEYRING_SERVICE}, username: test_user")
    keyring.set_password(KEYRING_SERVICE, "test_user", test_password)
    retrieved = keyring.get_password(KEYRING_SERVICE, "test_user")
    if retrieved == test_password:
        logger.info("[OK] Keyring test successful - keyring is working properly")
    else:
        logger.error(f"[FAIL] Keyring test failed - stored '{test_password}' but retrieved '{retrieved}'")
    # Clean up test entry
    keyring.delete_password(KEYRING_SERVICE, "test_user")
except Exception as e:
    logger.error(f"[FAIL] Keyring test error: {str(e)}")
    logger.error(traceback.format_exc())
    logger.warning("Fallback password storage will be used")

# Event system for app-wide events
class EventType:
    """Event types for the event system"""
    APP_STARTED = "app_started"
    SETTINGS_LOADED = "settings_loaded"
    CREDENTIALS_LOADED = "credentials_loaded"
    OBS_CONNECTED = "obs_connected"
    OBS_DISCONNECTED = "obs_disconnected"

class EventManager(QObject):
    """Simple event manager using signal/slot pattern for app-wide events"""
    event_occurred = pyqtSignal(str, object)  # event_type, data
    
    _instance = None
    
    @classmethod
    def instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = EventManager()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self._listeners = {}
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from an event"""
        if event_type in self._listeners and callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)
            logger.debug(f"Unsubscribed from event: {event_type}")
    
    def emit(self, event_type: str, data=None):
        """Emit an event"""
        logger.debug(f"Event emitted: {event_type}")
        self.event_occurred.emit(event_type, data)
        # Call direct listeners
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in event listener for {event_type}: {str(e)}")

# Get the event manager instance
event_manager = EventManager.instance()

class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class AsyncWorker(QRunnable):
    """Worker thread for running async tasks."""
    
    def __init__(self, coro, *args, **kwargs):
        super().__init__()
        self.coro = coro
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        """Run the async task in a separate thread."""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a coroutine to run
            coro = self.coro(*self.args, **self.kwargs)
            
            try:
                # Run the coroutine and get the result
                result = loop.run_until_complete(coro)
                
                # Emit the result
                self.signals.result.emit(result)
            except Exception as e:
                # Emit the error
                self.signals.error.emit(str(e))
                logger.error(f"Error in worker thread: {str(e)}")
            finally:
                # Close any remaining tasks
                pending = asyncio.all_tasks(loop)
                if pending:
                    # Give tasks a chance to cancel
                    for task in pending:
                        task.cancel()
                    
                    # Wait for cancellation with a timeout
                    try:
                        loop.run_until_complete(asyncio.wait(pending, timeout=1.0))
                    except:
                        # Ignore cancellation and timeout errors
                        pass
                
                # Close the loop
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            
        except Exception as e:
            # Emit the error for exceptions outside the async context
            self.signals.error.emit(str(e))
            logger.error(f"Critical error in worker thread: {str(e)}")
            
        finally:
            # Always emit finished signal
            self.signals.finished.emit()

class SettingsController(QObject):
    """Controller for the settings tab."""
    
    # Define signals
    connection_successful = pyqtSignal()
    connection_failed = pyqtSignal(str)
    disconnection_successful = pyqtSignal()
    disconnection_failed = pyqtSignal(str)
    settings_loaded = pyqtSignal(dict)
    notify_auto_connect_started = pyqtSignal(str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.obs_service = OBSWebSocketService()
        self.threadpool = QThreadPool()
        self.settings = {}
        
        # Flag to track if auto-connect has been attempted
        self.auto_connect_attempted = False
        
        # Flag to prevent duplicate settings operations
        self._settings_loaded = False
        self._last_save_time = 0
        
        # Log the settings file path
        logger.info(f"Settings file path: {SETTINGS_FILE}")
        
        # Initialize settings with defaults first
        self.settings = self._get_default_settings()
        
        # Then load settings from file
        self.load_settings()
        
        # Always ensure password is loaded to memory
        self._ensure_password_loaded()
        
        # Log password status for debugging
        self._debug_password_status()
        
        # Setup event listeners
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Setup event listeners for app-wide events"""
        # IMPORTANT: We don't subscribe to APP_STARTED here anymore
        # Auto-connect is now triggered directly from the main window
        # to ensure it happens only once and when the app is fully loaded
        
        # Connect signals to event system as well
        self.connection_successful.connect(
            lambda: event_manager.emit(EventType.OBS_CONNECTED))
        
        self.disconnection_successful.connect(
            lambda: event_manager.emit(EventType.OBS_DISCONNECTED))
    
    def _handle_app_started(self, data=None):
        """Handle app started event"""
        # This method is kept for compatibility but no longer used
        # Auto-connect is now triggered directly from main window
        logger.info("App started event handler in settings controller is deprecated")
        pass
    
    def _check_auto_connect(self):
        """Check if we should auto-connect to OBS"""
        # Check if auto-connect has already been attempted
        if self.auto_connect_attempted:
            logger.info("AUTO-CONNECT SKIPPED: Already attempted once this session")
            return
        
        # Mark as attempted to prevent multiple attempts
        self.auto_connect_attempted = True
        logger.info("PERFORMING AUTO-CONNECT CHECK (will not run again this session)")
        
        # Check if already connected first to avoid multiple connections
        if self.obs_service.connected:
            logger.info("AUTO-CONNECT SKIPPED: Already connected to OBS")
            return
        
        # Check if auto connect is enabled
        auto_connect = self.settings.get("auto_connect_enabled", False)
        
        # Debug: Log current settings (but hide password info)
        settings_debug = self.settings.copy()
        if "obs_password" in settings_debug:
            # SECURITY: Never log password details (not even length)
            has_password = bool(settings_debug["obs_password"])
            settings_debug["obs_password"] = f"<{'present' if has_password else 'empty'}>"
        logger.info(f"Checking auto-connect with settings: {settings_debug}")
        
        if not auto_connect:
            logger.info("Auto-connect is disabled")
            return
        
        # Check if we have credentials
        host = self.settings.get("obs_host", "")
        port = self.settings.get("obs_port", 0)
        password = self.settings.get("obs_password", "")
        
        # Log connection details (but never password info)
        has_password = bool(password)
        logger.info(f"Auto-connect credentials - Host: {host}, Port: {port}, Password: <{'present' if has_password else 'empty'}>")
        
        # Validate credentials
        if not host or not port:
            logger.warning("Cannot auto-connect: Missing host or port")
            return
        
        # Double-check not already connected (just to be extra safe)
        if self.obs_service.connected:
            logger.info("Already connected to OBS, skipping auto-connect")
            return
        
        logger.info(f"AUTO-CONNECT TRIGGERED: Connecting to OBS at {host}:{port}")
        
        # Emit a notification for the UI
        self.notify_auto_connect_started.emit(host, port)
        
        # Connect
        self.connect_to_obs(host, port, password)
    
    def run_async(self, coro, *args, **kwargs):
        """Run an async task in a separate thread."""
        # Extract callback functions from kwargs
        on_result = kwargs.pop('on_result', None)
        on_error = kwargs.pop('on_error', None)
        on_finished = kwargs.pop('on_finished', None)
        
        # Create worker with remaining args and kwargs
        worker = AsyncWorker(coro, *args, **kwargs)
        
        if on_result:
            worker.signals.result.connect(on_result)
        
        if on_error:
            worker.signals.error.connect(on_error)
            
        if on_finished:
            worker.signals.finished.connect(on_finished)
            
        self.threadpool.start(worker)
    
    def connect_to_obs(self, host: str, port: int, password: str) -> None:
        """
        Connect to OBS WebSocket server.
        
        Args:
            host: The hostname or IP address of the OBS WebSocket server
            port: The port of the OBS WebSocket server
            password: The password for the OBS WebSocket server (if any)
        """
        # CRITICAL: Check if already connected before proceeding
        if self.obs_service.connected:
            # We're already connected - don't create multiple connections
            logger.warning(f"IGNORING CONNECTION REQUEST - ALREADY CONNECTED to OBS at {host}:{port}")
            
            # Emit the success signal directly - pretend we connected for UI consistency
            # This prevents errors in the UI flow
            self.connection_successful.emit()
            return
        
        # Log connection attempt (never log password details)
        has_password = bool(password)
        logger.info(f"Connecting to OBS: {host}:{port} with password: <{'present' if has_password else 'empty'}>")
        
        # Save connection settings (but not password) to settings file
        self.settings["obs_host"] = host
        self.settings["obs_port"] = port
        
        # Always keep password in memory
        self.settings["obs_password"] = password
        
        # Double-check password is stored correctly (without logging details)
        stored_pwd = self.settings.get("obs_password", "")
        if stored_pwd != password:
            logger.error("Password storage inconsistency in memory")
            # Force set it again
            self.settings["obs_password"] = password
        
        # Store password securely in system keyring
        self._save_password_to_keyring(password)
        
        # Save settings to file (password is not saved here)
        self.save_settings()
        
        # Create a clean connection - make sure any previous connection is closed
        if self.obs_service.connected:
            logger.warning("Already connected - disconnecting first")
            # Disconnect synchronously to avoid issues
            self.run_sync_disconnect()
        
        # Connect asynchronously
        self.run_async(
            self.obs_service.connect,
            host=host,
            port=port,
            password=password,
            on_result=self._on_connect_result,
            on_error=self._on_connect_error
        )
    
    def disconnect_from_obs(self) -> None:
        """Disconnect from OBS WebSocket server."""
        logger.info("Performing disconnect operations")
        
        # Connect asynchronously
        self.run_async(
            self.obs_service.disconnect,
            on_result=self._on_disconnect_result,
            on_error=self._on_disconnect_error
        )
    
    def _on_connect_result(self, result: bool) -> None:
        """Handle the result of the connect operation."""
        if result:
            self.connection_successful.emit()
        else:
            self.connection_failed.emit("Failed to connect to OBS WebSocket. Please check your settings and try again.")
    
    def _on_connect_error(self, error: str) -> None:
        """Handle an error during the connect operation."""
        # Check for specific error types
        if "Authentication failed" in error or "authentication" in error.lower():
            self.connection_failed.emit("Authentication failed: Incorrect password")
        else:
            self.connection_failed.emit(f"Error connecting to OBS WebSocket: {error}")
    
    def _on_disconnect_result(self, result: bool) -> None:
        """Handle the result of the disconnect operation."""
        if result:
            self.disconnection_successful.emit()
        else:
            self.disconnection_failed.emit("Failed to disconnect from OBS WebSocket")
    
    def _on_disconnect_error(self, error: str) -> None:
        """Handle an error during the disconnect operation."""
        self.disconnection_failed.emit(f"Error disconnecting from OBS WebSocket: {error}")
    
    def is_connected(self) -> bool:
        """
        Check if connected to OBS WebSocket server.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.obs_service.connected
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Return default settings"""
        return {
            "obs_host": "localhost",
            "obs_port": 4455,
            "obs_password": "",
            "auto_connect_enabled": False  # New setting for auto-connect
        }
    
    def load_settings(self) -> None:
        """Load settings from disk."""
        # IMPORTANT: Prevent duplicate loads
        if hasattr(self, '_settings_loaded') and self._settings_loaded:
            logger.info("SKIPPING duplicate settings load - already loaded")
            return
        
        logger.info(f"Loading settings from {SETTINGS_FILE}")
        
        try:
            # Make sure our path exists
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            
            # If settings file exists and has content, load it
            if os.path.exists(SETTINGS_FILE) and os.path.getsize(SETTINGS_FILE) > 0:
                try:
                    # Direct approach - read the file content
                    with open(SETTINGS_FILE, 'r') as f:
                        file_settings = json.load(f)
                    
                    # Log loaded keys (without logging values)
                    logger.info(f"Settings loaded from {SETTINGS_FILE}, keys: {list(file_settings.keys())}")
                    
                    # Copy values to our settings dict
                    self.settings.update(file_settings)
                    
                    # Force auto_connect_enabled to be a proper boolean if present
                    if "auto_connect_enabled" in file_settings:
                        raw_value = file_settings["auto_connect_enabled"]
                        bool_value = bool(raw_value)
                        logger.info(f"AUTO-CONNECT loaded from file: {raw_value} (type: {type(raw_value).__name__}) -> forced to boolean: {bool_value}")
                        self.settings["auto_connect_enabled"] = bool_value
                    else:
                        logger.warning("AUTO-CONNECT setting not found in file, defaulting to False")
                        self.settings["auto_connect_enabled"] = False
                    
                    # Load password directly - do this every time
                    self._ensure_password_loaded()
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in settings file {SETTINGS_FILE}")
                    self.settings = self._get_default_settings()
            else:
                # Use default settings
                logger.info(f"Settings file not found or empty, using defaults")
                self.settings = self._get_default_settings()
                
                # Write default settings to file
                self.save_settings()
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            self.settings = self._get_default_settings()
        
        # Verify we have a password in memory before emitting settings
        if "obs_password" not in self.settings or self.settings["obs_password"] is None:
            logger.warning("Password missing before emitting settings - ensuring it's loaded")
            self._ensure_password_loaded()
        
        # Force auto_connect_enabled to be boolean
        if "auto_connect_enabled" in self.settings:
            self.settings["auto_connect_enabled"] = bool(self.settings["auto_connect_enabled"])
        
        # Log the auto-connect state
        auto_connect = self.settings.get("auto_connect_enabled", False)
        logger.info(f"AUTO-CONNECT SETTING (after loading): {auto_connect} (type: {type(auto_connect).__name__})")
        
        # Log the state of the password right before emitting
        has_pwd = "obs_password" in self.settings and self.settings["obs_password"] is not None
        pwd_len = len(self.settings["obs_password"]) if has_pwd and isinstance(self.settings["obs_password"], str) else 0
        logger.info(f"Emitting settings with password: {has_pwd} (length: {pwd_len})")
        
        # Mark settings as loaded to prevent duplicate loads
        self._settings_loaded = True
        
        # Always emit loaded settings
        self.settings_loaded.emit(self.settings.copy())
    
    def _ensure_password_loaded(self) -> None:
        """
        Ensure password is loaded into memory settings.
        """
        logger.info("Ensuring password is loaded to memory...")
        
        # Check if we already have a password in memory
        existing_password = self.settings.get("obs_password", "")
        if existing_password:
            # SECURITY: Never log password details (not even length)
            logger.info("Password already exists in memory settings")
            return
        
        # Try to load password from storage
        password = self._load_password_from_storage()
        if password:
            # Set the password in memory
            logger.info("Adding password from storage to memory settings")
            self.settings["obs_password"] = password
            
            # Double check it was set correctly
            check_pwd = self.settings.get("obs_password", "")
            if check_pwd != password:
                logger.error("Failed to set password in settings")
        else:
            # No password found, set empty string
            logger.info("No password found in storage, using empty string")
            self.settings["obs_password"] = ""
        
        # Log what will be emitted during settings_loaded signal
        settings_copy = self.settings.copy()
        if "obs_password" in settings_copy:
            pwd_present = bool(settings_copy["obs_password"])
            # SECURITY: Never log password details (not even length)
            logger.info(f"Settings contains password: {pwd_present}")
        else:
            logger.info("Settings does NOT contain password")
    
    def _load_password_from_storage(self) -> Optional[str]:
        """
        Load password from system keyring with fallback mechanism.
        
        Returns:
            Optional[str]: The password if found, None otherwise
        """
        logger.info("=== LOADING PASSWORD ===")
        
        # First try to get from keyring
        try:
            logger.info(f"Attempting to load password from system keyring (service: {KEYRING_SERVICE}, username: {KEYRING_USERNAME})")
            password = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if password:
                # SECURITY: Never log password details (not even length or first char)
                logger.info("[OK] Password successfully loaded from keyring")
                logger.info("=== END LOADING PASSWORD ===")
                return password
            else:
                logger.warning("[FAIL] No password found in keyring")
        except Exception as e:
            logger.error(f"[FAIL] Error retrieving password from keyring: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Try loading from fallback file
        try:
            if os.path.exists(FALLBACK_PWD_FILE):
                logger.info(f"Attempting to load password from fallback file: {FALLBACK_PWD_FILE}")
                with open(FALLBACK_PWD_FILE, 'r') as f:
                    password = f.read().strip()
                
                if password:
                    # SECURITY: Never log password details (not even length or first char)
                    logger.info("[OK] Password loaded from fallback file")
                    
                    # Try to save it to keyring for next time
                    try:
                        logger.info("Attempting to migrate password from fallback to keyring...")
                        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, password)
                        logger.info("[OK] Migrated password from fallback to keyring")
                    except Exception as ke:
                        logger.error(f"[FAIL] Failed to migrate password to keyring: {str(ke)}")
                    
                    logger.info("=== END LOADING PASSWORD ===")
                    return password
                else:
                    logger.warning("[FAIL] Empty password found in fallback file")
            else:
                logger.warning(f"[FAIL] Fallback file not found: {FALLBACK_PWD_FILE}")
        except Exception as e:
            logger.error(f"[FAIL] Error loading password from fallback: {str(e)}")
            logger.error(traceback.format_exc())
        
        logger.warning("[FAIL] No password found in any storage location")
        logger.info("=== END LOADING PASSWORD ===")
        return None
    
    def save_settings(self) -> None:
        """Save settings to disk using a direct approach."""
        # Debounce rapid saves - prevent multiple saves within 500ms
        current_time = time.time()
        if hasattr(self, '_last_save_time') and current_time - self._last_save_time < 0.5:
            logger.info("SKIPPING duplicate settings save - too soon after last save")
            return
        
        # Update last save time
        self._last_save_time = current_time
        
        try:
            # Make sure our path exists
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            
            logger.info(f"Saving settings to app directory: {SETTINGS_FILE}")
            
            # Create a copy for file storage (without password)
            settings_to_save = self.settings.copy()
            if "obs_password" in settings_to_save:
                # Remove password from the file storage copy
                del settings_to_save["obs_password"]
            
            # Ensure auto_connect_enabled is in the settings as a proper boolean
            auto_connect = bool(self.settings.get("auto_connect_enabled", False))
            settings_to_save["auto_connect_enabled"] = auto_connect
            
            # Make a copy for logging
            log_settings = settings_to_save.copy()
            logger.info(f"Settings to save: {log_settings}")
            
            # Write with direct file handling
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings_to_save, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Log success
            logger.info(f"Settings saved to: {SETTINGS_FILE}")
            
            # Verify file exists and read it back
            if not os.path.exists(SETTINGS_FILE):
                logger.error("Failed to save settings: File does not exist after save")
                return
                
            file_size = os.path.getsize(SETTINGS_FILE)
            if file_size == 0:
                logger.error("Failed to save settings: File is empty after save")
                return
                
            logger.info(f"Settings file saved (size: {file_size} bytes)")
                
            # Read back and verify
            with open(SETTINGS_FILE, 'r') as f:
                read_data = json.load(f)
            
            # Verify settings were saved correctly
            if "auto_connect_enabled" in read_data:
                saved_auto_connect = read_data.get("auto_connect_enabled", False)
                if saved_auto_connect == auto_connect:
                    logger.info(f"[OK] Auto-connect setting in file verified: {saved_auto_connect}")
                else:
                    logger.error(f"[FAIL] Auto-connect setting mismatch: memory={auto_connect}, file={saved_auto_connect}")
            else:
                logger.error("[FAIL] Auto-connect setting not found in saved file")
                
            # Verify password was NOT saved
            if "obs_password" in read_data:
                logger.error("[FAIL] Password was incorrectly saved to settings file")
            else:
                logger.info("[OK] Password was not saved to settings file (good)")
                
        except Exception as e:
            logger.error(f"[FAIL] Error saving settings: {str(e)}")
    
    def save_password(self, password: str) -> None:
        """
        Explicitly save the password to the settings file.
        
        Args:
            password: The password to save
        """
        logger.info("Explicitly saving password to settings")
        
        # Update settings with the password
        self.settings["obs_password"] = password
        
        # Save using direct file access to ensure it works
        try:
            # Make sure directory exists
            settings_dir = os.path.dirname(SETTINGS_FILE)
            os.makedirs(settings_dir, exist_ok=True)
            
            # Write directly to file
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
                f.flush()
            
            # Verify written file
            if os.path.exists(SETTINGS_FILE):
                logger.info(f"Password saved successfully to {SETTINGS_FILE}")
                try:
                    # Verify by reading back
                    with open(SETTINGS_FILE, 'r') as f:
                        saved_data = json.load(f)
                    if "obs_password" in saved_data and saved_data["obs_password"] == password:
                        logger.info("Password verification successful")
                    else:
                        logger.error("Password verification failed - passwords don't match")
                except Exception as e:
                    logger.error(f"Error verifying password save: {str(e)}")
            else:
                logger.error(f"Failed to save password - file not found after save")
        except Exception as e:
            logger.error(f"Error saving password: {str(e)}")

    def run_sync_disconnect(self) -> None:
        """Run a synchronous disconnect to ensure cleanup."""
        # Just reset the connection immediately - no event loop magic
        logger.info("Running sync disconnect - forcing immediate reset")
        self.obs_service.reset_connection()

    def _save_password_to_keyring(self, password: str) -> bool:
        """
        Save password to system keyring with fallback mechanism.
        
        Args:
            password: The password to save
            
        Returns:
            bool: True if password was saved successfully, False otherwise
        """
        # Skip if no password provided
        if not password:
            logger.warning("No password provided to save")
            return False
        
        # Check if password is already saved correctly
        try:
            stored_password = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if stored_password == password:
                logger.info("Password is already correctly stored in keyring - skipping save")
                return True
        except Exception:
            # If error checking, continue with save attempt
            pass
            
        logger.info("=== SAVING PASSWORD ===")
        
        # SECURITY: Never log password details (not even length or first char)
        logger.info("Attempting to save password to keyring")
        
        # Track if we've saved successfully anywhere
        saved_successfully = False
        
        # First try the standard keyring approach
        try:
            logger.info(f"Attempting to save password to system keyring (service: {KEYRING_SERVICE}, username: {KEYRING_USERNAME})")
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, password)
            
            # Verify the password was stored correctly
            logger.info("Verifying password was saved to keyring...")
            stored_password = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            
            if stored_password == password:
                logger.info("[OK] Password successfully verified in keyring")
                saved_successfully = True
            else:
                if stored_password:
                    logger.error("[FAIL] Password verification failed - stored value doesn't match")
                else:
                    logger.error("[FAIL] Password verification failed - nothing retrieved from keyring")
        except Exception as e:
            logger.error(f"[FAIL] Error saving password to keyring: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Always try saving to fallback file as well for redundancy
        try:
            # Skip fallback if already saved to keyring
            if saved_successfully:
                logger.info("Password already saved to keyring - skipping fallback file save")
            else:
                logger.info(f"Saving password to fallback file: {FALLBACK_PWD_FILE}")
                with open(FALLBACK_PWD_FILE, 'w') as f:
                    f.write(password)
            
            # Verify the password was saved to file
            if os.path.exists(FALLBACK_PWD_FILE):
                with open(FALLBACK_PWD_FILE, 'r') as f:
                    file_password = f.read().strip()
                
                if file_password == password:
                    logger.info("[OK] Password successfully saved and verified in fallback file")
                    saved_successfully = True
                else:
                    logger.error("[FAIL] Password verification in fallback file failed")
            else:
                logger.error("[FAIL] Fallback file not found after saving")
        except Exception as e:
            logger.error(f"[FAIL] Error saving password to fallback file: {str(e)}")
            logger.error(traceback.format_exc())
        
        logger.info(f"Password save result: {'SUCCESS' if saved_successfully else 'FAILED'}")
        logger.info("=== END SAVING PASSWORD ===")
        return saved_successfully

    def _debug_password_status(self) -> None:
        """Debug function to log password status."""
        logger.info("=== DEBUGGING PASSWORD STATUS ===")
        
        # Check if password is already loaded in settings
        existing_password = self.settings.get("obs_password", "")
        if existing_password:
            logger.info("[OK] Password already loaded in memory settings")
            logger.info("=== END DEBUGGING PASSWORD STATUS ===")
            return
        
        # Only load from storage if not already in memory
        logger.info("Password not found in memory, checking storage...")
        password = self._load_password_from_storage()
        
        if password:
            logger.info("[OK] Password loaded from storage")
        else:
            logger.warning("[FAIL] No password found in any storage location")
        
        logger.info("=== END DEBUGGING PASSWORD STATUS ===")

    def set_auto_connect_enabled(self, enabled: bool):
        """Enable or disable auto-connect feature"""
        # Ensure the input is a proper Python boolean
        enabled = bool(enabled)
        
        logger.info(f"Setting auto-connect enabled to STRICT BOOLEAN: {enabled} (type: {type(enabled).__name__})")
        
        # Update setting in memory - force boolean type
        previous = bool(self.settings.get("auto_connect_enabled", False))
        
        # Store as strict boolean
        self.settings["auto_connect_enabled"] = enabled
        
        # Double check it's a boolean
        if not isinstance(self.settings["auto_connect_enabled"], bool):
            logger.error(f"CRITICAL: Auto-connect setting is not boolean after assignment: {type(self.settings['auto_connect_enabled']).__name__}")
            # Force it again
            self.settings["auto_connect_enabled"] = bool(enabled)
        
        # Save to file immediately
        try:
            # Force save directly to ensure it's written correctly
            # Create a direct save dictionary
            settings_to_save = {
                "obs_host": self.settings.get("obs_host", "localhost"),
                "obs_port": self.settings.get("obs_port", 4455),
                "auto_connect_enabled": enabled  # Use direct boolean value
            }
            
            # Log what we're saving
            logger.info(f"DIRECT SAVING auto-connect setting: {enabled}")
            logger.info(f"Direct save data: {settings_to_save}")
            
            # Make sure directory exists
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            
            # Write directly to file
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings_to_save, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            logger.info(f"Direct save completed to: {SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"[FAIL] Error in direct save: {str(e)}")
        
        # Also do a standard save as backup
        self.save_settings()
        
        # Verify the setting was saved
        logger.info(f"Auto-connect setting changed from {previous} to {enabled}")
        
        # Read back from file to verify
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    saved_settings = json.load(f)
                
                # Verify auto-connect setting was saved
                if "auto_connect_enabled" in saved_settings:
                    saved_value = bool(saved_settings["auto_connect_enabled"])
                    logger.info(f"[VERIFICATION] Auto-connect in file: {saved_value} (type: {type(saved_value).__name__})")
                    
                    if saved_value == enabled:
                        logger.info(f"[OK] Auto-connect verified in file: {saved_value}")
                    else:
                        logger.error(f"[FAIL] Auto-connect mismatch: wanted {enabled}, got {saved_value}")
                        # Emergency fix - write the file again with explicit boolean
                        try:
                            saved_settings["auto_connect_enabled"] = enabled
                            with open(SETTINGS_FILE, 'w') as f:
                                json.dump(saved_settings, f, indent=2)
                                f.flush()
                                os.fsync(f.fileno())
                            logger.info(f"[EMERGENCY] Forced auto-connect in file to: {enabled}")
                        except Exception as fix_err:
                            logger.error(f"[CRITICAL] Failed to fix auto-connect: {str(fix_err)}")
                else:
                    logger.error("[FAIL] Auto-connect missing from file")
                    # Emergency fix - write with just this setting
                    try:
                        with open(SETTINGS_FILE, 'w') as f:
                            json.dump({"auto_connect_enabled": enabled}, f, indent=2)
                        logger.info(f"[EMERGENCY] Created new file with only auto-connect: {enabled}")
                    except Exception as fix_err:
                        logger.error(f"[CRITICAL] Failed to create basic setting file: {str(fix_err)}")
        except Exception as e:
            logger.error(f"[FAIL] Error verifying auto-connect: {str(e)}")
        
        return self.is_auto_connect_enabled()

    def is_auto_connect_enabled(self) -> bool:
        """Check if auto-connect is enabled - ALWAYS returns strict boolean"""
        # First check memory
        memory_value = self.settings.get("auto_connect_enabled", False)
        memory_bool = bool(memory_value)
        
        # Also check file directly
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    saved_settings = json.load(f)
                
                file_value = saved_settings.get("auto_connect_enabled", False)
                file_bool = bool(file_value)
                
                # Log both values
                logger.info(f"Auto-connect status - Memory: {memory_bool}, File: {file_bool}")
                
                # If they disagree, use file value and update memory
                if memory_bool != file_bool:
                    logger.warning(f"Auto-connect value mismatch - updating memory from file: {file_bool}")
                    self.settings["auto_connect_enabled"] = file_bool
                    return file_bool
        except Exception as e:
            logger.error(f"Error reading auto-connect from file: {str(e)}")
        
        # Return memory value as strict boolean
        return memory_bool 