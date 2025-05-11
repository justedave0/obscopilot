"""
Workflow Editor for OBSCopilot.

This module provides a visual workflow editor to create and modify workflows.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QComboBox, QScrollArea, QFrame, QSplitter, QTabWidget,
    QDialog, QMessageBox, QCheckBox, QGridLayout, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QToolButton, QMenu, QSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

from obscopilot.workflows.models import Workflow, Trigger, Action, Condition
from obscopilot.workflows.registry import TRIGGER_REGISTRY, ACTION_REGISTRY
from obscopilot.core.events import EventType, event_bus

logger = logging.getLogger(__name__)


class TriggerWidget(QFrame):
    """Widget for editing a workflow trigger."""
    
    trigger_updated = pyqtSignal(object)
    trigger_deleted = pyqtSignal(str)
    
    def __init__(self, trigger: Trigger, parent=None):
        """Initialize the trigger widget.
        
        Args:
            trigger: Trigger object to edit
            parent: Parent widget
        """
        super().__init__(parent)
        self.trigger = trigger
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#2A2A2A"))
        self.setPalette(palette)
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Trigger type
        type_label = QLabel(f"Trigger Type: {self.trigger.type}")
        type_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(type_label)
        
        # Spacer
        header_layout.addStretch()
        
        # Enabled checkbox
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(self.trigger.enabled)
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        header_layout.addWidget(self.enabled_checkbox)
        
        # Delete button
        delete_button = QPushButton("Delete")
        delete_button.setMaximumWidth(80)
        delete_button.clicked.connect(self._on_delete)
        header_layout.addWidget(delete_button)
        
        layout.addLayout(header_layout)
        
        # Form layout for trigger properties
        form_layout = QFormLayout()
        
        # Trigger name
        self.name_edit = QLineEdit(self.trigger.name)
        self.name_edit.textChanged.connect(self._on_name_changed)
        form_layout.addRow("Name:", self.name_edit)
        
        # Trigger description
        self.description_edit = QTextEdit(self.trigger.description or "")
        self.description_edit.setMaximumHeight(60)
        self.description_edit.textChanged.connect(self._on_description_changed)
        form_layout.addRow("Description:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Dynamic config based on trigger type
        self.config_widget = QWidget()
        self.config_layout = QFormLayout(self.config_widget)
        
        # Get trigger class from registry
        trigger_class = TRIGGER_REGISTRY.get(self.trigger.type)
        if trigger_class and hasattr(trigger_class, 'config_schema'):
            # Create input fields based on config schema
            for field_name, field_schema in trigger_class.config_schema().items():
                field_type = field_schema.get('type', 'string')
                field_label = field_schema.get('label', field_name.replace('_', ' ').title())
                field_default = field_schema.get('default', '')
                field_required = field_schema.get('required', False)
                
                current_value = self.trigger.config.get(field_name, field_default)
                
                # Create appropriate widget based on field type
                if field_type == 'string':
                    field_widget = QLineEdit(str(current_value))
                    field_widget.textChanged.connect(
                        lambda text, name=field_name: self._on_config_changed(name, text)
                    )
                elif field_type == 'boolean':
                    field_widget = QCheckBox()
                    field_widget.setChecked(bool(current_value))
                    field_widget.stateChanged.connect(
                        lambda state, name=field_name: self._on_config_changed(
                            name, state == Qt.CheckState.Checked
                        )
                    )
                elif field_type == 'integer':
                    field_widget = QSpinBox()
                    field_widget.setRange(
                        field_schema.get('minimum', 0),
                        field_schema.get('maximum', 9999)
                    )
                    field_widget.setValue(int(current_value) if current_value else 0)
                    field_widget.valueChanged.connect(
                        lambda value, name=field_name: self._on_config_changed(name, value)
                    )
                elif field_type == 'select':
                    field_widget = QComboBox()
                    options = field_schema.get('options', [])
                    for option in options:
                        field_widget.addItem(option.get('label', ''), option.get('value', ''))
                    
                    # Set current value
                    index = -1
                    for i in range(field_widget.count()):
                        if field_widget.itemData(i) == current_value:
                            index = i
                            break
                    if index >= 0:
                        field_widget.setCurrentIndex(index)
                    
                    field_widget.currentIndexChanged.connect(
                        lambda idx, name=field_name, widget=field_widget: 
                        self._on_config_changed(name, widget.itemData(idx))
                    )
                else:
                    # Default to text field
                    field_widget = QLineEdit(str(current_value))
                    field_widget.textChanged.connect(
                        lambda text, name=field_name: self._on_config_changed(name, text)
                    )
                
                # Add to form
                if field_required:
                    self.config_layout.addRow(f"{field_label}*:", field_widget)
                else:
                    self.config_layout.addRow(f"{field_label}:", field_widget)
        
        layout.addWidget(self.config_widget)
        
    def _on_name_changed(self, text):
        """Handle name changes.
        
        Args:
            text: New name text
        """
        self.trigger.name = text
        self.trigger_updated.emit(self.trigger)
        
    def _on_description_changed(self):
        """Handle description changes."""
        self.trigger.description = self.description_edit.toPlainText()
        self.trigger_updated.emit(self.trigger)
        
    def _on_enabled_changed(self, state):
        """Handle enabled state changes.
        
        Args:
            state: New checkbox state
        """
        self.trigger.enabled = state == Qt.CheckState.Checked
        self.trigger_updated.emit(self.trigger)
        
    def _on_config_changed(self, field_name, value):
        """Handle config field changes.
        
        Args:
            field_name: Name of the config field
            value: New field value
        """
        self.trigger.config[field_name] = value
        self.trigger_updated.emit(self.trigger)
        
    def _on_delete(self):
        """Handle trigger deletion."""
        confirm = QMessageBox.question(
            self, 
            "Delete Trigger", 
            f"Are you sure you want to delete the trigger '{self.trigger.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.trigger_deleted.emit(self.trigger.id)
    

class ActionWidget(QFrame):
    """Widget for editing a workflow action."""
    
    action_updated = pyqtSignal(object)
    action_deleted = pyqtSignal(str)
    
    def __init__(self, action: Action, parent=None):
        """Initialize the action widget.
        
        Args:
            action: Action object to edit
            parent: Parent widget
        """
        super().__init__(parent)
        self.action = action
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#2A2A2A"))
        self.setPalette(palette)
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Action type
        type_label = QLabel(f"Action Type: {self.action.type}")
        type_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(type_label)
        
        # Spacer
        header_layout.addStretch()
        
        # Enabled checkbox
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(self.action.enabled)
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        header_layout.addWidget(self.enabled_checkbox)
        
        # Delete button
        delete_button = QPushButton("Delete")
        delete_button.setMaximumWidth(80)
        delete_button.clicked.connect(self._on_delete)
        header_layout.addWidget(delete_button)
        
        layout.addLayout(header_layout)
        
        # Form layout for action properties
        form_layout = QFormLayout()
        
        # Action name
        self.name_edit = QLineEdit(self.action.name)
        self.name_edit.textChanged.connect(self._on_name_changed)
        form_layout.addRow("Name:", self.name_edit)
        
        # Action description
        self.description_edit = QTextEdit(self.action.description or "")
        self.description_edit.setMaximumHeight(60)
        self.description_edit.textChanged.connect(self._on_description_changed)
        form_layout.addRow("Description:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Dynamic config based on action type
        self.config_widget = QWidget()
        self.config_layout = QFormLayout(self.config_widget)
        
        # Get action class from registry
        action_class = ACTION_REGISTRY.get(self.action.type)
        if action_class and hasattr(action_class, 'config_schema'):
            # Create input fields based on config schema
            for field_name, field_schema in action_class.config_schema().items():
                field_type = field_schema.get('type', 'string')
                field_label = field_schema.get('label', field_name.replace('_', ' ').title())
                field_default = field_schema.get('default', '')
                field_required = field_schema.get('required', False)
                
                current_value = self.action.config.get(field_name, field_default)
                
                # Create appropriate widget based on field type
                if field_type == 'string':
                    field_widget = QLineEdit(str(current_value))
                    field_widget.textChanged.connect(
                        lambda text, name=field_name: self._on_config_changed(name, text)
                    )
                elif field_type == 'boolean':
                    field_widget = QCheckBox()
                    field_widget.setChecked(bool(current_value))
                    field_widget.stateChanged.connect(
                        lambda state, name=field_name: self._on_config_changed(
                            name, state == Qt.CheckState.Checked
                        )
                    )
                elif field_type == 'integer':
                    field_widget = QSpinBox()
                    field_widget.setRange(
                        field_schema.get('minimum', 0),
                        field_schema.get('maximum', 9999)
                    )
                    field_widget.setValue(int(current_value) if current_value else 0)
                    field_widget.valueChanged.connect(
                        lambda value, name=field_name: self._on_config_changed(name, value)
                    )
                elif field_type == 'select':
                    field_widget = QComboBox()
                    options = field_schema.get('options', [])
                    for option in options:
                        field_widget.addItem(option.get('label', ''), option.get('value', ''))
                    
                    # Set current value
                    index = -1
                    for i in range(field_widget.count()):
                        if field_widget.itemData(i) == current_value:
                            index = i
                            break
                    if index >= 0:
                        field_widget.setCurrentIndex(index)
                    
                    field_widget.currentIndexChanged.connect(
                        lambda idx, name=field_name, widget=field_widget: 
                        self._on_config_changed(name, widget.itemData(idx))
                    )
                else:
                    # Default to text field
                    field_widget = QLineEdit(str(current_value))
                    field_widget.textChanged.connect(
                        lambda text, name=field_name: self._on_config_changed(name, text)
                    )
                
                # Add to form
                if field_required:
                    self.config_layout.addRow(f"{field_label}*:", field_widget)
                else:
                    self.config_layout.addRow(f"{field_label}:", field_widget)
        
        layout.addWidget(self.config_widget)
        
    def _on_name_changed(self, text):
        """Handle name changes.
        
        Args:
            text: New name text
        """
        self.action.name = text
        self.action_updated.emit(self.action)
        
    def _on_description_changed(self):
        """Handle description changes."""
        self.action.description = self.description_edit.toPlainText()
        self.action_updated.emit(self.action)
        
    def _on_enabled_changed(self, state):
        """Handle enabled state changes.
        
        Args:
            state: New checkbox state
        """
        self.action.enabled = state == Qt.CheckState.Checked
        self.action_updated.emit(self.action)
        
    def _on_config_changed(self, field_name, value):
        """Handle config field changes.
        
        Args:
            field_name: Name of the config field
            value: New field value
        """
        self.action.config[field_name] = value
        self.action_updated.emit(self.action)
        
    def _on_delete(self):
        """Handle action deletion."""
        confirm = QMessageBox.question(
            self, 
            "Delete Action", 
            f"Are you sure you want to delete the action '{self.action.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.action_deleted.emit(self.action.id)


class AddTriggerDialog(QDialog):
    """Dialog for adding a new trigger to a workflow."""
    
    def __init__(self, parent=None):
        """Initialize dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Add Trigger")
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        
        self.trigger_type = None
        self.trigger_name = ""
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Trigger type selector
        self.type_selector = QComboBox()
        for trigger_type, trigger_class in TRIGGER_REGISTRY.items():
            self.type_selector.addItem(
                trigger_class.get_name() if hasattr(trigger_class, 'get_name') else trigger_type,
                trigger_type
            )
        form_layout.addRow("Trigger Type:", self.type_selector)
        
        # Trigger name
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # Add button
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_add)
        self.add_button.setEnabled(False)
        button_layout.addWidget(self.add_button)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.name_edit.textChanged.connect(self._validate)
        
    def _validate(self):
        """Validate form input."""
        if self.name_edit.text().strip():
            self.add_button.setEnabled(True)
        else:
            self.add_button.setEnabled(False)
            
    def _on_add(self):
        """Handle add button click."""
        self.trigger_type = self.type_selector.currentData()
        self.trigger_name = self.name_edit.text().strip()
        self.accept()


class AddActionDialog(QDialog):
    """Dialog for adding a new action to a workflow."""
    
    def __init__(self, parent=None):
        """Initialize dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Add Action")
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        
        self.action_type = None
        self.action_name = ""
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Action type selector
        self.type_selector = QComboBox()
        for action_type, action_class in ACTION_REGISTRY.items():
            self.type_selector.addItem(
                action_class.get_name() if hasattr(action_class, 'get_name') else action_type,
                action_type
            )
        form_layout.addRow("Action Type:", self.type_selector)
        
        # Action name
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # Add button
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_add)
        self.add_button.setEnabled(False)
        button_layout.addWidget(self.add_button)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.name_edit.textChanged.connect(self._validate)
        
    def _validate(self):
        """Validate form input."""
        if self.name_edit.text().strip():
            self.add_button.setEnabled(True)
        else:
            self.add_button.setEnabled(False)
            
    def _on_add(self):
        """Handle add button click."""
        self.action_type = self.type_selector.currentData()
        self.action_name = self.name_edit.text().strip()
        self.accept()


class WorkflowEditor(QWidget):
    """Workflow editor widget for creating and editing workflows."""
    
    workflow_saved = pyqtSignal(object)
    
    def __init__(self, workflow: Optional[Workflow] = None, parent=None):
        """Initialize the workflow editor.
        
        Args:
            workflow: Workflow to edit (or None for a new workflow)
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Create new workflow if none provided
        self.workflow = workflow or Workflow(
            name="New Workflow",
            description="",
            triggers=[],
            actions=[]
        )
        
        # Copy of the workflow for cancellation
        self.original_workflow = workflow
        
        # Track if the workflow has been modified
        self.is_modified = workflow is None
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Workflow name
        workflow_name_layout = QHBoxLayout()
        workflow_name_layout.addWidget(QLabel("Workflow Name:"))
        self.name_edit = QLineEdit(self.workflow.name)
        self.name_edit.textChanged.connect(self._on_name_changed)
        workflow_name_layout.addWidget(self.name_edit)
        
        # Enable checkbox
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(self.workflow.enabled)
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        
        header_layout.addLayout(workflow_name_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.enabled_checkbox)
        
        layout.addLayout(header_layout)
        
        # Description
        description_layout = QHBoxLayout()
        description_layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit(self.workflow.description or "")
        self.description_edit.setMaximumHeight(60)
        self.description_edit.textChanged.connect(self._on_description_changed)
        description_layout.addWidget(self.description_edit)
        
        layout.addLayout(description_layout)
        
        # Create tab widget for triggers and actions
        self.tab_widget = QTabWidget()
        
        # Triggers tab
        self.triggers_widget = QWidget()
        self.triggers_layout = QVBoxLayout(self.triggers_widget)
        self.triggers_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Add trigger button
        self.add_trigger_button = QPushButton("Add Trigger")
        self.add_trigger_button.clicked.connect(self._on_add_trigger)
        self.triggers_layout.addWidget(self.add_trigger_button)
        
        # Triggers container
        self.triggers_container = QWidget()
        self.triggers_container_layout = QVBoxLayout(self.triggers_container)
        self.triggers_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.triggers_container_layout.setContentsMargins(0, 0, 0, 0)
        self.triggers_container_layout.setSpacing(10)
        
        # Add existing triggers
        self._populate_triggers()
        
        # Add triggers container to scroll area
        triggers_scroll = QScrollArea()
        triggers_scroll.setWidgetResizable(True)
        triggers_scroll.setWidget(self.triggers_container)
        
        self.triggers_layout.addWidget(triggers_scroll)
        
        # Actions tab
        self.actions_widget = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_widget)
        self.actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Add action button
        self.add_action_button = QPushButton("Add Action")
        self.add_action_button.clicked.connect(self._on_add_action)
        self.actions_layout.addWidget(self.add_action_button)
        
        # Actions container
        self.actions_container = QWidget()
        self.actions_container_layout = QVBoxLayout(self.actions_container)
        self.actions_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.actions_container_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_container_layout.setSpacing(10)
        
        # Add existing actions
        self._populate_actions()
        
        # Add actions container to scroll area
        actions_scroll = QScrollArea()
        actions_scroll.setWidgetResizable(True)
        actions_scroll.setWidget(self.actions_container)
        
        self.actions_layout.addWidget(actions_scroll)
        
        # Add tabs
        self.tab_widget.addTab(self.triggers_widget, "Triggers")
        self.tab_widget.addTab(self.actions_widget, "Actions")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Export button
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self._on_export)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save)
        self.save_button.setEnabled(self.is_modified)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
    def _populate_triggers(self):
        """Populate triggers from the workflow."""
        # Clear existing widgets
        while self.triggers_container_layout.count() > 0:
            item = self.triggers_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add trigger widgets
        for trigger in self.workflow.triggers:
            trigger_widget = TriggerWidget(trigger)
            trigger_widget.trigger_updated.connect(self._on_trigger_updated)
            trigger_widget.trigger_deleted.connect(self._on_trigger_deleted)
            self.triggers_container_layout.addWidget(trigger_widget)
            
        # Add empty state if no triggers
        if not self.workflow.triggers:
            no_triggers_label = QLabel("No triggers defined. Add a trigger to start.")
            no_triggers_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.triggers_container_layout.addWidget(no_triggers_label)
    
    def _populate_actions(self):
        """Populate actions from the workflow."""
        # Clear existing widgets
        while self.actions_container_layout.count() > 0:
            item = self.actions_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add action widgets
        for action in self.workflow.actions:
            action_widget = ActionWidget(action)
            action_widget.action_updated.connect(self._on_action_updated)
            action_widget.action_deleted.connect(self._on_action_deleted)
            self.actions_container_layout.addWidget(action_widget)
            
        # Add empty state if no actions
        if not self.workflow.actions:
            no_actions_label = QLabel("No actions defined. Add an action to start.")
            no_actions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.actions_container_layout.addWidget(no_actions_label)
    
    def _on_name_changed(self, text):
        """Handle name changes.
        
        Args:
            text: New name text
        """
        self.workflow.name = text
        self.is_modified = True
        self.save_button.setEnabled(True)
        
    def _on_description_changed(self):
        """Handle description changes."""
        self.workflow.description = self.description_edit.toPlainText()
        self.is_modified = True
        self.save_button.setEnabled(True)
        
    def _on_enabled_changed(self, state):
        """Handle enabled state changes.
        
        Args:
            state: New checkbox state
        """
        self.workflow.enabled = state == Qt.CheckState.Checked
        self.is_modified = True
        self.save_button.setEnabled(True)
        
    def _on_trigger_updated(self, trigger):
        """Handle trigger updates.
        
        Args:
            trigger: Updated trigger
        """
        # Find and update trigger in workflow
        for i, t in enumerate(self.workflow.triggers):
            if t.id == trigger.id:
                self.workflow.triggers[i] = trigger
                break
        
        self.is_modified = True
        self.save_button.setEnabled(True)
        
    def _on_trigger_deleted(self, trigger_id):
        """Handle trigger deletion.
        
        Args:
            trigger_id: ID of the trigger to delete
        """
        # Remove trigger from workflow
        self.workflow.triggers = [t for t in self.workflow.triggers if t.id != trigger_id]
        
        # Update UI
        self._populate_triggers()
        
        self.is_modified = True
        self.save_button.setEnabled(True)
        
    def _on_action_updated(self, action):
        """Handle action updates.
        
        Args:
            action: Updated action
        """
        # Find and update action in workflow
        for i, a in enumerate(self.workflow.actions):
            if a.id == action.id:
                self.workflow.actions[i] = action
                break
        
        self.is_modified = True
        self.save_button.setEnabled(True)
        
    def _on_action_deleted(self, action_id):
        """Handle action deletion.
        
        Args:
            action_id: ID of the action to delete
        """
        # Remove action from workflow
        self.workflow.actions = [a for a in self.workflow.actions if a.id != action_id]
        
        # Update UI
        self._populate_actions()
        
        self.is_modified = True
        self.save_button.setEnabled(True)
        
    def _on_add_trigger(self):
        """Handle add trigger button click."""
        dialog = AddTriggerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Create new trigger
            trigger = Trigger(
                name=dialog.trigger_name,
                type=dialog.trigger_type
            )
            
            # Add to workflow
            self.workflow.triggers.append(trigger)
            
            # Update UI
            self._populate_triggers()
            
            self.is_modified = True
            self.save_button.setEnabled(True)
            
    def _on_add_action(self):
        """Handle add action button click."""
        dialog = AddActionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Create new action
            action = Action(
                name=dialog.action_name,
                type=dialog.action_type
            )
            
            # Add to workflow
            self.workflow.actions.append(action)
            
            # Update UI
            self._populate_actions()
            
            self.is_modified = True
            self.save_button.setEnabled(True)
    
    def _on_export(self):
        """Handle export button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Workflow",
            f"{self.workflow.name.replace(' ', '_')}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                # Export workflow to JSON
                with open(file_path, 'w') as f:
                    json.dump(json.loads(self.workflow.json()), f, indent=2)
                    
                QMessageBox.information(
                    self, 
                    "Export Successful", 
                    f"Workflow exported to {file_path}"
                )
            except Exception as e:
                logger.error(f"Error exporting workflow: {e}")
                QMessageBox.warning(
                    self, 
                    "Export Failed", 
                    f"Failed to export workflow: {str(e)}"
                )
    
    def _on_cancel(self):
        """Handle cancel button click."""
        if self.is_modified:
            confirm = QMessageBox.question(
                self, 
                "Unsaved Changes", 
                "You have unsaved changes. Are you sure you want to cancel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.No:
                return
        
        # Emit signal with original workflow
        self.workflow_saved.emit(self.original_workflow)
        
    def _on_save(self):
        """Handle save button click."""
        # Basic validation
        if not self.workflow.name:
            QMessageBox.warning(
                self, 
                "Validation Error", 
                "Workflow name is required."
            )
            return
            
        if not self.workflow.triggers:
            confirm = QMessageBox.question(
                self, 
                "No Triggers", 
                "This workflow has no triggers defined. Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.No:
                return
                
        if not self.workflow.actions:
            confirm = QMessageBox.question(
                self, 
                "No Actions", 
                "This workflow has no actions defined. Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.No:
                return
        
        # Emit signal with updated workflow
        self.workflow_saved.emit(self.workflow) 