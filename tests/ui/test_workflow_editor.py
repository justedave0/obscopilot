"""
Unit tests for workflow editor UI.

This module contains unit tests for the workflow editor UI component.
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from obscopilot.ui.workflow_editor import WorkflowEditor
from obscopilot.workflows.models import Workflow, Trigger, Action


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
    """Create a mock workflow."""
    return Workflow(
        name="Test Workflow",
        description="Test workflow description",
        triggers=[
            Trigger(name="Test Trigger", type="TWITCH_CHAT_MESSAGE", config={"pattern": "!test"})
        ],
        actions=[
            Action(name="Test Action", type="SEND_CHAT_MESSAGE", config={"message": "Test response"})
        ]
    )


@pytest.fixture
def editor(app, main_window, mock_workflow):
    """Create a workflow editor instance."""
    editor = WorkflowEditor(mock_workflow, main_window)
    main_window.setCentralWidget(editor)
    main_window.show()
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