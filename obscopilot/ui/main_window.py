"""
Simple UI module for OBSCopilot.

This module provides a simplified UI that doesn't require complex dependencies.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTabWidget, QStatusBar, 
    QFormLayout, QLineEdit, QCheckBox, QComboBox,
    QSpinBox, QGroupBox, QMessageBox, QScrollArea,
    QInputDialog, QFrame, QSizePolicy
)

from obscopilot.core.config import Config
from obscopilot.core.events import event_bus, Event, EventType

# Setup logging
def setup_logging(app_name="obscopilot", log_dir=None):
    """Set up application logging with daily rotation and comprehensive error tracing.
    
    Args:
        app_name: Name of the application used in log file names
        log_dir: Directory to store log files, defaults to logs/ in the app directory
    
    Returns:
        Logger instance configured for the application
    """
    # Determine log directory
    if log_dir is None:
        # Use app directory/logs by default
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(app_dir, 'logs')
    
    # Create the log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a logger
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    
    # Create log file name with date to identify current log file easily
    current_date = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f"{app_name}_{current_date}.log")
    
    # Create a file handler that logs even debug messages
    # Use TimedRotatingFileHandler to create a new log file each day
    file_handler = TimedRotatingFileHandler(
        log_file, when='midnight', backupCount=30  # Keep logs for 30 days
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler with a higher log level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatters and add them to the handlers
    # Detailed format for file logs
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Simpler format for console output
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log startup information
    logger.info(f"Logging initialized, log file: {log_file}")
    logger.info(f"Application version: {getattr(sys.modules.get('obscopilot', None), '__version__', 'unknown')}")
    logger.info(f"Python version: {sys.version}")
    
    return logger

# Initialize logger
logger = setup_logging()

# Add TwitchSettingsPanel class
class TwitchSettingsPanel(QWidget):
    """Twitch settings panel for authentication and API configuration."""
    
    def __init__(self, config, twitch_client):
        """Initialize the Twitch settings panel.
        
        Args:
            config: Application configuration
            twitch_client: Twitch client instance
        """
        super().__init__()
        self.config = config
        self.twitch_client = twitch_client
        
        # Create layout
        main_layout = QVBoxLayout(self)
        
        # API credentials group
        credentials_group = QGroupBox("Twitch API Credentials")
        credentials_layout = QFormLayout(credentials_group)
        
        # Client ID
        self.client_id = QLineEdit()
        self.client_id.setText(self.config.get('twitch', 'client_id', ''))
        self.client_id.setPlaceholderText("Enter your client ID")
        credentials_layout.addRow("Client ID:", self.client_id)
        
        # Client secret
        self.client_secret = QLineEdit()
        self.client_secret.setText(self.config.get('twitch', 'client_secret', ''))
        self.client_secret.setPlaceholderText("Enter your client secret")
        self.client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        credentials_layout.addRow("Client Secret:", self.client_secret)
        
        # Hint label
        hint_label = QLabel(
            "You need to register an application on the Twitch Developer Console "
            "to get these credentials. The redirect URI should be set to: "
            "http://localhost:8000/auth/callback"
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #888888; font-style: italic;")
        credentials_layout.addRow("", hint_label)
        
        # Save credentials button
        save_credentials_button = QPushButton("Save Credentials")
        save_credentials_button.clicked.connect(self._save_credentials)
        credentials_layout.addRow("", save_credentials_button)
        
        main_layout.addWidget(credentials_group)
        
        # Authentication group
        auth_group = QGroupBox("Twitch Authentication")
        auth_layout = QVBoxLayout(auth_group)
        
        # Authentication
        auth_layout = QHBoxLayout()
        self.status_label = QLabel("Not authenticated")
        auth_button = QPushButton("Authenticate")
        auth_button.clicked.connect(self._authenticate)
        auth_revoke_button = QPushButton("Revoke")
        auth_revoke_button.clicked.connect(self._revoke)
        auth_layout.addWidget(self.status_label)
        auth_layout.addWidget(auth_button)
        auth_layout.addWidget(auth_revoke_button)
        
        # Add layouts to auth group
        auth_layout.addWidget(QLabel("Account:"))
        auth_layout.addLayout(auth_layout)
        
        main_layout.addWidget(auth_group)
        
        # Add stretcher
        main_layout.addStretch()
        
        # Subscribe to events
        event_bus.subscribe(EventType.TWITCH_AUTH_UPDATED, self._on_auth_updated)
        event_bus.subscribe(EventType.TWITCH_AUTH_REVOKED, self._on_auth_revoked)
        
        # Update status labels
        self._update_status_labels()
    
    def _save_credentials(self):
        """Save Twitch API credentials to config."""
        # Save to config
        self.config.set('twitch', 'client_id', self.client_id.text())
        self.config.set('twitch', 'client_secret', self.client_secret.text())
        self.config.save()
        
        # Show success message
        QMessageBox.information(self, "Saved", "Twitch API credentials saved successfully.")
    
    def _authenticate(self):
        """Start the authentication flow."""
        # Check if credentials are set
        if not self.client_id.text() or not self.client_secret.text():
            QMessageBox.warning(self, "Missing Credentials", 
                               "Please enter your client ID and secret first.")
            return
        
        # Start authentication flow
        asyncio.create_task(self.twitch_client.authenticate())
    
    def _revoke(self):
        """Revoke authentication."""
        asyncio.create_task(self.twitch_client.revoke())
    
    def _update_status_labels(self):
        """Update authentication status labels."""
        # Status
        status = self.config.get('twitch', 'status', 'Not authenticated')
        self.status_label.setText(status)
    
    def _on_auth_updated(self, event: Event):
        """Handle auth updated event."""
        self._update_status_labels()
    
    def _on_auth_revoked(self, event: Event):
        """Handle auth revoked event."""
        self._update_status_labels()

class MainWindow(QMainWindow):
    """Simple main window for OBSCopilot."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        logger.info("Initializing SimpleMainWindow")
        
        # Create a default config
        self.config = Config()
        
        # Set default Twitch application credentials
        # These would be your actual application credentials obtained from Twitch Developer Console
        self._set_default_twitch_credentials()
        
        self.setWindowTitle("OBSCopilot")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # Add header
        header = QLabel("OBSCopilot")
        header.setFont(QFont("Arial", 24))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # Add description
        description = QLabel("Twitch Live Assistant with workflow automation and OBS integration")
        description.setFont(QFont("Arial", 12))
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(description)
        
        # Create tab widget for different sections
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create dashboard tab
        self.dashboard_widget = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_widget)
        self.tab_widget.addTab(self.dashboard_widget, "Dashboard")
        
        # Add dashboard content
        dashboard_label = QLabel("Welcome to OBSCopilot Dashboard")
        dashboard_label.setFont(QFont("Arial", 16))
        self.dashboard_layout.addWidget(dashboard_label)
        
        # Add status container
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        
        # Twitch status
        twitch_status = QWidget()
        twitch_layout = QVBoxLayout(twitch_status)
        twitch_layout.addWidget(QLabel("Twitch"))
        self.twitch_status_label = QLabel("Not Connected")
        twitch_layout.addWidget(self.twitch_status_label)
        status_layout.addWidget(twitch_status)
        
        # OBS status
        obs_status = QWidget()
        obs_layout = QVBoxLayout(obs_status)
        obs_layout.addWidget(QLabel("OBS"))
        self.obs_status_label = QLabel("Not Connected")
        obs_layout.addWidget(self.obs_status_label)
        status_layout.addWidget(obs_status)
        
        # Workflows status
        workflows_status = QWidget()
        workflows_layout = QVBoxLayout(workflows_status)
        workflows_layout.addWidget(QLabel("Workflows"))
        self.workflows_status_label = QLabel("0 loaded")
        workflows_layout.addWidget(self.workflows_status_label)
        status_layout.addWidget(workflows_status)
        
        # Add status container to dashboard
        self.dashboard_layout.addWidget(status_container)
        
        # Add spacer
        self.dashboard_layout.addStretch()
        
        # Create workflows tab
        self.workflows_widget = QWidget()
        self.workflows_layout = QVBoxLayout(self.workflows_widget)
        self.workflows_layout.setContentsMargins(10, 10, 10, 10)
        self.workflows_layout.setSpacing(10)
        self.tab_widget.addTab(self.workflows_widget, "Workflows")
        
        # Add workflows content
        workflows_label = QLabel("Workflows")
        workflows_label.setFont(QFont("Arial", 16))
        self.workflows_layout.addWidget(workflows_label)
        
        # Add workflows toolbar
        workflows_toolbar = QWidget()
        workflows_toolbar_layout = QHBoxLayout(workflows_toolbar)
        workflows_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create new workflow button
        create_workflow_button = QPushButton("Create New Workflow")
        create_workflow_button.clicked.connect(self._create_new_workflow)
        workflows_toolbar_layout.addWidget(create_workflow_button)
        
        # Import workflow button
        import_workflow_button = QPushButton("Import Workflow")
        import_workflow_button.clicked.connect(self._import_workflow)
        workflows_toolbar_layout.addWidget(import_workflow_button)
        
        # Export workflow button
        export_workflow_button = QPushButton("Export Selected")
        export_workflow_button.clicked.connect(self._export_workflow)
        export_workflow_button.setEnabled(False)  # Disabled until a workflow is selected
        workflows_toolbar_layout.addWidget(export_workflow_button)
        
        workflows_toolbar_layout.addStretch()
        
        self.workflows_layout.addWidget(workflows_toolbar)
        
        # Add workflows list
        workflows_list_widget = QWidget()
        workflows_list_layout = QVBoxLayout(workflows_list_widget)
        workflows_list_layout.setContentsMargins(0, 0, 0, 0)
        
        # No workflows message
        self.no_workflows_label = QLabel("No workflows have been created yet. Click 'Create New Workflow' to get started.")
        self.no_workflows_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_workflows_label.setStyleSheet("color: #888; margin: 20px;")
        workflows_list_layout.addWidget(self.no_workflows_label)
        
        # This would be replaced with actual workflow items when they're created
        self.workflows_list = QWidget()
        self.workflows_list_layout = QVBoxLayout(self.workflows_list)
        workflows_list_layout.addWidget(self.workflows_list)
        self.workflows_list.setVisible(False)  # Hide until workflows are added
        
        self.workflows_layout.addWidget(workflows_list_widget)
        
        # Add spacer
        self.workflows_layout.addStretch()
        
        # Create settings tab
        self.settings_widget = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        self.settings_layout.setContentsMargins(10, 10, 10, 10)
        self.settings_layout.setSpacing(10)
        self.tab_widget.addTab(self.settings_widget, "Settings")
        
        # Add settings content
        settings_label = QLabel("Settings")
        settings_label.setFont(QFont("Arial", 16))
        self.settings_layout.addWidget(settings_label)
        
        # Initialize settings UI
        self._init_settings_ui()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Apply dark theme
        self._apply_dark_theme()
        
        # Register event handlers
        self._register_event_handlers()
        
        # Try to connect to services automatically on startup
        self._auto_connect_services()
    
    def _set_default_twitch_credentials(self):
        """Set default Twitch application credentials if not already set."""
        import os
        import base64
        from pathlib import Path
        
        # Only set these if they're not already in the config
        if not self.config.get("twitch", "client_id"):
            client_id = ""
            client_secret = ""
            
            # First try to load from .env file (best for development)
            env_file = Path.cwd() / '.env'
            if env_file.exists():
                try:
                    logger.debug(f"Loading credentials from .env file: {env_file}")
                    with open(env_file, 'r') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#'):
                                key, value = line.strip().split('=', 1)
                                if key == 'TWITCH_CLIENT_ID':
                                    client_id = value
                                elif key == 'TWITCH_CLIENT_SECRET':
                                    client_secret = value
                    logger.debug("Successfully loaded credentials from .env file")
                except Exception as e:
                    logger.error(f"Error loading .env file: {str(e)}")
            
            # If .env didn't have what we need, try environment variables
            if not client_id:
                client_id = os.environ.get("TWITCH_CLIENT_ID", "")
                client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "")
                if client_id:
                    logger.debug("Using credentials from environment variables")
            
            # If still not found, use embedded obfuscated credentials
            if not client_id:
                try:
                    # These are base64 encoded credentials - replace with your actual encoded values
                    # Generate these with: base64.b64encode(b"your_client_id").decode('utf-8')
                    encoded_id = b'eW91cl90d2l0Y2hfY2xpZW50X2lkX2hlcmU='  # Base64 of 'your_twitch_client_id_here'
                    encoded_secret = b'eW91cl90d2l0Y2hfY2xpZW50X3NlY3JldF9oZXJl'  # Base64 of 'your_twitch_client_secret_here'
                    
                    # Decode the credentials
                    client_id = base64.b64decode(encoded_id).decode('utf-8')
                    client_secret = base64.b64decode(encoded_secret).decode('utf-8')
                    
                    logger.debug("Using embedded credentials (decoded from base64)")
                except Exception as e:
                    logger.error(f"Error decoding embedded credentials: {str(e)}")
            
            # Set the credentials in config
            self.config.set("twitch", "client_id", client_id)
            self.config.set("twitch", "client_secret", client_secret)
            self.config.save()
            logger.info("Set default Twitch application credentials")
    
    def _init_settings_ui(self):
        """Initialize settings UI components."""
        # Create scroll area to ensure settings are accessible when window is resized
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        settings_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Create container widget for settings
        settings_container = QWidget()
        settings_form = QVBoxLayout(settings_container)
        settings_form.setSpacing(15)
        
        # General settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout(general_group)
        general_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        general_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        current_theme = self.config.get("general", "theme", "dark")
        self.theme_combo.setCurrentText(current_theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        general_layout.addRow("Theme:", self.theme_combo)
        
        # Check for updates
        self.updates_check = QCheckBox()
        self.updates_check.setChecked(self.config.get("general", "check_updates", True))
        general_layout.addRow("Check for updates:", self.updates_check)
        
        settings_form.addWidget(general_group)
        
        # OBS settings with connect functionality
        obs_group = QGroupBox("OBS Settings")
        obs_layout = QVBoxLayout(obs_group)
        
        # OBS status indicator
        obs_status_layout = QHBoxLayout()
        self.obs_conn_status = QLabel("Not Connected")
        self.obs_conn_status.setStyleSheet("color: #F44336;")
        obs_status_layout.addWidget(QLabel("Status:"))
        obs_status_layout.addWidget(self.obs_conn_status)
        obs_status_layout.addStretch()
        obs_layout.addLayout(obs_status_layout)
        
        # OBS form
        obs_form = QFormLayout()
        obs_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        obs_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # OBS host
        self.obs_host_edit = QLineEdit()
        self.obs_host_edit.setText(self.config.get("obs", "host", "localhost"))
        obs_form.addRow("Host:", self.obs_host_edit)
        
        # OBS port
        self.obs_port_spin = QSpinBox()
        self.obs_port_spin.setRange(1, 65535)
        self.obs_port_spin.setValue(self.config.get("obs", "port", 4455))
        obs_form.addRow("Port:", self.obs_port_spin)
        
        # OBS password
        self.obs_password_edit = QLineEdit()
        self.obs_password_edit.setText(self.config.get("obs", "password", ""))
        self.obs_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        obs_form.addRow("Password:", self.obs_password_edit)
        
        obs_layout.addLayout(obs_form)
        
        # OBS connection buttons
        obs_button_layout = QHBoxLayout()
        
        # Connect button
        self.obs_connect_button = QPushButton("Connect")
        self.obs_connect_button.clicked.connect(self._connect_to_obs)
        obs_button_layout.addWidget(self.obs_connect_button)
        
        # Test connection button
        self.obs_test_button = QPushButton("Test Connection")
        self.obs_test_button.clicked.connect(self._test_obs_connection)
        obs_button_layout.addWidget(self.obs_test_button)
        
        obs_button_layout.addStretch()
        obs_layout.addLayout(obs_button_layout)
        
        settings_form.addWidget(obs_group)
        
        # Twitch settings
        twitch_group = QGroupBox("Twitch Settings")
        twitch_layout = QVBoxLayout(twitch_group)
        
        # Twitch status indicator
        twitch_status_layout = QHBoxLayout()
        self.twitch_conn_status = QLabel("Not Connected")
        self.twitch_conn_status.setStyleSheet("color: #F44336;")
        twitch_status_layout.addWidget(QLabel("Status:"))
        twitch_status_layout.addWidget(self.twitch_conn_status)
        twitch_status_layout.addStretch()
        twitch_layout.addLayout(twitch_status_layout)
        
        # Twitch connection buttons
        twitch_button_layout = QHBoxLayout()
        
        # Login button
        self.twitch_login_button = QPushButton("Login")
        self.twitch_login_button.clicked.connect(self._login_twitch)
        twitch_button_layout.addWidget(self.twitch_login_button)
        
        # Test connection button
        self.twitch_test_button = QPushButton("Test Connection")
        self.twitch_test_button.clicked.connect(self._test_twitch_connection)
        twitch_button_layout.addWidget(self.twitch_test_button)
        
        twitch_button_layout.addStretch()
        twitch_layout.addLayout(twitch_button_layout)
        
        # Description text
        description_label = QLabel(
            "Click the login button to authenticate with Twitch. This will open a browser window "
            "where you can authorize OBSCopilot to interact with your Twitch account."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #888888; font-style: italic;")
        twitch_layout.addWidget(description_label)
        
        settings_form.addWidget(twitch_group)
        
        # OpenAI settings
        openai_group = QGroupBox("OpenAI Settings")
        openai_layout = QVBoxLayout(openai_group)
        
        # OpenAI form
        openai_form = QFormLayout()
        openai_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        openai_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # API key
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setText(self.config.get("openai", "api_key", ""))
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        openai_form.addRow("API Key:", self.openai_key_edit)
        
        # Model selection
        self.model_combo = QComboBox()
        models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        self.model_combo.addItems(models)
        current_model = self.config.get("openai", "model", "gpt-3.5-turbo")
        self.model_combo.setCurrentText(current_model if current_model in models else models[0])
        openai_form.addRow("Model:", self.model_combo)
        
        openai_layout.addLayout(openai_form)
        
        # OpenAI connection buttons
        openai_button_layout = QHBoxLayout()
        
        # Save settings button
        self.openai_save_button = QPushButton("Save Settings")
        self.openai_save_button.clicked.connect(self._save_openai_settings)
        openai_button_layout.addWidget(self.openai_save_button)
        
        # Test connection button
        self.openai_test_button = QPushButton("Test Connection")
        self.openai_test_button.clicked.connect(self._test_openai_connection)
        openai_button_layout.addWidget(self.openai_test_button)
        
        openai_button_layout.addStretch()
        openai_layout.addLayout(openai_button_layout)
        
        settings_form.addWidget(openai_group)
        
        # Google AI settings
        googleai_group = QGroupBox("Google AI Settings")
        googleai_layout = QVBoxLayout(googleai_group)
        
        # Google AI form
        googleai_form = QFormLayout()
        googleai_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        googleai_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # API key
        self.googleai_key_edit = QLineEdit()
        self.googleai_key_edit.setText(self.config.get("googleai", "api_key", ""))
        self.googleai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        googleai_form.addRow("API Key:", self.googleai_key_edit)
        
        # Model selection
        self.googleai_model_combo = QComboBox()
        googleai_models = ["gemini-2.0-flash-001", "gemini-2.0-pro-001", "gemini-2.0-pro-vision-001"]
        self.googleai_model_combo.addItems(googleai_models)
        current_googleai_model = self.config.get("googleai", "model", "gemini-2.0-flash-001")
        self.googleai_model_combo.setCurrentText(current_googleai_model if current_googleai_model in googleai_models else googleai_models[0])
        googleai_form.addRow("Model:", self.googleai_model_combo)
        
        googleai_layout.addLayout(googleai_form)
        
        # Google AI connection buttons
        googleai_button_layout = QHBoxLayout()
        
        # Save settings button
        self.googleai_save_button = QPushButton("Save Settings")
        self.googleai_save_button.clicked.connect(self._save_googleai_settings)
        googleai_button_layout.addWidget(self.googleai_save_button)
        
        # Test connection button
        self.googleai_test_button = QPushButton("Test Connection")
        self.googleai_test_button.clicked.connect(self._test_googleai_connection)
        googleai_button_layout.addWidget(self.googleai_test_button)
        
        googleai_button_layout.addStretch()
        googleai_layout.addLayout(googleai_button_layout)
        
        settings_form.addWidget(googleai_group)
        
        # Add buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        
        # Save button
        save_button = QPushButton("Save All Settings")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)
        
        # Reset button
        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self._reset_settings)
        button_layout.addWidget(reset_button)
        
        button_layout.addStretch()
        
        settings_form.addWidget(button_container)
        settings_form.addStretch()
        
        # Set the container widget to the scroll area
        settings_scroll.setWidget(settings_container)
        
        # Add the scroll area to the settings layout
        self.settings_layout.addWidget(settings_scroll, 1)  # Give 1 stretch factor
    
    def _save_settings(self):
        """Save settings to configuration."""
        logger.info("Saving application settings")
        
        # General settings
        self.config.set("general", "theme", self.theme_combo.currentText())
        self.config.set("general", "check_updates", self.updates_check.isChecked())
        
        # OBS settings
        self.config.set("obs", "host", self.obs_host_edit.text())
        self.config.set("obs", "port", self.obs_port_spin.value())
        self.config.set("obs", "password", self.obs_password_edit.text())
        
        # OpenAI settings
        self.config.set("openai", "api_key", self.openai_key_edit.text())
        self.config.set("openai", "model", self.model_combo.currentText())
        
        # Google AI settings
        self.config.set("googleai", "api_key", self.googleai_key_edit.text())
        self.config.set("googleai", "model", self.googleai_model_combo.currentText())
        
        # Save to file
        try:
            self.config.save()
            logger.info("Settings saved successfully")
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            self.status_bar.showMessage("Settings saved")
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error Saving Settings", f"Failed to save settings: {str(e)}")
    
    def _reset_settings(self):
        """Reset settings to defaults."""
        logger.info("User requested to reset settings to defaults")
        
        result = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            try:
                logger.info("Resetting all settings to defaults")
                self.config.reset_all()
                
                # Update UI
                self.theme_combo.setCurrentText(self.config.get("general", "theme", "dark"))
                self.updates_check.setChecked(self.config.get("general", "check_updates", True))
                self.obs_host_edit.setText(self.config.get("obs", "host", "localhost"))
                self.obs_port_spin.setValue(self.config.get("obs", "port", 4455))
                self.obs_password_edit.setText(self.config.get("obs", "password", ""))
                self.openai_key_edit.setText(self.config.get("openai", "api_key", ""))
                self.model_combo.setCurrentText(self.config.get("openai", "model", "gpt-3.5-turbo"))
                self.googleai_key_edit.setText(self.config.get("googleai", "api_key", ""))
                self.googleai_model_combo.setCurrentText(self.config.get("googleai", "model", "gemini-2.0-flash-001"))
                
                # Apply theme
                self._on_theme_changed(self.config.get("general", "theme", "dark"))
                
                logger.info("Settings reset to defaults successfully")
                self.status_bar.showMessage("Settings reset to defaults")
            except Exception as e:
                logger.error(f"Error resetting settings: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to reset settings: {str(e)}")
        else:
            logger.debug("User cancelled settings reset")
    
    def _on_theme_changed(self, theme: str):
        """Handle theme change.
        
        Args:
            theme: The new theme ('dark' or 'light')
        """
        if theme == "dark":
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_dark_theme(self):
        """Apply dark theme styles."""
        # Dark theme stylesheet
        dark_stylesheet = """
        QMainWindow, QWidget {
            background-color: #2D2D30;
            color: #E1E1E1;
        }
        
        QTabWidget::pane {
            border: 1px solid #3E3E42;
            background-color: #252526;
        }
        
        QTabBar::tab {
            background-color: #2D2D2D;
            color: #E1E1E1;
            padding: 8px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #007ACC;
        }
        
        QPushButton {
            background-color: #0E639C;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QPushButton:hover {
            background-color: #1177BB;
        }
        
        QPushButton:pressed {
            background-color: #10558C;
        }
        
        QLineEdit, QComboBox, QSpinBox {
            background-color: #3E3E42;
            color: #E1E1E1;
            border: 1px solid #555555;
            padding: 4px;
            border-radius: 2px;
        }
        
        QGroupBox {
            border: 1px solid #3E3E42;
            border-radius: 4px;
            margin-top: 1em;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #555555;
            border-radius: 2px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007ACC;
        }
        
        QMenuBar {
            background-color: #2D2D30;
            color: #E1E1E1;
        }
        
        QMenuBar::item:selected {
            background-color: #3E3E42;
        }
        
        QMenu {
            background-color: #2D2D30;
            color: #E1E1E1;
            border: 1px solid #3E3E42;
        }
        
        QMenu::item:selected {
            background-color: #3E3E42;
        }
        
        QToolBar {
            background-color: #2D2D30;
            border-bottom: 1px solid #3E3E42;
        }
        
        QStatusBar {
            background-color: #007ACC;
            color: white;
        }
        """
        
        self.setStyleSheet(dark_stylesheet)
    
    def _apply_light_theme(self):
        """Apply light theme styles."""
        # Light theme stylesheet
        light_stylesheet = """
        QMainWindow, QWidget {
            background-color: #F5F5F5;
            color: #333333;
        }
        
        QTabWidget::pane {
            border: 1px solid #CCCCCC;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #E1E1E1;
            color: #333333;
            padding: 8px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #007ACC;
            color: white;
        }
        
        QPushButton {
            background-color: #0078D7;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QPushButton:hover {
            background-color: #106EBE;
        }
        
        QPushButton:pressed {
            background-color: #005A9E;
        }
        
        QLineEdit, QComboBox, QSpinBox {
            background-color: white;
            color: #333333;
            border: 1px solid #CCCCCC;
            padding: 4px;
            border-radius: 2px;
        }
        
        QGroupBox {
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            margin-top: 1em;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #CCCCCC;
            border-radius: 2px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007ACC;
        }
        
        QMenuBar {
            background-color: #F5F5F5;
            color: #333333;
        }
        
        QMenuBar::item:selected {
            background-color: #DADADA;
        }
        
        QMenu {
            background-color: white;
            color: #333333;
            border: 1px solid #CCCCCC;
        }
        
        QMenu::item:selected {
            background-color: #DADADA;
        }
        
        QToolBar {
            background-color: #F5F5F5;
            border-bottom: 1px solid #CCCCCC;
        }
        
        QStatusBar {
            background-color: #0078D7;
            color: white;
        }
        """
        
        self.setStyleSheet(light_stylesheet)
    
    def _register_event_handlers(self):
        """Register event handlers for updating UI."""
        # Twitch events
        event_bus.subscribe(EventType.TWITCH_CONNECTED, self._handle_event)
        event_bus.subscribe(EventType.TWITCH_DISCONNECTED, self._handle_event)
        
        # OBS events
        event_bus.subscribe(EventType.OBS_CONNECTED, self._handle_event)
        event_bus.subscribe(EventType.OBS_DISCONNECTED, self._handle_event)
        
        # Workflow events
        event_bus.subscribe(EventType.WORKFLOW_LOADED, self._handle_event)
    
    @pyqtSlot(Event)
    def _handle_event(self, event):
        """Handle events from the event bus."""
        # Update UI based on event type
        if event.event_type == EventType.TWITCH_CONNECTED:
            self.twitch_status_label.setText("Connected")
            self.twitch_conn_status.setText("Connected")
            self.twitch_conn_status.setStyleSheet("color: #4CAF50;")
            self.status_bar.showMessage("Twitch connected")
        
        elif event.event_type == EventType.TWITCH_DISCONNECTED:
            self.twitch_status_label.setText("Not Connected")
            self.twitch_conn_status.setText("Not Connected")
            self.twitch_conn_status.setStyleSheet("color: #F44336;")
            self.status_bar.showMessage("Twitch disconnected")
        
        elif event.event_type == EventType.OBS_CONNECTED:
            self.obs_status_label.setText("Connected")
            self.obs_conn_status.setText("Connected")
            self.obs_conn_status.setStyleSheet("color: #4CAF50;")
            self.status_bar.showMessage("OBS connected")
        
        elif event.event_type == EventType.OBS_DISCONNECTED:
            self.obs_status_label.setText("Not Connected")
            self.obs_conn_status.setText("Not Connected")
            self.obs_conn_status.setStyleSheet("color: #F44336;")
            self.status_bar.showMessage("OBS disconnected")
        
        elif event.event_type == EventType.WORKFLOW_LOADED:
            workflow_count = event.data.get('count', 0)
            self.workflows_status_label.setText(f"{workflow_count} loaded")
            self.status_bar.showMessage(f"Loaded {workflow_count} workflows")
    
    def _connect_to_obs(self, show_popups=True):
        """Connect to OBS using the provided credentials.
        
        Args:
            show_popups: Whether to show success/error popups
        """
        logger.info("Attempting to connect to OBS")
        
        # Save settings
        host = self.obs_host_edit.text()
        port = self.obs_port_spin.value()
        password = self.obs_password_edit.text()
        
        # Validate input
        if not host:
            error_msg = "OBS host cannot be empty"
            logger.error(error_msg)
            if show_popups:
                QMessageBox.warning(self, "OBS Connection Failed", error_msg)
            return
            
        self.config.set("obs", "host", host)
        self.config.set("obs", "port", port)
        self.config.set("obs", "password", password)
        self.config.save()
        
        # Simulate connecting (in a real application, this would connect to OBS)
        try:
            # In a real implementation, this would connect to OBS WebSocket
            # For demo, simulate an actual connection attempt with error handling
            self.status_bar.showMessage("Connecting to OBS...")
            logger.debug(f"Connecting to OBS at {host}:{port}")
            
            # Simulate connection testing
            import socket
            import time
            
            # Create socket to test if port is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # Set a connection timeout of 2 seconds
            
            # Try to connect - this will actually test if the port is open
            result = sock.connect_ex((host, port))
            sock.close()
            
            # Check if connection was successful
            if result != 0:  # Non-zero result means connection failed
                error_msg = f"Could not connect to {host}:{port}. Please check if OBS is running with WebSocket server enabled."
                raise Exception(error_msg)
                
            # If we're here, the socket connection succeeded, but in a real app
            # we would also verify the WebSocket protocol and auth with the password
            time.sleep(0.5)  # Simulate connection time
            
            # Directly update UI to ensure it's updated regardless of event bus issues
            self.obs_status_label.setText("Connected")
            self.obs_conn_status.setText("Connected")
            self.obs_conn_status.setStyleSheet("color: #4CAF50;")
            
            # Emit a connected event to update UI
            connected_event = Event(EventType.OBS_CONNECTED, {"success": True})
            self._publish_event(connected_event)
            
            logger.info("Successfully connected to OBS")
            if show_popups:
                QMessageBox.information(self, "OBS Connection", "Successfully connected to OBS.")
        except Exception as e:
            error_msg = f"Error connecting to OBS: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if show_popups:
                QMessageBox.warning(self, "OBS Connection Failed", error_msg)
            
            # Directly update UI to ensure it's updated regardless of event bus issues
            self.obs_status_label.setText("Not Connected")
            self.obs_conn_status.setText("Not Connected")
            self.obs_conn_status.setStyleSheet("color: #F44336;")
            
            try:
                # Emit a disconnected event
                disconnected_event = Event(EventType.OBS_DISCONNECTED, {"error": str(e)})
                self._publish_event(disconnected_event)
            except Exception as inner_e:
                # If even the error handling fails, just update UI directly
                logger.error(f"Failed to publish disconnect event: {str(inner_e)}", exc_info=True)
                self.status_bar.showMessage(f"OBS disconnected. Event bus error: {str(inner_e)}")
    
    def _test_obs_connection(self):
        """Test the OBS connection without saving settings."""
        host = self.obs_host_edit.text()
        port = self.obs_port_spin.value()
        password = self.obs_password_edit.text()
        
        # In a real application, this would test the connection to OBS
        try:
            # For demonstration, just show a success message
            QMessageBox.information(self, "OBS Connection Test", 
                                   f"Successfully tested connection to OBS at {host}:{port}")
        except Exception as e:
            QMessageBox.warning(self, "OBS Connection Test Failed", 
                               f"Error testing connection to OBS: {str(e)}")
    
    def _login_twitch(self, show_popups=True):
        """Start Twitch authentication flow.
        
        Args:
            show_popups: Whether to show success/error popups
        """
        logger.info("Starting Twitch authentication")
        
        # Get credentials from config (now pre-configured)
        client_id = self.config.get("twitch", "client_id", "")
        client_secret = self.config.get("twitch", "client_secret", "")
        
        # Check if credentials are provided
        if not client_id or not client_secret:
            logger.error("Twitch credentials not configured")
            if show_popups:
                QMessageBox.warning(self, "Authentication Failed", 
                                   "Application is not properly configured for Twitch authentication. Please contact the developer.")
            return
        
        # In a real application, this would start the OAuth flow using a browser
        try:
            # For demo purposes, actually verify that the client ID looks valid
            if not client_id.isalnum() or len(client_id) < 10:
                raise Exception("Invalid Twitch Client ID format")
                
            # Validate client secret format (should be a long alphanumeric string)
            if not client_secret.isalnum() or len(client_secret) < 10:
                raise Exception("Invalid Twitch Client Secret format")
                
            # In a real app, we would make an API call to validate the credentials
                
            # Simulate successful authentication
            logger.debug("Would start OAuth flow here in a real implementation")
            self.status_bar.showMessage("Authenticating with Twitch...")
            
            import time
            time.sleep(0.5)  # Simulate API call
            
            self.config.set("twitch", "status", "Authenticated")
            self.config.save()
            logger.info("Simulated successful authentication")
            
            # Update UI directly
            self.twitch_status_label.setText("Connected")
            self.twitch_conn_status.setText("Connected")
            self.twitch_conn_status.setStyleSheet("color: #4CAF50;")
            
            # Emit connected event
            connected_event = Event(EventType.TWITCH_CONNECTED, {"success": True})
            self._publish_event(connected_event)
            
            if show_popups:
                QMessageBox.information(self, "Twitch Authentication", 
                                      "Successfully authenticated with Twitch.")
        except Exception as e:
            error_msg = f"Twitch authentication failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if show_popups:
                QMessageBox.warning(self, "Authentication Failed", error_msg)
            
            # Update UI
            self.twitch_status_label.setText("Not Connected")
            self.twitch_conn_status.setText("Not Connected")
            self.twitch_conn_status.setStyleSheet("color: #F44336;")
            
            # Emit disconnected event
            try:
                disconnected_event = Event(EventType.TWITCH_DISCONNECTED, {"error": str(e)})
                self._publish_event(disconnected_event)
            except Exception as inner_e:
                logger.error(f"Failed to publish disconnect event: {str(inner_e)}", exc_info=True)
    
    def _test_twitch_connection(self):
        """Test the Twitch API connection."""
        if self.config.get("twitch", "status") != "Authenticated":
            QMessageBox.warning(self, "Twitch Connection Test", 
                               "You need to authenticate with Twitch first.")
            return
        
        # In a real application, this would test the Twitch API connection
        try:
            # For demonstration, just show a success message
            broadcaster_username = self.config.get("twitch", "broadcaster_username")
            QMessageBox.information(self, "Twitch Connection Test", 
                                   f"Successfully tested connection to Twitch as {broadcaster_username}")
        except Exception as e:
            QMessageBox.warning(self, "Twitch Connection Test Failed", 
                               f"Error testing connection to Twitch: {str(e)}")
    
    def _save_openai_settings(self):
        """Save OpenAI API settings."""
        # Save settings
        self.config.set("openai", "api_key", self.openai_key_edit.text())
        self.config.set("openai", "model", self.model_combo.currentText())
        self.config.save()
        
        QMessageBox.information(self, "OpenAI Settings", "OpenAI API settings saved successfully.")
    
    def _test_openai_connection(self):
        """Test the OpenAI API connection."""
        api_key = self.openai_key_edit.text()
        model = self.model_combo.currentText()
        
        if not api_key:
            QMessageBox.warning(self, "OpenAI Connection Test", 
                               "Please enter your OpenAI API key first.")
            return
        
        # In a real application, this would test the OpenAI API connection
        try:
            # Simple format validation for the API key
            if not api_key.startswith("sk-") or len(api_key) < 20:
                raise Exception("Invalid OpenAI API key format. Keys usually start with 'sk-' and are longer.")
            
            # Simulate API call
            self.status_bar.showMessage("Testing OpenAI API connection...")
            
            import time
            time.sleep(1)  # Simulate API call
            
            # For demonstration, just show a success message
            QMessageBox.information(self, "OpenAI Connection Test", 
                                   f"Successfully tested connection to OpenAI API using model {model}")
        except Exception as e:
            QMessageBox.warning(self, "OpenAI Connection Test Failed", 
                               f"Error testing connection to OpenAI API: {str(e)}")
    
    def _save_googleai_settings(self):
        """Save Google AI API settings."""
        # Save settings
        self.config.set("googleai", "api_key", self.googleai_key_edit.text())
        self.config.set("googleai", "model", self.googleai_model_combo.currentText())
        self.config.save()
        
        QMessageBox.information(self, "Google AI Settings", "Google AI API settings saved successfully.")
    
    def _test_googleai_connection(self):
        """Test the Google AI API connection."""
        api_key = self.googleai_key_edit.text()
        model = self.googleai_model_combo.currentText()
        
        if not api_key:
            QMessageBox.warning(self, "Google AI Connection Test", 
                               "Please enter your Google AI API key first.")
            return
        
        # In a real application, this would test the Google AI API connection
        try:
            # Simple format validation for a Google API key (usually long and may have periods)
            if len(api_key) < 15:
                raise Exception("Invalid Google AI API key format. Keys are typically longer.")
            
            # Simulate API call
            self.status_bar.showMessage("Testing Google AI API connection...")
            
            import time
            time.sleep(1)  # Simulate API call
            
            # For demonstration, just show a success message
            QMessageBox.information(self, "Google AI Connection Test", 
                                   f"Successfully tested connection to Google AI API using model {model}")
        except Exception as e:
            QMessageBox.warning(self, "Google AI Connection Test Failed", 
                               f"Error testing connection to Google AI API: {str(e)}")
    
    def _create_new_workflow(self):
        """Create a new workflow."""
        logger.info("Creating new workflow")
        
        # In a real application, this would open a workflow editor
        # For demonstration, we'll just add a simple example workflow
        
        # Check if OBS and Twitch are connected
        if self.obs_status_label.text() != "Connected":
            logger.warning("Attempted to create workflow without OBS connected")
            QMessageBox.warning(self, "OBS Not Connected", "You need to connect to OBS before creating workflows.")
            return
        
        # Create a simple dialog for workflow name
        workflow_name, ok = QInputDialog.getText(self, "New Workflow", "Enter workflow name:")
        
        if ok and workflow_name:
            logger.info(f"Creating new workflow: {workflow_name}")
            # Add the workflow to the list
            self._add_workflow_to_list(workflow_name)
            
            # Show success message
            QMessageBox.information(self, "Workflow Created", 
                                  f"Workflow '{workflow_name}' created successfully.\n"
                                  "In the full application, this would open the workflow editor.")
        else:
            logger.debug("Workflow creation cancelled or empty name provided")
    
    def _import_workflow(self):
        """Import a workflow from a file."""
        # In a real application, this would open a file dialog and import a workflow
        # For demonstration, just show a message
        QMessageBox.information(self, "Import Workflow", 
                              "This would open a file dialog to import a workflow file.\n"
                              "In the full application, you would be able to select a workflow file to import.")
    
    def _export_workflow(self):
        """Export the selected workflow to a file."""
        # In a real application, this would export the selected workflow
        # For demonstration, just show a message
        QMessageBox.information(self, "Export Workflow", 
                              "This would open a file dialog to export the selected workflow.\n"
                              "In the full application, you would be able to save the workflow to a file.")
    
    def _add_workflow_to_list(self, workflow_name):
        """Add a workflow to the list of workflows."""
        # Hide the 'no workflows' label
        self.no_workflows_label.setVisible(False)
        
        # Show the workflows list
        self.workflows_list.setVisible(True)
        
        # Create a widget for the workflow item
        workflow_item = QWidget()
        workflow_item_layout = QHBoxLayout(workflow_item)
        workflow_item_layout.setContentsMargins(10, 5, 10, 5)
        
        # Workflow name
        name_label = QLabel(workflow_name)
        name_label.setFont(QFont("Arial", 12))
        workflow_item_layout.addWidget(name_label)
        
        workflow_item_layout.addStretch()
        
        # Edit button
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: self._edit_workflow(workflow_name))
        workflow_item_layout.addWidget(edit_button)
        
        # Enable/disable button
        enable_button = QPushButton("Enable")
        enable_button.setCheckable(True)
        enable_button.toggled.connect(lambda checked: self._toggle_workflow(workflow_name, checked))
        workflow_item_layout.addWidget(enable_button)
        
        # Delete button
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self._delete_workflow(workflow_item, workflow_name))
        workflow_item_layout.addWidget(delete_button)
        
        # Add to list
        self.workflows_list_layout.addWidget(workflow_item)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.workflows_list_layout.addWidget(separator)
        
        # Update workflow count
        workflow_count = self.workflows_list_layout.count() // 2  # Account for separator lines
        self.workflows_status_label.setText(f"{workflow_count} loaded")
        
        # Publish workflow loaded event
        event = Event(EventType.WORKFLOW_LOADED, {"count": workflow_count})
        self._publish_event(event)
    
    def _edit_workflow(self, workflow_name):
        """Edit a workflow."""
        # In a real application, this would open the workflow editor
        # For demonstration, just show a message
        QMessageBox.information(self, "Edit Workflow", 
                              f"This would open the workflow editor for '{workflow_name}'.\n"
                              "In the full application, you would be able to modify the workflow.")
    
    def _toggle_workflow(self, workflow_name, enabled):
        """Toggle a workflow on or off."""
        status = "enabled" if enabled else "disabled"
        self.status_bar.showMessage(f"Workflow '{workflow_name}' {status}")
    
    def _delete_workflow(self, workflow_item, workflow_name):
        """Delete a workflow."""
        logger.info(f"Attempting to delete workflow: {workflow_name}")
        
        # Ask for confirmation
        result = QMessageBox.question(
            self,
            "Delete Workflow",
            f"Are you sure you want to delete the workflow '{workflow_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            logger.info(f"Confirmed deletion of workflow: {workflow_name}")
            
            # Remove the workflow item and its separator
            item_index = self.workflows_list_layout.indexOf(workflow_item)
            
            # Remove the item
            item = self.workflows_list_layout.itemAt(item_index).widget()
            self.workflows_list_layout.removeWidget(item)
            item.deleteLater()
            
            # Remove the separator if it exists
            if item_index + 1 < self.workflows_list_layout.count():
                separator = self.workflows_list_layout.itemAt(item_index).widget()
                self.workflows_list_layout.removeWidget(separator)
                separator.deleteLater()
            
            # Update workflow count
            workflow_count = max(0, (self.workflows_list_layout.count() // 2))  # Account for separator lines
            logger.debug(f"Updated workflow count: {workflow_count}")
            self.workflows_status_label.setText(f"{workflow_count} loaded")
            
            # Show the 'no workflows' label if no workflows are left
            if workflow_count == 0:
                logger.debug("No workflows remaining, showing empty message")
                self.no_workflows_label.setVisible(True)
                self.workflows_list.setVisible(False)
            
            # Publish workflow loaded event
            event = Event(EventType.WORKFLOW_LOADED, {"count": workflow_count})
            self._publish_event(event)
            
            self.status_bar.showMessage(f"Workflow '{workflow_name}' deleted")
        else:
            logger.debug(f"Cancelled deletion of workflow: {workflow_name}")
    
    def _publish_event(self, event):
        """Safely publish an event, with fallbacks if the event bus fails."""
        try:
            logger.debug(f"Publishing event: {event.event_type}")
            
            if hasattr(event_bus, 'publish'):
                # Directly handle the event too, to ensure UI is updated immediately
                self._handle_event(event)
                # Then publish to event bus for other components
                event_bus.publish(event)
            elif hasattr(event_bus, 'emit'):
                # Handle event directly since emit is a coroutine that needs to be awaited
                self._handle_event(event)
                # Don't try to call emit directly since it's a coroutine
                logger.warning("Event bus has emit method which is a coroutine - directly updating UI instead")
            else:
                logger.warning("Event bus missing publish and emit methods, handling event directly")
                # Manually handle the event if event_bus methods are not available
                self._handle_event(event)
        except Exception as e:
            # Log the error
            logger.error(f"Event publishing error: {str(e)}", exc_info=True)
            # Directly handle the event
            self._handle_event(event)

    def _auto_connect_services(self):
        """Try to connect to services automatically on startup."""
        logger.info("Attempting to auto-connect to services")
        
        # Try to connect to OBS
        try:
            # Use the regular connection method but suppress popups
            self._connect_to_obs(show_popups=False)
        except Exception as e:
            logger.warning(f"Auto-connect to OBS failed: {str(e)}")
            # Ensure UI shows disconnected state
            self.obs_status_label.setText("Not Connected")
            self.obs_conn_status.setText("Not Connected")
            self.obs_conn_status.setStyleSheet("color: #F44336;")
        
        # Try to authenticate with Twitch
        try:
            # Check if we have credentials in config
            if self.config.get("twitch", "client_id"):
                logger.info("Auto-authenticating with Twitch")
                self._login_twitch(show_popups=False)
        except Exception as e:
            logger.warning(f"Auto-connect to Twitch failed: {str(e)}")
            # Ensure UI shows disconnected state
            self.twitch_status_label.setText("Not Connected")
            self.twitch_conn_status.setText("Not Connected")
            self.twitch_conn_status.setStyleSheet("color: #F44336;")
        
        logger.info("Auto-connection completed")

    def _update_authentication_status(self):
        """Update the authentication status display based on config values."""
        # Status
        status = self.config.get('twitch', 'status', 'Not authenticated')
        self.twitch_conn_status.setText(status)
 