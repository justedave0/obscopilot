"""
OpenAI integration for OBSCopilot.

This module provides integration with the OpenAI API for generating AI responses.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Union

import openai
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageParam

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI API client for generating AI responses."""
    
    def __init__(self, config: Config):
        """Initialize OpenAI client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.event_bus = event_bus
        self.setup_client()
        self.conversation_contexts: Dict[str, List[ChatCompletionMessageParam]] = {}
        
    def setup_client(self) -> None:
        """Set up the OpenAI client with API key and other settings."""
        api_key = self.config.get('openai', 'api_key', '')
        if not api_key:
            logger.warning("OpenAI API key not configured")
            return
            
        try:
            # Initialize the OpenAI client
            openai.api_key = api_key
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Error setting up OpenAI client: {e}")
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_info: Optional[Dict] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Generate an AI response using the OpenAI API.
        
        Args:
            prompt: User prompt to generate a response for
            system_prompt: System prompt to guide the AI behavior
            conversation_id: ID for maintaining conversation context
            user_info: Information about the user to include in the context
            temperature: Temperature for response randomness (0-2)
            max_tokens: Maximum tokens in the response
            
        Returns:
            Generated response text or None on error
        """
        if not openai.api_key:
            logger.error("OpenAI API key not configured, cannot generate response")
            return None
            
        try:
            # Get settings from config if not provided
            model = self.config.get('openai', 'model', 'gpt-3.5-turbo')
            temperature = temperature or self.config.get('openai', 'temperature', 0.7)
            max_tokens = max_tokens or self.config.get('openai', 'max_tokens', 150)
            
            # Get or create conversation context
            messages = self._get_conversation_context(conversation_id)
            
            # Add system prompt if provided
            if system_prompt and not any(m.get('role') == 'system' for m in messages):
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            # Add user information to the prompt if provided
            if user_info:
                formatted_user_info = "\n".join([f"{k}: {v}" for k, v in user_info.items()])
                context_prompt = f"{prompt}\n\nUser Information:\n{formatted_user_info}"
            else:
                context_prompt = prompt
            
            # Add user message to the conversation
            messages.append({"role": "user", "content": context_prompt})
            
            # Generate response
            logger.debug(f"Generating AI response for prompt: {prompt}")
            start_time = time.time()
            
            response = await openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Get the response text
            assistant_message = response.choices[0].message
            response_text = assistant_message.content
            
            # Add assistant response to the conversation context
            messages.append({"role": "assistant", "content": response_text})
            
            # Save the updated conversation context
            self._save_conversation_context(conversation_id, messages)
            
            # Calculate token usage and cost
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            execution_time = time.time() - start_time
            
            logger.info(
                f"Generated AI response in {execution_time:.2f}s "
                f"(tokens: {prompt_tokens}+{completion_tokens}={total_tokens})"
            )
            
            # Emit AI response event
            await self.event_bus.emit(Event(
                EventType.AI_RESPONSE_GENERATED,
                {
                    'prompt': prompt,
                    'response': response_text,
                    'model': model,
                    'tokens': total_tokens,
                    'execution_time': execution_time
                }
            ))
            
            return response_text
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return None
    
    def _get_conversation_context(
        self, 
        conversation_id: Optional[str]
    ) -> List[ChatCompletionMessageParam]:
        """Get the conversation context for a given ID.
        
        Args:
            conversation_id: Conversation ID to get context for
            
        Returns:
            List of messages in the conversation
        """
        if not conversation_id:
            # Return empty context for one-off conversations
            return []
        
        # Get existing context or create new one
        return self.conversation_contexts.get(conversation_id, [])
    
    def _save_conversation_context(
        self, 
        conversation_id: Optional[str], 
        messages: List[ChatCompletionMessageParam]
    ) -> None:
        """Save the conversation context for a given ID.
        
        Args:
            conversation_id: Conversation ID to save context for
            messages: List of messages in the conversation
        """
        if not conversation_id:
            # Don't save context for one-off conversations
            return
        
        # Save the context
        self.conversation_contexts[conversation_id] = messages
        
        # Limit context size to prevent token overflow
        max_context_msgs = self.config.get('openai', 'max_context_messages', 20)
        if len(messages) > max_context_msgs:
            # Keep system message (if any) and truncate oldest messages
            has_system = messages[0].get('role') == 'system'
            start_idx = 1 if has_system else 0
            end_idx = max_context_msgs - (1 if has_system else 0)
            
            if has_system:
                self.conversation_contexts[conversation_id] = [
                    messages[0], 
                    *messages[-(end_idx):]
                ]
            else:
                self.conversation_contexts[conversation_id] = messages[-(end_idx):]
    
    def clear_conversation_context(self, conversation_id: str) -> bool:
        """Clear the conversation context for a given ID.
        
        Args:
            conversation_id: Conversation ID to clear context for
            
        Returns:
            True if context was cleared, False if not found
        """
        if conversation_id not in self.conversation_contexts:
            return False
        
        del self.conversation_contexts[conversation_id]
        return True 