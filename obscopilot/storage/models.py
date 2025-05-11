"""
Database models for OBSCopilot.

This module defines the SQLAlchemy ORM models for database storage.
"""

import datetime
import json
import uuid
import time
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


class ViewerModel(Base):
    """Database model for storing Twitch viewer statistics."""
    
    __tablename__ = 'viewers'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=True)
    
    # Profile data
    profile_image_url = Column(String(255), nullable=True)
    is_broadcaster = Column(Boolean, default=False, nullable=False)
    is_moderator = Column(Boolean, default=False, nullable=False)
    is_vip = Column(Boolean, default=False, nullable=False)
    is_subscriber = Column(Boolean, default=False, nullable=False)
    is_follower = Column(Boolean, default=False, nullable=False)
    
    # Engagement stats
    first_seen_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    bits_donated = Column(Integer, default=0, nullable=False)
    
    # Stream presence
    watch_time = Column(Integer, default=0, nullable=False)  # In seconds
    streams_watched = Column(Integer, default=0, nullable=False)
    last_active_stream_id = Column(String(100), nullable=True)
    
    # Chat stats
    last_chat_at = Column(DateTime, nullable=True)
    first_chat_at = Column(DateTime, nullable=True)
    
    # Custom notes
    notes = Column(String(1000), nullable=True)
    
    # Metadata
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
            'display_name': self.display_name,
            'profile_image_url': self.profile_image_url,
            'is_broadcaster': self.is_broadcaster,
            'is_moderator': self.is_moderator,
            'is_vip': self.is_vip,
            'is_subscriber': self.is_subscriber,
            'is_follower': self.is_follower,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'message_count': self.message_count,
            'bits_donated': self.bits_donated,
            'watch_time': self.watch_time,
            'streams_watched': self.streams_watched,
            'last_active_stream_id': self.last_active_stream_id,
            'last_chat_at': self.last_chat_at.isoformat() if self.last_chat_at else None,
            'first_chat_at': self.first_chat_at.isoformat() if self.first_chat_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StreamSessionModel(Base):
    """Database model for storing stream session data."""
    
    __tablename__ = 'stream_sessions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stream_id = Column(String(100), nullable=True)  # Twitch stream ID, if available
    title = Column(String(255), nullable=True)
    game_name = Column(String(255), nullable=True)
    
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # In seconds
    
    # Stats
    peak_viewers = Column(Integer, default=0, nullable=False)
    unique_viewers = Column(Integer, default=0, nullable=False)
    new_followers = Column(Integer, default=0, nullable=False)
    new_subscribers = Column(Integer, default=0, nullable=False)
    bits_received = Column(Integer, default=0, nullable=False)
    messages_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    health_metrics = relationship("StreamHealthModel", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'id': self.id,
            'stream_id': self.stream_id,
            'title': self.title,
            'game_name': self.game_name,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration': self.duration,
            'peak_viewers': self.peak_viewers,
            'unique_viewers': self.unique_viewers,
            'new_followers': self.new_followers,
            'new_subscribers': self.new_subscribers,
            'bits_received': self.bits_received,
            'messages_count': self.messages_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StreamHealthModel(Base):
    """Model for storing stream health metrics."""
    
    __tablename__ = 'stream_health'
    
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("stream_sessions.id"), nullable=False)
    timestamp = Column(Float, nullable=False)
    
    # OBS statistics
    fps = Column(Float)
    render_total_frames = Column(Integer)
    render_missed_frames = Column(Integer)
    output_total_frames = Column(Integer)
    output_skipped_frames = Column(Integer)
    average_frame_time = Column(Float)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    free_disk_space = Column(Float)
    
    # Stream statistics
    bitrate = Column(Float)
    num_dropped_frames = Column(Integer)
    num_total_frames = Column(Integer)
    strain = Column(Float)
    stream_duration = Column(Float)
    
    # Network statistics
    kbits_per_sec = Column(Float)
    ping = Column(Float)
    
    created_at = Column(Float, nullable=False, default=lambda: time.time())
    
    # Relationships
    session = relationship("StreamSessionModel", back_populates="health_metrics")


class AlertModel(Base):
    """Database model for storing alert templates."""
    
    __tablename__ = 'alerts'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Alert content
    message = Column(String(1000), nullable=True)  # Text overlay message
    image_path = Column(String(255), nullable=True)  # Image path
    sound_path = Column(String(255), nullable=True)  # Sound path
    
    # Style options
    duration = Column(Float, default=5.0, nullable=False)  # In seconds
    font_size = Column(Integer, default=24, nullable=False)
    font_color = Column(String(20), default="#FFFFFF", nullable=False)
    background_color = Column(String(20), default="#000000AA", nullable=False)
    text_position = Column(String(20), default="center", nullable=False)  # top, center, bottom
    
    # Animation options
    animation_in = Column(String(50), default="fade", nullable=False)  # fade, slide, bounce
    animation_out = Column(String(50), default="fade", nullable=False)
    
    # OBS source options
    source_name = Column(String(255), nullable=True)  # OBS source to update
    use_default_source = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'message': self.message,
            'image_path': self.image_path,
            'sound_path': self.sound_path,
            'duration': self.duration,
            'font_size': self.font_size,
            'font_color': self.font_color,
            'background_color': self.background_color,
            'text_position': self.text_position,
            'animation_in': self.animation_in,
            'animation_out': self.animation_out,
            'source_name': self.source_name,
            'use_default_source': self.use_default_source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 