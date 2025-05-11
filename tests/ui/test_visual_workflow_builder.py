"""
Tests for the visual workflow builder component.
"""

import pytest
import uuid
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from obscopilot.ui.visual_workflow_builder import (
    VisualWorkflowBuilder, WorkflowNodeItem, TriggerItem, ActionItem
)
from obscopilot.workflows.models import (
    Workflow, WorkflowNode, WorkflowAction, WorkflowTrigger,
    ActionType, TriggerType
)


@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name="Test Workflow",
        description="Test workflow description",
        enabled=True
    )
    
    # Add a trigger
    trigger = WorkflowTrigger(
        id=str(uuid.uuid4()),
        name="Test Trigger",
        type=TriggerType.CHAT_MESSAGE,
        config={"message": "!test"}
    )
    workflow.triggers.append(trigger)
    
    # Add an action node
    action_id = str(uuid.uuid4())
    action = WorkflowAction(
        name="Test Action",
        type=ActionType.CHAT_MESSAGE,
        config={"message": "Test response"}
    )
    
    node = WorkflowNode(
        id=action_id,
        action=action
    )
    
    workflow.nodes[action_id] = node
    workflow.entry_node_id = action_id
    
    return workflow


@pytest.fixture
def builder(qtbot, mock_workflow):
    """Create a visual workflow builder instance."""
    builder = VisualWorkflowBuilder(mock_workflow)
    qtbot.addWidget(builder)
    builder.show()
    return builder


def test_builder_initialization(builder):
    """Test that the builder initializes correctly."""
    # Check that the workflow was loaded
    assert builder.workflow is not None
    assert builder.workflow.name == "Test Workflow"
    
    # Check that the scene has items
    assert len(builder.scene.items()) > 0
    
    # Check for expected item types
    node_items = [item for item in builder.scene.items() 
                  if isinstance(item, WorkflowNodeItem)]
    assert len(node_items) > 0
    
    # Should have at least one trigger and one action
    trigger_items = [item for item in node_items 
                     if isinstance(item, TriggerItem)]
    assert len(trigger_items) > 0
    
    action_items = [item for item in node_items 
                    if isinstance(item, ActionItem)]
    assert len(action_items) > 0


def test_update_workflow_model(builder):
    """Test that workflow model updates correctly."""
    # Initially workflow should match what was passed in
    assert builder.workflow.name == "Test Workflow"
    
    # Change workflow
    builder.workflow.name = "Updated Workflow"
    
    # Update model from visual representation
    builder.update_workflow_model()
    
    # Should have the updated name
    assert builder.workflow.name == "Updated Workflow"
    
    # Should still have the trigger and action
    assert len(builder.workflow.triggers) > 0
    assert len(builder.workflow.nodes) > 0


def test_zoom_controls(builder, qtbot):
    """Test zoom controls."""
    # Get initial transform
    initial_transform = builder.view.transform()
    initial_m11 = initial_transform.m11()  # Horizontal scaling
    
    # Zoom in
    qtbot.mouseClick(builder.findChild(QApplication.focusWidget().__class__, "Zoom In"), Qt.MouseButton.LeftButton)
    
    # Check that view was scaled
    new_transform = builder.view.transform()
    assert new_transform.m11() > initial_m11
    
    # Zoom out
    qtbot.mouseClick(builder.findChild(QApplication.focusWidget().__class__, "Zoom Out"), Qt.MouseButton.LeftButton)
    
    # Should be back to approximately the initial scale
    reset_transform = builder.view.transform()
    assert abs(reset_transform.m11() - initial_m11) < 0.01 