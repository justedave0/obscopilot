"""
AI actions for the workflow engine.

This module implements AI-related workflow actions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from obscopilot.workflows.models import WorkflowAction, WorkflowContext
from obscopilot.workflows.actions.base import BaseAction, TemplateableMixin
from obscopilot.ai.openai import OpenAIClient

logger = logging.getLogger(__name__)


class BaseAiAction(BaseAction, TemplateableMixin):
    """Base class for AI actions."""
    pass


class AiGenerateResponseAction(BaseAiAction):
    """Action to generate a response using AI."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> Optional[str]:
        """Generate a response using AI.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            **kwargs: Additional dependencies, should include 'openai_client'
            
        Returns:
            Generated response or None on error
        """
        try:
            config = action.config
            openai_client = kwargs.get("openai_client")
            
            if not openai_client or not isinstance(openai_client, OpenAIClient):
                logger.error("OpenAI client not provided or invalid")
                return None
            
            # Get prompt
            prompt = cls.resolve_template(config.get("prompt", ""), context)
            if not prompt:
                logger.warning("No prompt provided")
                return None
            
            # Get system message
            system_message = cls.resolve_template(config.get("system_message", ""), context)
            
            # Get model
            model = config.get("model", "gpt-3.5-turbo")
            
            # Get temperature
            temperature = float(config.get("temperature", 0.7))
            
            # Get max tokens
            max_tokens = int(config.get("max_tokens", 150))
            
            # Generate response
            logger.info(f"Generating AI response with model {model}")
            messages = []
            
            # Add system message if provided
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            # Add chat history if provided and enabled
            if config.get("include_chat_history", False):
                chat_history = context.get_variable("chat_history", [])
                if chat_history and isinstance(chat_history, list):
                    # Insert chat history before the current prompt
                    # but limit to last N messages to avoid token limits
                    history_limit = int(config.get("chat_history_limit", 10))
                    limited_history = chat_history[-history_limit:] if history_limit > 0 else chat_history
                    messages = limited_history + messages
            
            # Get response from AI
            response = await openai_client.generate_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if not response:
                logger.warning("No response generated")
                return None
            
            # Store response in context variables
            context.set_variable("ai_response", response)
            context.set_variable(f"ai_response_{action.id}", response)
            
            # Append to chat history if enabled
            if config.get("update_chat_history", True):
                chat_history = context.get_variable("chat_history", [])
                if not isinstance(chat_history, list):
                    chat_history = []
                
                # Add user message and AI response to history
                chat_history.append({"role": "user", "content": prompt})
                chat_history.append({"role": "assistant", "content": response})
                
                # Update chat history in context
                context.set_variable("chat_history", chat_history)
            
            return response
        except Exception as e:
            logger.error(f"Error in AiGenerateResponseAction: {e}")
            return None
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "prompt": {
                "type": "string",
                "description": "The prompt to send to the AI",
                "required": True
            },
            "system_message": {
                "type": "string",
                "description": "System message to set the AI's behavior",
                "required": False
            },
            "model": {
                "type": "string",
                "description": "AI model to use",
                "default": "gpt-3.5-turbo",
                "required": False
            },
            "temperature": {
                "type": "number",
                "description": "Temperature for response generation (0.0 to 2.0)",
                "default": 0.7,
                "minimum": 0.0,
                "maximum": 2.0,
                "required": False
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens in the response",
                "default": 150,
                "minimum": 1,
                "required": False
            },
            "include_chat_history": {
                "type": "boolean",
                "description": "Whether to include chat history in the prompt",
                "default": False,
                "required": False
            },
            "chat_history_limit": {
                "type": "integer",
                "description": "Maximum number of messages to include from chat history",
                "default": 10,
                "minimum": 0,
                "required": False
            },
            "update_chat_history": {
                "type": "boolean",
                "description": "Whether to update chat history with this interaction",
                "default": True,
                "required": False
            }
        } 