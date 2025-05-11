"""
Google AI integration for OBSCopilot.

This module provides integration with the Google Generative AI API (Gemini models).
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Union, Any

from google import genai
from google.genai import types
from google.genai import errors

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class GoogleAIClient:
    """Google AI client for generating AI responses using Gemini models."""
    
    def __init__(self, config: Config):
        """Initialize Google AI client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.event_bus = event_bus
        self.client = None
        self.setup_client()
        self.conversation_contexts: Dict[str, List[Dict[str, Any]]] = {}
        
    def setup_client(self) -> None:
        """Set up the Google AI client with API key and other settings."""
        api_key = self.config.get('googleai', 'api_key', '')
        if not api_key:
            logger.warning("Google AI API key not configured")
            return
            
        try:
            # Initialize the Google AI client
            self.client = genai.Client(api_key=api_key)
            logger.info("Google AI client initialized")
        except Exception as e:
            logger.error(f"Error setting up Google AI client: {e}")
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_info: Optional[Dict] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Generate an AI response using the Google AI API.
        
        Args:
            prompt: User prompt to generate a response for
            system_prompt: System prompt to guide the AI behavior
            conversation_id: ID for maintaining conversation context
            user_info: Information about the user to include in the context
            temperature: Temperature for response randomness (0-1)
            max_tokens: Maximum tokens in the response
            
        Returns:
            Generated response text or None on error
        """
        if not self.client:
            logger.error("Google AI client not initialized, cannot generate response")
            return None
            
        try:
            # Get settings from config if not provided
            model = self.config.get('googleai', 'model', 'gemini-2.0-flash-001')
            temperature = temperature or self.config.get('googleai', 'temperature', 0.7)
            max_tokens = max_tokens or self.config.get('googleai', 'max_tokens', 150)
            
            # Add user information to the prompt if provided
            if user_info:
                formatted_user_info = "\n".join([f"{k}: {v}" for k, v in user_info.items()])
                context_prompt = f"{prompt}\n\nUser Information:\n{formatted_user_info}"
            else:
                context_prompt = prompt
            
            # Generate response
            logger.debug(f"Generating AI response for prompt: {prompt}")
            start_time = time.time()
            
            # Define content generation config
            generation_config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Add system instruction if provided
            if system_prompt:
                generation_config.system_instruction = system_prompt
            
            if conversation_id and conversation_id in self.conversation_contexts:
                # Continue an existing conversation
                chat = self.client.chats.create(model=model)
                
                # Load previous messages into the chat
                for msg in self.conversation_contexts[conversation_id]:
                    if msg['role'] == 'user':
                        chat.history.append(types.Content(
                            role='user',
                            parts=[types.Part.from_text(text=msg['content'])]
                        ))
                    elif msg['role'] == 'assistant':
                        chat.history.append(types.Content(
                            role='model',
                            parts=[types.Part.from_text(text=msg['content'])]
                        ))
                
                # Send the message and get response
                response = chat.send_message(
                    context_prompt,
                    generation_config=generation_config
                )
                response_text = response.text
                
                # Update conversation context
                self.conversation_contexts[conversation_id].append({
                    'role': 'user',
                    'content': context_prompt
                })
                self.conversation_contexts[conversation_id].append({
                    'role': 'assistant',
                    'content': response_text
                })
                
                # Limit context size
                self._limit_conversation_context(conversation_id)
            else:
                # Generate response for one-off request
                response = self.client.models.generate_content(
                    model=model,
                    contents=context_prompt,
                    config=generation_config
                )
                response_text = response.text
                
                # Create new conversation context if conversation_id provided
                if conversation_id:
                    self.conversation_contexts[conversation_id] = [
                        {'role': 'user', 'content': context_prompt},
                        {'role': 'assistant', 'content': response_text}
                    ]
            
            # Calculate token usage (estimate since Gemini doesn't provide token metrics directly)
            execution_time = time.time() - start_time
            
            logger.info(f"Generated AI response in {execution_time:.2f}s")
            
            # Emit AI response event
            await self.event_bus.emit(Event(
                EventType.AI_RESPONSE_GENERATED,
                {
                    'prompt': prompt,
                    'response': response_text,
                    'model': model,
                    'execution_time': execution_time
                }
            ))
            
            return response_text
        except errors.APIError as e:
            logger.error(f"Google AI API error: {e.code} - {e.message}")
            return None
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return None
    
    async def generate_streaming_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_info: Optional[Dict] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        callback: Optional[callable] = None
    ) -> Optional[str]:
        """Generate a streaming AI response using the Google AI API.
        
        Args:
            prompt: User prompt to generate a response for
            system_prompt: System prompt to guide the AI behavior
            conversation_id: ID for maintaining conversation context
            user_info: Information about the user to include in the context
            temperature: Temperature for response randomness (0-1)
            max_tokens: Maximum tokens in the response
            callback: Function to call for each chunk of the response
            
        Returns:
            Complete generated response text or None on error
        """
        if not self.client:
            logger.error("Google AI client not initialized, cannot generate response")
            return None
            
        try:
            # Get settings from config if not provided
            model = self.config.get('googleai', 'model', 'gemini-2.0-flash-001')
            temperature = temperature or self.config.get('googleai', 'temperature', 0.7)
            max_tokens = max_tokens or self.config.get('googleai', 'max_tokens', 150)
            
            # Add user information to the prompt if provided
            if user_info:
                formatted_user_info = "\n".join([f"{k}: {v}" for k, v in user_info.items()])
                context_prompt = f"{prompt}\n\nUser Information:\n{formatted_user_info}"
            else:
                context_prompt = prompt
            
            # Generate streaming response
            logger.debug(f"Generating streaming AI response for prompt: {prompt}")
            start_time = time.time()
            
            # Define content generation config
            generation_config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Add system instruction if provided
            if system_prompt:
                generation_config.system_instruction = system_prompt
            
            full_response = ""
            
            if conversation_id and conversation_id in self.conversation_contexts:
                # Continue an existing conversation
                chat = self.client.chats.create(model=model)
                
                # Load previous messages into the chat
                for msg in self.conversation_contexts[conversation_id]:
                    if msg['role'] == 'user':
                        chat.history.append(types.Content(
                            role='user',
                            parts=[types.Part.from_text(text=msg['content'])]
                        ))
                    elif msg['role'] == 'assistant':
                        chat.history.append(types.Content(
                            role='model',
                            parts=[types.Part.from_text(text=msg['content'])]
                        ))
                
                # Start streaming
                response_stream = chat.send_message_stream(
                    context_prompt,
                    generation_config=generation_config
                )
                
                for chunk in response_stream:
                    chunk_text = chunk.text
                    full_response += chunk_text
                    
                    # Call callback if provided
                    if callback and callable(callback):
                        await callback(chunk_text)
                
                # Update conversation context
                self.conversation_contexts[conversation_id].append({
                    'role': 'user',
                    'content': context_prompt
                })
                self.conversation_contexts[conversation_id].append({
                    'role': 'assistant',
                    'content': full_response
                })
                
                # Limit context size
                self._limit_conversation_context(conversation_id)
            else:
                # Generate streaming response for one-off request
                response_stream = self.client.models.generate_content_stream(
                    model=model,
                    contents=context_prompt,
                    config=generation_config
                )
                
                for chunk in response_stream:
                    chunk_text = chunk.text
                    full_response += chunk_text
                    
                    # Call callback if provided
                    if callback and callable(callback):
                        await callback(chunk_text)
                
                # Create new conversation context if conversation_id provided
                if conversation_id:
                    self.conversation_contexts[conversation_id] = [
                        {'role': 'user', 'content': context_prompt},
                        {'role': 'assistant', 'content': full_response}
                    ]
            
            execution_time = time.time() - start_time
            
            logger.info(f"Generated streaming AI response in {execution_time:.2f}s")
            
            # Emit AI response event
            await self.event_bus.emit(Event(
                EventType.AI_RESPONSE_GENERATED,
                {
                    'prompt': prompt,
                    'response': full_response,
                    'model': model,
                    'execution_time': execution_time
                }
            ))
            
            return full_response
        except errors.APIError as e:
            logger.error(f"Google AI API error: {e.code} - {e.message}")
            return None
        except Exception as e:
            logger.error(f"Error generating streaming AI response: {e}")
            return None
    
    async def analyze_image(
        self,
        image_path_or_url: str,
        prompt: str,
        is_url: bool = False,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Analyze an image using the Google AI multimodal capabilities.
        
        Args:
            image_path_or_url: Path to image or URL
            prompt: Prompt describing what to analyze in the image
            is_url: Whether the image_path_or_url is a URL or local path
            max_tokens: Maximum tokens for the response
            
        Returns:
            Analysis text or None on error
        """
        if not self.client:
            logger.error("Google AI client not initialized, cannot analyze image")
            return None
            
        try:
            # Get settings from config if not provided
            model = self.config.get('googleai', 'vision_model', 'gemini-2.0-pro-vision-001')
            max_tokens = max_tokens or self.config.get('googleai', 'max_tokens', 300)
            
            # Prepare the image source
            if is_url:
                image_data = {'uri': image_path_or_url}
            else:
                # For local files, read and encode
                with open(image_path_or_url, "rb") as image_file:
                    image_data = {'mime_type': 'image/jpeg', 'data': image_file.read()}
            
            # Create the content parts
            contents = [
                {'text': prompt},
                {'inline_data': image_data}
            ]
            
            # Make the API call
            logger.debug(f"Analyzing image with prompt: {prompt}")
            start_time = time.time()
            
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(max_output_tokens=max_tokens)
            )
            
            # Extract response
            analysis_text = response.text
            execution_time = time.time() - start_time
            
            logger.info(f"Analyzed image in {execution_time:.2f}s")
            
            # Emit event
            await self.event_bus.emit(Event(
                EventType.AI_RESPONSE_GENERATED,
                {
                    'prompt': prompt,
                    'response': analysis_text,
                    'model': model,
                    'type': 'vision',
                    'execution_time': execution_time
                }
            ))
            
            return analysis_text
        except errors.APIError as e:
            logger.error(f"Google AI API error: {e.code} - {e.message}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return None
    
    def _limit_conversation_context(self, conversation_id: str) -> None:
        """Limit the conversation context size to prevent token overflow.
        
        Args:
            conversation_id: Conversation ID to limit context for
        """
        if conversation_id not in self.conversation_contexts:
            return
            
        max_context_msgs = self.config.get('googleai', 'max_context_messages', 20)
        messages = self.conversation_contexts[conversation_id]
        
        if len(messages) > max_context_msgs:
            # Keep only the most recent messages
            self.conversation_contexts[conversation_id] = messages[-max_context_msgs:]
    
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