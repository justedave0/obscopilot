import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout,
                             QLineEdit, QLabel, QSpinBox, QPushButton, QHBoxLayout,
                             QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction

from ui.tabs.settings_controller import SettingsController, event_manager, EventType

# Configure logging
logger = logging.getLogger(__name__)

class PasswordLineEdit(QLineEdit):
    """Custom QLineEdit with toggle password visibility functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Create the show/hide password action
        self.toggle_password_action = QAction(self)
        self.toggle_password_action.setIcon(QIcon.fromTheme("eye"))
        self.toggle_password_action.triggered.connect(self.toggle_password_visibility)
        
        # Add the action to the right side of the line edit
        self.addAction(self.toggle_password_action, QLineEdit.ActionPosition.TrailingPosition)
    
    def toggle_password_visibility(self):
        """Toggle between password and normal mode"""
        if self.echoMode() == QLineEdit.EchoMode.Password:
            self.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_action.setIcon(QIcon.fromTheme("eye-off"))
        else:
            self.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_action.setIcon(QIcon.fromTheme("eye"))
    
    def set_password(self, password):
        """Special method to set password reliably"""
        # SECURITY: Never log password details (not even length)
        has_password = bool(password)
        logger.info(f"Setting password field directly: <{'present' if has_password else 'empty'}>")
        
        self.blockSignals(True)  # Block signals to prevent any interference
        self.clear()
        self.insert(password)
        self.blockSignals(False)
        
        return self.text() == password  # Return whether setting was successful


class SettingsTab(QWidget):
    def __init__(self, parent=None, settings_controller=None):
        super().__init__(parent)
        self.settings_loaded = False
        
        # Use provided controller or create one if not provided
        if settings_controller is not None:
            logger.info("SettingsTab: Using provided settings controller")
            self.controller = settings_controller
        else:
            logger.info("SettingsTab: Creating new settings controller")
            self.controller = SettingsController(self)
        
        self.setup_ui()
        self.setup_connections()
        
        # Use timer to ensure UI is fully initialized before loading settings
        QTimer.singleShot(100, self.delayed_init)
        
        # NOTE: App started event is now emitted only from the main window
        # to prevent double emissions
    
    def delayed_init(self):
        """Perform initialization after UI is fully created"""
        logger.info("Performing delayed initialization")
        
        # Only trigger settings load if we haven't received settings yet
        if not self.settings_loaded:
            logger.info("Settings not loaded yet, triggering load")
            self.controller.load_settings()
        else:
            logger.info("Settings already loaded, skipping load")
        
        # Make the UI reflect the current controller state
        self.update_ui_from_controller()
    
    def setup_ui(self):
        """Set up the settings tab UI"""
        main_layout = QVBoxLayout()
        
        # OBS WebSocket Settings Section
        self.create_obs_websocket_group()
        main_layout.addWidget(self.obs_websocket_group)
        
        # Add a stretch at the bottom to push all widgets to the top
        main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def setup_connections(self):
        """Set up connections between signals and slots"""
        # Connect controller signals to UI update methods
        self.controller.connection_successful.connect(self.on_connection_successful)
        self.controller.connection_failed.connect(self.on_connection_failed)
        self.controller.disconnection_successful.connect(self.on_disconnection_successful)
        self.controller.disconnection_failed.connect(self.on_disconnection_failed)
        self.controller.settings_loaded.connect(self.on_settings_loaded)
        self.controller.notify_auto_connect_started.connect(self.on_auto_connect_started)
    
    def on_settings_loaded(self, settings):
        """Handle loaded settings"""
        logger.info(f"Settings loaded in UI")
        self.settings_loaded = True
        
        # Debug log all settings keys (don't log values for security)
        logger.debug(f"Settings keys: {list(settings.keys())}")
        
        # Update the UI with saved settings
        if "obs_host" in settings and isinstance(settings["obs_host"], str):
            logger.debug(f"Setting host to: {settings['obs_host']}")
            self.host_input.setText(settings["obs_host"])
        else:
            logger.warning("No valid host in settings")
        
        if "obs_port" in settings and isinstance(settings["obs_port"], int):
            logger.debug(f"Setting port to: {settings['obs_port']}")
            self.port_input.setValue(settings["obs_port"])
        else:
            logger.warning("No valid port in settings")
        
        if "obs_password" in settings and isinstance(settings["obs_password"], str):
            # SECURITY: Never log password details (not even length)
            password = settings["obs_password"]
            has_password = bool(password)
            logger.info(f"Setting password field: <{'present' if has_password else 'empty'}>")
            
            # Use the special method to set the password
            success = self.password_input.set_password(password)
            logger.info(f"Password set {'succeeded' if success else 'failed'}")
            
            # If setting failed, try a delayed approach
            if not success and has_password:
                logger.warning("Failed to set password immediately, trying delayed approach")
                QTimer.singleShot(200, lambda: self.delayed_set_password(password))
        else:
            logger.warning("No valid password in settings")
        
        # Set auto-connect checkbox - CRITICAL section
        try:
            # Block signals to prevent triggering events during programmatic change
            self.auto_connect_checkbox.blockSignals(True)
            
            # Get the setting as a strict boolean
            auto_connect_enabled = bool(settings.get("auto_connect_enabled", False))
            
            # Log what we're doing
            logger.info(f"RESTORING AUTO-CONNECT CHECKBOX to: {auto_connect_enabled} (type: {type(auto_connect_enabled).__name__})")
            
            # Set the checkbox state
            self.auto_connect_checkbox.setChecked(auto_connect_enabled)
            
            # Verify the checkbox state matches the setting
            actual_state = self.auto_connect_checkbox.isChecked()
            logger.info(f"AUTO-CONNECT CHECKBOX state after setting: {actual_state}")
            
            if actual_state != auto_connect_enabled:
                logger.error(f"CRITICAL: Checkbox state mismatch after setting - Expected: {auto_connect_enabled}, Got: {actual_state}")
                # Try forcing it again
                self.auto_connect_checkbox.setChecked(auto_connect_enabled)
                logger.info(f"Second attempt to set checkbox state: {self.auto_connect_checkbox.isChecked()}")
        finally:
            # Always unblock signals
            self.auto_connect_checkbox.blockSignals(False)
    
    def delayed_set_password(self, password):
        """Set password after a delay to ensure UI is ready"""
        logger.info("Attempting delayed password set")
        # SECURITY: Never log password details (not even length)
        has_password = bool(password)
        
        success = self.password_input.set_password(password)
        logger.info(f"Delayed password set {'succeeded' if success else 'failed'}")
        
        # Final check - actual vs expected
        current = self.password_input.text()
        if current != password:
            logger.error("Password verification failed - mismatch between set and actual value")
        else:
            logger.info("Password successfully verified")

    def create_obs_websocket_group(self):
        """Create the OBS WebSocket settings group"""
        self.obs_websocket_group = QGroupBox("OBS WebSocket Settings")
        form_layout = QFormLayout()
        
        # Host
        self.host_input = QLineEdit()
        self.host_input.setText("localhost")
        form_layout.addRow("Host:", self.host_input)
        
        # Port
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(4455)  # Default port for OBS WebSocket v5
        form_layout.addRow("Port:", self.port_input)
        
        # Password
        self.password_input = PasswordLineEdit()
        form_layout.addRow("Password:", self.password_input)
        
        # Auto-connect option
        self.auto_connect_checkbox = QCheckBox("Auto-connect on startup")
        self.auto_connect_checkbox.setToolTip("Automatically connect to OBS when the application starts")
        
        # DISCONNECT normal stateChanged signal to prevent issues
        # Use clicked instead which only fires on user interaction
        self.auto_connect_checkbox.clicked.connect(self.on_auto_connect_clicked)
        form_layout.addRow("", self.auto_connect_checkbox)
        
        # Connection button layout
        button_layout = QHBoxLayout()
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_obs)
        button_layout.addWidget(self.connect_button)
        
        # Disconnect button
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_obs)
        self.disconnect_button.setEnabled(False)
        button_layout.addWidget(self.disconnect_button)
        
        # Status indicator
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        button_layout.addWidget(self.status_label)
        
        form_layout.addRow("", button_layout)
        
        self.obs_websocket_group.setLayout(form_layout)
    
    def connect_to_obs(self):
        """Connect to OBS WebSocket server"""
        host = self.host_input.text()
        port = self.port_input.value()
        password = self.password_input.text()
        
        # Update UI to show connecting state
        self.status_label.setText("Connecting...")
        self.status_label.setStyleSheet("color: orange;")
        self.connect_button.setEnabled(False)
        
        # Call the controller to connect
        self.controller.connect_to_obs(host, port, password)
    
    def disconnect_from_obs(self):
        """Disconnect from OBS WebSocket server"""
        # Update UI to show disconnecting state
        self.status_label.setText("Disconnecting...")
        self.status_label.setStyleSheet("color: orange;")
        self.disconnect_button.setEnabled(False)
        
        # Call the controller to disconnect
        self.controller.disconnect_from_obs()
    
    def on_connection_successful(self):
        """Handle successful connection to OBS WebSocket"""
        self.status_label.setText("Connected")
        self.status_label.setStyleSheet("color: green;")
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        
        # Disable the input fields while connected
        self.host_input.setEnabled(False)
        self.port_input.setEnabled(False)
        self.password_input.setEnabled(False)
    
    def on_connection_failed(self, error_message):
        """Handle failed connection to OBS WebSocket"""
        # Update UI to show disconnected state
        self.status_label.setText("Connection Failed")
        self.status_label.setStyleSheet("color: red;")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        
        # Make sure input fields are enabled
        self.host_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.password_input.setEnabled(True)
        
        # Show error message
        QMessageBox.critical(self, "Connection Failed", 
                            f"Failed to connect to OBS WebSocket:\n{error_message}")
    
    def on_disconnection_successful(self):
        """Handle successful disconnection from OBS WebSocket"""
        # Update UI to show disconnected state
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        
        # Re-enable the input fields when disconnected
        self.host_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.password_input.setEnabled(True)
    
    def on_disconnection_failed(self, error_message):
        """Handle failed disconnection from OBS WebSocket"""
        self.status_label.setText("Disconnection Failed")
        self.status_label.setStyleSheet("color: orange;")
        self.disconnect_button.setEnabled(True)
        
        # Show error message
        QMessageBox.critical(self, "Disconnection Failed", 
                            f"Failed to disconnect from OBS WebSocket:\n{error_message}")
    
    def on_auto_connect_clicked(self, checked):
        """Direct event handler for auto-connect checkbox CLICK (not state changed)"""
        # This is directly triggered only by user clicks, not programmatic changes
        logger.info(f"AUTO-CONNECT CHECKBOX CLICKED: {checked}")
        
        # Get current connection details to ensure they're saved with auto-connect setting
        host = self.host_input.text()
        port = self.port_input.value()
        password = self.password_input.text()
        
        # Log action (without exposing full password)
        pwd_info = "(none)" if not password else f"(length: {len(password)})"
        logger.info(f"MANUALLY SAVING AUTO-CONNECT ({checked}) with connection details - Host: {host}, Port: {port}, Password: {pwd_info}")
        
        # Force the state in case it was programmatically changed
        self.auto_connect_checkbox.setChecked(checked)
        
        # FORCE the setting to the value from the click
        current_controller_value = self.controller.is_auto_connect_enabled()
        if current_controller_value != checked:
            logger.info(f"Forcing auto-connect from {current_controller_value} to {checked}")
        
        # ONLY save the setting, don't initiate a connection
        # This ensures checking the box only enables auto-connect for NEXT startup
        self.controller.set_auto_connect_enabled(checked)
        
        # DO NOT CONNECT HERE - this was causing the issue with multiple connections
        # Connections are now only made by explicitly clicking the Connect button
        # or when the app starts with auto-connect enabled
        
        # Final verification
        saved_setting = self.controller.is_auto_connect_enabled()
        logger.info(f"AUTO-CONNECT FINAL STATE: UI={checked}, Settings={saved_setting}")
        
        # If there's still a mismatch, force another save with hard-coded boolean
        if saved_setting != checked:
            logger.error(f"CRITICAL: Auto-connect setting mismatch after save! Forcing direct boolean value.")
            self.controller.set_auto_connect_enabled(bool(checked))

    def on_auto_connect_started(self, host, port):
        """Handle auto-connect notification"""
        logger.info(f"Auto-connecting to OBS at {host}:{port}")
        
        # Update UI to show connecting state
        self.status_label.setText("Auto-connecting...")
        self.status_label.setStyleSheet("color: orange;")
        self.connect_button.setEnabled(False)
        
        # Optionally show a non-blocking notification
        # This makes a small popup appear in the bottom right
        QTimer.singleShot(0, lambda: self._show_auto_connect_notification(host, port))

    def _show_auto_connect_notification(self, host, port):
        """Show a non-blocking notification about auto-connect"""
        try:
            from PyQt6.QtWidgets import QToolTip
            from PyQt6.QtCore import QPoint
            
            message = f"Auto-connecting to OBS at {host}:{port}..."
            QToolTip.showText(
                self.mapToGlobal(QPoint(
                    self.width() - 200,  # Position near the right edge
                    self.height() - 50   # Position near the bottom
                )),
                message,
                self,
                timeout=3000  # Show for 3 seconds
            )
        except Exception as e:
            # Don't let notification errors affect functionality
            logger.error(f"Error showing notification: {str(e)}") 

    def _emit_app_started(self):
        """Emit app started event - DISABLED to avoid duplicate events"""
        # This is now handled exclusively by the main window
        logger.info("App started event emission from settings tab is disabled (handled by main window)")
        pass 

    def update_ui_from_controller(self):
        """Update UI to reflect current controller state without triggering settings load"""
        logger.info("Updating UI from controller state")
        
        # Get settings directly from controller
        settings = self.controller.settings.copy()
        
        # Update host field
        if "obs_host" in settings and isinstance(settings["obs_host"], str):
            logger.debug(f"Updating host to: {settings['obs_host']}")
            self.host_input.setText(settings["obs_host"])
        
        # Update port field
        if "obs_port" in settings and isinstance(settings["obs_port"], int):
            logger.debug(f"Updating port to: {settings['obs_port']}")
            self.port_input.setValue(settings["obs_port"])
        
        # Update password field
        if "obs_password" in settings and isinstance(settings["obs_password"], str):
            password = settings["obs_password"]
            # SECURITY: Never log password details (not even length)
            has_password = bool(password)
            if has_password:
                logger.info("Updating password field: <present>")
                
                # Block signals during update
                self.password_input.blockSignals(True)
                success = self.password_input.set_password(password)
                self.password_input.blockSignals(False)
                
                logger.info(f"Password update {'succeeded' if success else 'failed'}")
        
        # Update auto-connect checkbox
        try:
            # Block signals during update
            self.auto_connect_checkbox.blockSignals(True)
            
            # Get value from controller
            auto_connect = bool(settings.get("auto_connect_enabled", False))
            logger.info(f"Updating auto-connect checkbox to: {auto_connect}")
            
            # Set checkbox state
            self.auto_connect_checkbox.setChecked(auto_connect)
            
            # Verify checkbox state
            actual = self.auto_connect_checkbox.isChecked()
            logger.info(f"Auto-connect checkbox state after update: {actual}")
        finally:
            self.auto_connect_checkbox.blockSignals(False)
        
        # Update connection status
        if self.controller.is_connected():
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green;")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.password_input.setEnabled(False)
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red;")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.host_input.setEnabled(True)
            self.port_input.setEnabled(True)
            self.password_input.setEnabled(True) 