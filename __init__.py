"""
OBSCopilot - A Python plugin for OBS Studio that integrates Twitch functionality

This package allows streamers to use Twitch integration features directly 
within OBS without needing external tools like Streamer.bot.
"""

__version__ = "0.1.0"
__author__ = "splashxxx"

import logging

# Configure root logger
logger = logging.getLogger("OBSCopilot")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add a handler if none exists
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Import main modules
try:
    from .config import config, EventAction
except ImportError:
    logger.error("Failed to import config module")

try:
    from .obscontrol import (
        connect_to_obs_websocket, 
        set_source_visibility,
        set_text_source_content,
        switch_to_scene,
        get_scenes,
        get_sources_in_scene,
        execute_action
    )
except ImportError:
    logger.error("Failed to import obscontrol module")

try:
    from .twitchintegration import twitch
except ImportError:
    logger.error("Failed to import twitchintegration module") 