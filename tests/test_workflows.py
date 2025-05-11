"""
Unit tests for workflow components.

This module contains unit tests for the workflow engine and related components.
"""

import pytest
import json
import uuid
from unittest.mock import MagicMock, patch

from obscopilot.workflows.models import Workflow, Trigger, Action, workflow_from_dict
from obscopilot.workflows.engine import WorkflowEngine


class TestWorkflowModels:
    """Test cases for workflow models."""
    
    def test_workflow_creation(self):
        """Test creating a workflow."""
        # Create workflow
        workflow = Workflow(
            name="Test Workflow",
            description="Test workflow description",
            triggers=[
                Trigger(name="Test Trigger", type="TWITCH_CHAT_MESSAGE")
            ],
            actions=[
                Action(name="Test Action", type="SEND_CHAT_MESSAGE")
            ]
        )
        
        # Check attributes
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Test workflow description"
        assert len(workflow.triggers) == 1
        assert workflow.triggers[0].name == "Test Trigger"
        assert workflow.triggers[0].type == "TWITCH_CHAT_MESSAGE"
        assert len(workflow.actions) == 1
        assert workflow.actions[0].name == "Test Action"
        assert workflow.actions[0].type == "SEND_CHAT_MESSAGE"
        
    def test_workflow_serialization(self):
        """Test serializing a workflow to JSON."""
        # Create workflow
        workflow = Workflow(
            id="test-workflow-id",
            name="Test Workflow",
            description="Test workflow description",
            triggers=[
                Trigger(
                    id="test-trigger-id",
                    name="Test Trigger", 
                    type="TWITCH_CHAT_MESSAGE",
                    config={"pattern": "!hello"}
                )
            ],
            actions=[
                Action(
                    id="test-action-id",
                    name="Test Action", 
                    type="SEND_CHAT_MESSAGE",
                    config={"message": "Hello!"}
                )
            ]
        )
        
        # Serialize to JSON
        workflow_json = workflow.json()
        
        # Parse JSON
        workflow_dict = json.loads(workflow_json)
        
        # Verify serialization
        assert workflow_dict["id"] == "test-workflow-id"
        assert workflow_dict["name"] == "Test Workflow"
        assert workflow_dict["description"] == "Test workflow description"
        assert len(workflow_dict["triggers"]) == 1
        assert workflow_dict["triggers"][0]["id"] == "test-trigger-id"
        assert workflow_dict["triggers"][0]["name"] == "Test Trigger"
        assert workflow_dict["triggers"][0]["type"] == "TWITCH_CHAT_MESSAGE"
        assert workflow_dict["triggers"][0]["config"] == {"pattern": "!hello"}
        assert len(workflow_dict["actions"]) == 1
        assert workflow_dict["actions"][0]["id"] == "test-action-id"
        assert workflow_dict["actions"][0]["name"] == "Test Action"
        assert workflow_dict["actions"][0]["type"] == "SEND_CHAT_MESSAGE"
        assert workflow_dict["actions"][0]["config"] == {"message": "Hello!"}
        
    def test_workflow_deserialization(self):
        """Test deserializing a workflow from JSON."""
        # Create workflow dictionary
        workflow_dict = {
            "id": "test-workflow-id",
            "name": "Test Workflow",
            "description": "Test workflow description",
            "enabled": True,
            "version": "1.0.0",
            "triggers": [
                {
                    "id": "test-trigger-id",
                    "name": "Test Trigger",
                    "type": "TWITCH_CHAT_MESSAGE",
                    "config": {"pattern": "!hello"},
                    "enabled": True
                }
            ],
            "actions": [
                {
                    "id": "test-action-id",
                    "name": "Test Action",
                    "type": "SEND_CHAT_MESSAGE",
                    "config": {"message": "Hello!"},
                    "enabled": True
                }
            ]
        }
        
        # Deserialize from dict
        workflow = workflow_from_dict(workflow_dict)
        
        # Verify deserialization
        assert workflow.id == "test-workflow-id"
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Test workflow description"
        assert workflow.enabled is True
        assert workflow.version == "1.0.0"
        assert len(workflow.triggers) == 1
        assert workflow.triggers[0].id == "test-trigger-id"
        assert workflow.triggers[0].name == "Test Trigger"
        assert workflow.triggers[0].type == "TWITCH_CHAT_MESSAGE"
        assert workflow.triggers[0].config == {"pattern": "!hello"}
        assert workflow.triggers[0].enabled is True
        assert len(workflow.actions) == 1
        assert workflow.actions[0].id == "test-action-id"
        assert workflow.actions[0].name == "Test Action"
        assert workflow.actions[0].type == "SEND_CHAT_MESSAGE"
        assert workflow.actions[0].config == {"message": "Hello!"}
        assert workflow.actions[0].enabled is True


class TestWorkflowEngine:
    """Test cases for workflow engine."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create mock repositories
        self.workflow_repo = MagicMock()
        self.execution_repo = MagicMock()
        
        # Create engine
        self.engine = WorkflowEngine(
            workflow_repo=self.workflow_repo,
            execution_repo=self.execution_repo
        )
        
    def test_register_workflow(self):
        """Test registering a workflow."""
        # Create workflow
        workflow = Workflow(
            name="Test Workflow",
            description="Test workflow description",
            triggers=[
                Trigger(name="Test Trigger", type="TWITCH_CHAT_MESSAGE")
            ],
            actions=[
                Action(name="Test Action", type="SEND_CHAT_MESSAGE")
            ]
        )
        
        # Register workflow
        self.engine.register_workflow(workflow)
        
        # Verify workflow is registered
        assert workflow.id in self.engine.workflows
        assert self.engine.workflows[workflow.id] == workflow
        
    def test_register_multiple_workflows(self):
        """Test registering multiple workflows."""
        # Create workflows
        workflow1 = Workflow(
            id="workflow1",
            name="Test Workflow 1",
            triggers=[Trigger(type="TWITCH_CHAT_MESSAGE")],
            actions=[Action(type="SEND_CHAT_MESSAGE")]
        )
        
        workflow2 = Workflow(
            id="workflow2",
            name="Test Workflow 2",
            triggers=[Trigger(type="TWITCH_FOLLOW")],
            actions=[Action(type="PLAY_SOUND")]
        )
        
        # Register workflows
        self.engine.register_workflow(workflow1)
        self.engine.register_workflow(workflow2)
        
        # Verify workflows are registered
        assert len(self.engine.workflows) == 2
        assert "workflow1" in self.engine.workflows
        assert "workflow2" in self.engine.workflows
        
    def test_unregister_workflow(self):
        """Test unregistering a workflow."""
        # Create and register workflow
        workflow = Workflow(
            id="test-workflow",
            name="Test Workflow",
            triggers=[Trigger(type="TWITCH_CHAT_MESSAGE")],
            actions=[Action(type="SEND_CHAT_MESSAGE")]
        )
        
        self.engine.register_workflow(workflow)
        
        # Verify workflow is registered
        assert "test-workflow" in self.engine.workflows
        
        # Unregister workflow
        self.engine.unregister_workflow("test-workflow")
        
        # Verify workflow is unregistered
        assert "test-workflow" not in self.engine.workflows
        
    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test executing a workflow."""
        # Create workflow
        workflow = Workflow(
            id="test-workflow",
            name="Test Workflow",
            triggers=[
                Trigger(
                    id="test-trigger",
                    type="TWITCH_CHAT_MESSAGE",
                    config={"pattern": "!test"}
                )
            ],
            actions=[
                Action(
                    id="test-action",
                    type="SEND_CHAT_MESSAGE",
                    config={"message": "Test response"}
                )
            ]
        )
        
        # Register workflow
        self.engine.register_workflow(workflow)
        
        # Mock action executor
        mock_executor = MagicMock()
        mock_executor.execute = MagicMock(return_value=True)
        
        # Patch action registry
        with patch('obscopilot.workflows.engine.ACTION_REGISTRY', {
            'SEND_CHAT_MESSAGE': mock_executor
        }):
            # Execute workflow
            result = await self.engine.execute_workflow(
                workflow_id="test-workflow",
                trigger_type="TWITCH_CHAT_MESSAGE",
                trigger_data={"message": "!test", "username": "tester"}
            )
            
            # Verify workflow executed
            assert result is True
            
            # Verify execution was logged
            assert self.execution_repo.create.called
            
            # Verify action was executed
            assert mock_executor.execute.called 