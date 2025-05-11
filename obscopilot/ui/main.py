"""
Main UI window for OBSCopilot.
"""

import logging
import sys
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QFont, QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QStatusBar, QToolBar,
    QMessageBox, QFileDialog, QMenu, QScrollArea, QFrame, QDialog, QListWidget,
    QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox, QComboBox, QGroupBox
)

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.storage.database import Database
from obscopilot.storage.repositories import (
    WorkflowRepository, SettingRepository, TwitchAuthRepository
)
from obscopilot.twitch.client import TwitchClient
from obscopilot.obs.client import OBSClient
from obscopilot.workflows.engine import WorkflowEngine
from obscopilot.ai.openai import OpenAIClient
from obscopilot.ai.googleai import GoogleAIClient
from obscopilot.ui.viewer_stats_tab import ViewerStatsTab
from obscopilot.ui.alerts_tab import AlertsTab
from obscopilot.ui.stream_health_tab import StreamHealthTab
from obscopilot.ui.workflow_editor import WorkflowEditor
from obscopilot.ui.themes import get_theme_manager, ThemeType
from obscopilot.ui.dashboard import Dashboard
from obscopilot.ui.shortcuts import ShortcutAction, get_shortcut_manager
from obscopilot.ui.theme_switcher import ThemeSwitcher
from obscopilot.ui.template_dialog import TemplateDialog

logger = logging.getLogger(__name__)


class WorkflowItem(QWidget):
    """Widget representing a single workflow in the workflow list."""
    
    def __init__(self, workflow, parent=None):
        """Initialize the workflow item widget.
        
        Args:
            workflow: The workflow model to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.workflow = workflow
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Workflow name
        self.name_label = QLabel(workflow.name)
        self.name_label.setFixedWidth(200)
        self.name_label.setToolTip(workflow.name)
        
        # Workflow trigger type
        trigger_type = "Multiple" if len(workflow.triggers) > 1 else (
            workflow.triggers[0].type if workflow.triggers else "None")
        self.type_label = QLabel(trigger_type)
        self.type_label.setFixedWidth(120)
        
        # Workflow description
        self.description_label = QLabel(workflow.description or "No description")
        self.description_label.setToolTip(workflow.description or "No description")
        
        # Workflow status
        self.status_label = QLabel("Enabled" if workflow.enabled else "Disabled")
        self.status_label.setFixedWidth(80)
        self.status_label.setStyleSheet(
            "color: #4CAF50;" if workflow.enabled else "color: #F44336;")
        
        # Action buttons
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(5)
        
        # Edit button
        self.edit_button = QPushButton("Edit")
        self.edit_button.setFixedWidth(60)
        
        # Toggle button
        self.toggle_button = QPushButton("Disable" if workflow.enabled else "Enable")
        self.toggle_button.setFixedWidth(60)
        
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_widget.setFixedWidth(150)
        
        # Add widgets to layout
        layout.addWidget(self.name_label)
        layout.addWidget(self.type_label)
        layout.addWidget(self.description_label)
        layout.addWidget(self.status_label)
        layout.addWidget(actions_widget)
        
        # Set widget background
        self.setAutoFillBackground(True)
        
        # Set alternating row colors
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, 
                       QColor("#2A2A2A") if parent and parent.indexOf(self) % 2 == 0 
                       else QColor("#323232"))
        self.setPalette(palette)


class MainWindow(QMainWindow):
    """Main window for the OBSCopilot application."""
    
    def __init__(self, config: Config):
        """Initialize the main window.
        
        Args:
            config: Application configuration
        """
        super().__init__()
        
        self.config = config
        self.database = None
        self.twitch_client = None
        self.obs_client = None
        self.workflow_engine = None
        self.openai_client = None
        self.googleai_client = None
        self.workflow_repo = None
        self.setting_repo = None
        self.twitch_auth_repo = None
        
        self._init_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        
        self.setWindowTitle("OBSCopilot")
        self.setMinimumSize(800, 600)
        
        # Apply theme
        self._apply_theme()
        
        # Initialize shortcut manager
        self.shortcut_manager = get_shortcut_manager(self)
        self._setup_shortcuts()
    
    def set_dependencies(
        self,
        database: Database,
        twitch_client: TwitchClient,
        obs_client: OBSClient,
        workflow_engine: WorkflowEngine,
        openai_client: OpenAIClient,
        googleai_client: GoogleAIClient,
        workflow_repo: WorkflowRepository,
        setting_repo: SettingRepository,
        twitch_auth_repo: TwitchAuthRepository
    ):
        """Set dependencies for the main window.
        
        Args:
            database: Database instance
            twitch_client: Twitch client instance
            obs_client: OBS client instance
            workflow_engine: Workflow engine instance
            openai_client: OpenAI client instance
            googleai_client: Google AI client instance
            workflow_repo: Workflow repository
            setting_repo: Setting repository
            twitch_auth_repo: Twitch auth repository
        """
        self.database = database
        self.twitch_client = twitch_client
        self.obs_client = obs_client
        self.workflow_engine = workflow_engine
        self.openai_client = openai_client
        self.googleai_client = googleai_client
        self.workflow_repo = workflow_repo
        self.setting_repo = setting_repo
        self.twitch_auth_repo = twitch_auth_repo
        
        # Create component tabs after dependencies are set
        self.viewer_stats_tab = ViewerStatsTab(database)
        self.alerts_tab = AlertsTab(database, obs_client, config=self.config)
        self.stream_health_tab = StreamHealthTab(database, obs_client, self.config)
        
        # Add component tabs to the dashboard
        self.dashboard_tabs.addTab(self.viewer_stats_tab, "Viewer Stats")
        self.dashboard_tabs.addTab(self.alerts_tab, "Alerts")
        self.dashboard_tabs.addTab(self.stream_health_tab, "Stream Health")
        
        # Update connection status initially
        self._update_connection_status()
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Apply theme
        theme_value = self.config.get("ui", "theme", "dark")
        theme_type = ThemeType.LIGHT if theme_value == "light" else ThemeType.DARK
        get_theme_manager().apply_theme(QApplication.instance(), theme_type)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # Create tab widget for different sections
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create dashboard tab
        self.dashboard_widget = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_widget)
        self.tab_widget.addTab(self.dashboard_widget, "Dashboard")
        
        # Create workflows tab
        self.workflows_widget = QWidget()
        self.workflows_layout = QVBoxLayout(self.workflows_widget)
        self.tab_widget.addTab(self.workflows_widget, "Workflows")
        
        # Create connections tab
        self.connections_widget = QWidget()
        self.connections_layout = QVBoxLayout(self.connections_widget)
        self.tab_widget.addTab(self.connections_widget, "Connections")
        
        # Create settings tab
        self.settings_widget = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        self.tab_widget.addTab(self.settings_widget, "Settings")
        
        # Initialize dashboard components
        self._init_dashboard()
        
        # Initialize connections components
        self._init_connections()
        
        # Initialize workflows components
        self._init_workflows()
        
        # Initialize settings components
        self._init_settings()
    
    def _init_dashboard(self):
        """Initialize the dashboard tab."""
        self.dashboard = Dashboard(
            config=self.config,
            stream_health_repo=None,
            user_stats_repo=None
        )
        
        self.tabs.addTab(self.dashboard, "Dashboard")
    
    def _init_connections(self):
        """Initialize connections tab components."""
        # Add connections widgets here
        connections_label = QLabel("Connections")
        connections_label.setFont(QFont("Arial", 16))
        self.connections_layout.addWidget(connections_label)
        
        # Twitch section
        twitch_section = QWidget()
        twitch_layout = QVBoxLayout(twitch_section)
        twitch_header = QLabel("Twitch")
        twitch_header.setFont(QFont("Arial", 14))
        twitch_layout.addWidget(twitch_header)
        
        # Twitch connect button
        twitch_button_container = QWidget()
        twitch_button_layout = QHBoxLayout(twitch_button_container)
        self.twitch_connect_button = QPushButton("Connect")
        self.twitch_connect_button.clicked.connect(self._toggle_twitch_connection)
        twitch_button_layout.addWidget(self.twitch_connect_button)
        twitch_button_layout.addStretch()
        twitch_layout.addWidget(twitch_button_container)
        
        self.connections_layout.addWidget(twitch_section)
        
        # OBS section
        obs_section = QWidget()
        obs_layout = QVBoxLayout(obs_section)
        obs_header = QLabel("OBS")
        obs_header.setFont(QFont("Arial", 14))
        obs_layout.addWidget(obs_header)
        
        # OBS connect button
        obs_button_container = QWidget()
        obs_button_layout = QHBoxLayout(obs_button_container)
        self.obs_connect_button = QPushButton("Connect")
        self.obs_connect_button.clicked.connect(self._toggle_obs_connection)
        obs_button_layout.addWidget(self.obs_connect_button)
        obs_button_layout.addStretch()
        obs_layout.addWidget(obs_button_container)
        
        self.connections_layout.addWidget(obs_section)
        
        # Add spacer
        self.connections_layout.addStretch()
    
    def _init_workflows(self):
        """Initialize workflows tab components."""
        # Add workflows widgets here
        workflows_label = QLabel("Workflows")
        workflows_label.setFont(QFont("Arial", 16))
        self.workflows_layout.addWidget(workflows_label)
        
        # Workflow buttons
        workflow_button_container = QWidget()
        workflow_button_layout = QHBoxLayout(workflow_button_container)
        
        self.load_workflow_button = QPushButton("Load Workflow")
        self.load_workflow_button.clicked.connect(self._load_workflow)
        workflow_button_layout.addWidget(self.load_workflow_button)
        
        self.create_workflow_button = QPushButton("Create Workflow")
        self.create_workflow_button.clicked.connect(self._create_workflow)
        workflow_button_layout.addWidget(self.create_workflow_button)
        
        workflow_button_layout.addStretch()
        
        self.workflows_layout.addWidget(workflow_button_container)
        
        # Create workflow list widget
        workflows_container = QWidget()
        workflows_container_layout = QVBoxLayout(workflows_container)
        workflows_container_layout.setContentsMargins(0, 10, 0, 0)
        
        # Create header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        name_header = QLabel("Name")
        name_header.setFixedWidth(200)
        name_header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        type_header = QLabel("Trigger Type")
        type_header.setFixedWidth(120)
        type_header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        description_header = QLabel("Description")
        description_header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        status_header = QLabel("Status")
        status_header.setFixedWidth(80)
        status_header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        actions_header = QLabel("Actions")
        actions_header.setFixedWidth(150)
        actions_header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        header_layout.addWidget(name_header)
        header_layout.addWidget(type_header)
        header_layout.addWidget(description_header)
        header_layout.addWidget(status_header)
        header_layout.addWidget(actions_header)
        
        workflows_container_layout.addWidget(header_container)
        
        # Scrollable area for workflow items
        self.workflow_scroll_area = QScrollArea()
        self.workflow_scroll_area.setWidgetResizable(True)
        self.workflow_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.workflow_scroll_content = QWidget()
        self.workflow_scroll_layout = QVBoxLayout(self.workflow_scroll_content)
        self.workflow_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.workflow_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.workflow_scroll_layout.setSpacing(2)
        
        # Add empty state message
        self.workflow_empty_label = QLabel("No workflows loaded")
        self.workflow_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.workflow_scroll_layout.addWidget(self.workflow_empty_label)
        
        self.workflow_scroll_area.setWidget(self.workflow_scroll_content)
        workflows_container_layout.addWidget(self.workflow_scroll_area)
        
        self.workflows_layout.addWidget(workflows_container)
        
        # Add spacer
        self.workflows_layout.addStretch()
    
    def _init_settings(self):
        """Initialize the settings tab."""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # Settings tabs
        settings_tabs = QTabWidget()
        
        # General settings
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_dropdown = QComboBox()
        self.theme_dropdown.addItems(["Dark", "Light"])
        
        # Set initial theme based on config
        theme_value = self.config.get("ui", "theme", "dark")
        self.theme_dropdown.setCurrentIndex(1 if theme_value == "light" else 0)
        
        self.theme_dropdown.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addRow("Application Theme:", self.theme_dropdown)
        
        general_layout.addWidget(theme_group)
        
        # Twitch settings
        twitch_group = QGroupBox("Twitch")
        twitch_layout = QFormLayout(twitch_group)
        
        self.twitch_channel_edit = QLineEdit(self.config.get("twitch", "channel", ""))
        twitch_layout.addRow("Channel:", self.twitch_channel_edit)
        
        self.twitch_bot_name_edit = QLineEdit(self.config.get("twitch", "bot_name", ""))
        twitch_layout.addRow("Bot Name:", self.twitch_bot_name_edit)
        
        general_layout.addWidget(twitch_group)
        
        # OBS settings
        obs_group = QGroupBox("OBS")
        obs_layout = QFormLayout(obs_group)
        
        self.obs_host_edit = QLineEdit(self.config.get("obs", "host", "localhost"))
        obs_layout.addRow("Host:", self.obs_host_edit)
        
        self.obs_port_edit = QSpinBox()
        self.obs_port_edit.setRange(1, 65535)
        self.obs_port_edit.setValue(int(self.config.get("obs", "port", "4455")))
        obs_layout.addRow("Port:", self.obs_port_edit)
        
        general_layout.addWidget(obs_group)
        
        # Add save button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save_settings)
        general_layout.addWidget(save_button)
        
        # Add general tab
        settings_tabs.addTab(general_tab, "General")
        
        # Add AI settings tab
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # OpenAI settings
        openai_group = QGroupBox("OpenAI")
        openai_layout = QFormLayout(openai_group)
        
        self.openai_api_key_edit = QLineEdit(self.config.get("openai", "api_key", ""))
        self.openai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        openai_layout.addRow("API Key:", self.openai_api_key_edit)
        
        self.openai_model_edit = QLineEdit(self.config.get("openai", "model", "gpt-4o"))
        openai_layout.addRow("Model:", self.openai_model_edit)
        
        ai_layout.addWidget(openai_group)
        
        # Google AI settings
        googleai_group = QGroupBox("Google AI")
        googleai_layout = QFormLayout(googleai_group)
        
        self.googleai_api_key_edit = QLineEdit(self.config.get("googleai", "api_key", ""))
        self.googleai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        googleai_layout.addRow("API Key:", self.googleai_api_key_edit)
        
        self.googleai_model_edit = QLineEdit(self.config.get("googleai", "model", "gemini-1.5-pro"))
        googleai_layout.addRow("Model:", self.googleai_model_edit)
        
        ai_layout.addWidget(googleai_group)
        
        # Add save button
        save_button_ai = QPushButton("Save Settings")
        save_button_ai.clicked.connect(self._save_settings)
        ai_layout.addWidget(save_button_ai)
        
        # Add AI tab
        settings_tabs.addTab(ai_tab, "AI")
        
        # Add keyboard shortcuts tab
        from obscopilot.ui.shortcut_settings import ShortcutSettingsWidget
        shortcuts_tab = ShortcutSettingsWidget(self.shortcut_manager)
        settings_tabs.addTab(shortcuts_tab, "Keyboard Shortcuts")
        
        # Add database settings tab
        db_tab = QWidget()
        db_layout = QVBoxLayout(db_tab)
        
        # Database backup/restore
        backup_group = QGroupBox("Backup & Restore")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_description = QLabel(
            "Create a backup of your database or restore from a previous backup.\n"
            "Backup includes workflows, settings, and statistics."
        )
        backup_layout.addWidget(backup_description)
        
        backup_buttons = QHBoxLayout()
        
        backup_button = QPushButton("Backup Database")
        backup_button.clicked.connect(self._backup_database)
        backup_buttons.addWidget(backup_button)
        
        restore_button = QPushButton("Restore Database")
        restore_button.clicked.connect(self._restore_database)
        backup_buttons.addWidget(restore_button)
        
        backup_layout.addLayout(backup_buttons)
        db_layout.addWidget(backup_group)
        
        # Add database tab
        settings_tabs.addTab(db_tab, "Database")
        
        settings_layout.addWidget(settings_tabs)
        
        # Add to main tabs
        self.tabs.addTab(settings_widget, "Settings")
    
    def _create_actions(self):
        """Create application actions."""
        # Create exit action
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(self.shortcut_manager.get_shortcut_text(ShortcutAction.EXIT))
        self.exit_action.triggered.connect(self.close)
        
        # Create new workflow action
        self.new_workflow_action = QAction("New Workflow", self)
        self.new_workflow_action.setShortcut(self.shortcut_manager.get_shortcut_text(ShortcutAction.NEW_WORKFLOW))
        self.new_workflow_action.triggered.connect(self._create_workflow)
        
        # Create toggle streaming action
        self.toggle_streaming_action = QAction("Toggle Streaming", self)
        self.toggle_streaming_action.setShortcut(self.shortcut_manager.get_shortcut_text(ShortcutAction.TOGGLE_STREAMING))
        self.toggle_streaming_action.triggered.connect(self._toggle_streaming)
        
        # Create toggle recording action
        self.toggle_recording_action = QAction("Toggle Recording", self)
        self.toggle_recording_action.setShortcut(self.shortcut_manager.get_shortcut_text(ShortcutAction.TOGGLE_RECORDING))
        self.toggle_recording_action.triggered.connect(self._toggle_recording)
        
        # Create scene selector action
        self.scene_selector_action = QAction("Scene Selector", self)
        self.scene_selector_action.setShortcut(self.shortcut_manager.get_shortcut_text(ShortcutAction.SCENE_SELECTOR))
        self.scene_selector_action.triggered.connect(self._show_scene_selector)
        
        # Create toggle theme action
        self.toggle_theme_action = QAction("Toggle Theme", self)
        self.toggle_theme_action.setShortcut(self.shortcut_manager.get_shortcut_text(ShortcutAction.TOGGLE_THEME))
        self.toggle_theme_action.triggered.connect(self._toggle_theme)
        
        # Create about action
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self._show_about)
    
    def _create_menus(self):
        """Create application menus."""
        # File menu
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.exit_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction(self.about_action)
    
    def _create_toolbars(self):
        """Create application toolbars."""
        # Main toolbar
        main_toolbar = QToolBar("Main", self)
        self.addToolBar(main_toolbar)
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = self.statusBar()
        
        # Add connection status labels
        self.twitch_status_label = QLabel("Twitch: Disconnected")
        self.status_bar.addPermanentWidget(self.twitch_status_label)
        
        self.obs_status_label = QLabel("OBS: Disconnected")
        self.status_bar.addPermanentWidget(self.obs_status_label)
        
        # Add theme switcher
        self.theme_switcher = ThemeSwitcher(self.config)
        self.status_bar.addPermanentWidget(self.theme_switcher)
    
    def _apply_theme(self):
        """Apply the configured theme."""
        theme = self.config.get('general', 'theme', 'dark')
        
        if theme == 'dark':
            # Apply dark theme styles
            self._apply_dark_theme()
        else:
            # Apply light theme styles
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
    
    def _update_connection_status(self):
        """Update the connection status indicators in the UI."""
        if self.twitch_client and self.twitch_client.connected:
            self.twitch_status_label.setText("Connected")
            self.twitch_connect_button.setText("Disconnect")
        else:
            self.twitch_status_label.setText("Disconnected")
            self.twitch_connect_button.setText("Connect")
            
        if self.obs_client and self.obs_client.connected:
            self.obs_status_label.setText("Connected")
            self.obs_connect_button.setText("Disconnect")
        else:
            self.obs_status_label.setText("Disconnected")
            self.obs_connect_button.setText("Connect")
            
        if self.workflow_engine:
            workflow_count = len(self.workflow_engine.workflows)
            self.workflows_status_label.setText(f"{workflow_count} loaded")
    
    async def _toggle_twitch_connection(self):
        """Toggle Twitch connection state."""
        if not self.twitch_client:
            self.status_bar.showMessage("Twitch client not initialized")
            return
            
        if self.twitch_client.connected:
            # Disconnect from Twitch
            await self.twitch_client.disconnect()
        else:
            # Connect to Twitch
            success = await self.twitch_client.connect()
            if not success:
                self.status_bar.showMessage("Failed to connect to Twitch")
                QMessageBox.warning(self, "Connection Failed", "Failed to connect to Twitch API. Check your credentials.")
                
        # Update UI
        self._update_connection_status()
    
    async def _toggle_obs_connection(self):
        """Toggle OBS connection state."""
        if not self.obs_client:
            self.status_bar.showMessage("OBS client not initialized")
            return
            
        if self.obs_client.connected:
            # Disconnect from OBS
            self.obs_client.disconnect()
        else:
            # Connect to OBS
            success = await self.obs_client.connect()
            if not success:
                self.status_bar.showMessage("Failed to connect to OBS")
                QMessageBox.warning(self, "Connection Failed", "Failed to connect to OBS. Make sure OBS is running with the WebSocket plugin enabled.")
                
        # Update UI
        self._update_connection_status()
    
    def _edit_workflow(self, workflow_id):
        """Open workflow editor for the specified workflow.
        
        Args:
            workflow_id: ID of the workflow to edit
        """
        if not self.workflow_engine:
            self.status_bar.showMessage("Workflow engine not initialized")
            return
        
        workflow = self.workflow_engine.workflows.get(workflow_id)
        if not workflow:
            self.status_bar.showMessage(f"Workflow not found: {workflow_id}")
            return
        
        # Create and show workflow editor
        self._open_workflow_editor(workflow)
        
    def _open_workflow_editor(self, workflow=None):
        """Open the workflow editor.
        
        Args:
            workflow: Workflow to edit (or None for a new workflow)
        """
        # Close existing editor if open
        if hasattr(self, 'workflow_editor_tab_index') and self.workflow_editor_tab_index is not None:
            self.tab_widget.removeTab(self.workflow_editor_tab_index)
            self.workflow_editor_tab_index = None
        
        # Create workflow editor widget
        self.workflow_editor = WorkflowEditor(workflow)
        self.workflow_editor.workflow_saved.connect(self._on_workflow_saved)
        
        # Add to tabs
        self.workflow_editor_tab_index = self.tab_widget.addTab(
            self.workflow_editor,
            f"{'Edit' if workflow else 'New'} Workflow"
        )
        
        # Switch to editor tab
        self.tab_widget.setCurrentIndex(self.workflow_editor_tab_index)
        
    def _on_workflow_saved(self, workflow):
        """Handle workflow saving.
        
        Args:
            workflow: Saved workflow or None if cancelled
        """
        # Close editor tab
        if hasattr(self, 'workflow_editor_tab_index') and self.workflow_editor_tab_index is not None:
            self.tab_widget.removeTab(self.workflow_editor_tab_index)
            self.workflow_editor_tab_index = None
            
        if workflow and workflow != self.workflow_editor.original_workflow:
            # Save workflow to database
            self.workflow_repo.update(workflow)
            
            # Update in engine
            self.workflow_engine.register_workflow(workflow)
            
            # Update UI
            self.refresh_workflows()
            
            self.status_bar.showMessage(f"Workflow saved: {workflow.name}")
        
    def _create_workflow(self):
        """Create a new workflow."""
        # Show template selection dialog
        template_dialog = TemplateDialog(self)
        template_dialog.template_selected.connect(self._on_template_selected)
        template_dialog.exec()
    
    def _on_template_selected(self, workflow):
        """Handle template selection.
        
        Args:
            workflow: Selected workflow
        """
        self._open_workflow_editor(workflow)
    
    def _save_settings(self):
        """Save settings to config."""
        # OBS settings
        self.config.set("obs", "host", self.obs_host_edit.text())
        self.config.set("obs", "port", str(self.obs_port_edit.value()))
        
        # Twitch settings
        self.config.set("twitch", "channel", self.twitch_channel_edit.text())
        self.config.set("twitch", "bot_name", self.twitch_bot_name_edit.text())
        
        # OpenAI settings
        self.config.set("openai", "api_key", self.openai_api_key_edit.text())
        self.config.set("openai", "model", self.openai_model_edit.text())
        
        # Google AI settings
        self.config.set("googleai", "api_key", self.googleai_api_key_edit.text())
        self.config.set("googleai", "model", self.googleai_model_edit.text())
        
        # Save config
        self.config.save()
        
        # Show confirmation
        self.status_bar.showMessage("Settings saved successfully", 3000)
        
        # Apply theme (in case it changed)
        self._apply_theme()
    
    def _on_theme_changed(self, index):
        """Handle theme selection changes.
        
        Args:
            index: Selected index
        """
        # Get theme type
        theme_type = ThemeType.LIGHT if index == 1 else ThemeType.DARK
        
        # Save to config
        theme_str = "light" if theme_type == ThemeType.LIGHT else "dark"
        self.config.set("ui", "theme", theme_str)
        self.config.save()
        
        # Apply theme
        get_theme_manager().apply_theme(QApplication.instance(), theme_type)
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About OBSCopilot",
            f"""
            <h3>OBSCopilot</h3>
            <p>Version {self.config.get('version')}</p>
            <p>A powerful, cross-platform Twitch live assistant with workflow automation capabilities, OBS integration, and AI-powered interactions.</p>
            <p>&copy; 2024 OBSCopilot Team</p>
            """
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up resources
        if self.twitch_client and self.twitch_client.connected:
            asyncio.create_task(self.twitch_client.disconnect())
            
        if self.obs_client and self.obs_client.connected:
            self.obs_client.disconnect()
            
        if self.database:
            self.database.close()
            
        event.accept()

    def refresh_workflows(self):
        """Refresh the workflow list."""
        # Clear current items
        while self.workflow_scroll_layout.count() > 0:
            item = self.workflow_scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.workflow_engine or not self.workflow_engine.workflows:
            # Show empty state
            self.workflow_empty_label = QLabel("No workflows loaded")
            self.workflow_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.workflow_scroll_layout.addWidget(self.workflow_empty_label)
            return
        
        # Hide empty label
        if hasattr(self, 'workflow_empty_label') and self.workflow_empty_label:
            self.workflow_empty_label.hide()
            self.workflow_empty_label = None
        
        # Add workflow items
        for workflow_id, workflow in self.workflow_engine.workflows.items():
            workflow_item = WorkflowItem(workflow, self.workflow_scroll_content)
            
            # Connect signals
            workflow_item.edit_button.clicked.connect(
                lambda checked, wid=workflow_id: self._edit_workflow(wid))
            workflow_item.toggle_button.clicked.connect(
                lambda checked, wid=workflow_id: self._toggle_workflow(wid))
            
            self.workflow_scroll_layout.addWidget(workflow_item)
        
        # Update status
        self._update_connection_status()
    
    def _toggle_streaming(self):
        """Toggle OBS streaming state."""
        if not self.obs_client:
            self.status_bar.showMessage("OBS client not initialized")
            return
            
        if not self.obs_client.connected:
            self.status_bar.showMessage("OBS not connected")
            QMessageBox.warning(self, "OBS Not Connected", "Please connect to OBS first.")
            return
            
        try:
            if self.obs_client.is_streaming():
                # Stop streaming
                success = self.obs_client.stop_streaming()
                if success:
                    self.status_bar.showMessage("Streaming stopped")
                else:
                    self.status_bar.showMessage("Failed to stop streaming")
            else:
                # Start streaming
                success = self.obs_client.start_streaming()
                if success:
                    self.status_bar.showMessage("Streaming started")
                else:
                    self.status_bar.showMessage("Failed to start streaming")
        except Exception as e:
            logger.error(f"Error toggling streaming: {e}")
            self.status_bar.showMessage("Error toggling streaming")
            QMessageBox.warning(self, "Error", f"Failed to toggle streaming: {str(e)}")
    
    def _toggle_recording(self):
        """Toggle OBS recording state."""
        if not self.obs_client:
            self.status_bar.showMessage("OBS client not initialized")
            return
            
        if not self.obs_client.connected:
            self.status_bar.showMessage("OBS not connected")
            QMessageBox.warning(self, "OBS Not Connected", "Please connect to OBS first.")
            return
            
        try:
            if self.obs_client.is_recording():
                # Stop recording
                success = self.obs_client.stop_recording()
                if success:
                    self.status_bar.showMessage("Recording stopped")
                else:
                    self.status_bar.showMessage("Failed to stop recording")
            else:
                # Start recording
                success = self.obs_client.start_recording()
                if success:
                    self.status_bar.showMessage("Recording started")
                else:
                    self.status_bar.showMessage("Failed to start recording")
        except Exception as e:
            logger.error(f"Error toggling recording: {e}")
            self.status_bar.showMessage("Error toggling recording")
            QMessageBox.warning(self, "Error", f"Failed to toggle recording: {str(e)}")
    
    def _show_scene_selector(self):
        """Show scene selector dialog."""
        if not self.obs_client:
            self.status_bar.showMessage("OBS client not initialized")
            return
            
        if not self.obs_client.connected:
            self.status_bar.showMessage("OBS not connected")
            QMessageBox.warning(self, "OBS Not Connected", "Please connect to OBS first.")
            return
            
        try:
            # Get list of scenes
            scenes = self.obs_client.get_scenes()
            if not scenes:
                self.status_bar.showMessage("No scenes found")
                QMessageBox.warning(self, "No Scenes", "No scenes found in OBS.")
                return
                
            # Create scene selection dialog
            scene_dialog = QDialog(self)
            scene_dialog.setWindowTitle("Select Scene")
            scene_dialog.setMinimumWidth(300)
            
            layout = QVBoxLayout(scene_dialog)
            
            label = QLabel("Select a scene to switch to:")
            layout.addWidget(label)
            
            scene_list = QListWidget()
            for scene in scenes:
                scene_list.addItem(scene)
            layout.addWidget(scene_list)
            
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(scene_dialog.accept)
            buttons.rejected.connect(scene_dialog.reject)
            layout.addWidget(buttons)
            
            if scene_dialog.exec() == QDialog.DialogCode.Accepted:
                selected_items = scene_list.selectedItems()
                if selected_items:
                    selected_scene = selected_items[0].text()
                    success = self.obs_client.set_current_scene(selected_scene)
                    if success:
                        self.status_bar.showMessage(f"Switched to scene: {selected_scene}")
                    else:
                        self.status_bar.showMessage(f"Failed to switch to scene: {selected_scene}")
        except Exception as e:
            logger.error(f"Error showing scene selector: {e}")
            self.status_bar.showMessage("Error showing scene selector")
            QMessageBox.warning(self, "Error", f"Failed to show scene selector: {str(e)}")
    
    def _test_alert(self):
        """Test alert functionality."""
        if not self.workflow_engine:
            self.status_bar.showMessage("Workflow engine not initialized")
            return
            
        # Create test alert dialog
        alert_dialog = QDialog(self)
        alert_dialog.setWindowTitle("Test Alert")
        alert_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(alert_dialog)
        
        label = QLabel("Select alert type to test:")
        layout.addWidget(label)
        
        alert_type_combo = QComboBox()
        alert_type_combo.addItems([
            "Subscription", "Follow", "Bits", "Raid", "Channel Points"
        ])
        layout.addWidget(alert_type_combo)
        
        message_layout = QFormLayout()
        message_input = QLineEdit()
        message_input.setText("Test alert message")
        message_layout.addRow("Message:", message_input)
        layout.addLayout(message_layout)
        
        username_layout = QFormLayout()
        username_input = QLineEdit()
        username_input.setText("TestUser")
        username_layout.addRow("Username:", username_input)
        layout.addLayout(username_layout)
        
        amount_layout = QFormLayout()
        amount_input = QSpinBox()
        amount_input.setValue(1)
        amount_input.setMinimum(1)
        amount_input.setMaximum(10000)
        amount_layout.addRow("Amount:", amount_input)
        layout.addLayout(amount_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(alert_dialog.accept)
        buttons.rejected.connect(alert_dialog.reject)
        layout.addWidget(buttons)
        
        if alert_dialog.exec() == QDialog.DialogCode.Accepted:
            alert_type = alert_type_combo.currentText()
            username = username_input.text()
            message = message_input.text()
            amount = amount_input.value()
            
            # Create test event data based on alert type
            event_data = {
                "username": username,
                "message": message,
                "amount": amount,
                "test": True
            }
            
            # Determine event type based on selected alert type
            event_type = None
            if alert_type == "Subscription":
                event_type = EventType.TWITCH_SUBSCRIPTION
            elif alert_type == "Follow":
                event_type = EventType.TWITCH_FOLLOW
            elif alert_type == "Bits":
                event_type = EventType.TWITCH_BITS
            elif alert_type == "Raid":
                event_type = EventType.TWITCH_RAID
            elif alert_type == "Channel Points":
                event_type = EventType.TWITCH_CHANNEL_POINTS_REDEEM
            
            if event_type:
                # Create and emit test event
                test_event = Event(event_type, event_data)
                event_bus.emit_sync(test_event)
                self.status_bar.showMessage(f"Test {alert_type} alert triggered")
            else:
                self.status_bar.showMessage("Invalid alert type")

    def _backup_database(self):
        """Backup the database."""
        if not hasattr(self, 'schema_manager') or not self.schema_manager:
            from obscopilot.storage.schema import get_schema_manager
            self.schema_manager = get_schema_manager(self.config)
            
        # Get backup file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            "",
            "Database Backup Files (*.bak)"
        )
        
        if file_path:
            # Ensure file has .bak extension
            if not file_path.endswith('.bak'):
                file_path += '.bak'
                
            # Perform backup
            success = self.schema_manager.backup_database(file_path)
            
            if success:
                self.status_bar.showMessage(f"Database backed up to {file_path}")
                QMessageBox.information(self, "Backup Successful", f"Database backed up to {file_path}")
            else:
                self.status_bar.showMessage("Database backup failed")
                QMessageBox.warning(self, "Backup Failed", "Failed to backup database")
                
    def _restore_database(self):
        """Restore the database from backup."""
        if not hasattr(self, 'schema_manager') or not self.schema_manager:
            from obscopilot.storage.schema import get_schema_manager
            self.schema_manager = get_schema_manager(self.config)
            
        # Show warning
        confirm = QMessageBox.warning(
            self,
            "Restore Database",
            "Restoring from backup will replace your current database. This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
            
        # Get backup file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Database",
            "",
            "Database Backup Files (*.bak)"
        )
        
        if file_path:
            # Perform restore
            success = self.schema_manager.restore_database(file_path)
            
            if success:
                self.status_bar.showMessage(f"Database restored from {file_path}")
                QMessageBox.information(
                    self, 
                    "Restore Successful", 
                    f"Database restored from {file_path}. Please restart the application for changes to take effect."
                )
            else:
                self.status_bar.showMessage("Database restore failed")
                QMessageBox.warning(self, "Restore Failed", "Failed to restore database")

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts for the application."""
        shortcut_handlers = {
            ShortcutAction.EXIT: self.close,
            ShortcutAction.TOGGLE_THEME: self._toggle_theme,
            ShortcutAction.NEW_WORKFLOW: self._create_workflow,
            ShortcutAction.TOGGLE_TWITCH: lambda: self._toggle_twitch_connection(),
            ShortcutAction.TOGGLE_OBS: lambda: self._toggle_obs_connection(),
            ShortcutAction.TOGGLE_STREAMING: self._toggle_streaming,
            ShortcutAction.TOGGLE_RECORDING: self._toggle_recording,
            ShortcutAction.TAB_DASHBOARD: lambda: self.tab_widget.setCurrentIndex(0),
            ShortcutAction.TAB_CONNECTIONS: lambda: self.tab_widget.setCurrentIndex(1),
            ShortcutAction.TAB_WORKFLOWS: lambda: self.tab_widget.setCurrentIndex(2),
            ShortcutAction.TAB_SETTINGS: lambda: self.tab_widget.setCurrentIndex(3),
            ShortcutAction.SCENE_SELECTOR: self._show_scene_selector,
        }
        
        self.shortcut_manager.register_shortcuts(shortcut_handlers)

    def _toggle_theme(self):
        """Toggle between light and dark themes."""
        theme_manager = get_theme_manager()
        theme_manager.toggle_theme(QApplication.instance())
        
        # Update theme setting in config
        new_theme = "light" if theme_manager.current_theme == ThemeType.LIGHT else "dark"
        self.config.set("ui", "theme", new_theme)
        self.config.save()
        
        # Update theme dropdown in settings if it exists
        if hasattr(self, 'theme_dropdown'):
            index = 1 if new_theme == "light" else 0
            self.theme_dropdown.setCurrentIndex(index)
        
        # Apply theme
        self._apply_theme()
    
    def _toggle_workflow(self, workflow_id):
        """Toggle workflow state."""
        if not self.workflow_engine:
            self.status_bar.showMessage("Workflow engine not initialized")
            return
        
        workflow = self.workflow_engine.workflows.get(workflow_id)
        if not workflow:
            self.status_bar.showMessage(f"Workflow not found: {workflow_id}")
            return
        
        # Toggle workflow state
        workflow.enabled = not workflow.enabled
        self.workflow_repo.update(workflow)
        
        # Update in engine
        self.workflow_engine.register_workflow(workflow)
        
        # Update UI
        self.refresh_workflows()
        
        self.status_bar.showMessage(f"Workflow state toggled: {workflow.name}") 