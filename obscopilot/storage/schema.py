"""
Database schema management for OBSCopilot.

This module provides functionality for managing the database schema,
including schema versioning and migrations.
"""

import logging
import sqlite3
import json
import os
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from obscopilot.core.config import Config

logger = logging.getLogger(__name__)


class SchemaManager:
    """Database schema manager."""
    
    def __init__(self, config: Config):
        """Initialize schema manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.db_path = Path(config.get('database', 'path', 'data/obscopilot.db'))
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Current schema version
        self.current_version = 1
        
        # Schema migrations
        self.migrations = {
            1: self._create_schema_v1
        }
        
        # Initialize connection
        self.conn = None
        
    def connect(self) -> sqlite3.Connection:
        """Connect to the database.
        
        Returns:
            Database connection
        """
        if self.conn:
            return self.conn
            
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        return self.conn
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def init_schema(self) -> bool:
        """Initialize the database schema.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.connect()
            
            # Check if schema_version table exists
            cursor = conn.cursor()
            cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='schema_version'
            """)
            
            if not cursor.fetchone():
                # Create schema_version table
                cursor.execute("""
                CREATE TABLE schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """)
                
                # Insert initial version
                cursor.execute("""
                INSERT INTO schema_version (version, applied_at)
                VALUES (0, ?)
                """, (datetime.datetime.utcnow().isoformat(),))
                
                conn.commit()
            
            # Get current schema version
            cursor.execute("SELECT MAX(version) as version FROM schema_version")
            row = cursor.fetchone()
            db_version = row['version'] if row else 0
            
            logger.info(f"Current database schema version: {db_version}")
            logger.info(f"Latest schema version: {self.current_version}")
            
            # Apply missing migrations
            if db_version < self.current_version:
                for version in range(db_version + 1, self.current_version + 1):
                    if version in self.migrations:
                        logger.info(f"Applying migration to version {version}")
                        migration_func = self.migrations[version]
                        migration_func(conn)
                        
                        # Update schema version
                        cursor.execute("""
                        INSERT INTO schema_version (version, applied_at)
                        VALUES (?, ?)
                        """, (version, datetime.datetime.utcnow().isoformat()))
                        
                        conn.commit()
                    else:
                        logger.error(f"Missing migration for version {version}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            if conn:
                conn.rollback()
            return False
            
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Backup the database.
        
        Args:
            backup_path: Path to save backup (or None for default path)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not backup_path:
                # Create default backup path with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = str(self.db_path.with_suffix(f'.{timestamp}.bak'))
            
            # Ensure connection is closed
            self.close()
            
            # Copy database file
            import shutil
            shutil.copy2(str(self.db_path), backup_path)
            
            logger.info(f"Database backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
            
    def restore_database(self, backup_path: str) -> bool:
        """Restore the database from a backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure backup file exists
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
                
            # Ensure connection is closed
            self.close()
            
            # Backup current database
            self.backup_database()
            
            # Copy backup to database file
            import shutil
            shutil.copy2(backup_path, str(self.db_path))
            
            logger.info(f"Database restored from {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False
    
    def _create_schema_v1(self, conn: sqlite3.Connection):
        """Create initial schema (version 1).
        
        Args:
            conn: Database connection
        """
        cursor = conn.cursor()
        
        # Workflows table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            version TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Workflow execution logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflow_executions (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            trigger_data TEXT,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            execution_time REAL,
            error TEXT,
            execution_path TEXT,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id)
        )
        """)
        
        # Settings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Stream health metrics
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stream_health (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            cpu_usage REAL,
            memory_usage REAL,
            fps REAL,
            render_missed_frames INTEGER,
            output_skipped_frames INTEGER,
            network_congestion REAL,
            stream_time INTEGER,
            kbits_per_sec REAL,
            status TEXT
        )
        """)
        
        # User statistics
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            display_name TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            watch_time INTEGER DEFAULT 0,
            messages_count INTEGER DEFAULT 0,
            follows_count INTEGER DEFAULT 0,
            subscriptions_count INTEGER DEFAULT 0,
            bits_donated INTEGER DEFAULT 0,
            channel_points_redeemed INTEGER DEFAULT 0,
            user_data TEXT
        )
        """)
        
        # Message history
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_history (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            display_name TEXT,
            timestamp TEXT NOT NULL,
            message TEXT NOT NULL,
            is_command INTEGER DEFAULT 0,
            user_data TEXT
        )
        """)
        
        conn.commit()
        

# Single instance for the application
_schema_manager = None

def get_schema_manager(config: Config = None) -> SchemaManager:
    """Get the schema manager instance.
    
    Args:
        config: Application configuration
        
    Returns:
        Schema manager instance
    """
    global _schema_manager
    if not _schema_manager and config:
        _schema_manager = SchemaManager(config)
    return _schema_manager 