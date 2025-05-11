"""
Theme Management for OBSCopilot.

This module provides theme management functionality, 
including dark and light themes for the application.
"""

import logging
from enum import Enum
from typing import Dict, Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Theme types."""
    
    DARK = "dark"
    LIGHT = "light"


class ThemeManager:
    """Theme manager for application styling."""
    
    def __init__(self):
        """Initialize theme manager."""
        self.current_theme = ThemeType.DARK
        self._themes = {
            ThemeType.DARK: self._create_dark_palette(),
            ThemeType.LIGHT: self._create_light_palette()
        }
        
        # Stylesheet templates
        self._style_templates = {
            ThemeType.DARK: self._get_dark_stylesheet(),
            ThemeType.LIGHT: self._get_light_stylesheet()
        }
        
    def apply_theme(self, app: QApplication, theme_type: Optional[ThemeType] = None):
        """Apply theme to application.
        
        Args:
            app: QApplication instance
            theme_type: Theme type to apply, or None for current theme
        """
        if theme_type is not None:
            self.current_theme = theme_type
            
        # Apply palette
        app.setPalette(self._themes[self.current_theme])
        
        # Apply stylesheet
        app.setStyleSheet(self._style_templates[self.current_theme])
        
        logger.info(f"Applied {self.current_theme.value} theme")
    
    def toggle_theme(self, app: QApplication):
        """Toggle between dark and light themes.
        
        Args:
            app: QApplication instance
        """
        new_theme = ThemeType.LIGHT if self.current_theme == ThemeType.DARK else ThemeType.DARK
        self.apply_theme(app, new_theme)
        
    def _create_dark_palette(self) -> QPalette:
        """Create dark theme palette.
        
        Returns:
            QPalette configured for dark theme
        """
        palette = QPalette()
        
        # Base colors
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        
        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
        
        return palette
        
    def _create_light_palette(self) -> QPalette:
        """Create light theme palette.
        
        Returns:
            QPalette configured for light theme
        """
        palette = QPalette()
        
        # Base colors
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(233, 233, 233))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        
        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(115, 115, 115))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(115, 115, 115))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(115, 115, 115))
        
        return palette
    
    def _get_dark_stylesheet(self) -> str:
        """Get stylesheet for dark theme.
        
        Returns:
            CSS stylesheet string
        """
        return """
        QToolTip { 
            color: #ffffff; 
            background-color: #2a2a2a; 
            border: 1px solid #767676; 
        }
        
        QTabWidget::pane {
            border: 1px solid #444;
        }
        
        QTabBar::tab {
            background-color: #353535;
            color: #ffffff;
            padding: 6px 12px;
            border: 1px solid #444;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #444;
        }
        
        QTabBar::tab:hover {
            background-color: #555;
        }
        
        QPushButton {
            background-color: #353535;
            color: #ffffff;
            border: 1px solid #555;
            padding: 5px 10px;
            border-radius: 3px;
        }
        
        QPushButton:hover {
            background-color: #444;
        }
        
        QPushButton:pressed {
            background-color: #2a82da;
        }
        
        QPushButton:disabled {
            background-color: #353535;
            color: #7f7f7f;
        }
        
        QComboBox {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 3px 16px 3px 3px;
        }
        
        QComboBox:hover {
            background-color: #353535;
        }
        
        QComboBox QAbstractItemView {
            background-color: #2a2a2a;
            color: #ffffff;
            selection-background-color: #2a82da;
        }
        
        QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 14px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #5f5f5f;
            min-height: 20px;
            border-radius: 5px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #6f6f6f;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #2a2a2a;
            height: 14px;
            margin: 0px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #5f5f5f;
            min-width: 20px;
            border-radius: 5px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #6f6f6f;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        QLineEdit, QTextEdit {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 3px;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #2a82da;
        }
        
        QCheckBox {
            color: #ffffff;
        }
        
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #555;
            border-radius: 2px;
            background-color: #2a2a2a;
        }
        
        QCheckBox::indicator:checked {
            background-color: #2a82da;
        }
        
        QRadioButton {
            color: #ffffff;
        }
        
        QRadioButton::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #555;
            border-radius: 7px;
            background-color: #2a2a2a;
        }
        
        QRadioButton::indicator:checked {
            background-color: #2a82da;
        }
        
        QMenuBar {
            background-color: #353535;
            color: #ffffff;
        }
        
        QMenuBar::item {
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #444;
        }
        
        QMenu {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555;
        }
        
        QMenu::item:selected {
            background-color: #2a82da;
        }
        
        QProgressBar {
            border: 1px solid #555;
            border-radius: 3px;
            background-color: #2a2a2a;
            color: #ffffff;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #2a82da;
            width: 10px;
        }
        
        QStatusBar {
            background-color: #353535;
            color: #ffffff;
            border-top: 1px solid #555;
        }
        """
    
    def _get_light_stylesheet(self) -> str:
        """Get stylesheet for light theme.
        
        Returns:
            CSS stylesheet string
        """
        return """
        QToolTip { 
            color: #000000; 
            background-color: #ffffff; 
            border: 1px solid #c0c0c0; 
        }
        
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
        }
        
        QTabBar::tab {
            background-color: #f0f0f0;
            color: #000000;
            padding: 6px 12px;
            border: 1px solid #c0c0c0;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #ffffff;
        }
        
        QTabBar::tab:hover {
            background-color: #f5f5f5;
        }
        
        QPushButton {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #c0c0c0;
            padding: 5px 10px;
            border-radius: 3px;
        }
        
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        
        QPushButton:pressed {
            background-color: #0078d7;
            color: #ffffff;
        }
        
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #737373;
        }
        
        QComboBox {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 3px 16px 3px 3px;
        }
        
        QComboBox:hover {
            background-color: #f0f0f0;
        }
        
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #000000;
            selection-background-color: #0078d7;
            selection-color: #ffffff;
        }
        
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 14px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            min-height: 20px;
            border-radius: 5px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #f0f0f0;
            height: 14px;
            margin: 0px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #c0c0c0;
            min-width: 20px;
            border-radius: 5px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #a0a0a0;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        QLineEdit, QTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 3px;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #0078d7;
        }
        
        QCheckBox {
            color: #000000;
        }
        
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #c0c0c0;
            border-radius: 2px;
            background-color: #ffffff;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0078d7;
        }
        
        QRadioButton {
            color: #000000;
        }
        
        QRadioButton::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #c0c0c0;
            border-radius: 7px;
            background-color: #ffffff;
        }
        
        QRadioButton::indicator:checked {
            background-color: #0078d7;
        }
        
        QMenuBar {
            background-color: #f0f0f0;
            color: #000000;
        }
        
        QMenuBar::item {
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #c0c0c0;
        }
        
        QMenu::item:selected {
            background-color: #0078d7;
            color: #ffffff;
        }
        
        QProgressBar {
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            background-color: #ffffff;
            color: #000000;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #0078d7;
            width: 10px;
        }
        
        QStatusBar {
            background-color: #f0f0f0;
            color: #000000;
            border-top: 1px solid #c0c0c0;
        }
        """


# Global theme manager instance
theme_manager = ThemeManager()

def get_theme_manager() -> ThemeManager:
    """Get the theme manager instance.
    
    Returns:
        ThemeManager instance
    """
    return theme_manager 