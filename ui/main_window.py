import logging
import logging.handlers
import os
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, 
                            QWidget, QVBoxLayout, QLabel)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

from ui.tabs.settings_tab import SettingsTab
from ui.tabs.settings_controller import event_manager, EventType, SettingsController

# Configure logging
def setup_logging():
    """Set up logging for the application"""
    # Create logs directory
    logs_dir = os.path.join(os.path.expanduser("~"), ".obscopilot", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # File handler
    log_file = os.path.join(logs_dir, "obscopilot.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log startup
    logging.info(f"ObsCoPilot starting - Log file: {log_file}")

# Set up logging at import time
setup_logging()

class ObsCoPilotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info("Initializing ObsCoPilotApp")
        self.setWindowTitle("ObsCoPilot")
        self.setMinimumSize(1024, 768)
        
        # Flag to ensure we only emit app started once
        self.app_started_emitted = False
        
        # Create the central settings controller to be shared app-wide
        # This ensures only one instance exists for all tabs
        self.settings_controller = SettingsController()
        
        # Create the main tab widget
        self.tabs = QTabWidget()
        
        # Create the three main tabs
        self.dashboard_tab = QWidget()
        self.workflows_tab = QWidget()
        
        # Pass the shared controller to settings tab
        self.settings_tab = SettingsTab(settings_controller=self.settings_controller)
        
        # Set up each tab
        self.setup_dashboard_tab()
        self.setup_workflows_tab()
        
        # Add tabs to widget
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.workflows_tab, "Workflows")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Set the central widget
        self.setCentralWidget(self.tabs)
        logging.info("ObsCoPilotApp initialized")
        
        # Set up event listeners
        self.setup_event_listeners()
        
        # Emit app started event after a delay to ensure all components are loaded
        # Use a longer delay to ensure everything is ready
        QTimer.singleShot(2000, self.emit_app_started_event)
    
    def setup_event_listeners(self):
        """Set up event listeners for the app"""
        logging.info("Setting up event listeners in main window")
        event_manager.subscribe(EventType.APP_STARTED, self.on_app_started)
    
    def on_app_started(self, data=None):
        """Handle app started event - this is where we trigger auto-connect"""
        logging.info("MAIN WINDOW: App started event received - performing auto-connect check")
        # Trigger auto-connect check directly from main window
        # This is the CENTRAL place for auto-connect to happen, regardless of which tab is active
        self.settings_controller._check_auto_connect()
    
    def emit_app_started_event(self):
        """Emit app started event"""
        # Prevent duplicate emissions
        if self.app_started_emitted:
            logging.info("APP_STARTED event already emitted, skipping")
            return
        
        # Set the flag first to prevent any chance of re-entry
        self.app_started_emitted = True
            
        logging.info("Main window emitting APP_STARTED event")
        
        # Add try/except to ensure any errors don't crash the app
        try:
            event_manager.emit(EventType.APP_STARTED)
            logging.info("APP_STARTED event emission completed")
        except Exception as e:
            logging.error(f"Error during APP_STARTED event emission: {str(e)}")
            
        # Log completion
        logging.info("App initialization sequence completed")
    
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