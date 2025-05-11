"""
Database models for OBSCopilot.

This module defines the SQLAlchemy ORM models for database storage.
"""

import datetime
import json
import uuid
from typing import Dict, List, Optional, Any

from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship

from obscopilot.storage.database import Base


class WorkflowModel(Base):
    """Database model for storing workflows."""
    
    __tablename__ = 'workflows'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    version = Column(String(50), default='1.0.0', nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    data = Column(JSON, nullable=False)  # Full workflow JSON data
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    triggers = relationship("TriggerModel", back_populates="workflow", cascade="all, delete-orphan")
    actions = relationship("ActionModel", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecutionModel", back_populates="workflow", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'enabled': self.enabled,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TriggerModel(Base):
    """Database model for storing workflow triggers."""
    
    __tablename__ = 'triggers'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    type = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    workflow = relationship("WorkflowModel", back_populates="triggers")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'config': self.config,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ActionModel(Base):
    """Database model for storing workflow actions."""
    
    __tablename__ = 'actions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    type = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    workflow = relationship("WorkflowModel", back_populates="actions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'config': self.config,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WorkflowExecutionModel(Base):
    """Database model for storing workflow execution history."""
    
    __tablename__ = 'workflow_executions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False)
    trigger_type = Column(String(100), nullable=False)
    trigger_data = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False)  # started, completed, failed
    started_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    execution_time = Column(Float, nullable=True)  # in seconds
    error = Column(String(1000), nullable=True)
    execution_path = Column(JSON, nullable=True)  # List of node IDs in execution order
    
    # Relationships
    workflow = relationship("WorkflowModel", back_populates="executions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'trigger_type': self.trigger_type,
            'trigger_data': self.trigger_data,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'execution_time': self.execution_time,
            'error': self.error,
            'execution_path': self.execution_path
        }


class SettingModel(Base):
    """Database model for storing application settings."""
    
    __tablename__ = 'settings'
    
    key = Column(String(255), primary_key=True)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TwitchAuthModel(Base):
    """Database model for storing Twitch authentication data."""
    
    __tablename__ = 'twitch_auth'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    access_token = Column(String(255), nullable=False)
    refresh_token = Column(String(255), nullable=False)
    scope = Column(String(1000), nullable=False)
    token_type = Column(String(50), default='bearer', nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'scope': self.scope,
            'token_type': self.token_type,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 