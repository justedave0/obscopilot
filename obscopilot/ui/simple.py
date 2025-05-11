"""
Simple UI module for OBSCopilot.

This module provides a simplified UI that doesn't require complex dependencies.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTabWidget, QStatusBar
)

class SimpleMainWindow(QMainWindow):
    """Simple main window for OBSCopilot."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
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
        twitch_status_label = QLabel("Not Connected")
        twitch_layout.addWidget(twitch_status_label)
        status_layout.addWidget(twitch_status)
        
        # OBS status
        obs_status = QWidget()
        obs_layout = QVBoxLayout(obs_status)
        obs_layout.addWidget(QLabel("OBS"))
        obs_status_label = QLabel("Not Connected")
        obs_layout.addWidget(obs_status_label)
        status_layout.addWidget(obs_status)
        
        # Workflows status
        workflows_status = QWidget()
        workflows_layout = QVBoxLayout(workflows_status)
        workflows_layout.addWidget(QLabel("Workflows"))
        workflows_status_label = QLabel("0 loaded")
        workflows_layout.addWidget(workflows_status_label)
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
        
        # Add spacer
        self.settings_layout.addStretch()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Apply dark theme
        self._apply_dark_theme()
    
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