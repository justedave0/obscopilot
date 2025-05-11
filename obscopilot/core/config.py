"""
Configuration management for OBSCopilot.

This module provides functionality for loading, saving, and managing application configuration.
"""

import os
import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TypeVar, Type, cast

import toml
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar('T')

class Config:
    """Configuration manager for OBSCopilot."""
    
    DEFAULT_CONFIG = {
        'general': {
            'theme': 'dark',
            'language': 'en',
            'check_updates': True,
            'version': '0.1.0',
        },
        'twitch': {
            'broadcaster_client_id': '',
            'broadcaster_client_secret': '',
            'broadcaster_id': '',
            'bot_client_id': '',
            'bot_client_secret': '',
            'redirect_uri': 'http://localhost:17563',
            'scopes': [
                'chat:read', 'chat:edit', 
                'channel:read:redemptions', 'channel:manage:redemptions',
                'channel:read:subscriptions',
                'bits:read',
                'channel:moderate',
                'user:read:follows',
            ],
        },
        'obs': {
            'host': 'localhost',
            'port': 4455,
            'password': '',
            'auto_connect': True,
        },
        'openai': {
            'api_key': '',
            'model': 'gpt-3.5-turbo',
            'temperature': 0.7,
            'max_tokens': 150,
            'max_context_messages': 20,
        },
        'googleai': {
            'api_key': '',
            'model': 'gemini-2.0-flash-001',
            'vision_model': 'gemini-2.0-pro-vision-001',
            'temperature': 0.7,
            'max_tokens': 150,
            'max_context_messages': 20,
        },
        'workflows': {
            'auto_load': True,
            'workflow_dir': '',
        },
        'storage': {
            'database_path': '',
        },
        'ui': {
            'window_width': 1024,
            'window_height': 768,
            'startup_tab': 'dashboard',
        }
    }
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to the configuration file. If None, uses default location.
        """
        self.config_path = Path(config_path) if config_path else Path.home() / '.obscopilot' / 'config.toml'
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load configuration if it exists
        self.load()
        
        # Override with environment variables if they exist
        self._load_from_env()
    
    def load(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                logger.info(f"Loading configuration from {self.config_path}")
                loaded_config = toml.load(self.config_path)
                
                # Update config with loaded values while preserving default structure
                self._deep_update(self.config, loaded_config)
            else:
                logger.info(f"Configuration file {self.config_path} not found, using defaults")
                # Create directory if it doesn't exist
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save default configuration
                self.save()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            logger.info(f"Saving configuration to {self.config_path}")
            
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration to file
            with open(self.config_path, 'w') as f:
                toml.dump(self.config, f)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default if not found
        """
        try:
            return self.config[section][key]
        except KeyError:
            return default
    
    def get_typed(self, section: str, key: str, type_hint: Type[T], default: T = None) -> T:
        """Get a configuration value with type conversion.
        
        Args:
            section: Configuration section
            key: Configuration key
            type_hint: Expected type of the value
            default: Default value if not found or conversion fails
            
        Returns:
            Configuration value converted to the specified type
        """
        value = self.get(section, key, default)
        try:
            if value is None:
                return default
            if type_hint is bool and isinstance(value, str):
                return cast(T, value.lower() in ('true', 'yes', '1', 'y', 'on'))
            if type_hint is int and isinstance(value, str):
                return cast(T, int(value))
            if type_hint is float and isinstance(value, str):
                return cast(T, float(value))
            if type_hint is list and isinstance(value, str):
                return cast(T, json.loads(value))
            if type_hint is dict and isinstance(value, str):
                return cast(T, json.loads(value))
            return cast(T, value)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logger.warning(f"Error converting config value {section}.{key} to {type_hint.__name__}: {e}")
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
    
    def reset_section(self, section: str) -> None:
        """Reset a configuration section to default values.
        
        Args:
            section: Configuration section to reset
        """
        if section in self.DEFAULT_CONFIG:
            self.config[section] = self.DEFAULT_CONFIG[section].copy()
        else:
            logger.warning(f"Cannot reset unknown section: {section}")
    
    def reset_all(self) -> None:
        """Reset all configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()
    
    def get_env_var_name(self, section: str, key: str) -> str:
        """Get the environment variable name for a config option.
        
        Args:
            section: Configuration section
            key: Configuration key
            
        Returns:
            Environment variable name
        """
        return f"OBSCOPILOT_{section.upper()}_{key.upper()}"
    
    def _deep_update(self, target: Dict, source: Dict) -> Dict:
        """Recursively update a dictionary.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
            
        Returns:
            Updated dictionary
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                target[key] = self._deep_update(target[key], value)
            else:
                target[key] = value
        return target
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Check each section and key for corresponding environment variables
        for section, options in self.DEFAULT_CONFIG.items():
            for key in options:
                env_var = self.get_env_var_name(section, key)
                if env_var in os.environ:
                    value = os.environ[env_var]
                    
                    # Handle special types
                    if isinstance(self.config[section][key], bool):
                        value = value.lower() in ('true', 'yes', '1', 'y', 'on')
                    elif isinstance(self.config[section][key], int):
                        value = int(value)
                    elif isinstance(self.config[section][key], float):
                        value = float(value)
                    elif isinstance(self.config[section][key], list):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            value = value.split(',')
                    
                    # Set the value in the config
                    self.config[section][key] = value
                    logger.debug(f"Loaded config from environment: {env_var}")
    
    def export_env_file(self, path: Union[str, Path]) -> None:
        """Export configuration as environment variables to a .env file.
        
        Args:
            path: Path to the .env file
        """
        try:
            path = Path(path)
            with open(path, 'w') as f:
                for section, options in self.config.items():
                    for key, value in options.items():
                        env_var = self.get_env_var_name(section, key)
                        
                        # Handle special types
                        if isinstance(value, list):
                            value = json.dumps(value)
                        elif isinstance(value, dict):
                            value = json.dumps(value)
                        
                        f.write(f"{env_var}={value}\n")
            
            logger.info(f"Exported configuration to {path}")
        except Exception as e:
            logger.error(f"Error exporting configuration to .env file: {e}")
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Get the configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()
    
    def __str__(self) -> str:
        """Get a string representation of the configuration.
        
        Returns:
            String representation of the configuration
        """
        return f"Config(path={self.config_path})" 