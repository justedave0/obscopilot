"""
Unit tests for core components.

This module contains unit tests for the core components of OBSCopilot.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from obscopilot.core.events import EventType, Event, event_bus
from obscopilot.core.config import Config


class TestEventBus:
    """Test cases for the event bus."""
    
    def setup_method(self):
        """Set up test environment."""
        self.event_bus = event_bus
        self.event_bus.clear_all_listeners()
        
    @pytest.mark.asyncio
    async def test_emit_event(self):
        """Test emitting an event."""
        # Create mock listener
        listener = MagicMock()
        
        # Register listener
        self.event_bus.add_listener(EventType.TWITCH_CHAT_MESSAGE, listener)
        
        # Create and emit event
        test_event = Event(EventType.TWITCH_CHAT_MESSAGE, {'message': 'Test message'})
        await self.event_bus.emit(test_event)
        
        # Check listener was called
        listener.assert_called_once_with(test_event)
        
    @pytest.mark.asyncio
    async def test_emit_event_with_no_listeners(self):
        """Test emitting an event with no listeners."""
        # Create and emit event (should not raise any exception)
        test_event = Event(EventType.TWITCH_CHAT_MESSAGE, {'message': 'Test message'})
        await self.event_bus.emit(test_event)
        
    def test_add_and_remove_listener(self):
        """Test adding and removing a listener."""
        # Create mock listener
        listener = MagicMock()
        
        # Register listener
        self.event_bus.add_listener(EventType.TWITCH_CHAT_MESSAGE, listener)
        
        # Verify listener is registered
        assert len(self.event_bus.listeners[EventType.TWITCH_CHAT_MESSAGE]) == 1
        
        # Remove listener
        self.event_bus.remove_listener(EventType.TWITCH_CHAT_MESSAGE, listener)
        
        # Verify listener is removed
        assert len(self.event_bus.listeners[EventType.TWITCH_CHAT_MESSAGE]) == 0
        
    def test_clear_listeners(self):
        """Test clearing listeners for an event type."""
        # Create mock listeners
        listener1 = MagicMock()
        listener2 = MagicMock()
        
        # Register listeners
        self.event_bus.add_listener(EventType.TWITCH_CHAT_MESSAGE, listener1)
        self.event_bus.add_listener(EventType.TWITCH_CHAT_MESSAGE, listener2)
        
        # Verify listeners are registered
        assert len(self.event_bus.listeners[EventType.TWITCH_CHAT_MESSAGE]) == 2
        
        # Clear listeners
        self.event_bus.clear_listeners(EventType.TWITCH_CHAT_MESSAGE)
        
        # Verify listeners are cleared
        assert len(self.event_bus.listeners[EventType.TWITCH_CHAT_MESSAGE]) == 0
        
    def test_clear_all_listeners(self):
        """Test clearing all listeners."""
        # Create mock listeners
        listener1 = MagicMock()
        listener2 = MagicMock()
        
        # Register listeners for different events
        self.event_bus.add_listener(EventType.TWITCH_CHAT_MESSAGE, listener1)
        self.event_bus.add_listener(EventType.TWITCH_FOLLOW, listener2)
        
        # Verify listeners are registered
        assert len(self.event_bus.listeners[EventType.TWITCH_CHAT_MESSAGE]) == 1
        assert len(self.event_bus.listeners[EventType.TWITCH_FOLLOW]) == 1
        
        # Clear all listeners
        self.event_bus.clear_all_listeners()
        
        # Verify all listeners are cleared
        assert len(self.event_bus.listeners) == 0


class TestConfig:
    """Test cases for the configuration manager."""
    
    def setup_method(self):
        """Set up test environment."""
        # Use a temporary config file
        self.config = Config('tests/test_config.ini')
        
    def teardown_method(self):
        """Clean up after test."""
        import os
        if os.path.exists('tests/test_config.ini'):
            os.remove('tests/test_config.ini')
        
    def test_get_set_values(self):
        """Test getting and setting config values."""
        # Set values
        self.config.set('test', 'string_value', 'test_string')
        self.config.set('test', 'int_value', '42')
        self.config.set('test', 'bool_value', 'true')
        
        # Get values
        assert self.config.get('test', 'string_value') == 'test_string'
        assert self.config.get('test', 'int_value') == '42'
        assert self.config.get('test', 'bool_value') == 'true'
        
        # Get with default
        assert self.config.get('test', 'non_existent', 'default') == 'default'
        
    def test_get_int(self):
        """Test getting integer values."""
        # Set values
        self.config.set('test', 'int_value', '42')
        self.config.set('test', 'invalid_int', 'not_an_int')
        
        # Get int values
        assert self.config.get_int('test', 'int_value') == 42
        assert self.config.get_int('test', 'invalid_int', 99) == 99
        assert self.config.get_int('test', 'non_existent', 100) == 100
        
    def test_get_bool(self):
        """Test getting boolean values."""
        # Set values
        self.config.set('test', 'bool_true', 'true')
        self.config.set('test', 'bool_yes', 'yes')
        self.config.set('test', 'bool_false', 'false')
        self.config.set('test', 'bool_no', 'no')
        self.config.set('test', 'invalid_bool', 'not_a_bool')
        
        # Get bool values
        assert self.config.get_bool('test', 'bool_true') is True
        assert self.config.get_bool('test', 'bool_yes') is True
        assert self.config.get_bool('test', 'bool_false') is False
        assert self.config.get_bool('test', 'bool_no') is False
        assert self.config.get_bool('test', 'invalid_bool', True) is True
        assert self.config.get_bool('test', 'non_existent', False) is False
        
    def test_get_float(self):
        """Test getting float values."""
        # Set values
        self.config.set('test', 'float_value', '3.14')
        self.config.set('test', 'invalid_float', 'not_a_float')
        
        # Get float values
        assert self.config.get_float('test', 'float_value') == 3.14
        assert self.config.get_float('test', 'invalid_float', 2.71) == 2.71
        assert self.config.get_float('test', 'non_existent', 1.23) == 1.23
        
    def test_save_and_load(self):
        """Test saving and loading config values."""
        # Set values
        self.config.set('test', 'string_value', 'test_string')
        self.config.set('test', 'int_value', '42')
        
        # Save config
        self.config.save()
        
        # Create new config instance to load from file
        new_config = Config('tests/test_config.ini')
        
        # Check values are loaded
        assert new_config.get('test', 'string_value') == 'test_string'
        assert new_config.get('test', 'int_value') == '42' 