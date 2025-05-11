"""
Template selection dialog for workflow editor.
"""

import logging
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QTextEdit, QSplitter, QWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from obscopilot.workflows.template_manager import get_template_manager
from obscopilot.workflows.models import Workflow

logger = logging.getLogger(__name__)


class TemplateListItem(QListWidgetItem):
    """List item for a workflow template."""
    
    def __init__(self, template_id: str, template_info: Dict):
        """Initialize template list item.
        
        Args:
            template_id: Template ID
            template_info: Template information
        """
        super().__init__(template_info.get("name", "Unnamed Template"))
        self.template_id = template_id
        self.template_info = template_info
        self.setToolTip(template_info.get("description", ""))


class TemplateDialog(QDialog):
    """Dialog for selecting a workflow template."""
    
    template_selected = pyqtSignal(Workflow)
    
    def __init__(self, parent=None):
        """Initialize template dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Select Workflow Template")
        self.resize(800, 500)
        
        self.template_manager = get_template_manager()
        self.selected_template_id = None
        
        self._init_ui()
        self._load_templates()
    
    def _init_ui(self):
        """Initialize UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Choose a workflow template to get started")
        header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header_label)
        
        # Splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Template list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.template_list = QListWidget()
        self.template_list.setMinimumWidth(250)
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        list_layout.addWidget(self.template_list)
        
        # Preview area
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        # Template name
        self.name_label = QLabel("No template selected")
        self.name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        preview_layout.addWidget(self.name_label)
        
        # Template description
        self.description_box = QTextEdit()
        self.description_box.setReadOnly(True)
        self.description_box.setMaximumHeight(100)
        preview_layout.addWidget(self.description_box)
        
        # Trigger/Action preview
        structure_frame = QFrame()
        structure_frame.setFrameShape(QFrame.Shape.StyledPanel)
        structure_layout = QVBoxLayout(structure_frame)
        
        # Triggers section
        triggers_label = QLabel("Triggers:")
        triggers_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        structure_layout.addWidget(triggers_label)
        
        self.triggers_list = QListWidget()
        structure_layout.addWidget(self.triggers_list)
        
        # Actions section
        actions_label = QLabel("Actions:")
        actions_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        structure_layout.addWidget(actions_label)
        
        self.actions_list = QListWidget()
        structure_layout.addWidget(self.actions_list)
        
        preview_layout.addWidget(structure_frame)
        
        # Add widgets to splitter
        splitter.addWidget(list_widget)
        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Create empty workflow button
        self.empty_button = QPushButton("Create Empty Workflow")
        self.empty_button.clicked.connect(self._on_create_empty)
        button_layout.addWidget(self.empty_button)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # Select button
        self.select_button = QPushButton("Select Template")
        self.select_button.setEnabled(False)
        self.select_button.clicked.connect(self._on_select)
        button_layout.addWidget(self.select_button)
        
        layout.addLayout(button_layout)
    
    def _load_templates(self):
        """Load available templates into the list."""
        template_info = self.template_manager.get_template_info()
        
        # Sort templates by name
        template_info.sort(key=lambda t: t.get("name", ""))
        
        for info in template_info:
            template_id = info.get("id")
            item = TemplateListItem(template_id, info)
            self.template_list.addItem(item)
    
    def _on_template_selected(self, current, previous):
        """Handle template selection.
        
        Args:
            current: Current selected item
            previous: Previously selected item
        """
        if current is None:
            self.selected_template_id = None
            self.select_button.setEnabled(False)
            
            # Clear preview
            self.name_label.setText("No template selected")
            self.description_box.setPlainText("")
            self.triggers_list.clear()
            self.actions_list.clear()
            return
        
        # Get template data
        self.selected_template_id = current.template_id
        template_data = self.template_manager.get_template(self.selected_template_id)
        
        if template_data:
            # Update preview
            self.name_label.setText(template_data.get("name", "Unnamed Template"))
            self.description_box.setPlainText(template_data.get("description", ""))
            
            # Populate triggers
            self.triggers_list.clear()
            for trigger in template_data.get("triggers", []):
                trigger_name = trigger.get("name", "Unnamed Trigger")
                trigger_type = trigger.get("type", "Unknown")
                self.triggers_list.addItem(f"{trigger_name} ({trigger_type})")
            
            # Populate actions
            self.actions_list.clear()
            for action in template_data.get("actions", []):
                action_name = action.get("name", "Unnamed Action")
                action_type = action.get("type", "Unknown")
                self.actions_list.addItem(f"{action_name} ({action_type})")
            
            self.select_button.setEnabled(True)
    
    def _on_select(self):
        """Handle template selection button click."""
        if self.selected_template_id:
            workflow = self.template_manager.create_workflow_from_template(self.selected_template_id)
            if workflow:
                self.template_selected.emit(workflow)
                self.accept()
            else:
                # Failed to create workflow from template
                logger.error(f"Failed to create workflow from template: {self.selected_template_id}")
    
    def _on_create_empty(self):
        """Handle empty workflow button click."""
        workflow = Workflow(name="New Workflow", description="", triggers=[], actions=[])
        self.template_selected.emit(workflow)
        self.accept()


def select_workflow_template(parent=None) -> Optional[Workflow]:
    """Show template selection dialog and return selected workflow.
    
    Args:
        parent: Parent widget
        
    Returns:
        Selected workflow or None if canceled
    """
    dialog = TemplateDialog(parent)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted and hasattr(dialog, "selected_workflow"):
        return dialog.selected_workflow
    
    return None 