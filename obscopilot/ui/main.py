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
    QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox, QComboBox
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
    
    def set_dependencies(
        self,
        database: Database,
        twitch_client: TwitchClient,
        obs_client: OBSClient,
        workflow_engine: WorkflowEngine,
        openai_client: OpenAIClient,
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
            workflow_repo: Workflow repository instance
            setting_repo: Setting repository instance
            twitch_auth_repo: Twitch authentication repository instance
        """
        self.database = database
        self.twitch_client = twitch_client
        self.obs_client = obs_client
        self.workflow_engine = workflow_engine
        self.openai_client = openai_client
        self.workflow_repo = workflow_repo
        self.setting_repo = setting_repo
        self.twitch_auth_repo = twitch_auth_repo
        
        # Update UI based on dependencies
        self._update_connection_status()
    
    def _init_ui(self):
        """Initialize the UI components."""
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
        """Initialize dashboard tab components."""
        # Main container
        dashboard_container = QWidget()
        dashboard_container_layout = QVBoxLayout(dashboard_container)
        dashboard_container_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_container_layout.setSpacing(20)
        
        # Header section
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        dashboard_title = QLabel("Dashboard")
        dashboard_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header_layout.addWidget(dashboard_title)
        
        dashboard_subtitle = QLabel("Overview of your streaming setup")
        dashboard_subtitle.setFont(QFont("Arial", 12))
        dashboard_subtitle.setStyleSheet("color: #888888;")
        header_layout.addWidget(dashboard_subtitle)
        
        dashboard_container_layout.addWidget(header_container)
        
        # Status cards row
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(15)
        
        # Twitch status card
        twitch_card = QFrame()
        twitch_card.setFrameShape(QFrame.Shape.StyledPanel)
        twitch_card.setStyleSheet(
            "QFrame { background-color: #2D2D30; border-radius: 8px; padding: 10px; }"
        )
        twitch_card_layout = QVBoxLayout(twitch_card)
        
        twitch_header_layout = QHBoxLayout()
        twitch_icon_label = QLabel("🔴")  # Placeholder for an icon
        twitch_icon_label.setFont(QFont("Arial", 16))
        twitch_header_layout.addWidget(twitch_icon_label)
        
        twitch_title = QLabel("Twitch")
        twitch_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        twitch_header_layout.addWidget(twitch_title)
        twitch_header_layout.addStretch()
        
        twitch_card_layout.addLayout(twitch_header_layout)
        
        twitch_card_layout.addSpacing(10)
        
        self.twitch_status_label = QLabel("Disconnected")
        self.twitch_status_label.setFont(QFont("Arial", 12))
        self.twitch_status_label.setStyleSheet("color: #FF5252;")  # Red for disconnected
        twitch_card_layout.addWidget(self.twitch_status_label)
        
        twitch_card_layout.addSpacing(5)
        
        twitch_connect_button = QPushButton("Connect")
        twitch_connect_button.clicked.connect(self._toggle_twitch_connection)
        twitch_card_layout.addWidget(twitch_connect_button)
        
        status_layout.addWidget(twitch_card)
        
        # OBS status card
        obs_card = QFrame()
        obs_card.setFrameShape(QFrame.Shape.StyledPanel)
        obs_card.setStyleSheet(
            "QFrame { background-color: #2D2D30; border-radius: 8px; padding: 10px; }"
        )
        obs_card_layout = QVBoxLayout(obs_card)
        
        obs_header_layout = QHBoxLayout()
        obs_icon_label = QLabel("📹")  # Placeholder for an icon
        obs_icon_label.setFont(QFont("Arial", 16))
        obs_header_layout.addWidget(obs_icon_label)
        
        obs_title = QLabel("OBS")
        obs_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        obs_header_layout.addWidget(obs_title)
        obs_header_layout.addStretch()
        
        obs_card_layout.addLayout(obs_header_layout)
        
        obs_card_layout.addSpacing(10)
        
        self.obs_status_label = QLabel("Disconnected")
        self.obs_status_label.setFont(QFont("Arial", 12))
        self.obs_status_label.setStyleSheet("color: #FF5252;")  # Red for disconnected
        obs_card_layout.addWidget(self.obs_status_label)
        
        obs_card_layout.addSpacing(5)
        
        obs_connect_button = QPushButton("Connect")
        obs_connect_button.clicked.connect(self._toggle_obs_connection)
        obs_card_layout.addWidget(obs_connect_button)
        
        status_layout.addWidget(obs_card)
        
        # Workflows status card
        workflows_card = QFrame()
        workflows_card.setFrameShape(QFrame.Shape.StyledPanel)
        workflows_card.setStyleSheet(
            "QFrame { background-color: #2D2D30; border-radius: 8px; padding: 10px; }"
        )
        workflows_card_layout = QVBoxLayout(workflows_card)
        
        workflows_header_layout = QHBoxLayout()
        workflows_icon_label = QLabel("⚙️")  # Placeholder for an icon
        workflows_icon_label.setFont(QFont("Arial", 16))
        workflows_header_layout.addWidget(workflows_icon_label)
        
        workflows_title = QLabel("Workflows")
        workflows_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        workflows_header_layout.addWidget(workflows_title)
        workflows_header_layout.addStretch()
        
        workflows_card_layout.addLayout(workflows_header_layout)
        
        workflows_card_layout.addSpacing(10)
        
        self.workflows_status_label = QLabel("0 loaded")
        self.workflows_status_label.setFont(QFont("Arial", 12))
        workflows_card_layout.addWidget(self.workflows_status_label)
        
        workflows_card_layout.addSpacing(5)
        
        workflows_manage_button = QPushButton("Manage Workflows")
        workflows_manage_button.clicked.connect(
            lambda: self.tab_widget.setCurrentIndex(self.tab_widget.indexOf(self.workflows_widget))
        )
        workflows_card_layout.addWidget(workflows_manage_button)
        
        status_layout.addWidget(workflows_card)
        
        # AI status card
        ai_card = QFrame()
        ai_card.setFrameShape(QFrame.Shape.StyledPanel)
        ai_card.setStyleSheet(
            "QFrame { background-color: #2D2D30; border-radius: 8px; padding: 10px; }"
        )
        ai_card_layout = QVBoxLayout(ai_card)
        
        ai_header_layout = QHBoxLayout()
        ai_icon_label = QLabel("🧠")  # Placeholder for an icon
        ai_icon_label.setFont(QFont("Arial", 16))
        ai_header_layout.addWidget(ai_icon_label)
        
        ai_title = QLabel("AI")
        ai_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        ai_header_layout.addWidget(ai_title)
        ai_header_layout.addStretch()
        
        ai_card_layout.addLayout(ai_header_layout)
        
        ai_card_layout.addSpacing(10)
        
        self.ai_status_label = QLabel("Ready")
        self.ai_status_label.setFont(QFont("Arial", 12))
        self.ai_status_label.setStyleSheet("color: #4CAF50;")  # Green for ready
        ai_card_layout.addWidget(self.ai_status_label)
        
        ai_card_layout.addSpacing(5)
        
        ai_settings_button = QPushButton("AI Settings")
        ai_settings_button.clicked.connect(
            lambda: self.tab_widget.setCurrentIndex(self.tab_widget.indexOf(self.settings_widget))
        )
        ai_card_layout.addWidget(ai_settings_button)
        
        status_layout.addWidget(ai_card)
        
        dashboard_container_layout.addWidget(status_container)
        
        # Quick actions section
        actions_container = QWidget()
        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        actions_header = QLabel("Quick Actions")
        actions_header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        actions_layout.addWidget(actions_header)
        
        actions_buttons_layout = QHBoxLayout()
        actions_buttons_layout.setSpacing(10)
        
        toggle_stream_button = QPushButton("Toggle Stream")
        toggle_stream_button.setMinimumHeight(40)
        toggle_stream_button.clicked.connect(self._toggle_streaming)
        actions_buttons_layout.addWidget(toggle_stream_button)
        
        toggle_recording_button = QPushButton("Toggle Recording")
        toggle_recording_button.setMinimumHeight(40)
        toggle_recording_button.clicked.connect(self._toggle_recording)
        actions_buttons_layout.addWidget(toggle_recording_button)
        
        scene_switch_button = QPushButton("Switch Scene")
        scene_switch_button.setMinimumHeight(40)
        scene_switch_button.clicked.connect(self._show_scene_selector)
        actions_buttons_layout.addWidget(scene_switch_button)
        
        test_alert_button = QPushButton("Test Alert")
        test_alert_button.setMinimumHeight(40)
        test_alert_button.clicked.connect(self._test_alert)
        actions_buttons_layout.addWidget(test_alert_button)
        
        actions_layout.addLayout(actions_buttons_layout)
        
        dashboard_container_layout.addWidget(actions_container)
        
        # Stats section (placeholder for future metrics)
        stats_container = QWidget()
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        stats_header = QLabel("Stream Statistics")
        stats_header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        stats_layout.addWidget(stats_header)
        
        stats_placeholder = QLabel("Stream statistics will be displayed here")
        stats_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_placeholder.setStyleSheet("color: #888888; padding: 20px;")
        stats_layout.addWidget(stats_placeholder)
        
        dashboard_container_layout.addWidget(stats_container)
        
        # Add spacer to push everything to the top
        dashboard_container_layout.addStretch()
        
        # Add the main container to the dashboard layout
        self.dashboard_layout.addWidget(dashboard_container)
    
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
        """Initialize settings tab components."""
        # Add settings widgets here
        settings_label = QLabel("Settings")
        settings_label.setFont(QFont("Arial", 16))
        self.settings_layout.addWidget(settings_label)
        
        # Add a save settings button
        settings_button_container = QWidget()
        settings_button_layout = QHBoxLayout(settings_button_container)
        
        save_settings_button = QPushButton("Save Settings")
        save_settings_button.clicked.connect(self._save_settings)
        settings_button_layout.addWidget(save_settings_button)
        
        settings_button_layout.addStretch()
        
        self.settings_layout.addWidget(settings_button_container)
        
        # Add spacer
        self.settings_layout.addStretch()
    
    def _create_actions(self):
        """Create application actions."""
        # File actions
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        
        # Help actions
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
        """Create application status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
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
        
        # TODO: Implement workflow editor
        QMessageBox.information(
            self, 
            "Edit Workflow", 
            f"Workflow editor not implemented yet. Would edit: {workflow.name}"
        )
    
    def _toggle_workflow(self, workflow_id):
        """Toggle the enabled state of a workflow.
        
        Args:
            workflow_id: ID of the workflow to toggle
        """
        if not self.workflow_engine:
            self.status_bar.showMessage("Workflow engine not initialized")
            return
        
        workflow = self.workflow_engine.workflows.get(workflow_id)
        if not workflow:
            self.status_bar.showMessage(f"Workflow not found: {workflow_id}")
            return
        
        # Toggle enabled state
        workflow.enabled = not workflow.enabled
        
        # Update in database
        self.workflow_repo.update(workflow)
        
        # Update UI
        self.status_bar.showMessage(
            f"Workflow {'enabled' if workflow.enabled else 'disabled'}: {workflow.name}"
        )
        self.refresh_workflows()
    
    def _load_workflow(self):
        """Load a workflow from file."""
        if not self.workflow_engine:
            self.status_bar.showMessage("Workflow engine not initialized")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Workflow",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    workflow_json = f.read()
                    
                # Create workflow in database
                workflow = self.workflow_repo.create_from_json(workflow_json)
                
                # Register workflow with engine
                self.workflow_engine.register_workflow(workflow)
                
                self.status_bar.showMessage(f"Loaded workflow: {workflow.name}")
                
                # Refresh the workflow list
                self.refresh_workflows()
            except Exception as e:
                logger.error(f"Error loading workflow: {e}")
                self.status_bar.showMessage("Error loading workflow")
                QMessageBox.warning(self, "Load Error", f"Failed to load workflow: {str(e)}")
    
    def _create_workflow(self):
        """Create a new workflow."""
        # TODO: Implement workflow creation
        QMessageBox.information(self, "Not Implemented", "Workflow creation not implemented yet")
    
    def _save_settings(self):
        """Save application settings."""
        self.config.save()
        self.status_bar.showMessage("Settings saved")
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully")
    
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