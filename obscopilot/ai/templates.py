"""
Templating system for AI responses.

This module provides functionality for creating and rendering templates for AI responses,
including the ability to incorporate user information.
"""

import logging
from typing import Dict, Any, List, Optional
import re
import json
import jinja2

logger = logging.getLogger(__name__)


class AITemplateManager:
    """Manager for AI response templates."""
    
    def __init__(self):
        """Initialize the template manager."""
        # Initialize Jinja2 environment with safety features
        self.env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=True,
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register custom filters
        self.env.filters['json'] = lambda obj: json.dumps(obj)
        self.env.filters['username'] = self._format_username
        
        # Default templates
        self.default_templates = {
            "follower": "Thanks for the follow, {{ user.display_name }}!",
            "subscriber": ("Thanks for the subscription, {{ user.display_name }}! "
                          "{% if months > 1 %}Welcome back for month {{ months }}!{% else %}Welcome to the community!{% endif %}"),
            "bits": "Thanks for the {{ bits }} bits, {{ user.display_name }}!",
            "raid": "Thanks for the raid with {{ viewers }} viewers, {{ user.display_name }}!",
            "general": "{{ message }}"
        }
        
        # Custom templates loaded from database
        self.custom_templates: Dict[str, str] = {}
    
    def load_templates(self, templates: Dict[str, str]) -> None:
        """Load custom templates from database or config.
        
        Args:
            templates: Dictionary of template_id -> template_text
        """
        self.custom_templates = templates
        logger.info(f"Loaded {len(templates)} custom templates")
    
    def get_template(self, template_id: str) -> Optional[str]:
        """Get a template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template text or None if not found
        """
        # Check custom templates first
        if template_id in self.custom_templates:
            return self.custom_templates[template_id]
        
        # Fall back to default templates
        if template_id in self.default_templates:
            return self.default_templates[template_id]
        
        logger.warning(f"Template '{template_id}' not found")
        return None
    
    def save_template(self, template_id: str, template_text: str) -> None:
        """Save a custom template.
        
        Args:
            template_id: Template identifier
            template_text: Template text
        """
        # Validate template
        try:
            self.env.from_string(template_text)
            self.custom_templates[template_id] = template_text
            logger.info(f"Saved template '{template_id}'")
        except jinja2.exceptions.TemplateSyntaxError as e:
            logger.error(f"Invalid template syntax for '{template_id}': {e}")
            raise ValueError(f"Invalid template syntax: {e}")
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a custom template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            True if template was deleted, False otherwise
        """
        if template_id in self.custom_templates:
            del self.custom_templates[template_id]
            logger.info(f"Deleted template '{template_id}'")
            return True
        return False
    
    def render_template(
        self, 
        template_id: str, 
        context: Dict[str, Any],
        fallback_text: Optional[str] = None
    ) -> str:
        """Render a template with the given context.
        
        Args:
            template_id: Template identifier
            context: Context variables for template rendering
            fallback_text: Fallback text if template not found
            
        Returns:
            Rendered template text
        """
        template_text = self.get_template(template_id)
        
        if not template_text:
            if fallback_text:
                return fallback_text
            return f"Template '{template_id}' not found"
        
        try:
            template = self.env.from_string(template_text)
            return template.render(**context)
        except jinja2.exceptions.UndefinedError as e:
            logger.error(f"Missing context variable in template '{template_id}': {e}")
            if fallback_text:
                return fallback_text
            return f"Error rendering template: {e}"
        except Exception as e:
            logger.error(f"Error rendering template '{template_id}': {e}")
            if fallback_text:
                return fallback_text
            return f"Error rendering template: {e}"
    
    def render_text_with_variables(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> str:
        """Render text with variables from context.
        
        Args:
            text: Text with variable placeholders
            context: Context variables for rendering
            
        Returns:
            Rendered text
        """
        try:
            template = self.env.from_string(text)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering text with variables: {e}")
            return text
    
    def _format_username(self, username: str) -> str:
        """Format a username (custom filter for templates).
        
        Args:
            username: Raw username
            
        Returns:
            Formatted username
        """
        if not username:
            return ""
        
        # Ensure it starts with @ for mentions
        if not username.startswith("@"):
            return f"@{username}"
        
        return username


# Global template manager instance
template_manager = AITemplateManager() 