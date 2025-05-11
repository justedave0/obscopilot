"""
Keyboard Shortcuts for OBSCopilot.

This module provides keyboard shortcut management functionality.
"""

import logging
from enum import Enum
from typing import Dict, Optional, Callable

from PyQt6.QtWidgets import QMainWindow, QApplication, QShortcut
from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class ShortcutAction(Enum):
    """Shortcut actions."""
    
    # Application
    EXIT = "exit"
    TOGGLE_THEME = "toggle_theme"
    
    # Workflows
    NEW_WORKFLOW = "new_workflow"
    SAVE_WORKFLOW = "save_workflow"
    
    # Connections
    TOGGLE_TWITCH = "toggle_twitch"
    TOGGLE_OBS = "toggle_obs"
    
    # Streaming
    TOGGLE_STREAMING = "toggle_streaming"
    TOGGLE_RECORDING = "toggle_recording"
    
    # Navigation
    TAB_DASHBOARD = "tab_dashboard"
    TAB_CONNECTIONS = "tab_connections" 
    TAB_WORKFLOWS = "tab_workflows"
    TAB_SETTINGS = "tab_settings"
    
    # Scene control
    SCENE_SELECTOR = "scene_selector"


class ShortcutManager:
    """Manages application keyboard shortcuts."""
    
    def __init__(self, main_window: QMainWindow):
        """Initialize the shortcut manager.
        
        Args:
            main_window: Main application window
        """
        self.main_window = main_window
        self.shortcuts: Dict[ShortcutAction, QShortcut] = {}
        self.default_shortcuts = self._get_default_shortcuts()
        
    def register_shortcuts(self, shortcut_handlers: Dict[ShortcutAction, Callable]):
        """Register shortcuts with their handler functions.
        
        Args:
            shortcut_handlers: Dictionary mapping shortcut actions to handler functions
        """
        for action, handler in shortcut_handlers.items():
            if action in self.default_shortcuts:
                key_sequence = self.default_shortcuts[action]
                shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
                shortcut.activated.connect(handler)
                self.shortcuts[action] = shortcut
                logger.debug(f"Registered shortcut {key_sequence} for {action.value}")
    
    def update_shortcut(self, action: ShortcutAction, key_sequence: str):
        """Update a shortcut key sequence.
        
        Args:
            action: Shortcut action to update
            key_sequence: New key sequence string
        """
        if action in self.shortcuts:
            self.shortcuts[action].setKey(QKeySequence(key_sequence))
            logger.debug(f"Updated shortcut for {action.value} to {key_sequence}")
    
    def get_shortcut_text(self, action: ShortcutAction) -> str:
        """Get the current key sequence for a shortcut as text.
        
        Args:
            action: Shortcut action
            
        Returns:
            String representation of the key sequence
        """
        if action in self.shortcuts:
            return self.shortcuts[action].key().toString()
        elif action in self.default_shortcuts:
            return self.default_shortcuts[action]
        return ""
    
    def _get_default_shortcuts(self) -> Dict[ShortcutAction, str]:
        """Get default shortcut mappings.
        
        Returns:
            Dictionary mapping shortcut actions to key sequences
        """
        return {
            # Application
            ShortcutAction.EXIT: "Ctrl+Q",
            ShortcutAction.TOGGLE_THEME: "Ctrl+T",
            
            # Workflows
            ShortcutAction.NEW_WORKFLOW: "Ctrl+N",
            ShortcutAction.SAVE_WORKFLOW: "Ctrl+S",
            
            # Connections
            ShortcutAction.TOGGLE_TWITCH: "Ctrl+1",
            ShortcutAction.TOGGLE_OBS: "Ctrl+2",
            
            # Streaming
            ShortcutAction.TOGGLE_STREAMING: "F9",
            ShortcutAction.TOGGLE_RECORDING: "F10",
            
            # Navigation
            ShortcutAction.TAB_DASHBOARD: "Alt+1",
            ShortcutAction.TAB_CONNECTIONS: "Alt+2",
            ShortcutAction.TAB_WORKFLOWS: "Alt+3",
            ShortcutAction.TAB_SETTINGS: "Alt+4",
            
            # Scene control
            ShortcutAction.SCENE_SELECTOR: "Ctrl+Space"
        }


def get_shortcut_manager(main_window: QMainWindow) -> ShortcutManager:
    """Get or create the shortcut manager instance.
    
    Args:
        main_window: Main application window
        
    Returns:
        Shortcut manager instance
    """
    if not hasattr(get_shortcut_manager, "instance"):
        get_shortcut_manager.instance = ShortcutManager(main_window)
    return get_shortcut_manager.instance 