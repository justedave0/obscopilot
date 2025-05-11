"""
Tests for the theme customizer component.
"""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QColorDialog
from PyQt6.QtGui import QColor

from obscopilot.ui.theme_customizer import (
    ThemeCustomizerWidget, ThemeEditorDialog, ColorPickerButton
)
from obscopilot.ui.themes import ThemeManager, Theme, ColorRole


@pytest.fixture
def theme_manager():
    """Create a theme manager instance."""
    manager = ThemeManager()
    
    # Add a custom theme for testing
    test_theme = Theme(
        name="Test Theme",
        description="A theme for testing",
        colors={
            ColorRole.BACKGROUND: "#121212",
            ColorRole.TEXT: "#FFFFFF",
            ColorRole.ACCENT: "#00AAFF",
            ColorRole.BUTTON_BACKGROUND: "#333333",
            ColorRole.BUTTON_TEXT: "#FFFFFF"
        }
    )
    manager.add_theme(test_theme)
    
    return manager


@pytest.fixture
def customizer_widget(qtbot, theme_manager):
    """Create a theme customizer widget."""
    widget = ThemeCustomizerWidget(theme_manager)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def color_picker_button(qtbot):
    """Create a color picker button."""
    button = ColorPickerButton(QColor("#FF0000"))
    qtbot.addWidget(button)
    return button


@pytest.fixture
def theme_editor(qtbot, theme_manager):
    """Create a theme editor dialog."""
    dialog = ThemeEditorDialog(theme_manager)
    qtbot.addWidget(dialog)
    return dialog


def test_color_picker_button_init(color_picker_button):
    """Test color picker button initialization."""
    # Check initial color
    assert color_picker_button.color() == QColor("#FF0000")
    
    # Check that button has correct background color
    assert color_picker_button.styleSheet().startswith("background-color:")


def test_color_picker_button_set_color(color_picker_button):
    """Test setting color on button."""
    # Set new color
    color_picker_button.set_color(QColor("#00FF00"))
    
    # Check color was updated
    assert color_picker_button.color() == QColor("#00FF00")
    
    # Check that button style was updated
    assert "background-color: #00FF00" in color_picker_button.styleSheet()


@patch('PyQt6.QtWidgets.QColorDialog.getColor')
def test_color_picker_button_click(mock_get_color, qtbot, color_picker_button):
    """Test clicking color picker button."""
    # Set up mock to return a color
    mock_get_color.return_value = QColor("#0000FF")
    
    # Click button
    qtbot.mouseClick(color_picker_button, Qt.MouseButton.LeftButton)
    
    # Check that dialog was shown
    mock_get_color.assert_called_once()
    
    # Check that color was updated
    assert color_picker_button.color() == QColor("#0000FF")
    
    # Check that colorChanged signal was emitted
    assert "background-color: #0000FF" in color_picker_button.styleSheet()


def test_theme_editor_initialization(theme_editor, theme_manager):
    """Test theme editor initialization."""
    # Check that editor has theme manager
    assert theme_editor.theme_manager == theme_manager
    
    # Check that UI components were created
    assert theme_editor.name_edit is not None
    assert theme_editor.description_edit is not None
    
    # Check that color pickers were created for each role
    for role in ColorRole:
        assert role in theme_editor.color_pickers


def test_theme_editor_load_theme(theme_editor, theme_manager):
    """Test loading a theme in the editor."""
    # Load a theme
    theme = theme_manager.get_theme("Test Theme")
    theme_editor.load_theme(theme)
    
    # Check that fields were populated
    assert theme_editor.name_edit.text() == "Test Theme"
    assert theme_editor.description_edit.toPlainText() == "A theme for testing"
    
    # Check that color pickers were updated
    for role in ColorRole:
        if role in theme.colors:
            assert theme_editor.color_pickers[role].color() == QColor(theme.colors[role])


def test_theme_editor_create_theme(theme_editor):
    """Test creating a theme in the editor."""
    # Set values
    theme_editor.name_edit.setText("New Theme")
    theme_editor.description_edit.setText("A new test theme")
    
    # Set colors
    theme_editor.color_pickers[ColorRole.BACKGROUND].set_color(QColor("#222222"))
    theme_editor.color_pickers[ColorRole.TEXT].set_color(QColor("#EEEEEE"))
    
    # Create theme
    theme = theme_editor.create_theme()
    
    # Check theme properties
    assert theme.name == "New Theme"
    assert theme.description == "A new test theme"
    assert theme.colors[ColorRole.BACKGROUND] == "#222222"
    assert theme.colors[ColorRole.TEXT] == "#EEEEEE"


@patch('PyQt6.QtWidgets.QDialog.exec')
def test_theme_editor_accept(mock_exec, theme_editor):
    """Test accepting theme editor."""
    # Set up mock to return accepted
    mock_exec.return_value = QDialog.DialogCode.Accepted
    
    # Set theme data
    theme_editor.name_edit.setText("Accepted Theme")
    theme_editor.description_edit.setText("This theme was accepted")
    
    # Set result theme
    theme_editor._result_theme = Theme(
        name="Accepted Theme",
        description="This theme was accepted"
    )
    
    # Execute dialog
    result = theme_editor.exec()
    
    # Check that exec was called
    mock_exec.assert_called_once()
    
    # Check that return value is as expected
    assert result == QDialog.DialogCode.Accepted
    assert theme_editor.result_theme.name == "Accepted Theme"


def test_customizer_widget_initialization(customizer_widget, theme_manager):
    """Test customizer widget initialization."""
    # Check that widget has theme manager
    assert customizer_widget.theme_manager == theme_manager
    
    # Check that UI components were created
    assert customizer_widget.theme_selector is not None
    assert customizer_widget.apply_button is not None
    assert customizer_widget.edit_button is not None
    assert customizer_widget.add_button is not None
    assert customizer_widget.delete_button is not None
    
    # Check that theme selector has themes
    assert customizer_widget.theme_selector.count() > 0
    assert customizer_widget.theme_selector.findText("Test Theme") >= 0


@patch('obscopilot.ui.theme_customizer.ThemeEditorDialog')
def test_customizer_add_theme(mock_dialog, customizer_widget, theme_manager):
    """Test adding a theme in the customizer."""
    # Set up mock dialog
    mock_instance = MagicMock()
    mock_dialog.return_value = mock_instance
    mock_instance.exec.return_value = QDialog.DialogCode.Accepted
    
    # Set up result theme
    new_theme = Theme(
        name="Added Theme",
        description="Theme added via customizer"
    )
    mock_instance.result_theme = new_theme
    
    # Click add button
    customizer_widget._on_add_theme()
    
    # Check that dialog was created and executed
    mock_dialog.assert_called_once_with(theme_manager)
    mock_instance.exec.assert_called_once()
    
    # Check that theme was added to manager
    assert "Added Theme" in theme_manager.get_theme_names()
    
    # Check that theme selector was updated
    assert customizer_widget.theme_selector.findText("Added Theme") >= 0


@patch('obscopilot.ui.theme_customizer.ThemeEditorDialog')
def test_customizer_edit_theme(mock_dialog, customizer_widget, theme_manager):
    """Test editing a theme in the customizer."""
    # Select a theme
    index = customizer_widget.theme_selector.findText("Test Theme")
    customizer_widget.theme_selector.setCurrentIndex(index)
    
    # Set up mock dialog
    mock_instance = MagicMock()
    mock_dialog.return_value = mock_instance
    mock_instance.exec.return_value = QDialog.DialogCode.Accepted
    
    # Set up result theme
    edited_theme = Theme(
        name="Test Theme",
        description="Edited description",
        colors={
            ColorRole.BACKGROUND: "#333333",
            ColorRole.TEXT: "#CCCCCC"
        }
    )
    mock_instance.result_theme = edited_theme
    
    # Click edit button
    customizer_widget._on_edit_theme()
    
    # Check that dialog was created and executed
    mock_dialog.assert_called_once()
    mock_instance.load_theme.assert_called_once()
    mock_instance.exec.assert_called_once()
    
    # Check that theme was updated in manager
    updated_theme = theme_manager.get_theme("Test Theme")
    assert updated_theme.description == "Edited description"
    assert updated_theme.colors[ColorRole.BACKGROUND] == "#333333"


@patch('PyQt6.QtWidgets.QMessageBox.question')
def test_customizer_delete_theme(mock_question, customizer_widget, theme_manager):
    """Test deleting a theme in the customizer."""
    # Select a theme
    index = customizer_widget.theme_selector.findText("Test Theme")
    customizer_widget.theme_selector.setCurrentIndex(index)
    
    # Set up mock message box to return Yes
    from PyQt6.QtWidgets import QMessageBox
    mock_question.return_value = QMessageBox.StandardButton.Yes
    
    # Click delete button
    customizer_widget._on_delete_theme()
    
    # Check that confirmation was shown
    mock_question.assert_called_once()
    
    # Check that theme was removed from manager
    assert "Test Theme" not in theme_manager.get_theme_names()
    
    # Check that theme selector was updated
    assert customizer_widget.theme_selector.findText("Test Theme") == -1


def test_customizer_apply_theme(customizer_widget, theme_manager):
    """Test applying a theme in the customizer."""
    # Select a theme
    index = customizer_widget.theme_selector.findText("Test Theme")
    customizer_widget.theme_selector.setCurrentIndex(index)
    
    # Mock theme manager's apply_theme method
    theme_manager.apply_theme = MagicMock()
    
    # Click apply button
    customizer_widget._on_apply_theme()
    
    # Check that theme was applied
    theme_manager.apply_theme.assert_called_once_with("Test Theme") 