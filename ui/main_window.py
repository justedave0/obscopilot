from PyQt6.QtWidgets import (QMainWindow, QTabWidget, 
                            QWidget, QVBoxLayout, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class ObsCoPilotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ObsCoPilot")
        self.setMinimumSize(1024, 768)
        
        # Create the main tab widget
        self.tabs = QTabWidget()
        
        # Create the three main tabs
        self.dashboard_tab = QWidget()
        self.workflows_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Set up each tab
        self.setup_dashboard_tab()
        self.setup_workflows_tab()
        self.setup_settings_tab()
        
        # Add tabs to widget
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.workflows_tab, "Workflows")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Set the central widget
        self.setCentralWidget(self.tabs)
    
    def setup_dashboard_tab(self):
        layout = QVBoxLayout()
        label = QLabel("Dashboard")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.dashboard_tab.setLayout(layout)
    
    def setup_workflows_tab(self):
        layout = QVBoxLayout()
        label = QLabel("Workflows")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.workflows_tab.setLayout(layout)
    
    def setup_settings_tab(self):
        layout = QVBoxLayout()
        label = QLabel("Settings")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.settings_tab.setLayout(layout) 