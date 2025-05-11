"""
Theme management for OBSCopilot.

This module provides theme management functionality for the application.
"""

import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Theme types."""
    
    DARK = "dark"
    LIGHT = "light"
    CUSTOM = "custom"


class ColorRole:
    """Color roles for theme customization."""
    
    # Main areas
    WINDOW_BACKGROUND = "window_background"
    WINDOW_TEXT = "window_text"
    
    # Controls
    BUTTON_BACKGROUND = "button_background"
    BUTTON_TEXT = "button_text"
    BUTTON_HOVER = "button_hover"
    BUTTON_PRESSED = "button_pressed"
    
    # Tabs
    TAB_BACKGROUND = "tab_background"
    TAB_TEXT = "tab_text"
    TAB_SELECTED_BACKGROUND = "tab_selected_background"
    TAB_SELECTED_TEXT = "tab_selected_text"
    
    # Menus
    MENU_BACKGROUND = "menu_background"
    MENU_TEXT = "menu_text"
    MENU_SELECTED_BACKGROUND = "menu_selected_background"
    MENU_SELECTED_TEXT = "menu_selected_text"
    
    # Status bar
    STATUS_BACKGROUND = "status_background"
    STATUS_TEXT = "status_text"
    
    # Accents
    ACCENT_PRIMARY = "accent_primary"
    ACCENT_SECONDARY = "accent_secondary"
    ACCENT_SUCCESS = "accent_success"
    ACCENT_WARNING = "accent_warning"
    ACCENT_ERROR = "accent_error"
    
    # Workflow items
    WORKFLOW_ITEM_BACKGROUND = "workflow_item_background"
    WORKFLOW_ITEM_ALT_BACKGROUND = "workflow_item_alt_background"
    
    # Forms
    INPUT_BACKGROUND = "input_background"
    INPUT_TEXT = "input_text"
    INPUT_BORDER = "input_border"


class Theme:
    """Theme definition."""
    
    def __init__(
        self, 
        name: str, 
        type: ThemeType = ThemeType.CUSTOM,
        colors: Optional[Dict[str, str]] = None,
        description: str = ""
    ):
        """Initialize theme.
        
        Args:
            name: Theme name
            type: Theme type
            colors: Color definitions
            description: Theme description
        """
        self.name = name
        self.type = type
        self.colors = colors or {}
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary.
        
        Returns:
            Theme as dictionary
        """
        return {
            "name": self.name,
            "type": self.type.value,
            "colors": self.colors,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """Create theme from dictionary.
        
        Args:
            data: Theme data dictionary
            
        Returns:
            Theme instance
        """
        return cls(
            name=data.get("name", "Custom Theme"),
            type=ThemeType(data.get("type", "custom")),
            colors=data.get("colors", {}),
            description=data.get("description", "")
        )


class ThemeManager:
    """Manager for application themes."""
    
    def __init__(self):
        """Initialize theme manager."""
        self.current_theme = ThemeType.DARK
        self.custom_themes: Dict[str, Theme] = {}
        self._load_custom_themes()
        
        # Create built-in themes
        self.dark_theme = self._create_dark_theme()
        self.light_theme = self._create_light_theme()
    
    def get_themes_dir(self) -> Path:
        """Get themes directory.
        
        Returns:
            Path to themes directory
        """
        # Get application data directory
        settings = QSettings("OBSCopilot", "OBSCopilot")
        app_data_dir = Path(settings.fileName()).parent
        
        # Create themes directory if it doesn't exist
        themes_dir = app_data_dir / "themes"
        themes_dir.mkdir(parents=True, exist_ok=True)
        
        return themes_dir
    
    def _load_custom_themes(self) -> None:
        """Load custom themes from theme directory."""
        themes_dir = self.get_themes_dir()
        
        try:
            for file_path in themes_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        theme_data = json.load(f)
                    
                    theme = Theme.from_dict(theme_data)
                    self.custom_themes[theme.name] = theme
                    logger.debug(f"Loaded custom theme: {theme.name}")
                except Exception as e:
                    logger.error(f"Error loading theme {file_path.name}: {e}")
        except Exception as e:
            logger.error(f"Error loading custom themes: {e}")
    
    def _create_dark_theme(self) -> Theme:
        """Create dark theme.
        
        Returns:
            Dark theme
        """
        return Theme(
            name="Dark",
            type=ThemeType.DARK,
            colors={
                ColorRole.WINDOW_BACKGROUND: "#2D2D30",
                ColorRole.WINDOW_TEXT: "#E1E1E1",
                
                ColorRole.BUTTON_BACKGROUND: "#0E639C",
                ColorRole.BUTTON_TEXT: "#FFFFFF",
                ColorRole.BUTTON_HOVER: "#1177BB",
                ColorRole.BUTTON_PRESSED: "#10558C",
                
                ColorRole.TAB_BACKGROUND: "#2D2D2D",
                ColorRole.TAB_TEXT: "#E1E1E1",
                ColorRole.TAB_SELECTED_BACKGROUND: "#007ACC",
                ColorRole.TAB_SELECTED_TEXT: "#FFFFFF",
                
                ColorRole.MENU_BACKGROUND: "#2D2D30",
                ColorRole.MENU_TEXT: "#E1E1E1",
                ColorRole.MENU_SELECTED_BACKGROUND: "#3E3E42",
                ColorRole.MENU_SELECTED_TEXT: "#FFFFFF",
                
                ColorRole.STATUS_BACKGROUND: "#007ACC",
                ColorRole.STATUS_TEXT: "#FFFFFF",
                
                ColorRole.ACCENT_PRIMARY: "#007ACC",
                ColorRole.ACCENT_SECONDARY: "#0E639C",
                ColorRole.ACCENT_SUCCESS: "#4CAF50",
                ColorRole.ACCENT_WARNING: "#FF9800",
                ColorRole.ACCENT_ERROR: "#F44336",
                
                ColorRole.WORKFLOW_ITEM_BACKGROUND: "#2A2A2A",
                ColorRole.WORKFLOW_ITEM_ALT_BACKGROUND: "#323232",
                
                ColorRole.INPUT_BACKGROUND: "#1E1E1E",
                ColorRole.INPUT_TEXT: "#E1E1E1",
                ColorRole.INPUT_BORDER: "#3E3E42"
            },
            description="Dark theme with blue accents"
        )
    
    def _create_light_theme(self) -> Theme:
        """Create light theme.
        
        Returns:
            Light theme
        """
        return Theme(
            name="Light",
            type=ThemeType.LIGHT,
            colors={
                ColorRole.WINDOW_BACKGROUND: "#F5F5F5",
                ColorRole.WINDOW_TEXT: "#333333",
                
                ColorRole.BUTTON_BACKGROUND: "#0078D7",
                ColorRole.BUTTON_TEXT: "#FFFFFF",
                ColorRole.BUTTON_HOVER: "#106EBE",
                ColorRole.BUTTON_PRESSED: "#005A9E",
                
                ColorRole.TAB_BACKGROUND: "#E1E1E1",
                ColorRole.TAB_TEXT: "#333333",
                ColorRole.TAB_SELECTED_BACKGROUND: "#007ACC",
                ColorRole.TAB_SELECTED_TEXT: "#FFFFFF",
                
                ColorRole.MENU_BACKGROUND: "#FFFFFF",
                ColorRole.MENU_TEXT: "#333333",
                ColorRole.MENU_SELECTED_BACKGROUND: "#DADADA",
                ColorRole.MENU_SELECTED_TEXT: "#333333",
                
                ColorRole.STATUS_BACKGROUND: "#0078D7",
                ColorRole.STATUS_TEXT: "#FFFFFF",
                
                ColorRole.ACCENT_PRIMARY: "#0078D7",
                ColorRole.ACCENT_SECONDARY: "#106EBE",
                ColorRole.ACCENT_SUCCESS: "#107C10",
                ColorRole.ACCENT_WARNING: "#FF8C00",
                ColorRole.ACCENT_ERROR: "#E81123",
                
                ColorRole.WORKFLOW_ITEM_BACKGROUND: "#F8F8F8",
                ColorRole.WORKFLOW_ITEM_ALT_BACKGROUND: "#F0F0F0",
                
                ColorRole.INPUT_BACKGROUND: "#FFFFFF",
                ColorRole.INPUT_TEXT: "#333333",
                ColorRole.INPUT_BORDER: "#CCCCCC"
            },
            description="Light theme with blue accents"
        )
    
    def get_theme(self, theme_type: ThemeType, theme_name: Optional[str] = None) -> Theme:
        """Get theme by type and name.
        
        Args:
            theme_type: Theme type
            theme_name: Theme name for custom themes
            
        Returns:
            Theme instance
        """
        if theme_type == ThemeType.DARK:
            return self.dark_theme
        elif theme_type == ThemeType.LIGHT:
            return self.light_theme
        elif theme_type == ThemeType.CUSTOM and theme_name:
            return self.custom_themes.get(theme_name, self.dark_theme)
        else:
            return self.dark_theme
    
    def get_theme_names(self) -> List[str]:
        """Get list of available theme names.
        
        Returns:
            List of theme names
        """
        return ["Dark", "Light"] + list(self.custom_themes.keys())
    
    def add_custom_theme(self, theme: Theme) -> bool:
        """Add or update custom theme.
        
        Args:
            theme: Theme to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to internal dictionary
            self.custom_themes[theme.name] = theme
            
            # Save to file
            themes_dir = self.get_themes_dir()
            file_path = themes_dir / f"{theme.name.lower().replace(' ', '_')}.json"
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(theme.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error adding custom theme: {e}")
            return False
    
    def delete_custom_theme(self, theme_name: str) -> bool:
        """Delete custom theme.
        
        Args:
            theme_name: Name of theme to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if theme exists
            if theme_name not in self.custom_themes:
                logger.error(f"Theme not found: {theme_name}")
                return False
            
            # Remove from internal dictionary
            del self.custom_themes[theme_name]
            
            # Delete file
            themes_dir = self.get_themes_dir()
            file_path = themes_dir / f"{theme_name.lower().replace(' ', '_')}.json"
            if file_path.exists():
                os.remove(file_path)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting custom theme: {e}")
            return False
    
    def apply_theme(self, app: QApplication, theme_type: ThemeType, theme_name: Optional[str] = None) -> None:
        """Apply theme to application.
        
        Args:
            app: QApplication instance
            theme_type: Theme type
            theme_name: Theme name for custom themes
        """
        theme = self.get_theme(theme_type, theme_name)
        self.current_theme = theme_type
        
        # Create stylesheet
        stylesheet = self._create_stylesheet(theme)
        
        # Apply stylesheet
        app.setStyleSheet(stylesheet)
    
    def _create_stylesheet(self, theme: Theme) -> str:
        """Create stylesheet for theme.
        
        Args:
            theme: Theme to create stylesheet for
            
        Returns:
            CSS stylesheet
        """
        return f"""
        QMainWindow, QWidget {{
            background-color: {theme.colors.get(ColorRole.WINDOW_BACKGROUND, "#2D2D30")};
            color: {theme.colors.get(ColorRole.WINDOW_TEXT, "#E1E1E1")};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {theme.colors.get(ColorRole.INPUT_BORDER, "#3E3E42")};
            background-color: {theme.colors.get(ColorRole.WINDOW_BACKGROUND, "#2D2D30")};
        }}
        
        QTabBar::tab {{
            background-color: {theme.colors.get(ColorRole.TAB_BACKGROUND, "#2D2D2D")};
            color: {theme.colors.get(ColorRole.TAB_TEXT, "#E1E1E1")};
            padding: 8px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {theme.colors.get(ColorRole.TAB_SELECTED_BACKGROUND, "#007ACC")};
            color: {theme.colors.get(ColorRole.TAB_SELECTED_TEXT, "#FFFFFF")};
        }}
        
        QPushButton {{
            background-color: {theme.colors.get(ColorRole.BUTTON_BACKGROUND, "#0E639C")};
            color: {theme.colors.get(ColorRole.BUTTON_TEXT, "#FFFFFF")};
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }}
        
        QPushButton:hover {{
            background-color: {theme.colors.get(ColorRole.BUTTON_HOVER, "#1177BB")};
        }}
        
        QPushButton:pressed {{
            background-color: {theme.colors.get(ColorRole.BUTTON_PRESSED, "#10558C")};
        }}
        
        QMenuBar {{
            background-color: {theme.colors.get(ColorRole.MENU_BACKGROUND, "#2D2D30")};
            color: {theme.colors.get(ColorRole.MENU_TEXT, "#E1E1E1")};
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme.colors.get(ColorRole.MENU_SELECTED_BACKGROUND, "#3E3E42")};
            color: {theme.colors.get(ColorRole.MENU_SELECTED_TEXT, "#FFFFFF")};
        }}
        
        QMenu {{
            background-color: {theme.colors.get(ColorRole.MENU_BACKGROUND, "#2D2D30")};
            color: {theme.colors.get(ColorRole.MENU_TEXT, "#E1E1E1")};
            border: 1px solid {theme.colors.get(ColorRole.INPUT_BORDER, "#3E3E42")};
        }}
        
        QMenu::item:selected {{
            background-color: {theme.colors.get(ColorRole.MENU_SELECTED_BACKGROUND, "#3E3E42")};
            color: {theme.colors.get(ColorRole.MENU_SELECTED_TEXT, "#FFFFFF")};
        }}
        
        QToolBar {{
            background-color: {theme.colors.get(ColorRole.WINDOW_BACKGROUND, "#2D2D30")};
            border-bottom: 1px solid {theme.colors.get(ColorRole.INPUT_BORDER, "#3E3E42")};
        }}
        
        QStatusBar {{
            background-color: {theme.colors.get(ColorRole.STATUS_BACKGROUND, "#007ACC")};
            color: {theme.colors.get(ColorRole.STATUS_TEXT, "#FFFFFF")};
        }}
        
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {theme.colors.get(ColorRole.INPUT_BACKGROUND, "#1E1E1E")};
            color: {theme.colors.get(ColorRole.INPUT_TEXT, "#E1E1E1")};
            border: 1px solid {theme.colors.get(ColorRole.INPUT_BORDER, "#3E3E42")};
            border-radius: 4px;
            padding: 4px;
        }}
        
        QCheckBox, QRadioButton {{
            color: {theme.colors.get(ColorRole.WINDOW_TEXT, "#E1E1E1")};
        }}
        
        QComboBox::drop-down {{
            border: none;
            background-color: {theme.colors.get(ColorRole.BUTTON_BACKGROUND, "#0E639C")};
        }}
        
        QLabel {{
            color: {theme.colors.get(ColorRole.WINDOW_TEXT, "#E1E1E1")};
        }}
        
        QScrollBar:vertical {{
            border: none;
            background-color: {theme.colors.get(ColorRole.WINDOW_BACKGROUND, "#2D2D30")};
            width: 14px;
            margin: 14px 0 14px 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme.colors.get(ColorRole.MENU_SELECTED_BACKGROUND, "#3E3E42")};
            min-height: 30px;
            border-radius: 7px;
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
            height: 14px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }}
        
        QGroupBox {{
            border: 1px solid {theme.colors.get(ColorRole.INPUT_BORDER, "#3E3E42")};
            border-radius: 4px;
            margin-top: 15px;
            padding-top: 10px;
        }}
        
        QGroupBox::title {{
            color: {theme.colors.get(ColorRole.WINDOW_TEXT, "#E1E1E1")};
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            background-color: {theme.colors.get(ColorRole.WINDOW_BACKGROUND, "#2D2D30")};
        }}
        """
    
    def toggle_theme(self, app: QApplication) -> None:
        """Toggle between dark and light themes.
        
        Args:
            app: QApplication instance
        """
        if self.current_theme == ThemeType.DARK:
            self.apply_theme(app, ThemeType.LIGHT)
        else:
            self.apply_theme(app, ThemeType.DARK)


# Global theme manager instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance.
    
    Returns:
        Theme manager instance
    """
    global _theme_manager
    
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    
    return _theme_manager 