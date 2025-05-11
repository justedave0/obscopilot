"""
Simple UI module for OBSCopilot.

This module provides a simplified UI that doesn't require complex dependencies.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTabWidget, QStatusBar, 
    QFormLayout, QLineEdit, QCheckBox, QComboBox,
    QSpinBox, QGroupBox, QMessageBox
)

from obscopilot.core.config import Config
from obscopilot.core.events import event_bus, Event, EventType

class SimpleMainWindow(QMainWindow):
    """Simple main window for OBSCopilot."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Create a default config
        self.config = Config()
        
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
        
        # Create connections tab
        self.connections_widget = QWidget()
        self.connections_layout = QVBoxLayout(self.connections_widget)
        self.tab_widget.addTab(self.connections_widget, "Connections")
        
        # Add connections content
        connections_label = QLabel("Connections")
        connections_label.setFont(QFont("Arial", 16))
        self.connections_layout.addWidget(connections_label)
        
        # Add spacer
        self.connections_layout.addStretch()
        
        # Create workflows tab
        self.workflows_widget = QWidget()
        self.workflows_layout = QVBoxLayout(self.workflows_widget)
        self.tab_widget.addTab(self.workflows_widget, "Workflows")
        
        # Add workflows content
        workflows_label = QLabel("Workflows")
        workflows_label.setFont(QFont("Arial", 16))
        self.workflows_layout.addWidget(workflows_label)
        
        # Add spacer
        self.workflows_layout.addStretch()
        
        # Create settings tab
        self.settings_widget = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
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
    
    def _init_settings_ui(self):
        """Initialize settings UI components."""
        # Create form layout for settings
        settings_container = QWidget()
        settings_form = QVBoxLayout(settings_container)
        
        # General settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout(general_group)
        
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
        
        # Twitch settings
        twitch_group = QGroupBox("Twitch Settings")
        twitch_layout = QFormLayout(twitch_group)
        
        # Broadcaster client ID
        self.broadcaster_id_edit = QLineEdit()
        self.broadcaster_id_edit.setText(self.config.get("twitch", "broadcaster_client_id", ""))
        self.broadcaster_id_edit.setPlaceholderText("Enter your Twitch Client ID")
        twitch_layout.addRow("Broadcaster Client ID:", self.broadcaster_id_edit)
        
        # Broadcaster client secret
        self.broadcaster_secret_edit = QLineEdit()
        self.broadcaster_secret_edit.setText(self.config.get("twitch", "broadcaster_client_secret", ""))
        self.broadcaster_secret_edit.setPlaceholderText("Enter your Twitch Client Secret")
        self.broadcaster_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        twitch_layout.addRow("Broadcaster Client Secret:", self.broadcaster_secret_edit)
        
        settings_form.addWidget(twitch_group)
        
        # OBS settings
        obs_group = QGroupBox("OBS Settings")
        obs_layout = QFormLayout(obs_group)
        
        # OBS host
        self.obs_host_edit = QLineEdit()
        self.obs_host_edit.setText(self.config.get("obs", "host", "localhost"))
        obs_layout.addRow("Host:", self.obs_host_edit)
        
        # OBS port
        self.obs_port_spin = QSpinBox()
        self.obs_port_spin.setRange(1, 65535)
        self.obs_port_spin.setValue(self.config.get("obs", "port", 4455))
        obs_layout.addRow("Port:", self.obs_port_spin)
        
        # OBS password
        self.obs_password_edit = QLineEdit()
        self.obs_password_edit.setText(self.config.get("obs", "password", ""))
        self.obs_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        obs_layout.addRow("Password:", self.obs_password_edit)
        
        settings_form.addWidget(obs_group)
        
        # OpenAI settings
        openai_group = QGroupBox("OpenAI Settings")
        openai_layout = QFormLayout(openai_group)
        
        # API key
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setText(self.config.get("openai", "api_key", ""))
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        openai_layout.addRow("API Key:", self.openai_key_edit)
        
        # Model selection
        self.model_combo = QComboBox()
        models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        self.model_combo.addItems(models)
        current_model = self.config.get("openai", "model", "gpt-3.5-turbo")
        self.model_combo.setCurrentText(current_model if current_model in models else models[0])
        openai_layout.addRow("Model:", self.model_combo)
        
        settings_form.addWidget(openai_group)
        
        # Add buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        
        # Save button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)
        
        # Reset button
        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self._reset_settings)
        button_layout.addWidget(reset_button)
        
        button_layout.addStretch()
        
        settings_form.addWidget(button_container)
        settings_form.addStretch()
        
        self.settings_layout.addWidget(settings_container)
    
    def _save_settings(self):
        """Save settings to configuration."""
        # General settings
        self.config.set("general", "theme", self.theme_combo.currentText())
        self.config.set("general", "check_updates", self.updates_check.isChecked())
        
        # Twitch settings
        self.config.set("twitch", "broadcaster_client_id", self.broadcaster_id_edit.text())
        self.config.set("twitch", "broadcaster_client_secret", self.broadcaster_secret_edit.text())
        
        # OBS settings
        self.config.set("obs", "host", self.obs_host_edit.text())
        self.config.set("obs", "port", self.obs_port_spin.value())
        self.config.set("obs", "password", self.obs_password_edit.text())
        
        # OpenAI settings
        self.config.set("openai", "api_key", self.openai_key_edit.text())
        self.config.set("openai", "model", self.model_combo.currentText())
        
        # Save to file
        self.config.save()
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        self.status_bar.showMessage("Settings saved")
    
    def _reset_settings(self):
        """Reset settings to defaults."""
        result = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            self.config.reset_all()
            
            # Update UI
            self.theme_combo.setCurrentText(self.config.get("general", "theme", "dark"))
            self.updates_check.setChecked(self.config.get("general", "check_updates", True))
            self.broadcaster_id_edit.setText(self.config.get("twitch", "broadcaster_client_id", ""))
            self.broadcaster_secret_edit.setText(self.config.get("twitch", "broadcaster_client_secret", ""))
            self.obs_host_edit.setText(self.config.get("obs", "host", "localhost"))
            self.obs_port_spin.setValue(self.config.get("obs", "port", 4455))
            self.obs_password_edit.setText(self.config.get("obs", "password", ""))
            self.openai_key_edit.setText(self.config.get("openai", "api_key", ""))
            self.model_combo.setCurrentText(self.config.get("openai", "model", "gpt-3.5-turbo"))
            
            # Apply theme
            self._on_theme_changed(self.config.get("general", "theme", "dark"))
            
            self.status_bar.showMessage("Settings reset to defaults")
    
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
            self.status_bar.showMessage("Twitch connected")
        
        elif event.event_type == EventType.TWITCH_DISCONNECTED:
            self.twitch_status_label.setText("Not Connected")
            self.status_bar.showMessage("Twitch disconnected")
        
        elif event.event_type == EventType.OBS_CONNECTED:
            self.obs_status_label.setText("Connected")
            self.status_bar.showMessage("OBS connected")
        
        elif event.event_type == EventType.OBS_DISCONNECTED:
            self.obs_status_label.setText("Not Connected")
            self.status_bar.showMessage("OBS disconnected")
        
        elif event.event_type == EventType.WORKFLOW_LOADED:
            workflow_count = event.data.get('count', 0)
            self.workflows_status_label.setText(f"{workflow_count} loaded")
            self.status_bar.showMessage(f"Loaded {workflow_count} workflows") 