"""
Chat Commands tab for OBSCopilot UI.

This module provides a UI tab for managing custom chat commands.
"""

import logging
import time
from typing import Optional, Dict, List, Set

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QLineEdit, QLabel, QComboBox, QCheckBox, 
    QDialog, QDialogButtonBox, QFormLayout, QHeaderView, QMessageBox,
    QSpinBox, QTextEdit
)

from obscopilot.twitch.commands import (
    command_registry, register_command, unregister_command, get_command, ChatCommand
)
from obscopilot.workflows.models import WorkflowTrigger
from obscopilot.workflows.triggers.chat_triggers import ChatCommandTrigger

logger = logging.getLogger(__name__)


class CommandDialog(QDialog):
    """Dialog for creating/editing commands."""
    
    def __init__(
        self, 
        parent=None, 
        command: Optional[ChatCommand] = None,
        edit_mode: bool = False
    ):
        """Initialize command dialog.
        
        Args:
            parent: Parent widget
            command: Command to edit, or None for a new command
            edit_mode: Whether the dialog is in edit mode
        """
        super().__init__(parent)
        
        self.command = command
        self.edit_mode = edit_mode
        
        self.setWindowTitle("Edit Command" if edit_mode else "Add Command")
        self.setMinimumWidth(400)
        
        # Create layout
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Name field
        self.name_input = QLineEdit()
        if command:
            self.name_input.setText(command.name)
        if edit_mode:
            self.name_input.setReadOnly(True)
        form_layout.addRow("Command Name:", self.name_input)
        
        # Description field
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        if command:
            self.description_input.setText(command.description)
        form_layout.addRow("Description:", self.description_input)
        
        # Aliases field
        self.aliases_input = QLineEdit()
        if command and command.aliases:
            self.aliases_input.setText(", ".join(command.aliases))
        form_layout.addRow("Aliases (comma-separated):", self.aliases_input)
        
        # Cooldown fields
        self.cooldown_input = QSpinBox()
        self.cooldown_input.setRange(0, 3600)
        self.cooldown_input.setSuffix(" seconds")
        if command:
            self.cooldown_input.setValue(command.cooldown)
        form_layout.addRow("Global Cooldown:", self.cooldown_input)
        
        self.user_cooldown_input = QSpinBox()
        self.user_cooldown_input.setRange(0, 3600)
        self.user_cooldown_input.setSuffix(" seconds")
        if command:
            self.user_cooldown_input.setValue(command.user_cooldown)
        form_layout.addRow("Per-user Cooldown:", self.user_cooldown_input)
        
        # Permissions
        self.permissions_group = QWidget()
        permissions_layout = QVBoxLayout(self.permissions_group)
        permissions_layout.setContentsMargins(0, 0, 0, 0)
        
        self.broadcaster_check = QCheckBox("Broadcaster")
        self.mod_check = QCheckBox("Moderator")
        self.vip_check = QCheckBox("VIP")
        self.sub_check = QCheckBox("Subscriber")
        
        if command and command.permissions:
            self.broadcaster_check.setChecked("broadcaster" in command.permissions)
            self.mod_check.setChecked("mod" in command.permissions)
            self.vip_check.setChecked("vip" in command.permissions)
            self.sub_check.setChecked("sub" in command.permissions)
        
        permissions_layout.addWidget(self.broadcaster_check)
        permissions_layout.addWidget(self.mod_check)
        permissions_layout.addWidget(self.vip_check)
        permissions_layout.addWidget(self.sub_check)
        
        form_layout.addRow("Required Permissions:", self.permissions_group)
        
        # Enabled field
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(not command or command.enabled)
        form_layout.addRow("", self.enabled_check)
        
        # Add form to layout
        layout.addLayout(form_layout)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_form_data(self) -> dict:
        """Get form data as a dictionary.
        
        Returns:
            Form data dictionary
        """
        # Get permissions
        permissions = set()
        if self.broadcaster_check.isChecked():
            permissions.add("broadcaster")
        if self.mod_check.isChecked():
            permissions.add("mod")
        if self.vip_check.isChecked():
            permissions.add("vip")
        if self.sub_check.isChecked():
            permissions.add("sub")
        
        # Get aliases
        aliases_text = self.aliases_input.text().strip()
        aliases = [alias.strip() for alias in aliases_text.split(",")] if aliases_text else []
        
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "aliases": aliases,
            "cooldown": self.cooldown_input.value(),
            "user_cooldown": self.user_cooldown_input.value(),
            "permissions": permissions,
            "enabled": self.enabled_check.isChecked()
        }
    
    @staticmethod
    def get_command_data(parent=None, command=None, edit_mode=False) -> Optional[dict]:
        """Static method to show the dialog and get command data.
        
        Args:
            parent: Parent widget
            command: Command to edit, or None for a new command
            edit_mode: Whether the dialog is in edit mode
            
        Returns:
            Command data dictionary or None if canceled
        """
        dialog = CommandDialog(parent, command, edit_mode)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            return dialog.get_form_data()
        
        return None


class CommandsTab(QWidget):
    """Tab for managing custom chat commands."""
    
    command_updated = pyqtSignal(str, bool)  # Command name, added/removed
    
    def __init__(self, parent=None):
        """Initialize commands tab.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.initUI()
        
        # Refresh command list on init
        self.refresh_commands()
        
        # Set up auto-refresh timer (every 5 seconds)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_commands)
        self.refresh_timer.start(5000)
    
    def initUI(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Prefix input
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("Command Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setText(command_registry.prefix)
        self.prefix_input.setMaximumWidth(50)
        self.prefix_input.textChanged.connect(self.on_prefix_changed)
        prefix_layout.addWidget(self.prefix_input)
        prefix_layout.addStretch()
        
        header_layout.addLayout(prefix_layout)
        header_layout.addStretch()
        
        # Add button
        self.add_btn = QPushButton("Add Command")
        self.add_btn.clicked.connect(self.on_add_command)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # Commands table
        self.commands_table = QTableWidget(0, 7)
        self.commands_table.setHorizontalHeaderLabels([
            "Command", "Description", "Aliases", "Cooldown", "User Cooldown", "Permissions", "Actions"
        ])
        self.commands_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.commands_table.verticalHeader().setVisible(False)
        self.commands_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.commands_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.commands_table)
        
        # Command help
        help_layout = QVBoxLayout()
        help_layout.addWidget(QLabel("<b>Creating Chat Commands</b>"))
        help_text = (
            "Commands can be triggered by viewers typing '!command' in chat. "
            "You can create commands that: <ul>"
            "<li>Display a message</li>"
            "<li>Trigger a workflow</li>"
            "<li>Perform custom actions</li>"
            "</ul>"
            "To use a command in a workflow, create a new workflow with a 'Chat Command' trigger type "
            "and specify the command name."
        )
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_layout.addWidget(help_label)
        layout.addLayout(help_layout)
    
    def refresh_commands(self):
        """Refresh the commands table."""
        # Clear table
        self.commands_table.setRowCount(0)
        
        # Add each command
        for i, command in enumerate(command_registry.commands.values()):
            # Skip duplicates (aliases)
            if command.name != list(command_registry.commands.keys())[list(command_registry.commands.values()).index(command)]:
                continue
            
            self.commands_table.insertRow(i)
            
            # Command name
            name_item = QTableWidgetItem(command.name)
            if not command.enabled:
                name_item.setForeground(Qt.GlobalColor.gray)
            self.commands_table.setItem(i, 0, name_item)
            
            # Description
            self.commands_table.setItem(i, 1, QTableWidgetItem(command.description))
            
            # Aliases
            aliases_text = ", ".join(command.aliases) if command.aliases else ""
            self.commands_table.setItem(i, 2, QTableWidgetItem(aliases_text))
            
            # Cooldown
            cooldown_text = f"{command.cooldown}s" if command.cooldown else "-"
            self.commands_table.setItem(i, 3, QTableWidgetItem(cooldown_text))
            
            # User cooldown
            user_cooldown_text = f"{command.user_cooldown}s" if command.user_cooldown else "-"
            self.commands_table.setItem(i, 4, QTableWidgetItem(user_cooldown_text))
            
            # Permissions
            permissions_text = ", ".join(command.permissions) if command.permissions else "Any"
            self.commands_table.setItem(i, 5, QTableWidgetItem(permissions_text))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setProperty("command_name", command.name)
            edit_btn.clicked.connect(self.on_edit_command)
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setProperty("command_name", command.name)
            delete_btn.clicked.connect(self.on_delete_command)
            actions_layout.addWidget(delete_btn)
            
            self.commands_table.setCellWidget(i, 6, actions_widget)
    
    def on_prefix_changed(self, prefix: str):
        """Handle prefix change.
        
        Args:
            prefix: New prefix
        """
        if not prefix:
            # Don't allow empty prefix
            self.prefix_input.setText(command_registry.prefix)
            return
        
        # Update command registry
        command_registry.set_prefix(prefix)
    
    def on_add_command(self):
        """Handle add command button click."""
        # Show dialog
        command_data = CommandDialog.get_command_data(self)
        
        if not command_data:
            return
        
        # Validate name
        name = command_data["name"]
        if not name:
            QMessageBox.warning(self, "Invalid Command", "Command name cannot be empty.")
            return
        
        # Register command
        success = register_command(
            name=name,
            description=command_data["description"],
            aliases=command_data["aliases"],
            cooldown=command_data["cooldown"],
            user_cooldown=command_data["user_cooldown"],
            permissions=command_data["permissions"],
            enabled=command_data["enabled"]
        )
        
        if success:
            self.refresh_commands()
            self.command_updated.emit(name, True)
        else:
            QMessageBox.warning(
                self, 
                "Command Error", 
                f"Command '{name}' already exists or has invalid parameters."
            )
    
    def on_edit_command(self):
        """Handle edit command button click."""
        # Get command name from sender
        sender = self.sender()
        command_name = sender.property("command_name")
        
        if not command_name:
            return
        
        # Get command
        command = get_command(command_name)
        if not command:
            QMessageBox.warning(self, "Command Error", f"Command '{command_name}' not found.")
            return
        
        # Show dialog
        command_data = CommandDialog.get_command_data(self, command, edit_mode=True)
        
        if not command_data:
            return
        
        # Update command
        # First unregister the old command
        unregister_command(command_name)
        
        # Then register with new data
        success = register_command(
            name=command_data["name"],
            description=command_data["description"],
            aliases=command_data["aliases"],
            cooldown=command_data["cooldown"],
            user_cooldown=command_data["user_cooldown"],
            permissions=command_data["permissions"],
            enabled=command_data["enabled"]
        )
        
        if success:
            self.refresh_commands()
            self.command_updated.emit(command_name, False)
        else:
            QMessageBox.warning(
                self, 
                "Command Error", 
                f"Failed to update command '{command_name}'."
            )
    
    def on_delete_command(self):
        """Handle delete command button click."""
        # Get command name from sender
        sender = self.sender()
        command_name = sender.property("command_name")
        
        if not command_name:
            return
        
        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete command '{command_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        # Unregister command
        success = unregister_command(command_name)
        
        if success:
            self.refresh_commands()
            self.command_updated.emit(command_name, False)
        else:
            QMessageBox.warning(self, "Command Error", f"Failed to delete command '{command_name}'.")
    
    def closeEvent(self, event):
        """Handle close event.
        
        Args:
            event: Close event
        """
        # Stop refresh timer
        self.refresh_timer.stop()
        event.accept() 