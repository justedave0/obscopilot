"""
Dashboard Customization for OBSCopilot.

This module provides a UI for customizing the dashboard layout and widgets.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, 
    QGroupBox, QFormLayout, QCheckBox, QComboBox, QSpinBox,
    QFrame, QGridLayout, QMenu, QToolButton, QSizePolicy,
    QScrollArea
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QIcon, QDrag, QPixmap, QPainter, QColor

from obscopilot.core.config import Config

logger = logging.getLogger(__name__)


class WidgetType(Enum):
    """Dashboard widget types."""
    
    VIEWER_COUNT = "viewer_count"
    FOLLOWERS = "followers"
    SUBSCRIBERS = "subscribers"
    BITS = "bits"
    UPTIME = "uptime"
    RECENT_EVENTS = "recent_events"
    STREAM_HEALTH = "stream_health"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    FPS = "fps"
    DROPPED_FRAMES = "dropped_frames"
    MESSAGE_COUNT = "message_count"
    CHAT_ACTIVITY = "chat_activity"
    TOP_CHATTERS = "top_chatters"
    CUSTOM_COUNTER = "custom_counter"
    TIMER = "timer"
    STOPWATCH = "stopwatch"
    GOAL_PROGRESS = "goal_progress"


class WidgetDefinition:
    """Definition of a dashboard widget."""
    
    def __init__(
        self, 
        widget_id: str,
        widget_type: WidgetType,
        title: str,
        settings: Dict[str, Any] = None,
        position: Dict[str, int] = None
    ):
        """Initialize the widget definition.
        
        Args:
            widget_id: Unique widget ID
            widget_type: Widget type
            title: Widget title
            settings: Widget settings
            position: Widget position
        """
        self.widget_id = widget_id
        self.widget_type = widget_type
        self.title = title
        self.settings = settings or {}
        self.position = position or {"row": 0, "col": 0, "row_span": 1, "col_span": 1}
        
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WidgetDefinition':
        """Create widget definition from dictionary.
        
        Args:
            data: Widget data dictionary
            
        Returns:
            Widget definition
        """
        return WidgetDefinition(
            widget_id=data.get("widget_id", ""),
            widget_type=WidgetType(data.get("widget_type", "")),
            title=data.get("title", ""),
            settings=data.get("settings", {}),
            position=data.get("position", {})
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title": self.title,
            "settings": self.settings,
            "position": self.position
        }


class DashboardLayout:
    """Dashboard layout definition."""
    
    def __init__(
        self,
        name: str,
        widgets: List[WidgetDefinition] = None
    ):
        """Initialize the dashboard layout.
        
        Args:
            name: Layout name
            widgets: List of widget definitions
        """
        self.name = name
        self.widgets = widgets or []
        
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DashboardLayout':
        """Create dashboard layout from dictionary.
        
        Args:
            data: Layout data dictionary
            
        Returns:
            Dashboard layout
        """
        widgets = [
            WidgetDefinition.from_dict(widget_data) 
            for widget_data in data.get("widgets", [])
        ]
        
        return DashboardLayout(
            name=data.get("name", ""),
            widgets=widgets
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "widgets": [widget.to_dict() for widget in self.widgets]
        }


class DashboardManager:
    """Manages dashboard layouts and configuration."""
    
    def __init__(self, config: Config):
        """Initialize the dashboard manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.layouts: Dict[str, DashboardLayout] = {}
        self.active_layout = ""
        
        # Load layouts from config
        self._load_layouts()
        
    def _load_layouts(self):
        """Load dashboard layouts from config."""
        layouts_str = self.config.get("dashboard", "layouts", "{}")
        
        try:
            layouts_data = json.loads(layouts_str)
            
            for layout_name, layout_data in layouts_data.items():
                self.layouts[layout_name] = DashboardLayout.from_dict(layout_data)
                
            # Set active layout
            self.active_layout = self.config.get("dashboard", "active_layout", "")
            
            # If no active layout, set first one
            if not self.active_layout and self.layouts:
                self.active_layout = next(iter(self.layouts))
            
            # If no layouts, create default
            if not self.layouts:
                self._create_default_layout()
                
        except Exception as e:
            logger.error(f"Error loading dashboard layouts: {e}")
            self._create_default_layout()
            
    def _create_default_layout(self):
        """Create default dashboard layout."""
        default_layout = DashboardLayout("Default")
        
        # Add default widgets
        default_layout.widgets = [
            WidgetDefinition(
                widget_id="viewer_count",
                widget_type=WidgetType.VIEWER_COUNT,
                title="Viewer Count",
                position={"row": 0, "col": 0, "row_span": 1, "col_span": 1}
            ),
            WidgetDefinition(
                widget_id="followers",
                widget_type=WidgetType.FOLLOWERS,
                title="Followers",
                position={"row": 0, "col": 1, "row_span": 1, "col_span": 1}
            ),
            WidgetDefinition(
                widget_id="subscribers",
                widget_type=WidgetType.SUBSCRIBERS,
                title="Subscribers",
                position={"row": 0, "col": 2, "row_span": 1, "col_span": 1}
            ),
            WidgetDefinition(
                widget_id="recent_events",
                widget_type=WidgetType.RECENT_EVENTS,
                title="Recent Events",
                position={"row": 1, "col": 0, "row_span": 3, "col_span": 3}
            ),
            WidgetDefinition(
                widget_id="stream_health",
                widget_type=WidgetType.STREAM_HEALTH,
                title="Stream Health",
                position={"row": 4, "col": 0, "row_span": 1, "col_span": 3}
            )
        ]
        
        # Add to layouts
        self.layouts["Default"] = default_layout
        self.active_layout = "Default"
        
        # Save to config
        self._save_layouts()
        
    def _save_layouts(self):
        """Save dashboard layouts to config."""
        layouts_data = {
            name: layout.to_dict() 
            for name, layout in self.layouts.items()
        }
        
        layouts_str = json.dumps(layouts_data)
        self.config.set("dashboard", "layouts", layouts_str)
        self.config.set("dashboard", "active_layout", self.active_layout)
        self.config.save()
        
    def get_active_layout(self) -> Optional[DashboardLayout]:
        """Get the active dashboard layout.
        
        Returns:
            Active dashboard layout or None
        """
        return self.layouts.get(self.active_layout)
        
    def set_active_layout(self, layout_name: str):
        """Set the active dashboard layout.
        
        Args:
            layout_name: Name of layout to activate
        """
        if layout_name in self.layouts:
            self.active_layout = layout_name
            self.config.set("dashboard", "active_layout", layout_name)
            self.config.save()
            
    def add_layout(self, layout: DashboardLayout):
        """Add a new dashboard layout.
        
        Args:
            layout: Dashboard layout to add
        """
        self.layouts[layout.name] = layout
        self._save_layouts()
        
    def update_layout(self, layout: DashboardLayout):
        """Update an existing dashboard layout.
        
        Args:
            layout: Dashboard layout to update
        """
        if layout.name in self.layouts:
            self.layouts[layout.name] = layout
            self._save_layouts()
            
    def delete_layout(self, layout_name: str):
        """Delete a dashboard layout.
        
        Args:
            layout_name: Name of layout to delete
        """
        if layout_name in self.layouts:
            if len(self.layouts) <= 1:
                # Don't delete last layout
                return
                
            del self.layouts[layout_name]
            
            # Update active layout if needed
            if self.active_layout == layout_name:
                self.active_layout = next(iter(self.layouts))
                
            self._save_layouts()


class WidgetDragItem(QListWidgetItem):
    """List widget item for draggable dashboard widgets."""
    
    def __init__(self, widget_type: WidgetType, title: str, parent=None):
        """Initialize the widget drag item.
        
        Args:
            widget_type: Widget type
            title: Widget title
            parent: Parent widget
        """
        super().__init__(title, parent)
        self.widget_type = widget_type
        self.setToolTip(f"Drag to add {title} widget to dashboard")


class WidgetPlaceholder(QFrame):
    """Placeholder for a dashboard widget in the grid."""
    
    def __init__(self, widget_id: str, widget_type: WidgetType, title: str, parent=None):
        """Initialize the widget placeholder.
        
        Args:
            widget_id: Widget ID
            widget_type: Widget type
            title: Widget title
            parent: Parent widget
        """
        super().__init__(parent)
        self.widget_id = widget_id
        self.widget_type = widget_type
        self.title = title
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(QSize(150, 100))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#2A2A2A"))
        self.setPalette(palette)
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        header.addWidget(title_label)
        header.addStretch()
        
        # Menu button
        menu_button = QToolButton()
        menu_button.setText("⋮")
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # Create menu
        menu = QMenu()
        menu.addAction("Configure", self.on_configure)
        menu.addAction("Remove", self.on_remove)
        menu_button.setMenu(menu)
        
        header.addWidget(menu_button)
        layout.addLayout(header)
        
        # Preview content
        content = QLabel(f"[{widget_type.value}]")
        content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(content)
        
    def on_configure(self):
        """Handle configure action."""
        pass
        
    def on_remove(self):
        """Handle remove action."""
        if self.parent():
            self.parent().remove_widget(self.widget_id)


class DashboardDesigner(QWidget):
    """Widget for designing dashboard layouts."""
    
    layout_changed = pyqtSignal(DashboardLayout)
    
    def __init__(self, layout: DashboardLayout, parent=None):
        """Initialize the dashboard designer.
        
        Args:
            layout: Dashboard layout to edit
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.layout = layout
        self.grid_size = 6  # 6x6 grid
        self.widgets: Dict[str, WidgetPlaceholder] = {}
        
        # Initialize UI
        self._init_ui()
        
        # Load layout
        self._load_layout()
        
    def _init_ui(self):
        """Initialize the UI components."""
        main_layout = QHBoxLayout(self)
        
        # Left panel - available widgets
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Widget palette
        palette_group = QGroupBox("Widget Palette")
        palette_layout = QVBoxLayout(palette_group)
        
        self.widget_list = QListWidget()
        self.widget_list.setDragEnabled(True)
        
        # Add widget types
        for widget_type in WidgetType:
            title = widget_type.value.replace('_', ' ').title()
            item = WidgetDragItem(widget_type, title)
            self.widget_list.addItem(item)
            
        palette_layout.addWidget(self.widget_list)
        left_layout.addWidget(palette_group)
        
        # Layout settings
        settings_group = QGroupBox("Layout Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.name_edit = QComboBox()
        self.name_edit.setEditable(True)
        self.name_edit.setCurrentText(self.layout.name)
        settings_layout.addRow("Name:", self.name_edit)
        
        left_layout.addWidget(settings_group)
        
        # Add to main layout
        main_layout.addWidget(left_panel, 1)
        
        # Right panel - grid editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create grid
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        
        # Create grid cells
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                cell = QLabel()
                cell.setMinimumSize(QSize(20, 20))
                cell.setStyleSheet("background-color: #333; border: 1px solid #555;")
                cell.setAcceptDrops(True)
                self.grid_layout.addWidget(cell, row, col)
        
        # Add grid to scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.grid_widget)
        
        right_layout.addWidget(scroll_area)
        
        # Add to main layout
        main_layout.addWidget(right_panel, 3)
        
    def _load_layout(self):
        """Load the dashboard layout."""
        # Clear existing widgets
        self.widgets.clear()
        
        # Create widget placeholders
        for widget_def in self.layout.widgets:
            placeholder = WidgetPlaceholder(
                widget_def.widget_id,
                widget_def.widget_type,
                widget_def.title
            )
            
            # Add to grid
            pos = widget_def.position
            self.grid_layout.addWidget(
                placeholder,
                pos.get("row", 0),
                pos.get("col", 0),
                pos.get("row_span", 1),
                pos.get("col_span", 1)
            )
            
            # Store reference
            self.widgets[widget_def.widget_id] = placeholder
            
    def remove_widget(self, widget_id: str):
        """Remove a widget from the dashboard.
        
        Args:
            widget_id: ID of widget to remove
        """
        if widget_id in self.widgets:
            # Remove from grid
            self.grid_layout.removeWidget(self.widgets[widget_id])
            
            # Delete widget
            self.widgets[widget_id].deleteLater()
            del self.widgets[widget_id]
            
            # Update layout
            self._update_layout()
            
    def _update_layout(self):
        """Update the layout from the current grid."""
        # Clear widgets
        self.layout.widgets.clear()
        
        # Add current widgets
        for widget_id, placeholder in self.widgets.items():
            # Get position
            index = self.grid_layout.indexOf(placeholder)
            if index != -1:
                row, col, row_span, col_span = 0, 0, 1, 1
                
                # Get cell position
                info = self.grid_layout.getItemPosition(index)
                row, col, row_span, col_span = info
                
                # Create widget definition
                widget_def = WidgetDefinition(
                    widget_id=widget_id,
                    widget_type=placeholder.widget_type,
                    title=placeholder.title,
                    position={
                        "row": row,
                        "col": col,
                        "row_span": row_span,
                        "col_span": col_span
                    }
                )
                
                self.layout.widgets.append(widget_def)
        
        # Update layout name
        self.layout.name = self.name_edit.currentText()
        
        # Emit changed signal
        self.layout_changed.emit(self.layout)


class DashboardCustomizer(QDialog):
    """Dialog for customizing dashboard layouts."""
    
    layout_updated = pyqtSignal(DashboardLayout)
    
    def __init__(self, dashboard_manager: DashboardManager, parent=None):
        """Initialize the dashboard customizer.
        
        Args:
            dashboard_manager: Dashboard manager
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.dashboard_manager = dashboard_manager
        
        self.setWindowTitle("Dashboard Customizer")
        self.setMinimumSize(QSize(800, 600))
        
        # Initialize UI
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Layout selection
        layout_group = QGroupBox("Dashboard Layouts")
        layout_layout = QHBoxLayout(layout_group)
        
        self.layout_combo = QComboBox()
        self.layout_combo.currentTextChanged.connect(self._on_layout_changed)
        layout_layout.addWidget(self.layout_combo)
        
        # Add layout button
        add_layout_button = QPushButton("New")
        add_layout_button.clicked.connect(self._on_add_layout)
        layout_layout.addWidget(add_layout_button)
        
        # Delete layout button
        delete_layout_button = QPushButton("Delete")
        delete_layout_button.clicked.connect(self._on_delete_layout)
        layout_layout.addWidget(delete_layout_button)
        
        layout.addWidget(layout_group)
        
        # Designer
        active_layout = self.dashboard_manager.get_active_layout()
        if active_layout:
            self.designer = DashboardDesigner(active_layout)
            self.designer.layout_changed.connect(self._on_designer_layout_changed)
            layout.addWidget(self.designer)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Load layouts
        self._load_layouts()
        
    def _load_layouts(self):
        """Load available layouts."""
        self.layout_combo.clear()
        
        # Add layouts
        for name in self.dashboard_manager.layouts:
            self.layout_combo.addItem(name)
            
        # Set active layout
        active_layout = self.dashboard_manager.active_layout
        if active_layout in self.dashboard_manager.layouts:
            self.layout_combo.setCurrentText(active_layout)
            
    def _on_layout_changed(self, layout_name: str):
        """Handle layout selection change.
        
        Args:
            layout_name: Selected layout name
        """
        if layout_name in self.dashboard_manager.layouts:
            # Update designer
            layout = self.dashboard_manager.layouts[layout_name]
            
            # Replace designer
            if hasattr(self, 'designer'):
                self.designer.deleteLater()
                
            self.designer = DashboardDesigner(layout)
            self.designer.layout_changed.connect(self._on_designer_layout_changed)
            
            # Add to layout
            self.layout().insertWidget(1, self.designer)
            
    def _on_designer_layout_changed(self, updated_layout: DashboardLayout):
        """Handle designer layout changes.
        
        Args:
            updated_layout: Updated layout
        """
        # Update layout in manager
        self.dashboard_manager.update_layout(updated_layout)
        
        # Update layout selection if name changed
        current_text = self.layout_combo.currentText()
        if current_text != updated_layout.name:
            self._load_layouts()
            self.layout_combo.setCurrentText(updated_layout.name)
            
    def _on_add_layout(self):
        """Handle add layout button."""
        # Create new layout
        new_layout = DashboardLayout(f"New Layout {len(self.dashboard_manager.layouts) + 1}")
        
        # Add to manager
        self.dashboard_manager.add_layout(new_layout)
        
        # Update combo
        self._load_layouts()
        self.layout_combo.setCurrentText(new_layout.name)
        
    def _on_delete_layout(self):
        """Handle delete layout button."""
        layout_name = self.layout_combo.currentText()
        
        # Don't delete if only one layout
        if len(self.dashboard_manager.layouts) <= 1:
            return
            
        # Delete layout
        self.dashboard_manager.delete_layout(layout_name)
        
        # Reload layouts
        self._load_layouts()
        
    def accept(self):
        """Handle accept button."""
        # Activate selected layout
        layout_name = self.layout_combo.currentText()
        self.dashboard_manager.set_active_layout(layout_name)
        
        # Get updated layout
        active_layout = self.dashboard_manager.get_active_layout()
        if active_layout:
            self.layout_updated.emit(active_layout)
            
        super().accept() 