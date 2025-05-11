"""
Common fixtures for end-to-end testing.

This module provides fixtures used across end-to-end tests.
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from obscopilot.ui.main import MainWindow
from obscopilot.core.config import Config
from obscopilot.core.services import ServiceManager


@pytest.fixture(scope="session")
def app():
    """QApplication instance that persists for the full test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't call app.quit() as it would close the running app if pytest is being
    # run from within an existing PyQt application


@pytest.fixture
def test_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def config(test_data_dir):
    """Create a test configuration."""
    # Create config directories
    config_dir = test_data_dir / "config"
    workflows_dir = test_data_dir / "workflows"
    themes_dir = test_data_dir / "themes"
    logs_dir = test_data_dir / "logs"
    
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(workflows_dir, exist_ok=True)
    os.makedirs(themes_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create config object with test directories
    config = Config()
    config.config_dir = str(config_dir)
    config.workflows_dir = str(workflows_dir)
    config.themes_dir = str(themes_dir)
    config.logs_dir = str(logs_dir)
    
    # Set test mode
    config.test_mode = True
    
    yield config


@pytest.fixture
def service_manager(config):
    """Create a service manager with mock services."""
    manager = ServiceManager(config)
    
    # Replace actual services with mocks for testing
    # This prevents actual connections to external services during tests
    manager.register_mock_services()
    
    yield manager


@pytest.fixture
def main_window(qtbot, app, config, service_manager):
    """Create main application window for testing."""
    # Initialize main window with test config and services
    window = MainWindow(config, service_manager)
    window.show()
    
    # Add to qtbot so it can be closed properly
    qtbot.addWidget(window)
    
    # Wait for window to appear
    qtbot.waitExposed(window)
    
    yield window
    
    # Clean up
    window.close() 