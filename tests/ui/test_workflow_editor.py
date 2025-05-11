"""
Unit tests for workflow editor UI.

This module contains unit tests for the workflow editor UI component.
"""

import pytest
import json
import uuid
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QMessageBox
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from obscopilot.ui.workflow_editor import WorkflowEditor, AddTriggerDialog, AddActionDialog
from obscopilot.workflows.models import Workflow, Trigger, Action
from obscopilot.workflows.registry import TRIGGER_REGISTRY, ACTION_REGISTRY


@pytest.fixture
def app():
    """QApplication fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't call app.quit() as it would close the running app


@pytest.fixture
def main_window():
    """Main window fixture."""
    window = QMainWindow()
    yield window
    window.close()


@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Test Workflow",
        description="Test workflow description",
        enabled=True,
        triggers=[
            Trigger(
                id=str(uuid.uuid4()),
                name="Test Trigger",
                type=list(TRIGGER_REGISTRY.keys())[0],
                config={"message": "!test"}
            )
        ],
        actions=[
            Action(
                id=str(uuid.uuid4()),
                name="Test Action",
                type=list(ACTION_REGISTRY.keys())[0],
                config={"message": "Test response"}
            )
        ]
    )
    return workflow


@pytest.fixture
def editor(qtbot, mock_workflow):
    """Create a workflow editor instance."""
    editor = WorkflowEditor(mock_workflow)
    qtbot.addWidget(editor)
    editor.show()
    return editor


class TestWorkflowEditor:
    """Test cases for workflow editor UI."""
    
    def test_editor_initialization(self, editor, mock_workflow):
        """Test editor initialization with workflow."""
        # Check that workflow data is loaded correctly
        assert editor.name_edit.text() == mock_workflow.name
        assert editor.description_edit.toPlainText() == mock_workflow.description
        assert editor.enabled_checkbox.isChecked() == mock_workflow.enabled
        
    def test_add_trigger(self, editor, monkeypatch):
        """Test adding a trigger."""
        # Count initial number of triggers
        initial_count = editor.triggers_layout.count()
        
        # Mock the add trigger dialog
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = True
        mock_dialog.get_trigger.return_value = Trigger(
            name="New Trigger", 
            type="TWITCH_FOLLOW"
        )
        
        # Patch the dialog
        monkeypatch.setattr(
            'obscopilot.ui.workflow_editor.AddTriggerDialog',
            lambda *args, **kwargs: mock_dialog
        )
        
        # Click add trigger button
        editor.add_trigger_button.click()
        
        # Check that a trigger was added
        assert editor.triggers_layout.count() > initial_count
        
    def test_add_action(self, editor, monkeypatch):
        """Test adding an action."""
        # Count initial number of actions
        initial_count = editor.actions_layout.count()
        
        # Mock the add action dialog
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = True
        mock_dialog.get_action.return_value = Action(
            name="New Action", 
            type="PLAY_SOUND",
            config={"file_path": "sound.mp3"}
        )
        
        # Patch the dialog
        monkeypatch.setattr(
            'obscopilot.ui.workflow_editor.AddActionDialog',
            lambda *args, **kwargs: mock_dialog
        )
        
        # Click add action button
        editor.add_action_button.click()
        
        # Check that an action was added
        assert editor.actions_layout.count() > initial_count
        
    def test_save_workflow(self, editor, mock_workflow):
        """Test saving workflow."""
        # Edit workflow name
        new_name = "Updated Workflow"
        editor.name_edit.setText(new_name)
        
        # Signal spy
        with patch.object(editor, 'workflow_saved') as mock_signal:
            # Click save button
            editor.save_button.click()
            
            # Check signal was emitted with updated workflow
            mock_signal.emit.assert_called_once()
            saved_workflow = mock_signal.emit.call_args[0][0]
            assert saved_workflow.name == new_name 


def test_editor_initialization(editor, mock_workflow):
    """Test that editor initializes correctly."""
    # Check that workflow was loaded
    assert editor.workflow.name == mock_workflow.name
    assert editor.workflow.description == mock_workflow.description
    assert editor.workflow.enabled == mock_workflow.enabled
    
    # Check that UI components were set up
    assert editor.name_edit.text() == mock_workflow.name
    assert editor.description_edit.toPlainText() == mock_workflow.description
    assert editor.enabled_checkbox.isChecked() == mock_workflow.enabled
    
    # Check that tabs exist
    assert editor.editor_tabs.count() == 2
    assert editor.editor_tabs.tabText(0) == "Basic Editor"
    assert editor.editor_tabs.tabText(1) == "Visual Builder"


def test_basic_editor_tabs(editor):
    """Test basic editor tabs."""
    # Get basic editor tab
    basic_editor = editor.basic_editor
    
    # Check that basic editor has tab widget
    assert editor.tab_widget.count() == 2
    assert editor.tab_widget.tabText(0) == "Triggers"
    assert editor.tab_widget.tabText(1) == "Actions"


def test_visual_builder_integration(editor):
    """Test visual builder integration."""
    # Check that visual builder was created
    assert hasattr(editor, 'visual_builder')
    
    # Check that it has the same workflow data
    assert editor.visual_builder.workflow.name == editor.workflow.name
    assert editor.visual_builder.workflow.description == editor.workflow.description
    assert editor.visual_builder.workflow.enabled == editor.workflow.enabled


def test_name_change(editor, qtbot):
    """Test changing workflow name."""
    # Change name
    new_name = "Updated Workflow Name"
    qtbot.keyClicks(editor.name_edit, new_name)
    
    # Check that workflow was updated
    assert editor.workflow.name == new_name
    
    # Check that visual builder was updated
    assert editor.visual_builder.workflow.name == new_name
    
    # Check that save button is enabled
    assert editor.save_button.isEnabled()


def test_description_change(editor, qtbot):
    """Test changing workflow description."""
    # Change description
    new_description = "Updated workflow description"
    editor.description_edit.clear()
    qtbot.keyClicks(editor.description_edit, new_description)
    
    # Check that workflow was updated
    assert editor.workflow.description == new_description
    
    # Check that visual builder was updated
    assert editor.visual_builder.workflow.description == new_description
    
    # Check that save button is enabled
    assert editor.save_button.isEnabled()


def test_enabled_change(editor, qtbot):
    """Test changing workflow enabled state."""
    # Initial state is enabled
    assert editor.workflow.enabled
    
    # Change enabled state
    qtbot.mouseClick(editor.enabled_checkbox, Qt.MouseButton.LeftButton)
    
    # Check that workflow was updated
    assert not editor.workflow.enabled
    
    # Check that visual builder was updated
    assert not editor.visual_builder.workflow.enabled
    
    # Check that save button is enabled
    assert editor.save_button.isEnabled()


def test_add_trigger(monkeypatch, editor, qtbot):
    """Test adding a trigger."""
    # Count initial triggers
    initial_count = len(editor.workflow.triggers)
    
    # Mock AddTriggerDialog.exec to return accepted
    def mock_exec():
        editor.add_trigger_dialog.trigger_type = list(TRIGGER_REGISTRY.keys())[0]
        editor.add_trigger_dialog.trigger_name = "New Test Trigger"
        return QDialog.DialogCode.Accepted
    
    # Apply monkey patch
    monkeypatch.setattr(AddTriggerDialog, "exec", mock_exec)
    
    # Create dialog instance
    editor.add_trigger_dialog = AddTriggerDialog(editor)
    
    # Click add trigger button
    qtbot.mouseClick(editor.add_trigger_button, Qt.MouseButton.LeftButton)
    
    # Check that a trigger was added
    assert len(editor.workflow.triggers) == initial_count + 1
    assert editor.workflow.triggers[-1].name == "New Test Trigger"
    
    # Check that save button is enabled
    assert editor.save_button.isEnabled()


def test_add_action(monkeypatch, editor, qtbot):
    """Test adding an action."""
    # Count initial actions
    initial_count = len(editor.workflow.actions)
    
    # Mock AddActionDialog.exec to return accepted
    def mock_exec():
        editor.add_action_dialog.action_type = list(ACTION_REGISTRY.keys())[0]
        editor.add_action_dialog.action_name = "New Test Action"
        return QDialog.DialogCode.Accepted
    
    # Apply monkey patch
    monkeypatch.setattr(AddActionDialog, "exec", mock_exec)
    
    # Create dialog instance
    editor.add_action_dialog = AddActionDialog(editor)
    
    # Click add action button
    qtbot.mouseClick(editor.add_action_button, Qt.MouseButton.LeftButton)
    
    # Check that an action was added
    assert len(editor.workflow.actions) == initial_count + 1
    assert editor.workflow.actions[-1].name == "New Test Action"
    
    # Check that save button is enabled
    assert editor.save_button.isEnabled()


def test_save_workflow(editor, qtbot, monkeypatch):
    """Test saving workflow."""
    # Track emitted signal
    emitted_workflow = None
    
    def handle_workflow_saved(workflow):
        nonlocal emitted_workflow
        emitted_workflow = workflow
    
    editor.workflow_saved.connect(handle_workflow_saved)
    
    # Make a change
    editor.workflow.name = "Updated Workflow"
    editor.name_edit.setText("Updated Workflow")
    
    # Click save button
    qtbot.mouseClick(editor.save_button, Qt.MouseButton.LeftButton)
    
    # Check that signal was emitted with correct workflow
    assert emitted_workflow is not None
    assert emitted_workflow.name == "Updated Workflow"


def test_cancel_workflow(editor, qtbot, monkeypatch):
    """Test canceling workflow editing."""
    # Track emitted signal
    emitted_workflow = None
    
    def handle_workflow_saved(workflow):
        nonlocal emitted_workflow
        emitted_workflow = workflow
    
    editor.workflow_saved.connect(handle_workflow_saved)
    
    # Make a change
    original_name = editor.workflow.name
    editor.workflow.name = "Updated Workflow"
    editor.name_edit.setText("Updated Workflow")
    
    # Mock QMessageBox.question to return Yes
    def mock_question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes
    
    monkeypatch.setattr(QMessageBox, "question", mock_question)
    
    # Click cancel button
    qtbot.mouseClick(editor.cancel_button, Qt.MouseButton.LeftButton)
    
    # Check that signal was emitted with original workflow
    assert emitted_workflow is not None
    assert emitted_workflow.name == original_name
    assert emitted_workflow == editor.original_workflow


def test_switch_to_visual_builder(editor, qtbot):
    """Test switching to visual builder tab."""
    # Initially on basic editor tab
    assert editor.editor_tabs.currentIndex() == 0
    
    # Switch to visual builder tab
    editor.editor_tabs.setCurrentIndex(1)
    
    # Check that current widget is visual builder
    assert editor.editor_tabs.currentWidget() == editor.visual_builder


def test_visual_builder_update(editor, qtbot):
    """Test that visual builder updates propagate to editor."""
    # Switch to visual builder tab
    editor.editor_tabs.setCurrentIndex(1)
    
    # Update workflow in visual builder
    editor.visual_builder.workflow.name = "Updated from Visual Builder"
    
    # Emit signal
    editor.visual_builder.workflow_updated.emit(editor.visual_builder.workflow)
    
    # Check that editor received update
    assert editor.workflow.name == "Updated from Visual Builder"
    assert editor.name_edit.text() == "Updated from Visual Builder"
    
    # Check that save button is enabled
    assert editor.save_button.isEnabled() 