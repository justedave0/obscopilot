"""
End-to-end tests for workflow management UI.

These tests verify the workflow creation, editing, and management functionality.
"""

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAction, QDialog, QMessageBox, QPushButton, QListWidget,
    QLineEdit, QTextEdit, QCheckBox, QApplication
)
from PyQt6.QtTest import QTest

from obscopilot.ui.workflow_editor import WorkflowEditor


def find_menu_action(window, menu_name, action_name):
    """Find a menu action by name."""
    for action in window.menuBar().actions():
        if action.text() == menu_name:
            # Check in top level menu
            menu = action.menu()
            for sub_action in menu.actions():
                if sub_action.text() == action_name:
                    return sub_action
                
                # Check submenus
                if sub_action.menu():
                    for sub_sub_action in sub_action.menu().actions():
                        if sub_sub_action.text() == action_name:
                            return sub_sub_action
    return None


def test_create_new_workflow(main_window, qtbot, monkeypatch):
    """Test creating a new workflow."""
    # Find the Workflow menu and New Workflow action
    new_workflow_action = find_menu_action(main_window, "Workflows", "New Workflow")
    assert new_workflow_action is not None
    
    # Mock the QMessageBox.question to auto-accept
    def mock_question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes
    
    monkeypatch.setattr(QMessageBox, "question", mock_question)
    
    # Mock the save workflow function
    def mock_save_workflow(workflow):
        assert workflow.name == "Test E2E Workflow"
        assert workflow.description == "Test workflow description for E2E testing"
        assert workflow.enabled is True
        
    # Click on New Workflow action
    def handle_workflow_editor():
        # Set timer to handle workflow editor dialog that will appear
        QTimer.singleShot(100, lambda: handle_editor_dialog(qtbot))
        
        # Trigger the workflow save
        qtbot.wait(100)
        editor = main_window.findChild(WorkflowEditor)
        assert editor is not None
        
        # Monkeypatch the save method
        editor.parent().save_workflow = mock_save_workflow
    
    def handle_editor_dialog(qtbot):
        # This will be called when the editor appears
        editor = main_window.findChild(WorkflowEditor)
        assert editor is not None
        
        # Fill in workflow details
        qtbot.keyClicks(editor.name_edit, "Test E2E Workflow")
        editor.description_edit.setText("Test workflow description for E2E testing")
        if not editor.enabled_checkbox.isChecked():
            qtbot.mouseClick(editor.enabled_checkbox, Qt.MouseButton.LeftButton)
            
        # Click save button
        save_button = editor.findChild(QPushButton, "save_button")
        if save_button is None:
            save_button = [b for b in editor.findChildren(QPushButton) 
                          if b.text() == "Save"][0]
        qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
    
    # Schedule the handler and click the action
    QTimer.singleShot(50, handle_workflow_editor)
    new_workflow_action.trigger()
    
    # Wait for everything to process
    qtbot.wait(500)


def test_edit_workflow(main_window, qtbot, monkeypatch):
    """Test editing an existing workflow."""
    # We need a workflow first - assume one exists from previous test
    # or create a mock workflow directly
    
    # Find the Workflow menu and Edit Workflow action
    edit_workflow_action = find_menu_action(main_window, "Workflows", "Edit Workflow")
    assert edit_workflow_action is not None
    
    # Mock the QMessageBox.question to auto-accept
    def mock_question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes
    
    monkeypatch.setattr(QMessageBox, "question", mock_question)
    
    # Mock the save workflow function
    def mock_save_workflow(workflow):
        assert workflow.name == "Updated E2E Workflow"
        assert "updated" in workflow.description.lower()
        
    # Click on Edit Workflow action
    def handle_workflow_list():
        # This will be called when the workflow list dialog appears
        list_dialog = [w for w in QApplication.topLevelWidgets() 
                      if isinstance(w, QDialog) and hasattr(w, 'workflow_list')][0]
        assert list_dialog is not None
        
        # Select first workflow and click edit
        workflow_list = list_dialog.workflow_list
        if workflow_list.count() > 0:
            workflow_list.setCurrentRow(0)
            
            # Click edit button
            edit_button = [b for b in list_dialog.findChildren(QPushButton) 
                           if b.text() == "Edit"][0]
            assert edit_button is not None
            
            QTimer.singleShot(100, lambda: handle_editor_dialog(qtbot))
            qtbot.mouseClick(edit_button, Qt.MouseButton.LeftButton)
        else:
            # If no workflows, cancel
            cancel_button = [b for b in list_dialog.findChildren(QPushButton) 
                            if b.text() == "Cancel"][0]
            qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
    
    def handle_editor_dialog(qtbot):
        # This will be called when the editor appears
        editor = main_window.findChild(WorkflowEditor)
        assert editor is not None
        
        # Update workflow details
        editor.name_edit.clear()
        qtbot.keyClicks(editor.name_edit, "Updated E2E Workflow")
        
        current_desc = editor.description_edit.toPlainText()
        editor.description_edit.setText(current_desc + " - updated for E2E test")
            
        # Click save button
        save_button = editor.findChild(QPushButton, "save_button")
        if save_button is None:
            save_button = [b for b in editor.findChildren(QPushButton) 
                          if b.text() == "Save"][0]
        
        # Monkeypatch the save method before clicking
        editor.parent().save_workflow = mock_save_workflow
        qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
    
    # Schedule the handler and click the action
    QTimer.singleShot(50, handle_workflow_list)
    edit_workflow_action.trigger()
    
    # Wait for everything to process
    qtbot.wait(500)


def test_workflow_execution(main_window, qtbot, monkeypatch):
    """Test workflow execution."""
    # This is a simplified test as actual workflow execution
    # would require mocking many dependencies
    
    # Find the Workflow menu and Execute Workflow action
    execute_action = find_menu_action(main_window, "Workflows", "Execute Workflow")
    assert execute_action is not None
    
    # Mock the workflow execution to verify it's called
    was_called = False
    
    def mock_execute(*args, **kwargs):
        nonlocal was_called
        was_called = True
        
    # Override the execute_workflow method
    monkeypatch.setattr(main_window, "execute_workflow", mock_execute)
    
    # Trigger execution
    execute_action.trigger()
    
    # Check that execution was triggered
    assert was_called 