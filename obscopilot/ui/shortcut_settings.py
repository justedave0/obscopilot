"""
Shortcut Settings for OBSCopilot.

This module provides a UI for viewing and customizing keyboard shortcuts.
"""

import logging
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QLineEdit, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QKeyEvent

from obscopilot.ui.shortcuts import ShortcutAction, ShortcutManager

logger = logging.getLogger(__name__)


class KeySequenceEdit(QLineEdit):
    """Line edit for capturing key sequences."""
    
    key_sequence_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize the key sequence edit widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Press keys...")
        
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events.
        
        Args:
            event: Key event
        """
        # Get key sequence
        key = event.key()
        modifiers = event.modifiers()
        
        # Skip modifier-only key presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, 
                  Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
        
        # Create key sequence
        sequence = QKeySequence(key | int(modifiers))
        sequence_text = sequence.toString()
        
        # Update text
        self.setText(sequence_text)
        self.key_sequence_changed.emit(sequence_text)
        
        # Prevent default handling
        event.accept()


class ShortcutDialog(QDialog):
    """Dialog for editing a keyboard shortcut."""
    
    def __init__(self, action: ShortcutAction, current_shortcut: str, parent=None):
        """Initialize the shortcut dialog.
        
        Args:
            action: Shortcut action being edited
            current_shortcut: Current shortcut key sequence
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.action = action
        self.current_shortcut = current_shortcut
        self.new_shortcut = current_shortcut
        
        self.setWindowTitle("Edit Shortcut")
        self.setMinimumWidth(300)
        
        # Initialize UI
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Action name
        action_name = self.action.value.replace('_', ' ').title()
        name_label = QLabel(f"Action: {action_name}")
        layout.addWidget(name_label)
        
        # Current shortcut
        current_label = QLabel(f"Current: {self.current_shortcut}")
        layout.addWidget(current_label)
        
        # New shortcut
        layout.addWidget(QLabel("New Shortcut:"))
        
        self.key_edit = KeySequenceEdit()
        self.key_edit.setText(self.current_shortcut)
        self.key_edit.key_sequence_changed.connect(self._on_key_sequence_changed)
        layout.addWidget(self.key_edit)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def _on_key_sequence_changed(self, sequence_text: str):
        """Handle key sequence changes.
        
        Args:
            sequence_text: New key sequence text
        """
        self.new_shortcut = sequence_text
        
    def get_new_shortcut(self) -> str:
        """Get the new shortcut key sequence.
        
        Returns:
            New key sequence as string
        """
        return self.new_shortcut


class ShortcutSettingsWidget(QWidget):
    """Widget for viewing and customizing keyboard shortcuts."""
    
    def __init__(self, shortcut_manager: ShortcutManager, parent=None):
        """Initialize the shortcut settings widget.
        
        Args:
            shortcut_manager: Shortcut manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.shortcut_manager = shortcut_manager
        
        # Initialize UI
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Keyboard Shortcuts")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Instructions
        instructions = QLabel(
            "You can customize the keyboard shortcuts below.\n"
            "Click on a shortcut to edit it."
        )
        layout.addWidget(instructions)
        
        # Shortcuts table
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(2)
        self.shortcuts_table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.shortcuts_table.verticalHeader().setVisible(False)
        self.shortcuts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.shortcuts_table.cellDoubleClicked.connect(self._on_shortcut_double_clicked)
        
        # Populate shortcuts
        self._populate_shortcuts()
        
        layout.addWidget(self.shortcuts_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_shortcuts)
        button_layout.addWidget(reset_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def _populate_shortcuts(self):
        """Populate the shortcuts table."""
        self.shortcuts_table.setRowCount(0)
        
        # Get all actions
        actions = list(ShortcutAction)
        
        # Sort actions by category and name
        actions.sort(key=lambda a: (a.value.split('_')[0], a.value))
        
        # Add shortcuts to table
        for action in actions:
            row = self.shortcuts_table.rowCount()
            self.shortcuts_table.insertRow(row)
            
            # Action name
            action_name = action.value.replace('_', ' ').title()
            action_item = QTableWidgetItem(action_name)
            action_item.setData(Qt.ItemDataRole.UserRole, action)
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.shortcuts_table.setItem(row, 0, action_item)
            
            # Shortcut key sequence
            shortcut_text = self.shortcut_manager.get_shortcut_text(action)
            shortcut_item = QTableWidgetItem(shortcut_text)
            shortcut_item.setFlags(shortcut_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.shortcuts_table.setItem(row, 1, shortcut_item)
    
    def _on_shortcut_double_clicked(self, row: int, column: int):
        """Handle double-click on shortcut.
        
        Args:
            row: Table row
            column: Table column
        """
        # Get action
        action_item = self.shortcuts_table.item(row, 0)
        if not action_item:
            return
            
        action = action_item.data(Qt.ItemDataRole.UserRole)
        if not action:
            return
            
        # Get current shortcut
        shortcut_item = self.shortcuts_table.item(row, 1)
        if not shortcut_item:
            return
            
        current_shortcut = shortcut_item.text()
        
        # Show edit dialog
        dialog = ShortcutDialog(action, current_shortcut, self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            new_shortcut = dialog.get_new_shortcut()
            
            # Update shortcut
            if new_shortcut != current_shortcut:
                self.shortcut_manager.update_shortcut(action, new_shortcut)
                
                # Update table
                shortcut_item.setText(new_shortcut)
    
    def _reset_shortcuts(self):
        """Reset shortcuts to defaults."""
        # Confirm reset
        confirm = QMessageBox.question(
            self, 
            "Reset Shortcuts",
            "Are you sure you want to reset all shortcuts to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Recreate shortcut manager instance
            self.shortcut_manager = ShortcutManager(self.shortcut_manager.main_window)
            
            # Repopulate table
            self._populate_shortcuts() 