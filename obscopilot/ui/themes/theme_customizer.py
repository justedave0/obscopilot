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
    QGroupBox, QComboBox, QScrollArea, QWidget, QFormLayout,
    QTabWidget, QLineEdit, QTextEdit, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont

from obscopilot.ui.themes import ThemeType, get_theme_manager, Theme
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
    WINDOW_BACKGROUND = "window_background"
    ACCENT_PRIMARY = "accent_primary"
    ACCENT_SECONDARY = "accent_secondary"
    ACCENT_SUCCESS = "accent_success"
    ACCENT_WARNING = "accent_warning"
    ACCENT_ERROR = "accent_error"
    TAB_BACKGROUND = "tab_background"
    TAB_TEXT = "tab_text"
    TAB_SELECTED_BACKGROUND = "tab_selected_background"
    TAB_SELECTED_TEXT = "tab_selected_text"
    MENU_BACKGROUND = "menu_background"
    MENU_TEXT = "menu_text"
    MENU_SELECTED_BACKGROUND = "menu_selected_background"
    MENU_SELECTED_TEXT = "menu_selected_text"
    STATUS_BACKGROUND = "status_background"
    STATUS_TEXT = "status_text"
    WORKFLOW_ITEM_BACKGROUND = "workflow_item_background"
    WORKFLOW_ITEM_ALT_BACKGROUND = "workflow_item_alt_background"
    
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
            ColorRole.LINK: QPalette.ColorRole.Link,
            ColorRole.WINDOW_BACKGROUND: QPalette.ColorRole.Window,
            ColorRole.ACCENT_PRIMARY: QPalette.ColorRole.Button,
            ColorRole.ACCENT_SECONDARY: QPalette.ColorRole.Button,
            ColorRole.ACCENT_SUCCESS: QPalette.ColorRole.Button,
            ColorRole.ACCENT_WARNING: QPalette.ColorRole.Button,
            ColorRole.ACCENT_ERROR: QPalette.ColorRole.Button,
            ColorRole.TAB_BACKGROUND: QPalette.ColorRole.Window,
            ColorRole.TAB_TEXT: QPalette.ColorRole.WindowText,
            ColorRole.TAB_SELECTED_BACKGROUND: QPalette.ColorRole.Button,
            ColorRole.TAB_SELECTED_TEXT: QPalette.ColorRole.ButtonText,
            ColorRole.MENU_BACKGROUND: QPalette.ColorRole.Window,
            ColorRole.MENU_TEXT: QPalette.ColorRole.WindowText,
            ColorRole.MENU_SELECTED_BACKGROUND: QPalette.ColorRole.Button,
            ColorRole.MENU_SELECTED_TEXT: QPalette.ColorRole.ButtonText,
            ColorRole.STATUS_BACKGROUND: QPalette.ColorRole.Window,
            ColorRole.STATUS_TEXT: QPalette.ColorRole.WindowText,
            ColorRole.WORKFLOW_ITEM_BACKGROUND: QPalette.ColorRole.Window,
            ColorRole.WORKFLOW_ITEM_ALT_BACKGROUND: QPalette.ColorRole.Window
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
            ColorRole.LINK: "Link",
            ColorRole.WINDOW_BACKGROUND: "Window Background",
            ColorRole.ACCENT_PRIMARY: "Accent Primary",
            ColorRole.ACCENT_SECONDARY: "Accent Secondary",
            ColorRole.ACCENT_SUCCESS: "Success",
            ColorRole.ACCENT_WARNING: "Warning",
            ColorRole.ACCENT_ERROR: "Error",
            ColorRole.TAB_BACKGROUND: "Tab Background",
            ColorRole.TAB_TEXT: "Tab Text",
            ColorRole.TAB_SELECTED_BACKGROUND: "Tab Selected Background",
            ColorRole.TAB_SELECTED_TEXT: "Tab Selected Text",
            ColorRole.MENU_BACKGROUND: "Menu Background",
            ColorRole.MENU_TEXT: "Menu Text",
            ColorRole.MENU_SELECTED_BACKGROUND: "Menu Selected Background",
            ColorRole.MENU_SELECTED_TEXT: "Menu Selected Text",
            ColorRole.STATUS_BACKGROUND: "Status Bar Background",
            ColorRole.STATUS_TEXT: "Status Bar Text",
            ColorRole.WORKFLOW_ITEM_BACKGROUND: "Workflow Item Background",
            ColorRole.WORKFLOW_ITEM_ALT_BACKGROUND: "Workflow Item Alt Background"
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


class ColorPickerButton(QPushButton):
    """Custom button for color picking."""
    
    color_changed = pyqtSignal(str, QColor)
    
    def __init__(self, color_role: str, color: str, label: str, parent=None):
        """Initialize color picker button.
        
        Args:
            color_role: Color role identifier
            color: Initial color (hex format)
            label: Label text
            parent: Parent widget
        """
        super().__init__(parent)
        self.color_role = color_role
        self.color = QColor(color)
        self.label = label
        
        self.setAutoFillBackground(True)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.update_color()
        self.clicked.connect(self.pick_color)
    
    def update_color(self):
        """Update button color display."""
        # Set background color
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Button, self.color)
        self.setPalette(palette)
        
        # Set tooltip
        self.setToolTip(f"{self.label}: {self.color.name()}")
    
    def pick_color(self):
        """Show color picker dialog."""
        color = QColorDialog.getColor(
            self.color, 
            self.parent(),
            f"Select Color for {self.label}",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        
        if color.isValid():
            self.color = color
            self.update_color()
            self.color_changed.emit(self.color_role, self.color)


class ThemeEditorDialog(QDialog):
    """Dialog for creating or editing a theme."""
    
    def __init__(self, theme: Optional[Theme] = None, parent=None):
        """Initialize theme editor dialog.
        
        Args:
            theme: Theme to edit, or None for a new theme
            parent: Parent widget
        """
        super().__init__(parent)
        self.theme = theme or Theme(
            name="New Theme",
            type=ThemeType.CUSTOM,
            colors=get_theme_manager().dark_theme.colors.copy(),
            description="Custom theme"
        )
        
        self.color_buttons: Dict[str, ColorPickerButton] = {}
        
        self.setWindowTitle(f"{'Edit' if theme else 'Create'} Theme")
        self.resize(800, 600)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Theme details form
        details_group = QGroupBox("Theme Details")
        details_layout = QFormLayout(details_group)
        
        # Theme name
        self.name_edit = QLineEdit(self.theme.name)
        details_layout.addRow("Name:", self.name_edit)
        
        # Theme description
        self.description_edit = QTextEdit(self.theme.description)
        self.description_edit.setMaximumHeight(80)
        details_layout.addRow("Description:", self.description_edit)
        
        # Add details group to main layout
        layout.addWidget(details_group)
        
        # Create tabbed interface for color categories
        color_tabs = QTabWidget()
        
        # Main colors tab
        main_tab = QWidget()
        main_layout = QFormLayout(main_tab)
        self._add_color_pickers(main_layout, [
            (ColorRole.WINDOW_BACKGROUND, "Window Background"),
            (ColorRole.WINDOW_TEXT, "Window Text"),
            (ColorRole.ACCENT_PRIMARY, "Accent Primary"),
            (ColorRole.ACCENT_SECONDARY, "Accent Secondary"),
            (ColorRole.ACCENT_SUCCESS, "Success"),
            (ColorRole.ACCENT_WARNING, "Warning"),
            (ColorRole.ACCENT_ERROR, "Error")
        ])
        color_tabs.addTab(main_tab, "Main Colors")
        
        # Controls tab
        controls_tab = QWidget()
        controls_layout = QFormLayout(controls_tab)
        self._add_color_pickers(controls_layout, [
            (ColorRole.BUTTON_BACKGROUND, "Button Background"),
            (ColorRole.BUTTON_TEXT, "Button Text"),
            (ColorRole.BUTTON_HOVER, "Button Hover"),
            (ColorRole.BUTTON_PRESSED, "Button Pressed"),
            (ColorRole.INPUT_BACKGROUND, "Input Background"),
            (ColorRole.INPUT_TEXT, "Input Text"),
            (ColorRole.INPUT_BORDER, "Input Border")
        ])
        color_tabs.addTab(controls_tab, "Controls")
        
        # Navigation tab
        nav_tab = QWidget()
        nav_layout = QFormLayout(nav_tab)
        self._add_color_pickers(nav_layout, [
            (ColorRole.TAB_BACKGROUND, "Tab Background"),
            (ColorRole.TAB_TEXT, "Tab Text"),
            (ColorRole.TAB_SELECTED_BACKGROUND, "Tab Selected Background"),
            (ColorRole.TAB_SELECTED_TEXT, "Tab Selected Text"),
            (ColorRole.MENU_BACKGROUND, "Menu Background"),
            (ColorRole.MENU_TEXT, "Menu Text"),
            (ColorRole.MENU_SELECTED_BACKGROUND, "Menu Selected Background"),
            (ColorRole.MENU_SELECTED_TEXT, "Menu Selected Text"),
            (ColorRole.STATUS_BACKGROUND, "Status Bar Background"),
            (ColorRole.STATUS_TEXT, "Status Bar Text")
        ])
        color_tabs.addTab(nav_tab, "Navigation")
        
        # Workflow tab
        workflow_tab = QWidget()
        workflow_layout = QFormLayout(workflow_tab)
        self._add_color_pickers(workflow_layout, [
            (ColorRole.WORKFLOW_ITEM_BACKGROUND, "Workflow Item Background"),
            (ColorRole.WORKFLOW_ITEM_ALT_BACKGROUND, "Workflow Item Alt Background")
        ])
        color_tabs.addTab(workflow_tab, "Workflow")
        
        # Add preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_widget = QWidget()
        self.preview_widget.setAutoFillBackground(True)
        self.preview_widget.setMinimumHeight(120)
        preview_inner_layout = QVBoxLayout(self.preview_widget)
        
        preview_title = QLabel("Theme Preview")
        preview_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        preview_inner_layout.addWidget(preview_title)
        
        preview_text = QLabel("This is how your theme will look in the application.")
        preview_inner_layout.addWidget(preview_text)
        
        preview_button = QPushButton("Sample Button")
        preview_button_layout = QHBoxLayout()
        preview_button_layout.addWidget(preview_button)
        preview_button_layout.addStretch()
        preview_inner_layout.addLayout(preview_button_layout)
        
        preview_layout.addWidget(self.preview_widget)
        
        # Add color tabs
        layout.addWidget(color_tabs)
        
        # Add preview
        layout.addWidget(preview_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add buttons
        layout.addWidget(button_box)
        
        # Update preview initially
        self._update_preview()
    
    def _add_color_pickers(self, layout: QFormLayout, color_roles: List[Tuple[str, str]]):
        """Add color pickers to layout.
        
        Args:
            layout: Layout to add pickers to
            color_roles: List of (role, label) tuples
        """
        for role, label in color_roles:
            # Get current color
            color = self.theme.colors.get(role, "#000000")
            
            # Create color picker button
            button = ColorPickerButton(role, color, label)
            button.color_changed.connect(self._on_color_changed)
            
            # Add to layout with label
            layout.addRow(f"{label}:", button)
            
            # Store button reference
            self.color_buttons[role] = button
    
    def _on_color_changed(self, role: str, color: QColor):
        """Handle color change.
        
        Args:
            role: Color role
            color: New color
        """
        # Update theme colors
        self.theme.colors[role] = color.name()
        
        # Update preview
        self._update_preview()
    
    def _update_preview(self):
        """Update preview widget with current theme colors."""
        # Set preview widget background color
        palette = self.preview_widget.palette()
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(self.theme.colors.get(ColorRole.WINDOW_BACKGROUND, "#2D2D30"))
        )
        
        # Set text color
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(self.theme.colors.get(ColorRole.WINDOW_TEXT, "#E1E1E1"))
        )
        
        self.preview_widget.setPalette(palette)
    
    def get_theme(self) -> Theme:
        """Get the edited theme.
        
        Returns:
            Updated theme
        """
        # Update theme with form values
        self.theme.name = self.name_edit.text()
        self.theme.description = self.description_edit.toPlainText()
        
        return self.theme


class ThemeCustomizerWidget(QWidget):
    """Widget for customizing themes."""
    
    theme_changed = pyqtSignal(ThemeType, str)
    
    def __init__(self, parent=None):
        """Initialize theme customizer widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        
        self._init_ui()
        self._load_themes()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Theme selection
        selection_layout = QHBoxLayout()
        
        selection_layout.addWidget(QLabel("Current Theme:"))
        self.theme_combo = QComboBox()
        selection_layout.addWidget(self.theme_combo)
        
        layout.addLayout(selection_layout)
        
        # Custom themes section
        custom_group = QGroupBox("Custom Themes")
        custom_layout = QVBoxLayout(custom_group)
        
        # Themes list
        self.themes_list = QScrollArea()
        self.themes_list.setWidgetResizable(True)
        self.themes_list.setFrameShape(QFrame.Shape.NoFrame)
        self.themes_list_widget = QWidget()
        self.themes_list_layout = QVBoxLayout(self.themes_list_widget)
        self.themes_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.themes_list.setWidget(self.themes_list_widget)
        
        custom_layout.addWidget(self.themes_list)
        
        # Custom theme buttons
        buttons_layout = QHBoxLayout()
        self.create_button = QPushButton("Create Theme")
        self.create_button.clicked.connect(self._on_create_theme)
        buttons_layout.addWidget(self.create_button)
        
        self.import_button = QPushButton("Import Theme")
        self.import_button.clicked.connect(self._on_import_theme)
        buttons_layout.addWidget(self.import_button)
        
        buttons_layout.addStretch()
        
        custom_layout.addLayout(buttons_layout)
        
        layout.addWidget(custom_group)
        
        # Connect signals
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selection_changed)
    
    def _load_themes(self):
        """Load available themes."""
        # Clear current items
        self.theme_combo.clear()
        
        # Add built-in themes
        self.theme_combo.addItem("Dark Theme", (ThemeType.DARK, None))
        self.theme_combo.addItem("Light Theme", (ThemeType.LIGHT, None))
        
        # Add custom themes
        for theme_name in self.theme_manager.custom_themes:
            self.theme_combo.addItem(f"{theme_name} (Custom)", (ThemeType.CUSTOM, theme_name))
            
        # Set current theme
        current_theme = self.theme_manager.current_theme
        if current_theme == ThemeType.DARK:
            self.theme_combo.setCurrentIndex(0)
        elif current_theme == ThemeType.LIGHT:
            self.theme_combo.setCurrentIndex(1)
        else:
            # Find custom theme
            for i in range(2, self.theme_combo.count()):
                theme_type, theme_name = self.theme_combo.itemData(i)
                if theme_type == ThemeType.CUSTOM and theme_name == current_theme:
                    self.theme_combo.setCurrentIndex(i)
                    break
        
        # Update custom themes list
        self._refresh_custom_themes_list()
    
    def _refresh_custom_themes_list(self):
        """Refresh the custom themes list."""
        # Clear current items
        while self.themes_list_layout.count() > 0:
            item = self.themes_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add custom themes
        for theme_name, theme in self.theme_manager.custom_themes.items():
            theme_widget = self._create_theme_item_widget(theme)
            self.themes_list_layout.addWidget(theme_widget)
        
        # Add empty state message if no custom themes
        if not self.theme_manager.custom_themes:
            empty_label = QLabel("No custom themes available. Create one to get started!")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.themes_list_layout.addWidget(empty_label)
    
    def _create_theme_item_widget(self, theme: Theme) -> QWidget:
        """Create a widget for a theme item.
        
        Args:
            theme: Theme to create widget for
            
        Returns:
            Widget representing the theme
        """
        widget = QFrame()
        widget.setFrameShape(QFrame.Shape.StyledPanel)
        widget.setAutoFillBackground(True)
        
        # Set theme colors for widget
        palette = widget.palette()
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(theme.colors.get(ColorRole.WINDOW_BACKGROUND, "#2D2D30"))
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(theme.colors.get(ColorRole.WINDOW_TEXT, "#E1E1E1"))
        )
        widget.setPalette(palette)
        
        # Create layout
        layout = QHBoxLayout(widget)
        
        # Theme info
        info_layout = QVBoxLayout()
        
        # Theme name
        name_label = QLabel(theme.name)
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(name_label)
        
        # Theme description
        desc_label = QLabel(theme.description or "No description")
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, 1)
        
        # Theme actions
        actions_layout = QVBoxLayout()
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._on_apply_theme(theme))
        actions_layout.addWidget(apply_button)
        
        # Edit/Delete buttons
        edit_delete_layout = QHBoxLayout()
        
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: self._on_edit_theme(theme))
        edit_delete_layout.addWidget(edit_button)
        
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self._on_delete_theme(theme))
        edit_delete_layout.addWidget(delete_button)
        
        actions_layout.addLayout(edit_delete_layout)
        
        layout.addLayout(actions_layout)
        
        return widget
    
    def _on_theme_selection_changed(self, index: int):
        """Handle theme selection change.
        
        Args:
            index: Selected index
        """
        if index < 0:
            return
        
        # Get theme data
        theme_type, theme_name = self.theme_combo.itemData(index)
        
        # Emit signal
        self.theme_changed.emit(theme_type, theme_name)
    
    def _on_create_theme(self):
        """Handle create theme button click."""
        dialog = ThemeEditorDialog(parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the theme
            theme = dialog.get_theme()
            
            # Add to theme manager
            if self.theme_manager.add_custom_theme(theme):
                # Reload themes
                self._load_themes()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Theme Created",
                    f"Theme '{theme.name}' has been created successfully."
                )
            else:
                # Show error message
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to create theme '{theme.name}'."
                )
    
    def _on_edit_theme(self, theme: Theme):
        """Handle edit theme button click.
        
        Args:
            theme: Theme to edit
        """
        # Create a copy of the theme for editing
        theme_copy = Theme(
            name=theme.name,
            type=theme.type,
            colors=theme.colors.copy(),
            description=theme.description
        )
        
        dialog = ThemeEditorDialog(theme_copy, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the edited theme
            edited_theme = dialog.get_theme()
            
            # Add/update theme in manager
            if self.theme_manager.add_custom_theme(edited_theme):
                # Reload themes
                self._load_themes()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Theme Updated",
                    f"Theme '{edited_theme.name}' has been updated successfully."
                )
            else:
                # Show error message
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to update theme '{edited_theme.name}'."
                )
    
    def _on_delete_theme(self, theme: Theme):
        """Handle delete theme button click.
        
        Args:
            theme: Theme to delete
        """
        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Delete Theme",
            f"Are you sure you want to delete the theme '{theme.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Delete theme
            if self.theme_manager.delete_custom_theme(theme.name):
                # Reload themes
                self._load_themes()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Theme Deleted",
                    f"Theme '{theme.name}' has been deleted successfully."
                )
            else:
                # Show error message
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to delete theme '{theme.name}'."
                )
    
    def _on_apply_theme(self, theme: Theme):
        """Handle apply theme button click.
        
        Args:
            theme: Theme to apply
        """
        # Emit theme changed signal
        self.theme_changed.emit(ThemeType.CUSTOM, theme.name)
        
        # Update the theme selector to match
        for i in range(self.theme_combo.count()):
            theme_type, theme_name = self.theme_combo.itemData(i)
            if theme_type == ThemeType.CUSTOM and theme_name == theme.name:
                self.theme_combo.setCurrentIndex(i)
                break
    
    def _on_import_theme(self):
        """Handle import theme button click."""
        # TODO: Implement theme import functionality
        QMessageBox.information(
            self,
            "Not Implemented",
            "Theme import functionality is not yet implemented."
        )


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