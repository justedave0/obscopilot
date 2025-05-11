"""
Unit tests for workflow template manager.

This module contains tests for the workflow template manager.
"""

import pytest
import os
import tempfile
import json
import shutil
from pathlib import Path

from obscopilot.workflows.template_manager import WorkflowTemplateManager
from obscopilot.workflows.models import Workflow


def create_template_file(dir_path, template_id, template_data):
    """Create a template file for testing.
    
    Args:
        dir_path: Directory path
        template_id: Template ID
        template_data: Template data
    """
    file_path = Path(dir_path) / f"{template_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(template_data, f)


class TestTemplateManager:
    """Test cases for template manager."""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create a temporary directory for template files."""
        temp_dir = tempfile.mkdtemp()
        
        # Create test template files
        create_template_file(
            temp_dir,
            "test_template_1",
            {
                "name": "Test Template 1",
                "description": "Test template 1 description",
                "version": "1.0.0",
                "triggers": [
                    {
                        "name": "Test Trigger",
                        "type": "TWITCH_CHAT_MESSAGE",
                        "config": {"pattern": "!test"}
                    }
                ],
                "actions": [
                    {
                        "name": "Test Action",
                        "type": "SEND_CHAT_MESSAGE",
                        "config": {"message": "Test response"}
                    }
                ]
            }
        )
        
        create_template_file(
            temp_dir,
            "test_template_2",
            {
                "name": "Test Template 2",
                "description": "Test template 2 description",
                "version": "1.0.0",
                "triggers": [],
                "actions": []
            }
        )
        
        yield temp_dir
        
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_load_templates(self, temp_templates_dir):
        """Test loading templates from directory."""
        manager = WorkflowTemplateManager(temp_templates_dir)
        
        # Check that templates were loaded
        template_ids = manager.get_template_ids()
        assert len(template_ids) == 2
        assert "test_template_1" in template_ids
        assert "test_template_2" in template_ids
    
    def test_get_template_info(self, temp_templates_dir):
        """Test getting template information."""
        manager = WorkflowTemplateManager(temp_templates_dir)
        
        # Get template info
        template_info = manager.get_template_info()
        
        # Check info contents
        assert len(template_info) == 2
        
        # Find template 1
        template_1 = next((t for t in template_info if t["id"] == "test_template_1"), None)
        assert template_1 is not None
        assert template_1["name"] == "Test Template 1"
        assert template_1["description"] == "Test template 1 description"
        assert template_1["version"] == "1.0.0"
    
    def test_get_template(self, temp_templates_dir):
        """Test getting a template by ID."""
        manager = WorkflowTemplateManager(temp_templates_dir)
        
        # Get template
        template = manager.get_template("test_template_1")
        
        # Check template contents
        assert template is not None
        assert template["name"] == "Test Template 1"
        assert len(template["triggers"]) == 1
        assert len(template["actions"]) == 1
        
        # Get non-existent template
        template = manager.get_template("non_existent")
        assert template is None
    
    def test_create_workflow_from_template(self, temp_templates_dir):
        """Test creating a workflow from a template."""
        manager = WorkflowTemplateManager(temp_templates_dir)
        
        # Create workflow from template
        workflow = manager.create_workflow_from_template("test_template_1")
        
        # Check workflow
        assert isinstance(workflow, Workflow)
        assert workflow.name == "Test Template 1"
        assert workflow.description == "Test template 1 description"
        assert len(workflow.triggers) == 1
        assert len(workflow.actions) == 1
        
        # Check trigger
        assert workflow.triggers[0].name == "Test Trigger"
        assert workflow.triggers[0].type == "TWITCH_CHAT_MESSAGE"
        assert workflow.triggers[0].config["pattern"] == "!test"
        
        # Check action
        assert workflow.actions[0].name == "Test Action"
        assert workflow.actions[0].type == "SEND_CHAT_MESSAGE"
        assert workflow.actions[0].config["message"] == "Test response"
    
    def test_add_template(self, temp_templates_dir):
        """Test adding a new template."""
        manager = WorkflowTemplateManager(temp_templates_dir)
        
        # Template data
        template_data = {
            "name": "New Template",
            "description": "New template description",
            "version": "1.0.0",
            "triggers": [
                {
                    "name": "New Trigger",
                    "type": "TWITCH_FOLLOW",
                    "config": {}
                }
            ],
            "actions": [
                {
                    "name": "New Action",
                    "type": "SEND_CHAT_MESSAGE",
                    "config": {"message": "New template"}
                }
            ]
        }
        
        # Add template
        result = manager.add_template("new_template", template_data)
        assert result is True
        
        # Check that template was added
        template_ids = manager.get_template_ids()
        assert "new_template" in template_ids
        
        # Check file was created
        file_path = Path(temp_templates_dir) / "new_template.json"
        assert file_path.exists()
        
        # Check file contents
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        assert file_data["name"] == "New Template"
    
    def test_delete_template(self, temp_templates_dir):
        """Test deleting a template."""
        manager = WorkflowTemplateManager(temp_templates_dir)
        
        # Delete template
        result = manager.delete_template("test_template_1")
        assert result is True
        
        # Check that template was removed
        template_ids = manager.get_template_ids()
        assert "test_template_1" not in template_ids
        
        # Check file was deleted
        file_path = Path(temp_templates_dir) / "test_template_1.json"
        assert not file_path.exists()
        
        # Try to delete non-existent template
        result = manager.delete_template("non_existent")
        assert result is False 