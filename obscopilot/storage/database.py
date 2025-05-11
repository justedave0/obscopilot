"""
Database management for OBSCopilot.

This module provides a SQLite database backend for persisting application data.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship, Session

from obscopilot.core.config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()


class Database:
    """Database manager for OBSCopilot."""
    
    def __init__(self, config: Config):
        """Initialize database connection.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.engine = None
        self.session_factory = None
        self._setup_database()
    
    def _setup_database(self) -> None:
        """Set up database connection and create tables if needed."""
        try:
            # Get database path from config
            db_path = self.config.get('storage', 'database_path', '')
            if not db_path:
                # Use default location in user's home directory
                db_path = os.path.join(str(Path.home()), '.obscopilot', 'obscopilot.db')
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Create SQLite engine
            db_url = f"sqlite:///{db_path}"
            self.engine = create_engine(db_url)
            
            # Create session factory
            self.session_factory = scoped_session(sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            ))
            
            # Create tables
            Base.metadata.create_all(self.engine)
            
            logger.info(f"Database initialized at {db_path}")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
    
    def get_session(self) -> Session:
        """Get a new database session.
        
        Returns:
            SQLAlchemy session object
        """
        if not self.session_factory:
            raise Exception("Database not initialized")
        return self.session_factory()
    
    def close(self) -> None:
        """Close database connection."""
        if self.session_factory:
            self.session_factory.remove()
            logger.info("Database session closed")


class DatabaseSession:
    """Context manager for database sessions."""
    
    def __init__(self, database: Database):
        """Initialize database session context.
        
        Args:
            database: Database instance
        """
        self.database = database
        self.session = None
    
    def __enter__(self) -> Session:
        """Enter the context, providing a database session.
        
        Returns:
            Active database session
        """
        self.session = self.database.get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context, closing the database session."""
        if exc_type:
            # An exception occurred, rollback the session
            if self.session:
                self.session.rollback()
                logger.debug("Database session rolled back due to exception")
        else:
            # No exception, commit the session
            if self.session:
                self.session.commit()
                logger.debug("Database session committed")
        
        # Close the session
        if self.session:
            self.session.close() 