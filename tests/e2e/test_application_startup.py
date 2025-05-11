"""
End-to-end tests for application startup.

These tests verify that the application starts up correctly and all
main components are properly initialized.
"""

import pytest
from PyQt6.QtWidgets import QMenuBar, QStatusBar, QDockWidget, QToolBar


def test_main_window_creation(main_window):
    """Test that main window is created successfully."""
    # Check that the main window has a title
    assert main_window.windowTitle() == "OBSCopilot"
    
    # Check that window is visible
    assert main_window.isVisible()
    
    # Test window has expected size
    assert main_window.width() >= 800
    assert main_window.height() >= 600


def test_main_window_components(main_window):
    """Test that main window has all required components."""
    # Check for menubar
    assert main_window.menuBar() is not None
    assert isinstance(main_window.menuBar(), QMenuBar)
    
    # Check for status bar
    assert main_window.statusBar() is not None
    assert isinstance(main_window.statusBar(), QStatusBar)
    
    # Check for toolbar
    toolbar = main_window.findChild(QToolBar)
    assert toolbar is not None
    
    # Check for dock widgets (should have at least one)
    dock_widgets = main_window.findChildren(QDockWidget)
    assert len(dock_widgets) > 0


def test_services_initialized(main_window, service_manager):
    """Test that services are initialized properly."""
    # Check that service manager has registered services
    assert len(service_manager.services) > 0
    
    # Services should be in test mode
    for service in service_manager.services:
        assert service.config.test_mode is True


def test_theme_applied(main_window):
    """Test that a theme is applied to the application."""
    # Check that palette has been set
    palette = main_window.palette()
    assert palette is not None
    
    # Should have different colors for different roles
    bg_color = palette.color(palette.ColorRole.Window)
    text_color = palette.color(palette.ColorRole.WindowText)
    
    # Text and background should be different colors
    assert bg_color != text_color 