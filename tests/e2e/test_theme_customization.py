"""
End-to-end tests for theme customization.

These tests verify the theme customization and management functionality.
"""

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QPushButton, QComboBox, QColorDialog, QApplication
)
from PyQt6.QtGui import QColor

from obscopilot.ui.theme_customizer import ThemeCustomizerWidget, ThemeEditorDialog


def find_settings_dialog(qtbot):
    """Find the settings dialog."""
    dialogs = [w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog)]
    for dialog in dialogs:
        if hasattr(dialog, 'tab_widget'):
            return dialog
    return None


def test_open_theme_settings(main_window, qtbot, monkeypatch):
    """Test opening theme settings dialog."""
    # Find Settings in menu
    settings_action = None
    for action in main_window.menuBar().actions():
        if action.text() == "Settings":
            settings_action = action
            break
    
    assert settings_action is not None
    
    # Click on Settings action
    def handle_settings_dialog():
        settings_dialog = find_settings_dialog(qtbot)
        assert settings_dialog is not None
        
        # Find and click on Appearance tab
        tab_widget = settings_dialog.tab_widget
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "Appearance":
                tab_widget.setCurrentIndex(i)
                break
        
        # Verify theme customizer is in the tab
        theme_customizer = None
        for widget in tab_widget.currentWidget().findChildren(ThemeCustomizerWidget):
            theme_customizer = widget
            break
        
        assert theme_customizer is not None
        
        # Close dialog
        close_button = [b for b in settings_dialog.findChildren(QPushButton) 
                       if b.text() == "Close"][0]
        qtbot.mouseClick(close_button, Qt.MouseButton.LeftButton)
    
    # Schedule the handler and click the action
    QTimer.singleShot(100, handle_settings_dialog)
    settings_action.trigger()
    
    # Wait for everything to process
    qtbot.wait(500)


def test_create_custom_theme(main_window, qtbot, monkeypatch):
    """Test creating a custom theme."""
    # First open settings
    settings_action = None
    for action in main_window.menuBar().actions():
        if action.text() == "Settings":
            settings_action = action
            break
    
    assert settings_action is not None
    
    # Mock color dialog to return specific colors
    def mock_get_color(initial=None, *args, **kwargs):
        return QColor("#00FF00")  # Return green
    
    monkeypatch.setattr(QColorDialog, "getColor", mock_get_color)
    
    # Click on Settings action
    def handle_settings_dialog():
        settings_dialog = find_settings_dialog(qtbot)
        assert settings_dialog is not None
        
        # Find and click on Appearance tab
        tab_widget = settings_dialog.tab_widget
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "Appearance":
                tab_widget.setCurrentIndex(i)
                break
        
        # Find theme customizer
        theme_customizer = None
        for widget in tab_widget.currentWidget().findChildren(ThemeCustomizerWidget):
            theme_customizer = widget
            break
        
        assert theme_customizer is not None
        
        # Click Add Theme button
        add_button = theme_customizer.add_button
        
        # Set up handler for editor dialog
        QTimer.singleShot(100, lambda: handle_theme_editor_dialog(qtbot))
        
        # Click add button
        qtbot.mouseClick(add_button, Qt.MouseButton.LeftButton)
    
    def handle_theme_editor_dialog(qtbot):
        # Find the theme editor dialog
        editor_dialog = None
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, ThemeEditorDialog):
                editor_dialog = widget
                break
                
        assert editor_dialog is not None
        
        # Fill in theme details
        qtbot.keyClicks(editor_dialog.name_edit, "E2E Test Theme")
        qtbot.keyClicks(editor_dialog.description_edit, "Theme created by E2E test")
        
        # Click on a color picker to change a color
        background_picker = editor_dialog.color_pickers[0]  # First color picker
        qtbot.mouseClick(background_picker, Qt.MouseButton.LeftButton)
        
        # Verify color was changed
        assert background_picker.color() == QColor("#00FF00")
        
        # Click save button
        save_button = [b for b in editor_dialog.findChildren(QPushButton) 
                      if b.text() == "Save"][0]
        qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
        
        # Close settings dialog
        settings_dialog = find_settings_dialog(qtbot)
        close_button = [b for b in settings_dialog.findChildren(QPushButton) 
                       if b.text() == "Close"][0]
        qtbot.mouseClick(close_button, Qt.MouseButton.LeftButton)
    
    # Schedule the handler and click the action
    QTimer.singleShot(100, handle_settings_dialog)
    settings_action.trigger()
    
    # Wait for everything to process
    qtbot.wait(1000)


def test_apply_theme(main_window, qtbot, monkeypatch):
    """Test applying a theme."""
    # First open settings
    settings_action = None
    for action in main_window.menuBar().actions():
        if action.text() == "Settings":
            settings_action = action
            break
    
    assert settings_action is not None
    
    # Click on Settings action
    def handle_settings_dialog():
        settings_dialog = find_settings_dialog(qtbot)
        assert settings_dialog is not None
        
        # Find and click on Appearance tab
        tab_widget = settings_dialog.tab_widget
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "Appearance":
                tab_widget.setCurrentIndex(i)
                break
        
        # Find theme customizer
        theme_customizer = None
        for widget in tab_widget.currentWidget().findChildren(ThemeCustomizerWidget):
            theme_customizer = widget
            break
        
        assert theme_customizer is not None
        
        # Select "Light" theme
        theme_selector = theme_customizer.theme_selector
        for i in range(theme_selector.count()):
            if theme_selector.itemText(i) == "Light":
                theme_selector.setCurrentIndex(i)
                break
        
        # Mock theme manager to verify apply_theme is called
        original_apply_theme = theme_customizer.theme_manager.apply_theme
        
        def mock_apply_theme(theme_name):
            assert theme_name == "Light"
            # Call original to actually apply the theme
            original_apply_theme(theme_name)
        
        theme_customizer.theme_manager.apply_theme = mock_apply_theme
        
        # Click Apply button
        apply_button = theme_customizer.apply_button
        qtbot.mouseClick(apply_button, Qt.MouseButton.LeftButton)
        
        # Close settings dialog
        close_button = [b for b in settings_dialog.findChildren(QPushButton) 
                       if b.text() == "Close"][0]
        qtbot.mouseClick(close_button, Qt.MouseButton.LeftButton)
    
    # Schedule the handler and click the action
    QTimer.singleShot(100, handle_settings_dialog)
    settings_action.trigger()
    
    # Wait for everything to process
    qtbot.wait(500) 