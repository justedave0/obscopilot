"""
Event system for OBSCopilot.

This module provides a simple event bus for inter-component communication.
Components can emit events and subscribe to events from other components.
"""

import asyncio
import inspect
import logging
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for the event bus."""
    
    # Twitch events
    TWITCH_CONNECTED = auto()
    TWITCH_DISCONNECTED = auto()
    TWITCH_CHAT_MESSAGE = auto()
    TWITCH_FOLLOW = auto()
    TWITCH_SUBSCRIPTION = auto()
    TWITCH_SUBSCRIPTION_GIFT = auto()
    TWITCH_SUBSCRIPTION_END = auto()
    TWITCH_BITS = auto()
    TWITCH_RAID = auto()
    TWITCH_CHANNEL_POINTS_REDEEM = auto()
    TWITCH_STREAM_ONLINE = auto()
    TWITCH_STREAM_OFFLINE = auto()
    TWITCH_AUTH_UPDATED = auto()
    TWITCH_AUTH_REVOKED = auto()
    TWITCH_TOKEN_REFRESHED = auto()
    TWITCH_POLL_BEGIN = auto()
    TWITCH_POLL_PROGRESS = auto()
    TWITCH_POLL_END = auto()
    TWITCH_PREDICTION_BEGIN = auto()
    TWITCH_PREDICTION_PROGRESS = auto()
    TWITCH_PREDICTION_END = auto()
    TWITCH_HYPE_TRAIN_BEGIN = auto()
    TWITCH_HYPE_TRAIN_PROGRESS = auto()
    TWITCH_HYPE_TRAIN_END = auto()
    TWITCH_MOD_ADDED = auto()
    TWITCH_MOD_REMOVED = auto()
    TWITCH_USER_BANNED = auto()
    TWITCH_USER_TIMED_OUT = auto()
    TWITCH_USER_UNBANNED = auto()
    TWITCH_CHARITY_CAMPAIGN_START = auto()
    TWITCH_CHARITY_CAMPAIGN_PROGRESS = auto()
    TWITCH_CHARITY_CAMPAIGN_STOP = auto()
    TWITCH_CHARITY_DONATION = auto()
    
    # OBS events
    OBS_CONNECTED = auto()
    OBS_DISCONNECTED = auto()
    OBS_SCENE_CHANGED = auto()
    OBS_SOURCE_VISIBILITY_CHANGED = auto()
    OBS_STREAMING_STARTED = auto()
    OBS_STREAMING_STOPPED = auto()
    OBS_RECORDING_STARTED = auto()
    OBS_RECORDING_STOPPED = auto()
    
    # Workflow events
    WORKFLOW_LOADED = auto()
    WORKFLOW_STARTED = auto()
    WORKFLOW_COMPLETED = auto()
    WORKFLOW_FAILED = auto()
    
    # AI events
    AI_RESPONSE_GENERATED = auto()
    
    # UI events
    UI_INITIALIZED = auto()
    
    # System events
    SHUTDOWN_REQUESTED = auto()


class Event:
    """Event class for the event bus."""
    
    def __init__(self, event_type: EventType, data: Optional[Any] = None):
        """Initialize a new event.
        
        Args:
            event_type: Type of the event
            data: Event data payload
        """
        self.event_type = event_type
        self.data = data


class EventBus:
    """Event bus for inter-component communication."""
    
    _instance = None
    
    def __new__(cls):
        """Create a new EventBus instance or return the existing one."""
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the event bus."""
        self._subscribers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self._queue = asyncio.Queue()
        self._processing_task = None
        self._running = False
    
    def start(self):
        """Start the event processing loop."""
        if not self._running:
            self._running = True
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event processing loop."""
        if self._running and self._processing_task:
            self._running = False
            await self._queue.put(None)  # Signal to stop
            await self._processing_task
            logger.info("Event bus stopped")
    
    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            event = await self._queue.get()
            
            # Check for stop signal
            if event is None:
                break
                
            try:
                # Get subscribers for this event type
                subscribers = self._subscribers.get(event.event_type, [])
                
                # Process event with all subscribers
                for callback in subscribers:
                    try:
                        # Check if the callback is a coroutine function
                        if inspect.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event.event_type}: {e}")
            except Exception as e:
                logger.error(f"Error processing event {event.event_type}: {e}")
            finally:
                self._queue.task_done()
    
    def subscribe(self, event_type: Union[EventType, List[EventType]], callback: Callable[[Event], Any]) -> None:
        """Subscribe to an event.
        
        Args:
            event_type: Event type or list of event types to subscribe to
            callback: Function to call when the event is emitted
        """
        if isinstance(event_type, list):
            for etype in event_type:
                self._subscribers[etype].append(callback)
                logger.debug(f"Subscribed to {etype}")
        else:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type}")
    
    def unsubscribe(self, event_type: Union[EventType, List[EventType]], callback: Callable[[Event], Any]) -> None:
        """Unsubscribe from an event.
        
        Args:
            event_type: Event type or list of event types to unsubscribe from
            callback: Function to remove from the subscribers
        """
        if isinstance(event_type, list):
            for etype in event_type:
                if callback in self._subscribers[etype]:
                    self._subscribers[etype].remove(callback)
                    logger.debug(f"Unsubscribed from {etype}")
        else:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type}")
    
    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers.
        
        Args:
            event: Event to emit
        """
        await self._queue.put(event)
        logger.debug(f"Emitted event {event.event_type}")
    
    def emit_sync(self, event: Event) -> None:
        """Emit an event synchronously.
        
        This is a convenience method for emitting events from non-async contexts.
        If possible, use the async emit method instead.
        
        Args:
            event: Event to emit
        """
        asyncio.create_task(self.emit(event))
        logger.debug(f"Emitted event synchronously {event.event_type}")


# Global event bus instance
event_bus = EventBus() 