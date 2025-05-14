import os
import pytest
import logging
import tempfile
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QTabWidget, QWidget, QVBoxLayout, QLabel

from ui.main_window import ObsCoPilotApp, setup_logging
from ui.tabs.settings_controller import EventType, event_manager

class TestMainWindow:
    @pytest.fixture
    def app(self):
        """Fixture that provides a QApplication instance."""
        app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def main_window(self, app):
        """Fixture that provides a main window instance."""
        with patch('ui.main_window.QTimer.singleShot') as mock_timer:
            window = ObsCoPilotApp()
            yield window
    
    def test_init(self, main_window):
        """Test initializing the main window."""
        assert main_window.windowTitle() == "ObsCoPilot"
        assert main_window.minimumSize().width() == 1024
        assert main_window.minimumSize().height() == 768
        assert isinstance(main_window.tabs, QTabWidget)
        assert main_window.tabs.count() == 3
        assert main_window.tabs.tabText(0) == "Dashboard"
        assert main_window.tabs.tabText(1) == "Workflows"
        assert main_window.tabs.tabText(2) == "Settings"
        assert isinstance(main_window.dashboard_tab, QWidget)
        assert isinstance(main_window.workflows_tab, QWidget)
        assert not main_window.app_started_emitted
    
    def test_emit_app_started_event(self, main_window):
        """Test emitting the app started event."""
        # Mock the event_manager.emit method
        with patch('ui.tabs.settings_controller.event_manager.emit') as mock_emit:
            # Call the method
            main_window.emit_app_started_event()
            
            # Check that the event was emitted
            mock_emit.assert_called_once_with(EventType.APP_STARTED)
            
            # Check that the flag was set
            assert main_window.app_started_emitted
            
            # Call again to test the skipping behavior
            main_window.emit_app_started_event()
            
            # Check that emit was not called again
            mock_emit.assert_called_once()
    
    def test_on_app_started(self, main_window):
        """Test handling the app started event."""
        # Mock the _check_auto_connect method
        main_window.settings_controller._check_auto_connect = MagicMock()
        
        # Call the method
        main_window.on_app_started()
        
        # Check that _check_auto_connect was called
        main_window.settings_controller._check_auto_connect.assert_called_once()
    
    def test_setup_dashboard_tab(self, main_window):
        """Test setting up the dashboard tab."""
        # Clear the dashboard tab layout
        if main_window.dashboard_tab.layout():
            for i in reversed(range(main_window.dashboard_tab.layout().count())): 
                main_window.dashboard_tab.layout().itemAt(i).widget().deleteLater()
        
        # Call the method
        main_window.setup_dashboard_tab()
        
        # Check that the layout was set up correctly
        assert isinstance(main_window.dashboard_tab.layout(), QVBoxLayout)
        assert main_window.dashboard_tab.layout().count() == 1
        assert isinstance(main_window.dashboard_tab.layout().itemAt(0).widget(), QLabel)
        assert main_window.dashboard_tab.layout().itemAt(0).widget().text() == "Dashboard"
    
    def test_setup_workflows_tab(self, main_window):
        """Test setting up the workflows tab."""
        # Clear the workflows tab layout
        if main_window.workflows_tab.layout():
            for i in reversed(range(main_window.workflows_tab.layout().count())): 
                main_window.workflows_tab.layout().itemAt(i).widget().deleteLater()
        
        # Call the method
        main_window.setup_workflows_tab()
        
        # Check that the layout was set up correctly
        assert isinstance(main_window.workflows_tab.layout(), QVBoxLayout)
        assert main_window.workflows_tab.layout().count() == 1
        assert isinstance(main_window.workflows_tab.layout().itemAt(0).widget(), QLabel)
        assert main_window.workflows_tab.layout().itemAt(0).widget().text() == "Workflows"
    
    def test_setup_event_listeners(self, main_window):
        """Test setting up event listeners."""
        # Mock the event_manager.subscribe method
        with patch('ui.tabs.settings_controller.event_manager.subscribe') as mock_subscribe:
            # Call the method
            main_window.setup_event_listeners()
            
            # Check that subscribe was called with the correct arguments
            mock_subscribe.assert_called_once_with(EventType.APP_STARTED, main_window.on_app_started)
    
    def test_setup_logging(self):
        """Test setting up logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch expanduser to use temp directory
            with patch('os.path.expanduser', return_value=temp_dir):
                # Patch logging setup functions
                with patch('logging.getLogger') as mock_get_logger, \
                     patch('logging.StreamHandler') as mock_stream_handler, \
                     patch('logging.handlers.RotatingFileHandler') as mock_file_handler, \
                     patch('logging.info') as mock_info:
                    
                    # Setup mock logger
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    
                    # Create mock handlers
                    mock_console = MagicMock()
                    mock_file = MagicMock()
                    mock_stream_handler.return_value = mock_console
                    mock_file_handler.return_value = mock_file
                    
                    # Call setup_logging
                    setup_logging()
                    
                    # Verify the log directory was created
                    log_dir = os.path.join(temp_dir, '.obscopilot', 'logs')
                    assert os.path.exists(log_dir)
                    
                    # Verify logger was configured
                    mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
                    mock_logger.addHandler.assert_any_call(mock_console)
                    mock_logger.addHandler.assert_any_call(mock_file)
                    
                    # Verify handlers were configured
                    mock_console.setLevel.assert_called_once_with(logging.INFO)
                    mock_file.setLevel.assert_called_once_with(logging.DEBUG) 