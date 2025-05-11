"""
OpenAI integration for OBSCopilot.

This module provides integration with the OpenAI API for generating AI responses.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Union, Any
import backoff
import aiohttp

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai import APIError, RateLimitError, APIConnectionError, APITimeoutError

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.ai.rate_limiter import rate_limiter

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
        self.client = None
        self.async_client = None
        self.setup_client()
        self.conversation_contexts: Dict[str, List[ChatCompletionMessageParam]] = {}
        
    def setup_client(self) -> None:
        """Set up the OpenAI client with API key and other settings."""
        api_key = self.config.get('openai', 'api_key', '')
        if not api_key:
            logger.warning("OpenAI API key not configured")
            return
            
        try:
            # Create both sync and async OpenAI clients
            self.client = OpenAI(api_key=api_key)
            self.async_client = AsyncOpenAI(api_key=api_key)
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Error setting up OpenAI client: {e}")
    
    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APITimeoutError),
        max_tries=3,
        factor=2
    )
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
        if not self.async_client:
            logger.error("OpenAI client not initialized, cannot generate response")
            return None
            
        try:
            # Check rate limits before making API call
            allowed, retry_after = rate_limiter.check_rate_limit()
            if not allowed:
                logger.warning(f"Rate limit exceeded, retry after {retry_after:.2f} seconds")
                await asyncio.sleep(retry_after)
                return await self.generate_response(
                    prompt, system_prompt, conversation_id, user_info, temperature, max_tokens
                )
            
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
            
            # Use the async client for better performance
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Get the response text
            assistant_message = response.choices[0].message
            response_text = assistant_message.content
            
            # Add assistant response to the conversation context
            if response_text:
                messages.append({"role": "assistant", "content": response_text})
                
                # Save the updated conversation context
                self._save_conversation_context(conversation_id, messages)
            
            # Calculate token usage and cost
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            execution_time = time.time() - start_time
            
            # Record token usage
            rate_limiter.record_token_usage(prompt_tokens, completion_tokens, model)
            
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
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            await self.event_bus.emit(Event(
                EventType.AI_ERROR,
                {
                    'error': 'rate_limit',
                    'message': str(e),
                    'prompt': prompt
                }
            ))
            # Let backoff handle the retry
            raise
        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            await self.event_bus.emit(Event(
                EventType.AI_ERROR,
                {
                    'error': 'timeout',
                    'message': str(e),
                    'prompt': prompt
                }
            ))
            # Let backoff handle the retry
            raise
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            await self.event_bus.emit(Event(
                EventType.AI_ERROR,
                {
                    'error': 'connection',
                    'message': str(e),
                    'prompt': prompt
                }
            ))
            return None
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            await self.event_bus.emit(Event(
                EventType.AI_ERROR,
                {
                    'error': 'api',
                    'message': str(e),
                    'prompt': prompt
                }
            ))
            return None
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            await self.event_bus.emit(Event(
                EventType.AI_ERROR,
                {
                    'error': 'unknown',
                    'message': str(e),
                    'prompt': prompt
                }
            ))
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
        """Generate a streaming AI response using the OpenAI API.
        
        Args:
            prompt: User prompt to generate a response for
            system_prompt: System prompt to guide the AI behavior
            conversation_id: ID for maintaining conversation context
            user_info: Information about the user to include in the context
            temperature: Temperature for response randomness (0-2)
            max_tokens: Maximum tokens in the response
            callback: Function to call for each chunk of the response
            
        Returns:
            Complete generated response text or None on error
        """
        if not self.async_client:
            logger.error("OpenAI client not initialized, cannot generate response")
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
            
            # Generate streaming response
            logger.debug(f"Generating streaming AI response for prompt: {prompt}")
            start_time = time.time()
            
            full_response = ""
            
            # Start streaming
            stream = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            # Collect response chunks
            async for chunk in stream:
                # Process each chunk
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # Call callback if provided
                    if callback:
                        await callback(content)
            
            # Add final response to conversation context
            if full_response:
                messages.append({"role": "assistant", "content": full_response})
                
                # Save the updated context
                self._save_conversation_context(conversation_id, messages)
            
            execution_time = time.time() - start_time
            logger.info(f"Generated streaming AI response in {execution_time:.2f}s")
            
            # Emit AI response event
            await self.event_bus.emit(Event(
                EventType.AI_RESPONSE_GENERATED,
                {
                    'prompt': prompt,
                    'response': full_response,
                    'model': model,
                    'streaming': True,
                    'execution_time': execution_time
                }
            ))
            
            return full_response
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
        """Analyze an image using the OpenAI Vision API.
        
        Args:
            image_path_or_url: Path to image or URL
            prompt: Prompt describing what to analyze in the image
            is_url: Whether the image_path_or_url is a URL or local path
            max_tokens: Maximum tokens for the response
            
        Returns:
            Analysis text or None on error
        """
        if not self.async_client:
            logger.error("OpenAI client not initialized, cannot analyze image")
            return None
            
        try:
            # Get settings from config if not provided
            model = self.config.get('openai', 'vision_model', 'gpt-4o')
            max_tokens = max_tokens or self.config.get('openai', 'max_tokens', 300)
            
            # Prepare the image source
            if is_url:
                image_source = image_path_or_url
            else:
                # For local files, read and base64 encode
                import base64
                with open(image_path_or_url, "rb") as image_file:
                    image_source = f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"
            
            # Create the message content
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_source}}
            ]
            
            # Make the API call
            logger.debug(f"Analyzing image with prompt: {prompt}")
            start_time = time.time()
            
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": content}
                ],
                max_tokens=max_tokens
            )
            
            # Extract response
            analysis_text = response.choices[0].message.content
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
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return None
    
    def _get_conversation_context(
        self, 
        conversation_id: Optional[str]
    ) -> List[Dict[str, Any]]:
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
        messages: List[Dict[str, Any]]
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