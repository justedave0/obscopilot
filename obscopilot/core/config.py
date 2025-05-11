"""
Configuration management for OBSCopilot.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import toml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration manager for OBSCopilot."""
    
    DEFAULT_CONFIG = {
        'general': {
            'theme': 'dark',
            'language': 'en',
            'check_updates': True,
        },
        'twitch': {
            'broadcaster_client_id': '',
            'broadcaster_client_secret': '',
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
        },
        'workflows': {
            'auto_load': True,
            'workflow_dir': '',
        },
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
        # Twitch credentials
        if os.getenv('OBSCOPILOT_BROADCASTER_CLIENT_ID'):
            self.config['twitch']['broadcaster_client_id'] = os.getenv('OBSCOPILOT_BROADCASTER_CLIENT_ID')
            
        if os.getenv('OBSCOPILOT_BROADCASTER_CLIENT_SECRET'):
            self.config['twitch']['broadcaster_client_secret'] = os.getenv('OBSCOPILOT_BROADCASTER_CLIENT_SECRET')
            
        if os.getenv('OBSCOPILOT_BOT_CLIENT_ID'):
            self.config['twitch']['bot_client_id'] = os.getenv('OBSCOPILOT_BOT_CLIENT_ID')
            
        if os.getenv('OBSCOPILOT_BOT_CLIENT_SECRET'):
            self.config['twitch']['bot_client_secret'] = os.getenv('OBSCOPILOT_BOT_CLIENT_SECRET')
        
        # OBS connection
        if os.getenv('OBSCOPILOT_OBS_PASSWORD'):
            self.config['obs']['password'] = os.getenv('OBSCOPILOT_OBS_PASSWORD')
            
        if os.getenv('OBSCOPILOT_OBS_HOST'):
            self.config['obs']['host'] = os.getenv('OBSCOPILOT_OBS_HOST')
            
        if os.getenv('OBSCOPILOT_OBS_PORT'):
            self.config['obs']['port'] = int(os.getenv('OBSCOPILOT_OBS_PORT'))
        
        # OpenAI
        if os.getenv('OPENAI_API_KEY'):
            self.config['openai']['api_key'] = os.getenv('OPENAI_API_KEY') 