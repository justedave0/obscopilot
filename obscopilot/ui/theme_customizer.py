"""
Theme Customizer for OBSCopilot.

This module provides a dialog for customizing application theme colors.
"""

import logging
import json
from typing import Dict, Any, Optional
from enum import Enum

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QColorDialog, QGridLayout, QFrame, QDialogButtonBox,
    QGroupBox, QComboBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont

from obscopilot.ui.themes import ThemeType, get_theme_manager
from obscopilot.core.config import Config

logger = logging.getLogger(__name__)


class ColorRole(Enum):
    """Color roles for theme customization."""
    
    WINDOW = "window"
    WINDOW_TEXT = "window_text"
    BASE = "base"
    ALTERNATE_BASE = "alternate_base"
    TEXT = "text"
    BUTTON = "button"
    BUTTON_TEXT = "button_text"
    HIGHLIGHT = "highlight"
    HIGHLIGHTED_TEXT = "highlighted_text"
    LINK = "link"
    
    @staticmethod
    def to_palette_role(role: 'ColorRole') -> QPalette.ColorRole:
        """Convert ColorRole to QPalette.ColorRole.
        
        Args:
            role: ColorRole to convert
            
        Returns:
            Corresponding QPalette.ColorRole
        """
        mapping = {
            ColorRole.WINDOW: QPalette.ColorRole.Window,
            ColorRole.WINDOW_TEXT: QPalette.ColorRole.WindowText,
            ColorRole.BASE: QPalette.ColorRole.Base,
            ColorRole.ALTERNATE_BASE: QPalette.ColorRole.AlternateBase,
            ColorRole.TEXT: QPalette.ColorRole.Text,
            ColorRole.BUTTON: QPalette.ColorRole.Button,
            ColorRole.BUTTON_TEXT: QPalette.ColorRole.ButtonText,
            ColorRole.HIGHLIGHT: QPalette.ColorRole.Highlight,
            ColorRole.HIGHLIGHTED_TEXT: QPalette.ColorRole.HighlightedText,
            ColorRole.LINK: QPalette.ColorRole.Link
        }
        return mapping.get(role, QPalette.ColorRole.Window)
    
    @staticmethod
    def get_display_name(role: 'ColorRole') -> str:
        """Get display name for a color role.
        
        Args:
            role: ColorRole to get display name for
            
        Returns:
            Display name string
        """
        mapping = {
            ColorRole.WINDOW: "Window Background",
            ColorRole.WINDOW_TEXT: "Window Text",
            ColorRole.BASE: "Base Background",
            ColorRole.ALTERNATE_BASE: "Alternate Background",
            ColorRole.TEXT: "Text",
            ColorRole.BUTTON: "Button Background",
            ColorRole.BUTTON_TEXT: "Button Text",
            ColorRole.HIGHLIGHT: "Highlight",
            ColorRole.HIGHLIGHTED_TEXT: "Highlighted Text",
            ColorRole.LINK: "Link"
        }
        return mapping.get(role, role.value.replace('_', ' ').title())


class ColorSwatch(QFrame):
    """Color swatch widget."""
    
    clicked = pyqtSignal()
    
    def __init__(self, color: QColor, parent=None):
        """Initialize the color swatch.
        
        Args:
            color: Initial color
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.color = color
        
        # Set up appearance
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.setMinimumSize(40, 20)
        self.setMaximumSize(120, 20)
        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        )
        
        # Set color
        self.update_color(color)
        
    def update_color(self, color: QColor):
        """Update the swatch color.
        
        Args:
            color: New color
        """
        self.color = color
        
        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        self.setPalette(palette)
        
    def mousePressEvent(self, event):
        """Handle mouse press events.
        
        Args:
            event: Mouse event
        """
        self.clicked.emit()
        super().mousePressEvent(event)


class ThemeCustomizer(QDialog):
    """Dialog for customizing theme colors."""
    
    theme_updated = pyqtSignal()
    
    def __init__(self, config: Config, parent=None):
        """Initialize the theme customizer.
        
        Args:
            config: Application configuration
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config = config
        self.theme_manager = get_theme_manager()
        
        # Store color values
        self.colors = {
            ThemeType.DARK: {},
            ThemeType.LIGHT: {}
        }
        
        # Load custom colors from config
        self._load_colors()
        
        # Initialize UI
        self.setWindowTitle("Theme Customizer")
        self.setMinimumSize(500, 400)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Theme selector
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme", ThemeType.DARK)
        self.theme_combo.addItem("Light Theme", ThemeType.LIGHT)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        
        # Reset button
        reset_button = QPushButton("Reset to Default")
        reset_button.clicked.connect(self._reset_theme)
        theme_layout.addWidget(reset_button)
        
        layout.addLayout(theme_layout)
        
        # Color editor scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        
        # Basic colors group
        basic_group = QGroupBox("Basic Colors")
        basic_grid = QGridLayout(basic_group)
        
        # Add color swatches for each role
        self.swatches = {}
        row = 0
        for role in ColorRole:
            # Label
            role_label = QLabel(ColorRole.get_display_name(role))
            basic_grid.addWidget(role_label, row, 0)
            
            # Color swatch
            current_theme = self.theme_combo.currentData()
            color = self._get_color(current_theme, role)
            swatch = ColorSwatch(color)
            swatch.clicked.connect(lambda r=role: self._edit_color(r))
            basic_grid.addWidget(swatch, row, 1)
            
            # Store reference
            self.swatches[role] = swatch
            
            row += 1
            
        scroll_layout.addWidget(basic_group)
        
        # Advanced styling
        advanced_group = QGroupBox("Advanced Styling")
        advanced_grid = QVBoxLayout(advanced_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Sample text
        sample_text = QLabel("Sample text")
        preview_layout.addWidget(sample_text)
        
        # Sample button
        sample_button = QPushButton("Sample Button")
        preview_layout.addWidget(sample_button)
        
        advanced_grid.addWidget(preview_group)
        
        scroll_layout.addWidget(advanced_group)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_container)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Set initial theme
        current_theme = self.theme_manager.current_theme
        index = 0 if current_theme == ThemeType.DARK else 1
        self.theme_combo.setCurrentIndex(index)
        
    def _load_colors(self):
        """Load custom colors from config."""
        # Get color values from config
        dark_colors_str = self.config.get("theme", "dark_colors", "{}")
        light_colors_str = self.config.get("theme", "light_colors", "{}")
        
        try:
            self.colors[ThemeType.DARK] = json.loads(dark_colors_str)
        except Exception as e:
            logger.error(f"Error loading dark theme colors: {e}")
            self.colors[ThemeType.DARK] = {}
            
        try:
            self.colors[ThemeType.LIGHT] = json.loads(light_colors_str)
        except Exception as e:
            logger.error(f"Error loading light theme colors: {e}")
            self.colors[ThemeType.LIGHT] = {}
            
    def _save_colors(self):
        """Save custom colors to config."""
        dark_colors_str = json.dumps(self.colors[ThemeType.DARK])
        light_colors_str = json.dumps(self.colors[ThemeType.LIGHT])
        
        self.config.set("theme", "dark_colors", dark_colors_str)
        self.config.set("theme", "light_colors", light_colors_str)
        self.config.save()
        
    def _get_color(self, theme_type: ThemeType, role: ColorRole) -> QColor:
        """Get color for a specific role and theme.
        
        Args:
            theme_type: Theme type
            role: Color role
            
        Returns:
            Color value
        """
        # Check if custom color exists
        theme_colors = self.colors[theme_type]
        if role.value in theme_colors:
            color_str = theme_colors[role.value]
            return QColor(color_str)
            
        # Otherwise get from default palette
        palette = self.theme_manager._themes[theme_type]
        palette_role = ColorRole.to_palette_role(role)
        return palette.color(palette_role)
        
    def _set_color(self, theme_type: ThemeType, role: ColorRole, color: QColor):
        """Set color for a specific role and theme.
        
        Args:
            theme_type: Theme type
            role: Color role
            color: New color
        """
        # Store color
        self.colors[theme_type][role.value] = color.name()
        
        # Update swatch if this is the current theme
        current_theme = self.theme_combo.currentData()
        if current_theme == theme_type and role in self.swatches:
            self.swatches[role].update_color(color)
            
    def _on_theme_changed(self, index: int):
        """Handle theme selection changes.
        
        Args:
            index: Selected index
        """
        # Get selected theme
        theme_type = self.theme_combo.currentData()
        
        # Update swatches
        for role in ColorRole:
            if role in self.swatches:
                color = self._get_color(theme_type, role)
                self.swatches[role].update_color(color)
                
    def _edit_color(self, role: ColorRole):
        """Show color picker for a role.
        
        Args:
            role: Color role to edit
        """
        # Get current color
        theme_type = self.theme_combo.currentData()
        current_color = self._get_color(theme_type, role)
        
        # Show color dialog
        color = QColorDialog.getColor(
            current_color, 
            self,
            f"Select color for {ColorRole.get_display_name(role)}"
        )
        
        # Update if valid
        if color.isValid():
            self._set_color(theme_type, role, color)
            
    def _reset_theme(self):
        """Reset current theme to default colors."""
        # Get current theme
        theme_type = self.theme_combo.currentData()
        
        # Clear custom colors
        self.colors[theme_type] = {}
        
        # Update swatches
        self._on_theme_changed(self.theme_combo.currentIndex())
        
    def _apply_custom_colors(self, theme_type: ThemeType, palette: QPalette) -> QPalette:
        """Apply custom colors to a palette.
        
        Args:
            theme_type: Theme type
            palette: Base palette
            
        Returns:
            Updated palette
        """
        theme_colors = self.colors[theme_type]
        
        # Apply custom colors
        for role_value, color_str in theme_colors.items():
            try:
                role = ColorRole(role_value)
                palette_role = ColorRole.to_palette_role(role)
                palette.setColor(palette_role, QColor(color_str))
            except Exception as e:
                logger.error(f"Error applying custom color {role_value}: {e}")
                
        return palette
        
    def accept(self):
        """Handle dialog acceptance."""
        # Save colors
        self._save_colors()
        
        # Apply to theme manager
        self.theme_manager._create_palette_func = self._apply_custom_colors
        
        # Apply current theme
        current_theme = self.theme_manager.current_theme
        self.theme_manager.apply_theme(QApplication.instance(), current_theme)
        
        # Emit signal
        self.theme_updated.emit()
        
        super().accept() 