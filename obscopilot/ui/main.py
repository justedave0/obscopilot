"""
Main UI window for OBSCopilot.
"""

import logging
import sys
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QStatusBar, QToolBar,
    QMessageBox, QFileDialog, QMenu
)

from obscopilot.core.config import Config
from obscopilot.storage.database import Database
from obscopilot.storage.repositories import (
    WorkflowRepository, SettingRepository, TwitchAuthRepository
)
from obscopilot.twitch.client import TwitchClient
from obscopilot.obs.client import OBSClient
from obscopilot.workflows.engine import WorkflowEngine
from obscopilot.ai.openai import OpenAIClient

logger = logging.getLogger(__name__)


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
        # Add dashboard widgets here
        status_label = QLabel("Dashboard - Status Overview")
        status_label.setFont(QFont("Arial", 16))
        self.dashboard_layout.addWidget(status_label)
        
        # Add placeholders for status widgets
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        
        # Twitch status
        twitch_status = QWidget()
        twitch_layout = QVBoxLayout(twitch_status)
        twitch_layout.addWidget(QLabel("Twitch"))
        self.twitch_status_label = QLabel("Disconnected")
        twitch_layout.addWidget(self.twitch_status_label)
        status_layout.addWidget(twitch_status)
        
        # OBS status
        obs_status = QWidget()
        obs_layout = QVBoxLayout(obs_status)
        obs_layout.addWidget(QLabel("OBS"))
        self.obs_status_label = QLabel("Disconnected")
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
        
        # Workflow list placeholder
        workflow_list_label = QLabel("No workflows loaded")
        self.workflows_layout.addWidget(workflow_list_label)
        
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
                self._update_connection_status()
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