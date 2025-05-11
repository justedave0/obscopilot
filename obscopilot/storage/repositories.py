"""
Repository classes for database operations.

This module provides repository classes that abstract database operations.
"""

import datetime
import json
import logging
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
import uuid
import time

from sqlalchemy.orm import Session
from sqlalchemy import select

from obscopilot.storage.database import Database, DatabaseSession
from obscopilot.storage.models import (
    WorkflowModel, TriggerModel, ActionModel, 
    WorkflowExecutionModel, SettingModel, TwitchAuthModel, ViewerModel, StreamSessionModel, AlertModel, StreamHealthModel
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Repository(Generic[T]):
    """Base repository for database operations."""
    
    def __init__(self, database: Database, model_class: Type[T]):
        """Initialize repository.
        
        Args:
            database: Database instance
            model_class: SQLAlchemy model class
        """
        self.database = database
        self.model_class = model_class
    
    def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Entity if found, None otherwise
        """
        with DatabaseSession(self.database) as session:
            return session.query(self.model_class).filter_by(id=id).first()
    
    def get_all(self) -> List[T]:
        """Get all entities.
        
        Returns:
            List of all entities
        """
        with DatabaseSession(self.database) as session:
            return session.query(self.model_class).all()
    
    def create(self, entity: T) -> T:
        """Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity
        """
        with DatabaseSession(self.database) as session:
            session.add(entity)
            session.flush()
            return entity
    
    def update(self, entity: T) -> T:
        """Update an existing entity.
        
        Args:
            entity: Entity to update
            
        Returns:
            Updated entity
        """
        with DatabaseSession(self.database) as session:
            session.merge(entity)
            session.flush()
            return entity
    
    def delete(self, id: str) -> bool:
        """Delete an entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            True if entity was deleted, False otherwise
        """
        with DatabaseSession(self.database) as session:
            entity = session.query(self.model_class).filter_by(id=id).first()
            if entity:
                session.delete(entity)
                return True
            return False


class WorkflowRepository(Repository[WorkflowModel]):
    """Repository for workflow operations."""
    
    def __init__(self, database: Database):
        """Initialize workflow repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, WorkflowModel)
    
    def get_enabled_workflows(self) -> List[WorkflowModel]:
        """Get all enabled workflows.
        
        Returns:
            List of enabled workflows
        """
        with DatabaseSession(self.database) as session:
            return session.query(WorkflowModel).filter_by(enabled=True).all()
    
    def create_from_json(self, workflow_json: str) -> WorkflowModel:
        """Create a workflow from JSON data.
        
        Args:
            workflow_json: JSON string with workflow data
            
        Returns:
            Created workflow model
        """
        try:
            # Parse JSON data
            data = json.loads(workflow_json)
            
            # Create workflow model
            workflow = WorkflowModel(
                id=data.get('id'),
                name=data.get('name', 'Unnamed Workflow'),
                description=data.get('description', ''),
                version=data.get('version', '1.0.0'),
                enabled=data.get('enabled', True),
                data=data
            )
            
            return self.create(workflow)
        except Exception as e:
            logger.error(f"Error creating workflow from JSON: {e}")
            raise


class TriggerRepository(Repository[TriggerModel]):
    """Repository for trigger operations."""
    
    def __init__(self, database: Database):
        """Initialize trigger repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, TriggerModel)
    
    def get_by_workflow_id(self, workflow_id: str) -> List[TriggerModel]:
        """Get triggers by workflow ID.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            List of triggers for the workflow
        """
        with DatabaseSession(self.database) as session:
            return session.query(TriggerModel).filter_by(workflow_id=workflow_id).all()


class ActionRepository(Repository[ActionModel]):
    """Repository for action operations."""
    
    def __init__(self, database: Database):
        """Initialize action repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, ActionModel)
    
    def get_by_workflow_id(self, workflow_id: str) -> List[ActionModel]:
        """Get actions by workflow ID.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            List of actions for the workflow
        """
        with DatabaseSession(self.database) as session:
            return session.query(ActionModel).filter_by(workflow_id=workflow_id).all()


class WorkflowExecutionRepository(Repository[WorkflowExecutionModel]):
    """Repository for workflow execution operations."""
    
    def __init__(self, database: Database):
        """Initialize workflow execution repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, WorkflowExecutionModel)
    
    def get_by_workflow_id(self, workflow_id: str, limit: int = 100) -> List[WorkflowExecutionModel]:
        """Get executions by workflow ID.
        
        Args:
            workflow_id: Workflow ID
            limit: Maximum number of executions to return
            
        Returns:
            List of executions for the workflow
        """
        with DatabaseSession(self.database) as session:
            return session.query(WorkflowExecutionModel) \
                .filter_by(workflow_id=workflow_id) \
                .order_by(WorkflowExecutionModel.started_at.desc()) \
                .limit(limit) \
                .all()
    
    def record_execution_start(self, workflow_id: str, trigger_type: str, trigger_data: Dict[str, Any]) -> WorkflowExecutionModel:
        """Record the start of a workflow execution.
        
        Args:
            workflow_id: Workflow ID
            trigger_type: Trigger type that started the workflow
            trigger_data: Trigger data
            
        Returns:
            Created workflow execution record
        """
        execution = WorkflowExecutionModel(
            workflow_id=workflow_id,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            status='started',
            started_at=datetime.datetime.utcnow()
        )
        
        return self.create(execution)
    
    def record_execution_completion(self, execution_id: str, execution_path: List[str], execution_time: float) -> WorkflowExecutionModel:
        """Record the successful completion of a workflow execution.
        
        Args:
            execution_id: Execution ID
            execution_path: List of node IDs in execution order
            execution_time: Execution time in seconds
            
        Returns:
            Updated workflow execution record
        """
        with DatabaseSession(self.database) as session:
            execution = session.query(WorkflowExecutionModel).filter_by(id=execution_id).first()
            if execution:
                execution.status = 'completed'
                execution.completed_at = datetime.datetime.utcnow()
                execution.execution_time = execution_time
                execution.execution_path = execution_path
                
                session.flush()
                return execution
            
            return None
    
    def record_execution_failure(self, execution_id: str, error: str) -> WorkflowExecutionModel:
        """Record the failure of a workflow execution.
        
        Args:
            execution_id: Execution ID
            error: Error message
            
        Returns:
            Updated workflow execution record
        """
        with DatabaseSession(self.database) as session:
            execution = session.query(WorkflowExecutionModel).filter_by(id=execution_id).first()
            if execution:
                execution.status = 'failed'
                execution.completed_at = datetime.datetime.utcnow()
                execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()
                execution.error = error
                
                session.flush()
                return execution
            
            return None


class SettingRepository:
    """Repository for application settings."""
    
    def __init__(self, database: Database):
        """Initialize setting repository.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        with DatabaseSession(self.database) as session:
            setting = session.query(SettingModel).filter_by(key=key).first()
            return setting.value if setting else default
    
    def set(self, key: str, value: Any) -> SettingModel:
        """Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            Updated setting model
        """
        with DatabaseSession(self.database) as session:
            setting = session.query(SettingModel).filter_by(key=key).first()
            if not setting:
                setting = SettingModel(key=key)
                session.add(setting)
            
            setting.value = value
            setting.updated_at = datetime.datetime.utcnow()
            
            session.flush()
            return setting
    
    def delete(self, key: str) -> bool:
        """Delete a setting.
        
        Args:
            key: Setting key
            
        Returns:
            True if setting was deleted, False otherwise
        """
        with DatabaseSession(self.database) as session:
            setting = session.query(SettingModel).filter_by(key=key).first()
            if setting:
                session.delete(setting)
                return True
            return False


class TwitchAuthRepository(Repository[TwitchAuthModel]):
    """Repository for Twitch authentication data."""
    
    def __init__(self, database: Database):
        """Initialize Twitch auth repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, TwitchAuthModel)
    
    def get_by_user_id(self, user_id: str) -> Optional[TwitchAuthModel]:
        """Get auth data by user ID.
        
        Args:
            user_id: Twitch user ID
            
        Returns:
            Auth data if found, None otherwise
        """
        with DatabaseSession(self.database) as session:
            return session.query(TwitchAuthModel).filter_by(user_id=user_id).first()
    
    def save_auth_data(
        self, 
        user_id: str, 
        username: str, 
        access_token: str, 
        refresh_token: str, 
        scope: str,
        expires_in: int = None
    ) -> TwitchAuthModel:
        """Save Twitch authentication data.
        
        Args:
            user_id: Twitch user ID
            username: Twitch username
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            scope: OAuth scopes
            expires_in: Token expiration time in seconds
            
        Returns:
            Created or updated auth model
        """
        # Calculate expires_at if expires_in is provided
        expires_at = None
        if expires_in:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
        
        with DatabaseSession(self.database) as session:
            # Check if auth data already exists for this user
            auth = session.query(TwitchAuthModel).filter_by(user_id=user_id).first()
            
            if auth:
                # Update existing auth data
                auth.username = username
                auth.access_token = access_token
                auth.refresh_token = refresh_token
                auth.scope = scope
                if expires_at:
                    auth.expires_at = expires_at
            else:
                # Create new auth data
                auth = TwitchAuthModel(
                    user_id=user_id,
                    username=username,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    scope=scope,
                    expires_at=expires_at
                )
                session.add(auth)
            
            session.flush()
            return auth
    
    def delete_by_user_id(self, user_id: str) -> bool:
        """Delete auth data by user ID.
        
        Args:
            user_id: Twitch user ID
            
        Returns:
            True if auth data was deleted, False otherwise
        """
        with DatabaseSession(self.database) as session:
            auth = session.query(TwitchAuthModel).filter_by(user_id=user_id).first()
            if auth:
                session.delete(auth)
                return True
            return False


class ViewerRepository(Repository[ViewerModel]):
    """Repository for Twitch viewer data."""
    
    def __init__(self, database: Database):
        """Initialize viewer repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, ViewerModel)
    
    def get_by_user_id(self, user_id: str) -> Optional[ViewerModel]:
        """Get viewer by Twitch user ID.
        
        Args:
            user_id: Twitch user ID
            
        Returns:
            Viewer if found, None otherwise
        """
        with DatabaseSession(self.database) as session:
            return session.query(ViewerModel).filter_by(user_id=user_id).first()
    
    def get_by_username(self, username: str) -> Optional[ViewerModel]:
        """Get viewer by username.
        
        Args:
            username: Twitch username
            
        Returns:
            Viewer if found, None otherwise
        """
        with DatabaseSession(self.database) as session:
            return session.query(ViewerModel).filter_by(username=username.lower()).first()
    
    def update_or_create(
        self, 
        user_id: str, 
        username: str, 
        data: Dict[str, Any] = None
    ) -> ViewerModel:
        """Update or create a viewer.
        
        Args:
            user_id: Twitch user ID
            username: Twitch username
            data: Additional viewer data
            
        Returns:
            Updated or created viewer
        """
        data = data or {}
        
        with DatabaseSession(self.database) as session:
            viewer = session.query(ViewerModel).filter_by(user_id=user_id).first()
            
            if viewer:
                # Update existing viewer
                viewer.username = username.lower()
                
                # Update other fields if provided
                for key, value in data.items():
                    if hasattr(viewer, key):
                        setattr(viewer, key, value)
                
                # Always update last_seen_at
                viewer.last_seen_at = datetime.datetime.utcnow()
            else:
                # Create new viewer
                viewer_data = {
                    'user_id': user_id,
                    'username': username.lower(),
                    'first_seen_at': datetime.datetime.utcnow(),
                    'last_seen_at': datetime.datetime.utcnow()
                }
                viewer_data.update(data)
                
                viewer = ViewerModel(**viewer_data)
                session.add(viewer)
            
            session.flush()
            return viewer
    
    def increment_message_count(self, user_id: str) -> Optional[ViewerModel]:
        """Increment message count for a viewer.
        
        Args:
            user_id: Twitch user ID
            
        Returns:
            Updated viewer or None if not found
        """
        with DatabaseSession(self.database) as session:
            viewer = session.query(ViewerModel).filter_by(user_id=user_id).first()
            if viewer:
                viewer.message_count += 1
                viewer.last_chat_at = datetime.datetime.utcnow()
                if not viewer.first_chat_at:
                    viewer.first_chat_at = datetime.datetime.utcnow()
                session.flush()
                return viewer
            return None
    
    def add_bits_donated(self, user_id: str, bits: int) -> Optional[ViewerModel]:
        """Add bits donated by a viewer.
        
        Args:
            user_id: Twitch user ID
            bits: Number of bits donated
            
        Returns:
            Updated viewer or None if not found
        """
        with DatabaseSession(self.database) as session:
            viewer = session.query(ViewerModel).filter_by(user_id=user_id).first()
            if viewer:
                viewer.bits_donated += bits
                session.flush()
                return viewer
            return None
    
    def update_watch_time(self, user_id: str, seconds: int) -> Optional[ViewerModel]:
        """Update watch time for a viewer.
        
        Args:
            user_id: Twitch user ID
            seconds: Seconds to add to watch time
            
        Returns:
            Updated viewer or None if not found
        """
        with DatabaseSession(self.database) as session:
            viewer = session.query(ViewerModel).filter_by(user_id=user_id).first()
            if viewer:
                viewer.watch_time += seconds
                session.flush()
                return viewer
            return None
    
    def increment_streams_watched(self, user_id: str, stream_id: str) -> Optional[ViewerModel]:
        """Increment streams watched count for a viewer.
        
        Args:
            user_id: Twitch user ID
            stream_id: Current stream ID
            
        Returns:
            Updated viewer or None if not found
        """
        with DatabaseSession(self.database) as session:
            viewer = session.query(ViewerModel).filter_by(user_id=user_id).first()
            if viewer:
                # Only increment if this is a new stream
                if viewer.last_active_stream_id != stream_id:
                    viewer.streams_watched += 1
                    viewer.last_active_stream_id = stream_id
                session.flush()
                return viewer
            return None
    
    def get_top_chatters(self, limit: int = 10) -> List[ViewerModel]:
        """Get top chatters by message count.
        
        Args:
            limit: Maximum number of viewers to return
            
        Returns:
            List of top chatters
        """
        with DatabaseSession(self.database) as session:
            return session.query(ViewerModel) \
                .filter(ViewerModel.message_count > 0) \
                .order_by(ViewerModel.message_count.desc()) \
                .limit(limit) \
                .all()
    
    def get_top_donors(self, limit: int = 10) -> List[ViewerModel]:
        """Get top donors by bits donated.
        
        Args:
            limit: Maximum number of viewers to return
            
        Returns:
            List of top donors
        """
        with DatabaseSession(self.database) as session:
            return session.query(ViewerModel) \
                .filter(ViewerModel.bits_donated > 0) \
                .order_by(ViewerModel.bits_donated.desc()) \
                .limit(limit) \
                .all()
    
    def get_most_loyal_viewers(self, limit: int = 10) -> List[ViewerModel]:
        """Get most loyal viewers by watch time.
        
        Args:
            limit: Maximum number of viewers to return
            
        Returns:
            List of most loyal viewers
        """
        with DatabaseSession(self.database) as session:
            return session.query(ViewerModel) \
                .filter(ViewerModel.watch_time > 0) \
                .order_by(ViewerModel.watch_time.desc()) \
                .limit(limit) \
                .all()


class StreamSessionRepository(Repository[StreamSessionModel]):
    """Repository for stream session data."""
    
    def __init__(self, database: Database):
        """Initialize stream session repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, StreamSessionModel)
    
    def get_by_stream_id(self, stream_id: str) -> Optional[StreamSessionModel]:
        """Get stream session by Twitch stream ID.
        
        Args:
            stream_id: Twitch stream ID
            
        Returns:
            Stream session if found, None otherwise
        """
        with DatabaseSession(self.database) as session:
            return session.query(StreamSessionModel).filter_by(stream_id=stream_id).first()
    
    def get_current_session(self) -> Optional[StreamSessionModel]:
        """Get current active stream session.
        
        Returns:
            Current stream session if found, None otherwise
        """
        with DatabaseSession(self.database) as session:
            return session.query(StreamSessionModel) \
                .filter(StreamSessionModel.ended_at.is_(None)) \
                .order_by(StreamSessionModel.started_at.desc()) \
                .first()
    
    def start_session(self, stream_data: Dict[str, Any] = None) -> StreamSessionModel:
        """Start a new stream session.
        
        Args:
            stream_data: Stream data from Twitch API
            
        Returns:
            Created stream session
        """
        stream_data = stream_data or {}
        
        # Extract data from stream info
        session_data = {
            'started_at': datetime.datetime.utcnow(),
            'stream_id': stream_data.get('id'),
            'title': stream_data.get('title'),
            'game_name': stream_data.get('game_name')
        }
        
        session = StreamSessionModel(**session_data)
        
        with DatabaseSession(self.database) as session:
            session.add(session)
            session.flush()
            return session
    
    def end_session(self, session_id: str, stream_data: Dict[str, Any] = None) -> Optional[StreamSessionModel]:
        """End a stream session.
        
        Args:
            session_id: Stream session ID
            stream_data: Final stream data
            
        Returns:
            Updated stream session or None if not found
        """
        with DatabaseSession(self.database) as session:
            stream_session = session.query(StreamSessionModel).filter_by(id=session_id).first()
            if not stream_session:
                return None
            
            # Set end time
            stream_session.ended_at = datetime.datetime.utcnow()
            
            # Calculate duration
            if stream_session.started_at:
                duration = (stream_session.ended_at - stream_session.started_at).total_seconds()
                stream_session.duration = int(duration)
            
            # Update with final stream data if provided
            if stream_data:
                if 'title' in stream_data:
                    stream_session.title = stream_data['title']
                if 'game_name' in stream_data:
                    stream_session.game_name = stream_data['game_name']
            
            session.flush()
            return stream_session
    
    def update_session_stats(self, session_id: str, stats: Dict[str, Any]) -> Optional[StreamSessionModel]:
        """Update stream session statistics.
        
        Args:
            session_id: Stream session ID
            stats: Statistics to update
            
        Returns:
            Updated stream session or None if not found
        """
        with DatabaseSession(self.database) as session:
            stream_session = session.query(StreamSessionModel).filter_by(id=session_id).first()
            if not stream_session:
                return None
            
            # Update stats
            for key, value in stats.items():
                if hasattr(stream_session, key):
                    setattr(stream_session, key, value)
            
            session.flush()
            return stream_session
    
    def get_recent_sessions(self, limit: int = 10) -> List[StreamSessionModel]:
        """Get recent stream sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of recent stream sessions
        """
        with DatabaseSession(self.database) as session:
            return session.query(StreamSessionModel) \
                .filter(StreamSessionModel.ended_at.isnot(None)) \
                .order_by(StreamSessionModel.started_at.desc()) \
                .limit(limit) \
                .all()


class AlertRepository(Repository[AlertModel]):
    """Repository for alert templates."""
    
    def __init__(self, database: Database):
        """Initialize alert repository.
        
        Args:
            database: Database instance
        """
        super().__init__(database, AlertModel)
    
    def get_by_name(self, name: str) -> Optional[AlertModel]:
        """Get alert by name.
        
        Args:
            name: Alert name
            
        Returns:
            Alert if found, None otherwise
        """
        with DatabaseSession(self.database) as session:
            return session.query(AlertModel).filter_by(name=name).first()
    
    def create_alert(self, alert_data: Dict[str, Any]) -> AlertModel:
        """Create a new alert template.
        
        Args:
            alert_data: Alert data
            
        Returns:
            Created alert
        """
        alert = AlertModel(**alert_data)
        
        with DatabaseSession(self.database) as session:
            session.add(alert)
            session.flush()
            return alert
    
    def update_alert(self, alert_id: str, alert_data: Dict[str, Any]) -> Optional[AlertModel]:
        """Update an existing alert template.
        
        Args:
            alert_id: Alert ID
            alert_data: Alert data
            
        Returns:
            Updated alert or None if not found
        """
        with DatabaseSession(self.database) as session:
            alert = session.query(AlertModel).filter_by(id=alert_id).first()
            if not alert:
                return None
            
            # Update alert attributes
            for key, value in alert_data.items():
                if hasattr(alert, key):
                    setattr(alert, key, value)
            
            session.flush()
            return alert
    
    def list_alerts(self) -> List[AlertModel]:
        """Get all alert templates.
        
        Returns:
            List of alert templates
        """
        with DatabaseSession(self.database) as session:
            return session.query(AlertModel).order_by(AlertModel.name).all()


class StreamHealthRepository:
    """Repository for managing stream health data."""
    
    def __init__(self, database: Database):
        """Initialize the repository.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    async def create(self, session_id: str, metrics: Dict[str, Any]) -> str:
        """Create a new stream health record.
        
        Args:
            session_id: Stream session ID
            metrics: Stream health metrics
            
        Returns:
            ID of the created record
        """
        async with self.database.session() as session:
            record_id = str(uuid.uuid4())
            
            # Create new stream health record
            health_record = StreamHealthModel(
                id=record_id,
                session_id=session_id,
                timestamp=time.time(),
                
                # OBS statistics
                fps=metrics.get('fps'),
                render_total_frames=metrics.get('render_total_frames'),
                render_missed_frames=metrics.get('render_missed_frames'),
                output_total_frames=metrics.get('output_total_frames'),
                output_skipped_frames=metrics.get('output_skipped_frames'),
                average_frame_time=metrics.get('average_frame_time'),
                cpu_usage=metrics.get('cpu_usage'),
                memory_usage=metrics.get('memory_usage'),
                free_disk_space=metrics.get('free_disk_space'),
                
                # Stream statistics
                bitrate=metrics.get('bitrate'),
                num_dropped_frames=metrics.get('num_dropped_frames'),
                num_total_frames=metrics.get('num_total_frames'),
                strain=metrics.get('strain'),
                stream_duration=metrics.get('stream_duration'),
                
                # Network statistics
                kbits_per_sec=metrics.get('kbits_per_sec'),
                ping=metrics.get('ping')
            )
            
            session.add(health_record)
            await session.commit()
            
            return record_id
    
    async def get_by_session(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get stream health records for a session.
        
        Args:
            session_id: Stream session ID
            limit: Maximum number of records to return
            
        Returns:
            List of stream health records
        """
        async with self.database.session() as session:
            stmt = (
                select(StreamHealthModel)
                .where(StreamHealthModel.session_id == session_id)
                .order_by(StreamHealthModel.timestamp.desc())
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            return [
                {
                    'id': record.id,
                    'session_id': record.session_id,
                    'timestamp': record.timestamp,
                    'fps': record.fps,
                    'render_total_frames': record.render_total_frames,
                    'render_missed_frames': record.render_missed_frames,
                    'output_total_frames': record.output_total_frames,
                    'output_skipped_frames': record.output_skipped_frames,
                    'average_frame_time': record.average_frame_time,
                    'cpu_usage': record.cpu_usage,
                    'memory_usage': record.memory_usage,
                    'free_disk_space': record.free_disk_space,
                    'bitrate': record.bitrate,
                    'num_dropped_frames': record.num_dropped_frames,
                    'num_total_frames': record.num_total_frames,
                    'strain': record.strain,
                    'stream_duration': record.stream_duration,
                    'kbits_per_sec': record.kbits_per_sec,
                    'ping': record.ping,
                    'created_at': record.created_at
                }
                for record in records
            ]
    
    async def get_latest_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest stream health record for a session.
        
        Args:
            session_id: Stream session ID
            
        Returns:
            Latest stream health record or None if not found
        """
        async with self.database.session() as session:
            stmt = (
                select(StreamHealthModel)
                .where(StreamHealthModel.session_id == session_id)
                .order_by(StreamHealthModel.timestamp.desc())
                .limit(1)
            )
            
            result = await session.execute(stmt)
            record = result.scalars().first()
            
            if not record:
                return None
            
            return {
                'id': record.id,
                'session_id': record.session_id,
                'timestamp': record.timestamp,
                'fps': record.fps,
                'render_total_frames': record.render_total_frames,
                'render_missed_frames': record.render_missed_frames,
                'output_total_frames': record.output_total_frames,
                'output_skipped_frames': record.output_skipped_frames,
                'average_frame_time': record.average_frame_time,
                'cpu_usage': record.cpu_usage,
                'memory_usage': record.memory_usage,
                'free_disk_space': record.free_disk_space,
                'bitrate': record.bitrate,
                'num_dropped_frames': record.num_dropped_frames,
                'num_total_frames': record.num_total_frames,
                'strain': record.strain,
                'stream_duration': record.stream_duration,
                'kbits_per_sec': record.kbits_per_sec,
                'ping': record.ping,
                'created_at': record.created_at
            } 