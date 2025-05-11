"""
Repository classes for database operations.

This module provides repository classes that abstract database operations.
"""

import datetime
import json
import logging
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic

from sqlalchemy.orm import Session

from obscopilot.storage.database import Database, DatabaseSession
from obscopilot.storage.models import (
    WorkflowModel, TriggerModel, ActionModel, 
    WorkflowExecutionModel, SettingModel, TwitchAuthModel
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
        with DatabaseSession(self.database) as session:
            auth = session.query(TwitchAuthModel).filter_by(user_id=user_id).first()
            
            # Calculate expiration time if provided
            expires_at = None
            if expires_in:
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
            
            if not auth:
                # Create new auth record
                auth = TwitchAuthModel(
                    user_id=user_id,
                    username=username,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    scope=scope,
                    token_type='bearer',
                    expires_at=expires_at
                )
                session.add(auth)
            else:
                # Update existing auth record
                auth.username = username
                auth.access_token = access_token
                auth.refresh_token = refresh_token
                auth.scope = scope
                auth.expires_at = expires_at
                auth.updated_at = datetime.datetime.utcnow()
            
            session.flush()
            return auth 