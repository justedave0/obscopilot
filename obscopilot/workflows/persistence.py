"""
Workflow persistence for OBSCopilot.

This module provides functionality to save and load workflows from the database.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from obscopilot.storage.database import get_database
from obscopilot.workflows.models import Workflow, workflow_from_dict, workflow_to_dict

logger = logging.getLogger(__name__)


class WorkflowRepository:
    """Repository for workflow persistence."""
    
    def __init__(self, db=None):
        """Initialize workflow repository.
        
        Args:
            db: Database connection (if None, a new connection will be created)
        """
        self.db = db if db else get_database()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure that the necessary tables exist."""
        self.db.execute('''
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            version TEXT,
            enabled INTEGER DEFAULT 1,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        self.db.execute('''
        CREATE TABLE IF NOT EXISTS workflow_execution_logs (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            trigger_id TEXT,
            trigger_type TEXT,
            trigger_data TEXT,
            status TEXT NOT NULL,
            execution_path TEXT,
            variables TEXT,
            error TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id)
        )
        ''')
        
        self.db.commit()
    
    def save_workflow(self, workflow: Workflow) -> bool:
        """Save a workflow to the database.
        
        Args:
            workflow: Workflow to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert workflow to dict
            workflow_dict = workflow_to_dict(workflow)
            
            # Convert dict to JSON
            workflow_data = json.dumps(workflow_dict)
            
            # Check if workflow exists
            existing = self.db.execute(
                "SELECT id FROM workflows WHERE id = ?", 
                (workflow.id,)
            ).fetchone()
            
            if existing:
                # Update existing workflow
                self.db.execute('''
                UPDATE workflows SET
                    name = ?,
                    description = ?,
                    version = ?,
                    enabled = ?,
                    data = ?,
                    updated_at = ?
                WHERE id = ?
                ''', (
                    workflow.name,
                    workflow.description,
                    workflow.version,
                    1 if workflow.enabled else 0,
                    workflow_data,
                    workflow.updated_at.isoformat(),
                    workflow.id
                ))
            else:
                # Insert new workflow
                self.db.execute('''
                INSERT INTO workflows (
                    id, name, description, version, enabled, data, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    workflow.id,
                    workflow.name,
                    workflow.description,
                    workflow.version,
                    1 if workflow.enabled else 0,
                    workflow_data,
                    workflow.created_at.isoformat(),
                    workflow.updated_at.isoformat()
                ))
            
            self.db.commit()
            logger.info(f"Saved workflow '{workflow.name}' (ID: {workflow.id})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving workflow: {e}")
            self.db.rollback()
            return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow from the database.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow or None if not found
        """
        try:
            # Query database
            result = self.db.execute(
                "SELECT data FROM workflows WHERE id = ?", 
                (workflow_id,)
            ).fetchone()
            
            if not result:
                logger.warning(f"Workflow not found: {workflow_id}")
                return None
            
            # Parse JSON data
            workflow_dict = json.loads(result[0])
            
            # Convert dict to workflow object
            workflow = workflow_from_dict(workflow_dict)
            
            return workflow
            
        except Exception as e:
            logger.error(f"Error getting workflow: {e}")
            return None
    
    def get_all_workflows(self, enabled_only: bool = False) -> List[Workflow]:
        """Get all workflows from the database.
        
        Args:
            enabled_only: Only return enabled workflows
            
        Returns:
            List of workflows
        """
        try:
            # Query database
            if enabled_only:
                results = self.db.execute(
                    "SELECT data FROM workflows WHERE enabled = 1"
                ).fetchall()
            else:
                results = self.db.execute(
                    "SELECT data FROM workflows"
                ).fetchall()
            
            workflows = []
            
            for result in results:
                try:
                    # Parse JSON data
                    workflow_dict = json.loads(result[0])
                    
                    # Convert dict to workflow object
                    workflow = workflow_from_dict(workflow_dict)
                    
                    workflows.append(workflow)
                    
                except Exception as e:
                    logger.error(f"Error parsing workflow: {e}")
                    continue
            
            return workflows
            
        except Exception as e:
            logger.error(f"Error getting workflows: {e}")
            return []
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from the database.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if workflow exists
            existing = self.db.execute(
                "SELECT id FROM workflows WHERE id = ?", 
                (workflow_id,)
            ).fetchone()
            
            if not existing:
                logger.warning(f"Workflow not found: {workflow_id}")
                return False
            
            # Delete workflow
            self.db.execute(
                "DELETE FROM workflows WHERE id = ?", 
                (workflow_id,)
            )
            
            # Also delete execution logs
            self.db.execute(
                "DELETE FROM workflow_execution_logs WHERE workflow_id = ?", 
                (workflow_id,)
            )
            
            self.db.commit()
            logger.info(f"Deleted workflow (ID: {workflow_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting workflow: {e}")
            self.db.rollback()
            return False
    
    def log_workflow_execution(self, workflow_id: str, execution_data: Dict) -> str:
        """Log a workflow execution.
        
        Args:
            workflow_id: ID of the workflow
            execution_data: Execution data
            
        Returns:
            Execution log ID
        """
        try:
            import uuid
            
            # Generate execution log ID
            execution_id = str(uuid.uuid4())
            
            # Insert execution log
            self.db.execute('''
            INSERT INTO workflow_execution_logs (
                id, workflow_id, trigger_id, trigger_type, trigger_data, status,
                execution_path, variables, error, start_time, end_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                execution_id,
                workflow_id,
                execution_data.get('trigger_id'),
                execution_data.get('trigger_type'),
                json.dumps(execution_data.get('trigger_data', {})),
                execution_data.get('status'),
                json.dumps(execution_data.get('execution_path', [])),
                json.dumps(execution_data.get('variables', {})),
                execution_data.get('error'),
                execution_data.get('start_time'),
                execution_data.get('end_time')
            ))
            
            self.db.commit()
            logger.info(f"Logged workflow execution (ID: {execution_id})")
            return execution_id
            
        except Exception as e:
            logger.error(f"Error logging workflow execution: {e}")
            self.db.rollback()
            return ""
    
    def get_workflow_execution_logs(self, workflow_id: str, limit: int = 100) -> List[Dict]:
        """Get execution logs for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of logs to return
            
        Returns:
            List of execution logs
        """
        try:
            # Query database
            results = self.db.execute('''
            SELECT id, trigger_id, trigger_type, trigger_data, status,
                   execution_path, variables, error, start_time, end_time
            FROM workflow_execution_logs
            WHERE workflow_id = ?
            ORDER BY start_time DESC
            LIMIT ?
            ''', (workflow_id, limit)).fetchall()
            
            logs = []
            
            for result in results:
                log = {
                    'id': result[0],
                    'workflow_id': workflow_id,
                    'trigger_id': result[1],
                    'trigger_type': result[2],
                    'trigger_data': json.loads(result[3]) if result[3] else {},
                    'status': result[4],
                    'execution_path': json.loads(result[5]) if result[5] else [],
                    'variables': json.loads(result[6]) if result[6] else {},
                    'error': result[7],
                    'start_time': result[8],
                    'end_time': result[9]
                }
                
                logs.append(log)
            
            return logs
            
        except Exception as e:
            logger.error(f"Error getting workflow execution logs: {e}")
            return [] 