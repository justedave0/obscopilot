"""
Workflow template manager for OBSCopilot.

This module provides functionality for managing workflow templates.
"""

import json
import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

from obscopilot.workflows.models import Workflow, workflow_from_dict

logger = logging.getLogger(__name__)


class WorkflowTemplateManager:
    """Manager for workflow templates."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """Initialize template manager.
        
        Args:
            templates_dir: Directory containing template files (or None for default)
        """
        if templates_dir is None:
            # Use default templates directory
            self.templates_dir = Path(__file__).parent / "templates"
        else:
            self.templates_dir = Path(templates_dir)
        
        self.templates: Dict[str, Dict] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load all templates from the templates directory."""
        try:
            if not self.templates_dir.exists():
                logger.warning(f"Templates directory not found: {self.templates_dir}")
                return
            
            for file_path in self.templates_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        template_data = json.load(f)
                    
                    template_id = file_path.stem
                    self.templates[template_id] = template_data
                    logger.debug(f"Loaded template: {template_id}")
                except Exception as e:
                    logger.error(f"Error loading template {file_path.name}: {e}")
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
    
    def get_template_ids(self) -> List[str]:
        """Get list of available template IDs.
        
        Returns:
            List of template IDs
        """
        return list(self.templates.keys())
    
    def get_template_info(self) -> List[Dict]:
        """Get information about all templates.
        
        Returns:
            List of dictionaries with template information
        """
        return [
            {
                "id": template_id,
                "name": template_data.get("name", "Unnamed Template"),
                "description": template_data.get("description", ""),
                "version": template_data.get("version", "1.0.0")
            }
            for template_id, template_data in self.templates.items()
        ]
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get template data by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template data dictionary or None if not found
        """
        return self.templates.get(template_id)
    
    def create_workflow_from_template(self, template_id: str) -> Optional[Workflow]:
        """Create a workflow instance from a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Workflow instance or None if template not found
        """
        template_data = self.get_template(template_id)
        if template_data is None:
            logger.error(f"Template not found: {template_id}")
            return None
        
        try:
            # Create workflow from template data
            workflow = workflow_from_dict(template_data)
            return workflow
        except Exception as e:
            logger.error(f"Error creating workflow from template {template_id}: {e}")
            return None
    
    def add_template(self, template_id: str, template_data: Dict) -> bool:
        """Add a new template.
        
        Args:
            template_id: Template ID
            template_data: Template data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate template data
            required_fields = ["name", "triggers", "actions"]
            for field in required_fields:
                if field not in template_data:
                    logger.error(f"Template is missing required field: {field}")
                    return False
            
            # Save template to file
            file_path = self.templates_dir / f"{template_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(template_data, f, indent=2)
            
            # Add to templates dictionary
            self.templates[template_id] = template_data
            
            return True
        except Exception as e:
            logger.error(f"Error adding template {template_id}: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            True if successful, False otherwise
        """
        if template_id not in self.templates:
            logger.error(f"Template not found: {template_id}")
            return False
        
        try:
            # Delete template file
            file_path = self.templates_dir / f"{template_id}.json"
            if file_path.exists():
                os.remove(file_path)
            
            # Remove from templates dictionary
            del self.templates[template_id]
            
            return True
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {e}")
            return False


# Global template manager instance
_template_manager = None


def get_template_manager(templates_dir: Optional[str] = None) -> WorkflowTemplateManager:
    """Get the global template manager instance.
    
    Args:
        templates_dir: Directory containing template files (or None for default)
        
    Returns:
        Template manager instance
    """
    global _template_manager
    
    if _template_manager is None:
        _template_manager = WorkflowTemplateManager(templates_dir)
    
    return _template_manager 