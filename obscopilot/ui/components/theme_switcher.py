"""
Theme Switcher for OBSCopilot.

This module provides a simple widget for switching between light and dark themes.
"""

import logging
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QToolButton, 
    QLabel, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QColor

from obscopilot.ui.themes import ThemeType, get_theme_manager
from obscopilot.core.config import Config

logger = logging.getLogger(__name__)


class ThemeSwitcher(QWidget):
    """Widget for switching between themes."""
    
    theme_changed = pyqtSignal(ThemeType)
    
    def __init__(
        self, 
        config: Config,
        callback: Optional[Callable[[ThemeType], None]] = None,
        parent=None
    ):
        """Initialize the theme switcher.
        
        Args:
            config: Application configuration
            callback: Optional callback function when theme changes
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config = config
        self.callback = callback
        
        # Get theme manager
        self.theme_manager = get_theme_manager()
        
        # Initialize UI
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Theme label
        self.label = QLabel("Theme:")
        layout.addWidget(self.label)
        
        # Light theme button
        self.light_button = QToolButton()
        self.light_button.setText("Light")
        self.light_button.setCheckable(True)
        self.light_button.clicked.connect(lambda: self._on_theme_selected(ThemeType.LIGHT))
        layout.addWidget(self.light_button)
        
        # Dark theme button
        self.dark_button = QToolButton()
        self.dark_button.setText("Dark")
        self.dark_button.setCheckable(True)
        self.dark_button.clicked.connect(lambda: self._on_theme_selected(ThemeType.DARK))
        layout.addWidget(self.dark_button)
        
        # Set initial state
        self._update_buttons()
        
    def _update_buttons(self):
        """Update button states based on current theme."""
        is_dark = self.theme_manager.current_theme == ThemeType.DARK
        self.dark_button.setChecked(is_dark)
        self.light_button.setChecked(not is_dark)
        
    def _on_theme_selected(self, theme_type: ThemeType):
        """Handle theme selection.
        
        Args:
            theme_type: Selected theme type
        """
        # Apply theme
        self.theme_manager.apply_theme(QApplication.instance(), theme_type)
        
        # Save to config
        theme_str = "light" if theme_type == ThemeType.LIGHT else "dark"
        self.config.set("ui", "theme", theme_str)
        self.config.save()
        
        # Update buttons
        self._update_buttons()
        
        # Call callback if provided
        if self.callback:
            self.callback(theme_type)
            
        # Emit signal
        self.theme_changed.emit(theme_type)
        
    def update_theme(self, theme_type: ThemeType):
        """Update the current theme.
        
        Args:
            theme_type: Theme type to set
        """
        # Apply theme
        self.theme_manager.apply_theme(QApplication.instance(), theme_type)
        
        # Update buttons
        self._update_buttons() 