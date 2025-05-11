"""
Viewer statistics tracking for OBSCopilot.

This module provides tracking and analytics for Twitch viewers.
"""

import asyncio
import datetime
import logging
import time
from typing import Dict, List, Optional, Set, Any

from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.storage.database import Database
from obscopilot.storage.repositories import ViewerRepository, StreamSessionRepository

logger = logging.getLogger(__name__)


class ViewerStatsTracker:
    """Tracker for Twitch viewer statistics."""
    
    def __init__(self, database: Database):
        """Initialize the viewer stats tracker.
        
        Args:
            database: Database instance
        """
        self.database = database
        self.viewer_repo = ViewerRepository(database)
        self.session_repo = StreamSessionRepository(database)
        
        # Current stream tracking
        self.current_session_id: Optional[str] = None
        self.stream_start_time: Optional[float] = None
        self.active_viewers: Set[str] = set()  # User IDs of viewers currently watching
        self.total_unique_viewers: Set[str] = set()  # All unique viewers in this stream
        self.peak_viewer_count: int = 0
        self.is_tracking: bool = False
        
        # Event cache
        self.new_followers: Set[str] = set()
        self.new_subscribers: Set[str] = set()
        self.bits_received: int = 0
        self.message_count: int = 0
        
        # Watch time tracking - format: {user_id: last_active_timestamp}
        self.viewer_activity: Dict[str, float] = {}
        
        # Background tasks
        self.watch_time_task = None
    
    async def start(self) -> None:
        """Start the viewer stats tracker."""
        logger.info("Starting viewer statistics tracker")
        
        # Register event handlers
        event_bus.subscribe(EventType.TWITCH_CHAT_MESSAGE, self.handle_chat_message)
        event_bus.subscribe(EventType.TWITCH_BITS, self.handle_bits)
        event_bus.subscribe(EventType.TWITCH_FOLLOW, self.handle_follow)
        event_bus.subscribe(EventType.TWITCH_SUBSCRIPTION, self.handle_subscription)
        event_bus.subscribe(EventType.TWITCH_STREAM_ONLINE, self.handle_stream_online)
        event_bus.subscribe(EventType.TWITCH_STREAM_OFFLINE, self.handle_stream_offline)
        
        # Start watch time tracking task
        self.watch_time_task = asyncio.create_task(self.update_watch_time())
    
    async def stop(self) -> None:
        """Stop the viewer stats tracker."""
        logger.info("Stopping viewer statistics tracker")
        
        # End current stream session if active
        if self.current_session_id and self.is_tracking:
            await self.end_stream_tracking()
        
        # Cancel background task
        if self.watch_time_task:
            self.watch_time_task.cancel()
            try:
                await self.watch_time_task
            except asyncio.CancelledError:
                pass
        
        # Unregister event handlers
        event_bus.unsubscribe(EventType.TWITCH_CHAT_MESSAGE, self.handle_chat_message)
        event_bus.unsubscribe(EventType.TWITCH_BITS, self.handle_bits)
        event_bus.unsubscribe(EventType.TWITCH_FOLLOW, self.handle_follow)
        event_bus.unsubscribe(EventType.TWITCH_SUBSCRIPTION, self.handle_subscription)
        event_bus.unsubscribe(EventType.TWITCH_STREAM_ONLINE, self.handle_stream_online)
        event_bus.unsubscribe(EventType.TWITCH_STREAM_OFFLINE, self.handle_stream_offline)
    
    async def update_watch_time(self) -> None:
        """Background task to update watch time for active viewers."""
        try:
            while True:
                if self.is_tracking:
                    current_time = time.time()
                    
                    # Update watch time for active viewers (add 30 seconds)
                    for user_id, last_active in list(self.viewer_activity.items()):
                        # Consider a viewer inactive after 5 minutes of no activity
                        if current_time - last_active > 300:
                            # Remove inactive viewers
                            self.viewer_activity.pop(user_id, None)
                            self.active_viewers.discard(user_id)
                            logger.debug(f"Viewer {user_id} marked as inactive")
                        else:
                            # Update watch time (+30 seconds)
                            await self.viewer_repo.update_watch_time(user_id, 30)
                    
                    # Update session stats every 30 seconds
                    await self.update_session_stats()
                
                # Sleep for 30 seconds
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.debug("Watch time tracking task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in watch time tracking task: {e}")
    
    async def handle_chat_message(self, event: Event) -> None:
        """Handle chat message event.
        
        Args:
            event: Chat message event
        """
        if not event.data:
            return
        
        user_id = event.data.get("user_id")
        username = event.data.get("username")
        
        if not user_id or not username:
            return
        
        # Mark viewer as active
        self.active_viewers.add(user_id)
        self.total_unique_viewers.add(user_id)
        self.viewer_activity[user_id] = time.time()
        
        # Update peak viewer count
        if len(self.active_viewers) > self.peak_viewer_count:
            self.peak_viewer_count = len(self.active_viewers)
        
        # Increment message count
        self.message_count += 1
        
        # Update viewer data
        viewer_data = {
            'is_broadcaster': event.data.get("is_broadcaster", False),
            'is_moderator': event.data.get("is_mod", False),
            'is_vip': event.data.get("is_vip", False),
            'is_subscriber': event.data.get("is_sub", False),
        }
        
        # Update or create viewer in database
        await self.viewer_repo.update_or_create(user_id, username, viewer_data)
        
        # Increment message count
        await self.viewer_repo.increment_message_count(user_id)
        
        # Track stream participation if streaming
        if self.is_tracking and self.current_session_id:
            # Mark as participating in this stream
            await self.viewer_repo.increment_streams_watched(
                user_id, 
                self.current_session_id
            )
    
    async def handle_bits(self, event: Event) -> None:
        """Handle bits donation event.
        
        Args:
            event: Bits event
        """
        if not event.data:
            return
        
        user_id = event.data.get("user_id")
        username = event.data.get("user_name")
        bits = event.data.get("bits", 0)
        
        if not user_id or not username or not bits:
            return
        
        # Mark viewer as active
        self.active_viewers.add(user_id)
        self.total_unique_viewers.add(user_id)
        self.viewer_activity[user_id] = time.time()
        
        # Update bits received for current stream
        self.bits_received += bits
        
        # Update viewer data
        viewer_data = {
            'is_subscriber': event.data.get("is_subscriber", False),
        }
        
        # Update or create viewer in database
        await self.viewer_repo.update_or_create(user_id, username, viewer_data)
        
        # Add bits donation
        await self.viewer_repo.add_bits_donated(user_id, bits)
    
    async def handle_follow(self, event: Event) -> None:
        """Handle follow event.
        
        Args:
            event: Follow event
        """
        if not event.data:
            return
        
        user_id = event.data.get("user_id")
        username = event.data.get("user_name")
        
        if not user_id or not username:
            return
        
        # Mark as follower
        viewer_data = {
            'is_follower': True
        }
        
        # Update or create viewer in database
        await self.viewer_repo.update_or_create(user_id, username, viewer_data)
        
        # Track as new follower in current stream
        if self.is_tracking:
            self.new_followers.add(user_id)
    
    async def handle_subscription(self, event: Event) -> None:
        """Handle subscription event.
        
        Args:
            event: Subscription event
        """
        if not event.data:
            return
        
        user_id = event.data.get("user_id")
        username = event.data.get("user_name")
        
        if not user_id or not username:
            return
        
        # Mark as subscriber
        viewer_data = {
            'is_subscriber': True
        }
        
        # Update or create viewer in database
        await self.viewer_repo.update_or_create(user_id, username, viewer_data)
        
        # Track as new subscriber in current stream
        if self.is_tracking:
            self.new_subscribers.add(user_id)
    
    async def handle_stream_online(self, event: Event) -> None:
        """Handle stream online event.
        
        Args:
            event: Stream online event
        """
        if not event.data:
            return
        
        stream_data = {
            'id': event.data.get('stream_id') or event.data.get('id'),
            'title': event.data.get('title'),
            'game_name': event.data.get('game_name')
        }
        
        await self.start_stream_tracking(stream_data)
    
    async def handle_stream_offline(self, event: Event) -> None:
        """Handle stream offline event.
        
        Args:
            event: Stream offline event
        """
        await self.end_stream_tracking()
    
    async def start_stream_tracking(self, stream_data: Optional[Dict[str, Any]] = None) -> None:
        """Start tracking a new stream session.
        
        Args:
            stream_data: Stream data from Twitch API
        """
        if self.is_tracking:
            # Already tracking a stream
            return
        
        logger.info("Starting stream statistics tracking")
        
        # Create new session
        session = await self.session_repo.start_session(stream_data)
        
        # Set tracking state
        self.current_session_id = session.id
        self.stream_start_time = time.time()
        self.active_viewers.clear()
        self.total_unique_viewers.clear()
        self.peak_viewer_count = 0
        self.new_followers.clear()
        self.new_subscribers.clear()
        self.bits_received = 0
        self.message_count = 0
        self.viewer_activity.clear()
        self.is_tracking = True
        
        # Emit event
        await event_bus.emit(Event(
            EventType.WORKFLOW_STARTED,
            data={
                'type': 'viewer_stats_tracking',
                'session_id': session.id
            }
        ))
    
    async def end_stream_tracking(self) -> None:
        """End the current stream tracking session."""
        if not self.is_tracking or not self.current_session_id:
            return
        
        logger.info("Ending stream statistics tracking")
        
        # Update final stats before ending
        await self.update_session_stats()
        
        # End session
        await self.session_repo.end_session(
            self.current_session_id,
            {
                'messages_count': self.message_count,
                'peak_viewers': self.peak_viewer_count,
                'unique_viewers': len(self.total_unique_viewers),
                'new_followers': len(self.new_followers),
                'new_subscribers': len(self.new_subscribers),
                'bits_received': self.bits_received
            }
        )
        
        # Reset tracking state
        session_id = self.current_session_id
        self.current_session_id = None
        self.stream_start_time = None
        self.is_tracking = False
        
        # Clear tracking data
        self.active_viewers.clear()
        self.total_unique_viewers.clear()
        self.viewer_activity.clear()
        
        # Emit event
        await event_bus.emit(Event(
            EventType.WORKFLOW_COMPLETED,
            data={
                'type': 'viewer_stats_tracking',
                'session_id': session_id
            }
        ))
    
    async def update_session_stats(self) -> None:
        """Update the current session statistics."""
        if not self.is_tracking or not self.current_session_id:
            return
        
        # Prepare stats update
        stats = {
            'messages_count': self.message_count,
            'peak_viewers': self.peak_viewer_count,
            'unique_viewers': len(self.total_unique_viewers),
            'new_followers': len(self.new_followers),
            'new_subscribers': len(self.new_subscribers),
            'bits_received': self.bits_received
        }
        
        # Update session
        await self.session_repo.update_session_stats(self.current_session_id, stats)
    
    async def get_current_stats(self) -> Dict[str, Any]:
        """Get current stream statistics.
        
        Returns:
            Dictionary with current stats
        """
        if not self.is_tracking:
            return {
                'is_live': False
            }
        
        # Calculate stream duration
        duration = 0
        if self.stream_start_time:
            duration = int(time.time() - self.stream_start_time)
        
        return {
            'is_live': True,
            'session_id': self.current_session_id,
            'duration': duration,
            'active_viewers': len(self.active_viewers),
            'total_unique_viewers': len(self.total_unique_viewers),
            'peak_viewers': self.peak_viewer_count,
            'message_count': self.message_count,
            'new_followers': len(self.new_followers),
            'new_subscribers': len(self.new_subscribers),
            'bits_received': self.bits_received
        }
    
    async def get_top_chatters(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top chatters.
        
        Args:
            limit: Maximum number of viewers to return
            
        Returns:
            List of top chatters
        """
        chatters = await self.viewer_repo.get_top_chatters(limit)
        return [chatter.to_dict() for chatter in chatters]
    
    async def get_top_donors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top donors.
        
        Args:
            limit: Maximum number of viewers to return
            
        Returns:
            List of top donors
        """
        donors = await self.viewer_repo.get_top_donors(limit)
        return [donor.to_dict() for donor in donors]
    
    async def get_most_loyal_viewers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most loyal viewers.
        
        Args:
            limit: Maximum number of viewers to return
            
        Returns:
            List of most loyal viewers
        """
        viewers = await self.viewer_repo.get_most_loyal_viewers(limit)
        return [viewer.to_dict() for viewer in viewers]
    
    async def get_recent_sessions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent stream sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of recent stream sessions
        """
        sessions = await self.session_repo.get_recent_sessions(limit)
        return [session.to_dict() for session in sessions] 