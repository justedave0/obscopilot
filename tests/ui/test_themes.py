"""
Tests for the theme manager component.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QWidget

from obscopilot.ui.themes import ThemeManager, Theme, ColorRole


@pytest.fixture
def theme_manager():
    """Create a theme manager instance."""
    # Use a temporary directory for theme storage
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create theme manager with temp directory
        manager = ThemeManager(themes_dir=temp_dir)
        yield manager


def test_theme_initialization():
    """Test theme initialization."""
    # Create a theme
    theme = Theme(
        name="Test Theme",
        description="Test theme description",
        colors={
            ColorRole.BACKGROUND: "#121212",
            ColorRole.TEXT: "#FFFFFF"
        }
    )
    
    # Check theme properties
    assert theme.name == "Test Theme"
    assert theme.description == "Test theme description"
    assert theme.colors[ColorRole.BACKGROUND] == "#121212"
    assert theme.colors[ColorRole.TEXT] == "#FFFFFF"
    
    # Check that theme has default colors for other roles
    assert ColorRole.ACCENT in theme.colors
    assert ColorRole.BUTTON_BACKGROUND in theme.colors


def test_theme_manager_initialization(theme_manager):
    """Test theme manager initialization."""
    # Check that default themes are loaded
    assert len(theme_manager.themes) > 0
    assert "Dark" in theme_manager.get_theme_names()
    assert "Light" in theme_manager.get_theme_names()


def test_get_theme(theme_manager):
    """Test getting a theme."""
    # Get dark theme
    dark_theme = theme_manager.get_theme("Dark")
    
    # Check that theme exists and has properties
    assert dark_theme is not None
    assert dark_theme.name == "Dark"
    assert isinstance(dark_theme, Theme)
    
    # Check for non-existent theme
    assert theme_manager.get_theme("NonExistent") is None


def test_add_theme(theme_manager):
    """Test adding a theme."""
    # Create new theme
    new_theme = Theme(
        name="Custom Theme",
        description="A custom test theme",
        colors={
            ColorRole.BACKGROUND: "#222222",
            ColorRole.TEXT: "#EEEEEE",
            ColorRole.ACCENT: "#FF5500"
        }
    )
    
    # Add theme
    theme_manager.add_theme(new_theme)
    
    # Check that theme was added
    assert "Custom Theme" in theme_manager.get_theme_names()
    
    # Get theme and check properties
    theme = theme_manager.get_theme("Custom Theme")
    assert theme is not None
    assert theme.name == "Custom Theme"
    assert theme.colors[ColorRole.ACCENT] == "#FF5500"


def test_remove_theme(theme_manager):
    """Test removing a theme."""
    # Add custom theme
    new_theme = Theme(
        name="Theme To Remove",
        description="This theme will be removed",
        colors={
            ColorRole.BACKGROUND: "#333333",
            ColorRole.TEXT: "#FFFFFF"
        }
    )
    theme_manager.add_theme(new_theme)
    
    # Check theme exists
    assert "Theme To Remove" in theme_manager.get_theme_names()
    
    # Remove theme
    theme_manager.remove_theme("Theme To Remove")
    
    # Check theme was removed
    assert "Theme To Remove" not in theme_manager.get_theme_names()
    
    # Try to remove non-existent theme (should not raise error)
    theme_manager.remove_theme("NonExistent")


def test_save_and_load_theme(theme_manager):
    """Test saving and loading themes."""
    # Create a theme
    custom_theme = Theme(
        name="Save Test Theme",
        description="Theme for testing save/load",
        colors={
            ColorRole.BACKGROUND: "#111111",
            ColorRole.TEXT: "#EEEEEE",
            ColorRole.ACCENT: "#00AAFF"
        }
    )
    
    # Add and save theme
    theme_manager.add_theme(custom_theme)
    theme_manager.save_themes()
    
    # Create a new theme manager with same directory
    new_manager = ThemeManager(themes_dir=theme_manager.themes_dir)
    
    # Check that theme was loaded
    assert "Save Test Theme" in new_manager.get_theme_names()
    loaded_theme = new_manager.get_theme("Save Test Theme")
    assert loaded_theme is not None
    assert loaded_theme.name == "Save Test Theme"
    assert loaded_theme.colors[ColorRole.ACCENT] == "#00AAFF"


def test_color_for_role(theme_manager):
    """Test getting color for role."""
    # Get a theme
    theme = theme_manager.get_theme("Dark")
    
    # Get color for roles
    background_color = theme_manager.color_for_role(ColorRole.BACKGROUND, theme.name)
    text_color = theme_manager.color_for_role(ColorRole.TEXT, theme.name)
    
    # Check colors
    assert isinstance(background_color, QColor)
    assert isinstance(text_color, QColor)
    
    # Check that colors match theme
    assert background_color.name() == QColor(theme.colors[ColorRole.BACKGROUND]).name()
    assert text_color.name() == QColor(theme.colors[ColorRole.TEXT]).name()


@patch('PyQt6.QtWidgets.QApplication')
def test_apply_theme(mock_qapp, theme_manager):
    """Test applying theme to application."""
    # Create mock application and widgets
    app = MagicMock()
    mock_qapp.instance.return_value = app
    
    # Create a fake palette
    palette = MagicMock()
    app.palette.return_value = palette
    
    # Create a theme
    theme = theme_manager.get_theme("Dark")
    
    # Apply theme
    theme_manager.apply_theme(theme.name)
    
    # Check that palette was modified and set
    assert palette.setColor.call_count > 0
    assert app.setPalette.call_count == 1


def test_get_theme_names(theme_manager):
    """Test getting theme names."""
    # Add custom themes
    theme1 = Theme(name="Custom Theme 1", description="Test theme 1")
    theme2 = Theme(name="Custom Theme 2", description="Test theme 2")
    
    theme_manager.add_theme(theme1)
    theme_manager.add_theme(theme2)
    
    # Get theme names
    theme_names = theme_manager.get_theme_names()
    
    # Check that default and custom themes are included
    assert "Dark" in theme_names
    assert "Light" in theme_names
    assert "Custom Theme 1" in theme_names
    assert "Custom Theme 2" in theme_names


def test_active_theme(theme_manager):
    """Test active theme functionality."""
    # Check default active theme
    assert theme_manager.active_theme_name == "Dark"
    
    # Change active theme
    theme_manager.apply_theme("Light")
    assert theme_manager.active_theme_name == "Light"
    
    # Get active theme
    active_theme = theme_manager.get_active_theme()
    assert active_theme is not None
    assert active_theme.name == "Light" 