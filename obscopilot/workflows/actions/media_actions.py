"""
Media actions for the workflow engine.

This module implements media-related workflow actions.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from obscopilot.workflows.models import WorkflowAction, WorkflowContext
from obscopilot.workflows.actions.base import BaseAction, TemplateableMixin, RetryableMixin

logger = logging.getLogger(__name__)


class BaseMediaAction(BaseAction, TemplateableMixin):
    """Base class for media actions."""
    pass


class PlaySoundAction(BaseMediaAction, RetryableMixin):
    """Action to play a sound."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> bool:
        """Play a sound file.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            True if sound was played, False otherwise
        """
        try:
            config = action.config
            
            # Get sound file path
            sound_path = cls.resolve_template(config.get("sound_path", ""), context)
            if not sound_path:
                logger.warning("No sound file path provided")
                return False
                
            # Resolve to absolute path if not already
            if not os.path.isabs(sound_path):
                # Check if media directory is defined in config
                media_dir = kwargs.get("config", {}).get("media", {}).get("directory", "")
                if media_dir:
                    sound_path = os.path.join(media_dir, sound_path)
                
            # Check if file exists
            if not os.path.exists(sound_path):
                logger.warning(f"Sound file not found: {sound_path}")
                return False
                
            # Get volume (0.0 to 1.0)
            volume = float(config.get("volume", 1.0))
            
            # Check if we should wait for completion
            wait_for_completion = config.get("wait_for_completion", True)
            
            # Get looping config
            loop = config.get("loop", False)
            loop_count = int(config.get("loop_count", 1)) if not loop else -1
            
            logger.info(f"Playing sound: {sound_path} (volume: {volume}, loop: {loop})")
            
            # Platform-specific sound playing
            try:
                # Try to use platform-specific sound playing
                if os.name == 'posix':  # Linux/Mac
                    await cls._play_sound_posix(sound_path, volume, wait_for_completion, loop_count)
                else:  # Windows
                    await cls._play_sound_windows(sound_path, volume, wait_for_completion, loop_count)
                    
                return True
            except Exception as e:
                logger.error(f"Error playing sound: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error in PlaySoundAction: {e}")
            return False
    
    @staticmethod
    async def _play_sound_windows(sound_path: str, volume: float, wait: bool, loop_count: int) -> None:
        """Play sound on Windows.
        
        Args:
            sound_path: Path to sound file
            volume: Volume level (0.0 to 1.0)
            wait: Whether to wait for completion
            loop_count: Number of times to loop (-1 for infinite)
        """
        try:
            import winsound
            
            # Windows can only play WAV files with winsound
            if sound_path.lower().endswith('.wav'):
                flags = winsound.SND_FILENAME
                if not wait:
                    flags |= winsound.SND_ASYNC
                if loop_count < 0:
                    flags |= winsound.SND_LOOP
                
                # Volume control not supported in winsound
                
                if asyncio.iscoroutinefunction(winsound.PlaySound):
                    await winsound.PlaySound(sound_path, flags)
                else:
                    # Run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, lambda: winsound.PlaySound(sound_path, flags)
                    )
            else:
                # For non-WAV files, try to use alternative methods
                await cls._play_sound_alternative(sound_path, volume, wait, loop_count)
        except ImportError:
            # Fall back to alternative method
            await cls._play_sound_alternative(sound_path, volume, wait, loop_count)
    
    @staticmethod
    async def _play_sound_posix(sound_path: str, volume: float, wait: bool, loop_count: int) -> None:
        """Play sound on Linux/Mac.
        
        Args:
            sound_path: Path to sound file
            volume: Volume level (0.0 to 1.0)
            wait: Whether to wait for completion
            loop_count: Number of times to loop (-1 for infinite)
        """
        try:
            # Check if pygame is available
            import pygame
            
            pygame.mixer.init()
            sound = pygame.mixer.Sound(sound_path)
            sound.set_volume(volume)
            
            if loop_count < 0:
                sound.play(loops=-1)
            else:
                sound.play(loops=loop_count-1)
                
            if wait:
                # Wait for sound to finish
                await asyncio.sleep(sound.get_length() * max(1, loop_count))
        except ImportError:
            # Fall back to alternative method
            await cls._play_sound_alternative(sound_path, volume, wait, loop_count)
    
    @staticmethod
    async def _play_sound_alternative(sound_path: str, volume: float, wait: bool, loop_count: int) -> None:
        """Alternative sound playing method.
        
        Args:
            sound_path: Path to sound file
            volume: Volume level (0.0 to 1.0)
            wait: Whether to wait for completion
            loop_count: Number of times to loop (-1 for infinite)
        """
        # Try to use command-line tools
        if os.name == 'posix':
            # On Linux/Mac, try to use aplay or afplay
            if os.path.exists('/usr/bin/aplay'):  # Linux
                cmd = f"aplay -q {sound_path}"
            elif os.path.exists('/usr/bin/afplay'):  # Mac
                cmd = f"afplay {sound_path}"
            else:
                logger.warning("No suitable audio player found on system")
                return
        else:
            # On Windows, try to use PowerShell
            cmd = f'powershell -c "(New-Object Media.SoundPlayer \'{sound_path}\').PlaySync();"'
        
        # Execute the command
        for i in range(max(1, loop_count)):
            if i > 0 and not wait:
                # Don't wait for multiple plays if not waiting
                break
                
            proc = await asyncio.create_subprocess_shell(cmd)
            
            if wait:
                await proc.wait()
            
            if loop_count < 0:  # Infinite loop
                continue
            elif i >= loop_count - 1:
                break
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "sound_path": {
                "type": "string",
                "description": "Path to sound file (absolute or relative to media directory)",
                "required": True
            },
            "volume": {
                "type": "number",
                "description": "Volume level (0.0 to 1.0)",
                "default": 1.0,
                "minimum": 0.0,
                "maximum": 1.0,
                "required": False
            },
            "wait_for_completion": {
                "type": "boolean",
                "description": "Whether to wait for sound to finish before proceeding",
                "default": True,
                "required": False
            },
            "loop": {
                "type": "boolean",
                "description": "Whether to loop the sound",
                "default": False,
                "required": False
            },
            "loop_count": {
                "type": "integer",
                "description": "Number of times to play the sound (ignored if loop is true)",
                "default": 1,
                "minimum": 1,
                "required": False
            }
        }


class ShowImageAction(BaseMediaAction):
    """Action to show an image."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> bool:
        """Show an image.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            True if image was shown, False otherwise
        """
        try:
            config = action.config
            
            # Get image file path
            image_path = cls.resolve_template(config.get("image_path", ""), context)
            if not image_path:
                logger.warning("No image file path provided")
                return False
                
            # Resolve to absolute path if not already
            if not os.path.isabs(image_path):
                # Check if media directory is defined in config
                media_dir = kwargs.get("config", {}).get("media", {}).get("directory", "")
                if media_dir:
                    image_path = os.path.join(media_dir, image_path)
                
            # Check if file exists
            if not os.path.exists(image_path):
                logger.warning(f"Image file not found: {image_path}")
                return False
            
            # Get duration (seconds)
            duration = float(config.get("duration", 5.0))
            
            # Get position (x, y)
            position_x = int(config.get("position_x", 0))
            position_y = int(config.get("position_y", 0))
            
            # Get size (width, height)
            width = int(config.get("width", 0))
            height = int(config.get("height", 0))
            
            logger.info(f"Showing image: {image_path} (duration: {duration}s)")
            
            # Currently, we don't have a UI component to show images
            # This will be implemented when we have a UI system
            # For now, we just log it and return success
            logger.warning("ShowImageAction not implemented yet")
            
            # If duration > 0, wait for that time
            if duration > 0:
                await asyncio.sleep(duration)
                
            return True
        except Exception as e:
            logger.error(f"Error in ShowImageAction: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "image_path": {
                "type": "string",
                "description": "Path to image file (absolute or relative to media directory)",
                "required": True
            },
            "duration": {
                "type": "number",
                "description": "Duration to show the image in seconds (0 for indefinite)",
                "default": 5.0,
                "minimum": 0.0,
                "required": False
            },
            "position_x": {
                "type": "integer",
                "description": "X position of the image (pixels from left)",
                "default": 0,
                "required": False
            },
            "position_y": {
                "type": "integer",
                "description": "Y position of the image (pixels from top)",
                "default": 0,
                "required": False
            },
            "width": {
                "type": "integer",
                "description": "Width of the image (0 for original size)",
                "default": 0,
                "minimum": 0,
                "required": False
            },
            "height": {
                "type": "integer",
                "description": "Height of the image (0 for original size)",
                "default": 0,
                "minimum": 0,
                "required": False
            }
        }


class ShowAlertAction(BaseMediaAction):
    """Action to show an alert on stream."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> bool:
        """Show an alert.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            True if alert was shown, False otherwise
        """
        try:
            config = action.config
            database = kwargs.get("database")
            obs_client = kwargs.get("obs_client")
            
            if not database:
                logger.error("Database not provided for ShowAlertAction")
                return False
                
            if not obs_client:
                logger.error("OBS client not provided for ShowAlertAction")
                return False
            
            # Get alert template by ID or name
            alert_id = config.get("alert_id")
            alert_name = config.get("alert_name")
            
            alert = None
            from obscopilot.storage import AlertRepository
            
            alert_repo = AlertRepository(database)
            
            if alert_id:
                alert = await alert_repo.get_by_id(alert_id)
            elif alert_name:
                alert = await alert_repo.get_by_name(alert_name)
            
            if not alert:
                # Check if we should create a temporary alert from config
                if not config.get("use_inline_config", False):
                    logger.error(f"Alert not found: {alert_id or alert_name}")
                    return False
                
                # Create temporary alert from inline config
                logger.info("Creating temporary alert from inline config")
                alert_data = {
                    'name': 'Temporary Alert',
                    'message': config.get("message", ""),
                    'image_path': config.get("image_path"),
                    'sound_path': config.get("sound_path"),
                    'duration': float(config.get("duration", 5.0)),
                    'font_size': int(config.get("font_size", 24)),
                    'font_color': config.get("font_color", "#FFFFFF"),
                    'background_color': config.get("background_color", "#000000AA"),
                    'text_position': config.get("text_position", "center"),
                    'animation_in': config.get("animation_in", "fade"),
                    'animation_out': config.get("animation_out", "fade"),
                    'source_name': config.get("source_name"),
                    'use_default_source': config.get("use_default_source", True)
                }
                alert = type('Alert', (), alert_data)
            
            # Resolve template variables in message
            message = alert.message
            if message:
                message = cls.resolve_template(message, context)
            
            logger.info(f"Showing alert: {alert.name}")
            
            # Get or create OBS text source
            source_name = alert.source_name
            if not source_name and alert.use_default_source:
                source_name = "OBSCopilot_Alert"
            
            if not source_name:
                logger.error("No source name provided for alert")
                return False
            
            # Check if we should play a sound
            sound_played = False
            if alert.sound_path:
                sound_path = alert.sound_path
                
                # Resolve to absolute path if not already
                if not os.path.isabs(sound_path):
                    # Check if media directory is defined in config
                    media_dir = kwargs.get("config", {}).get("media", {}).get("directory", "")
                    if media_dir:
                        sound_path = os.path.join(media_dir, sound_path)
                
                # Check if file exists
                if os.path.exists(sound_path):
                    # Play sound in background (don't wait)
                    asyncio.create_task(PlaySoundAction._play_sound_windows(
                        sound_path, 1.0, False, 1
                    ))
                    sound_played = True
                else:
                    logger.warning(f"Sound file not found: {sound_path}")
            
            # Create text and image in OBS
            # Use the OBS client to create/update sources
            try:
                # Get or create browser source for the alert
                # This is the most versatile way to show alerts in OBS
                
                # Check if source exists
                source_exists = await obs_client.get_source_settings(source_name)
                scene_name = await obs_client.get_current_scene()
                
                if not source_exists:
                    # Create the source
                    logger.info(f"Creating browser source for alert: {source_name}")
                    
                    # For now, we'll use a text source (simpler)
                    await obs_client.create_text_source(source_name, scene_name)
                
                # Get font settings
                font_settings = {
                    "font": {
                        "face": "Arial",
                        "size": alert.font_size,
                        "style": "Regular"
                    },
                    "color": alert.font_color,
                    "bgcolor": alert.background_color,
                    "align": "center"
                }
                
                # Update the text
                await obs_client.set_source_text(source_name, message, font_settings)
                
                # Show the source
                await obs_client.set_source_visibility(source_name, True, scene_name)
                
                # Wait for the duration
                await asyncio.sleep(alert.duration)
                
                # Hide the source
                await obs_client.set_source_visibility(source_name, False, scene_name)
                
                return True
            except Exception as e:
                logger.error(f"Error showing alert in OBS: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error in ShowAlertAction: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "alert_id": {
                "type": "string",
                "description": "ID of the alert template to use",
                "required": False
            },
            "alert_name": {
                "type": "string",
                "description": "Name of the alert template to use",
                "required": False
            },
            "use_inline_config": {
                "type": "boolean",
                "description": "Whether to use inline configuration instead of a template",
                "default": False,
                "required": False
            },
            "message": {
                "type": "string",
                "description": "Alert message (supports templating with {{ var }})",
                "required": False
            },
            "image_path": {
                "type": "string",
                "description": "Path to image file (absolute or relative to media directory)",
                "required": False
            },
            "sound_path": {
                "type": "string",
                "description": "Path to sound file (absolute or relative to media directory)",
                "required": False
            },
            "duration": {
                "type": "number",
                "description": "Duration to show the alert in seconds",
                "default": 5.0,
                "minimum": 0.1,
                "required": False
            },
            "font_size": {
                "type": "integer",
                "description": "Font size for alert text",
                "default": 24,
                "minimum": 8,
                "required": False
            },
            "font_color": {
                "type": "string",
                "description": "Font color (hex format)",
                "default": "#FFFFFF",
                "required": False
            },
            "background_color": {
                "type": "string",
                "description": "Background color (hex format with alpha)",
                "default": "#000000AA",
                "required": False
            },
            "text_position": {
                "type": "string",
                "description": "Position of the text (top, center, bottom)",
                "default": "center",
                "enum": ["top", "center", "bottom"],
                "required": False
            },
            "animation_in": {
                "type": "string",
                "description": "Animation type for appearance",
                "default": "fade",
                "enum": ["none", "fade", "slide", "bounce"],
                "required": False
            },
            "animation_out": {
                "type": "string",
                "description": "Animation type for disappearance",
                "default": "fade",
                "enum": ["none", "fade", "slide", "bounce"],
                "required": False
            },
            "source_name": {
                "type": "string",
                "description": "OBS source name to use (created if doesn't exist)",
                "required": False
            },
            "use_default_source": {
                "type": "boolean",
                "description": "Whether to use the default source name (OBSCopilot_Alert)",
                "default": True,
                "required": False
            }
        } 