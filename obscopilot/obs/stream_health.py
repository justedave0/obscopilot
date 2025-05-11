"""
Stream health monitoring for OBSCopilot.

This module provides tracking and analytics for stream health metrics from OBS.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.obs.client import OBSClient
from obscopilot.storage.database import Database
from obscopilot.storage.repositories import StreamHealthRepository, StreamSessionRepository

logger = logging.getLogger(__name__)


class StreamHealthMonitor:
    """Monitor for OBS stream health metrics."""
    
    def __init__(self, obs_client: OBSClient, database: Database, config: Config):
        """Initialize the stream health monitor.
        
        Args:
            obs_client: OBS client instance
            database: Database instance
            config: Config instance
        """
        self.obs_client = obs_client
        self.database = database
        self.config = config
        self.health_repo = StreamHealthRepository(database)
        self.session_repo = StreamSessionRepository(database)
        
        # Monitoring state
        self.is_monitoring = False
        self.current_session_id = None
        self.stream_start_time = None
        self.monitoring_task = None
        
        # Health thresholds from config
        self.cpu_warning_threshold = self.config.get('stream_health', 'cpu_warning_threshold', 70)
        self.cpu_critical_threshold = self.config.get('stream_health', 'cpu_critical_threshold', 90)
        self.drop_warning_threshold = self.config.get('stream_health', 'drop_warning_threshold', 1)
        self.drop_critical_threshold = self.config.get('stream_health', 'drop_critical_threshold', 5)
        self.monitoring_interval = self.config.get('stream_health', 'monitoring_interval', 15)
        
    async def start(self) -> None:
        """Start the stream health monitor."""
        logger.info("Starting stream health monitor")
        
        # Register event handlers
        event_bus.subscribe(EventType.OBS_STREAM_STARTED, self.handle_stream_started)
        event_bus.subscribe(EventType.OBS_STREAM_STOPPED, self.handle_stream_stopped)
        
    async def stop(self) -> None:
        """Stop the stream health monitor."""
        logger.info("Stopping stream health monitor")
        
        # Stop monitoring if active
        if self.is_monitoring:
            await self.stop_monitoring()
        
        # Unregister event handlers
        event_bus.unsubscribe(EventType.OBS_STREAM_STARTED, self.handle_stream_started)
        event_bus.unsubscribe(EventType.OBS_STREAM_STOPPED, self.handle_stream_stopped)
    
    async def handle_stream_started(self, event: Event) -> None:
        """Handle stream started event.
        
        Args:
            event: Stream started event
        """
        if not event.data:
            return
            
        # Get current stream session
        session_id = event.data.get('session_id')
        if session_id:
            await self.start_monitoring(session_id)
        else:
            logger.warning("Stream started event missing session_id")
    
    async def handle_stream_stopped(self, event: Event) -> None:
        """Handle stream stopped event.
        
        Args:
            event: Stream stopped event
        """
        await self.stop_monitoring()
    
    async def start_monitoring(self, session_id: str) -> None:
        """Start monitoring stream health.
        
        Args:
            session_id: Stream session ID
        """
        if self.is_monitoring:
            logger.warning("Health monitoring already in progress")
            return
            
        logger.info(f"Starting health monitoring for session {session_id}")
        
        self.current_session_id = session_id
        self.stream_start_time = time.time()
        self.is_monitoring = True
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
    async def stop_monitoring(self) -> None:
        """Stop monitoring stream health."""
        if not self.is_monitoring:
            return
            
        logger.info("Stopping health monitoring")
        
        self.is_monitoring = False
        
        # Cancel monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
                
        self.current_session_id = None
        self.stream_start_time = None
    
    async def _monitoring_loop(self) -> None:
        """Background task to periodically check stream health."""
        try:
            while self.is_monitoring and self.current_session_id:
                await self._check_stream_health()
                await asyncio.sleep(self.monitoring_interval)
        except asyncio.CancelledError:
            logger.debug("Stream health monitoring task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in stream health monitoring task: {e}")
            
    async def _check_stream_health(self) -> None:
        """Check current stream health and record it."""
        if not self.obs_client.connected or not self.current_session_id:
            return
            
        try:
            # Get health metrics from OBS
            health_data = await self.obs_client.get_stream_health()
            if not health_data:
                logger.warning("Failed to get stream health data from OBS")
                return
                
            # Store health metrics in database
            record_id = await self.health_repo.create(self.current_session_id, health_data)
            
            # Check for warning/critical conditions
            await self._analyze_health_metrics(health_data)
            
            # Emit event with current health data
            await event_bus.emit(Event(EventType.STREAM_HEALTH_UPDATED, {
                'session_id': self.current_session_id,
                'record_id': record_id,
                'health_data': health_data
            }))
            
        except Exception as e:
            logger.error(f"Error checking stream health: {e}")
    
    async def _analyze_health_metrics(self, health_data: Dict[str, Any]) -> None:
        """Analyze health metrics and emit warning events if needed.
        
        Args:
            health_data: Stream health data
        """
        warnings = []
        
        # Check CPU usage
        cpu_usage = health_data.get('cpu_usage')
        if cpu_usage is not None:
            if cpu_usage >= self.cpu_critical_threshold:
                warnings.append({
                    'type': 'cpu_usage',
                    'level': 'critical',
                    'message': f"CPU usage is critically high: {cpu_usage:.1f}%",
                    'value': cpu_usage
                })
            elif cpu_usage >= self.cpu_warning_threshold:
                warnings.append({
                    'type': 'cpu_usage',
                    'level': 'warning',
                    'message': f"CPU usage is high: {cpu_usage:.1f}%",
                    'value': cpu_usage
                })
        
        # Check dropped frames
        drop_percentage = health_data.get('drop_percentage')
        if drop_percentage is not None:
            if drop_percentage >= self.drop_critical_threshold:
                warnings.append({
                    'type': 'dropped_frames',
                    'level': 'critical',
                    'message': f"Dropped frames critically high: {drop_percentage:.1f}%",
                    'value': drop_percentage
                })
            elif drop_percentage >= self.drop_warning_threshold:
                warnings.append({
                    'type': 'dropped_frames',
                    'level': 'warning',
                    'message': f"Dropped frames: {drop_percentage:.1f}%",
                    'value': drop_percentage
                })
        
        # Emit events for any warnings
        for warning in warnings:
            await event_bus.emit(Event(EventType.STREAM_HEALTH_WARNING, {
                'session_id': self.current_session_id,
                'warning': warning
            }))
    
    async def get_health_history(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get stream health history for a session.
        
        Args:
            session_id: Stream session ID (default: current session)
            limit: Maximum number of records to return
            
        Returns:
            List of stream health records
        """
        session_id = session_id or self.current_session_id
        if not session_id:
            return []
            
        return await self.health_repo.get_by_session(session_id, limit)
    
    async def get_latest_health(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get latest stream health record for a session.
        
        Args:
            session_id: Stream session ID (default: current session)
            
        Returns:
            Latest stream health record or None if not found
        """
        session_id = session_id or self.current_session_id
        if not session_id:
            return None
            
        return await self.health_repo.get_latest_by_session(session_id) 