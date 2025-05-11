"""
Time-based triggers for OBSCopilot workflow engine.

This module implements time-based workflow triggers including schedules and intervals.
"""

import logging
import datetime
from typing import Any, Dict, List, Optional

from obscopilot.workflows.models import TriggerType, WorkflowTrigger
from obscopilot.workflows.triggers.base import BaseTrigger, ScheduleableTriggerMixin

logger = logging.getLogger(__name__)


class BaseTimeTrigger(BaseTrigger):
    """Base class for time-based triggers."""
    pass


class ScheduleTrigger(BaseTimeTrigger, ScheduleableTriggerMixin):
    """Trigger based on a schedule (cron expression)."""
    
    trigger_type = TriggerType.SCHEDULE
    
    @classmethod
    def prepare(cls, trigger: WorkflowTrigger) -> None:
        """Prepare trigger for use.
        
        Parse cron expression and validate.
        
        Args:
            trigger: Trigger to prepare
        """
        config = trigger.config
        
        # Parse cron expression
        if "cron" in config:
            schedule_info = cls.parse_cron_expression(config["cron"])
            if schedule_info:
                config["_schedule_info"] = schedule_info
        
        # Parse specific time (alternative to cron)
        if "time" in config:
            try:
                # Convert string time to datetime.time
                time_str = config["time"]
                time_parts = time_str.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1] if len(time_parts) > 1 else 0)
                second = int(time_parts[2] if len(time_parts) > 2 else 0)
                
                config["_time"] = datetime.time(hour, minute, second)
            except Exception as e:
                logger.warning(f"Invalid time format: {config['time']}, error: {e}")
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate the trigger configuration.
        
        Args:
            config: Trigger configuration
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for cron or time
        if "cron" not in config and "time" not in config:
            errors.append("Schedule trigger requires either 'cron' or 'time' config")
        
        # Validate cron expression
        if "cron" in config:
            if not cls.parse_cron_expression(config["cron"]):
                errors.append(f"Invalid cron expression: {config['cron']}")
        
        # Validate time format
        if "time" in config:
            try:
                time_str = config["time"]
                time_parts = time_str.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1] if len(time_parts) > 1 else 0)
                second = int(time_parts[2] if len(time_parts) > 2 else 0)
                
                if hour < 0 or hour > 23:
                    errors.append(f"Invalid hour: {hour}, must be 0-23")
                if minute < 0 or minute > 59:
                    errors.append(f"Invalid minute: {minute}, must be 0-59")
                if second < 0 or second > 59:
                    errors.append(f"Invalid second: {second}, must be 0-59")
            except Exception as e:
                errors.append(f"Invalid time format: {config['time']}, error: {e}")
        
        return errors
    
    @classmethod
    def is_time_to_run(cls, trigger: WorkflowTrigger, current_time: Optional[datetime.datetime] = None) -> bool:
        """Check if it's time to run this trigger based on schedule.
        
        Args:
            trigger: Trigger to check
            current_time: Current time (uses datetime.now() if not provided)
            
        Returns:
            True if trigger should run, False otherwise
        """
        config = trigger.config
        
        if current_time is None:
            current_time = datetime.datetime.now()
        
        # Check cron-based schedule
        if "_schedule_info" in config:
            try:
                from croniter import croniter
                
                # Get last run time from execution history
                last_run = config.get("_last_run")
                
                # Create croniter instance
                cron_expr = config["cron"]
                if last_run:
                    it = croniter(cron_expr, last_run)
                    next_run = it.get_next(datetime.datetime)
                else:
                    it = croniter(cron_expr, current_time)
                    next_run = it.get_prev(datetime.datetime)
                
                return current_time >= next_run
            except ImportError:
                logger.warning("croniter package not installed, cron scheduling not available")
                return False
            except Exception as e:
                logger.warning(f"Error checking cron schedule: {e}")
                return False
        
        # Check specific time schedule
        elif "_time" in config:
            scheduled_time = config["_time"]
            current_time_of_day = current_time.time()
            
            # Get days of week to run on
            days_of_week = config.get("days_of_week", [0, 1, 2, 3, 4, 5, 6])  # Default to all days
            current_day_of_week = current_time.weekday()
            
            # Get last run time from execution history
            last_run = config.get("_last_run")
            
            # Check if we've already run today
            if last_run and last_run.date() == current_time.date():
                return False
            
            # Check if today is a day we should run
            if current_day_of_week not in days_of_week:
                return False
            
            # Check if it's past the scheduled time
            return current_time_of_day >= scheduled_time
        
        return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "cron": {
                "type": "string",
                "description": "Cron expression for schedule (e.g., '0 9 * * 1-5' for weekdays at 9am)",
                "required": False
            },
            "time": {
                "type": "string",
                "description": "Specific time to run (e.g., '09:00')",
                "required": False
            },
            "days_of_week": {
                "type": "array",
                "description": "Days of week to run on (0 = Monday, 6 = Sunday), used with 'time'",
                "required": False,
                "items": {
                    "type": "integer"
                }
            }
        }


class IntervalTrigger(BaseTimeTrigger):
    """Trigger based on a time interval."""
    
    trigger_type = TriggerType.INTERVAL
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate the trigger configuration.
        
        Args:
            config: Trigger configuration
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for interval
        if "interval" not in config:
            errors.append("Interval trigger requires 'interval' config")
        else:
            try:
                interval = int(config["interval"])
                if interval <= 0:
                    errors.append(f"Interval must be greater than 0, got {interval}")
            except ValueError:
                errors.append(f"Invalid interval: {config['interval']}, must be an integer")
        
        return errors
    
    @classmethod
    def is_time_to_run(cls, trigger: WorkflowTrigger, current_time: Optional[datetime.datetime] = None) -> bool:
        """Check if it's time to run this trigger based on interval.
        
        Args:
            trigger: Trigger to check
            current_time: Current time (uses datetime.now() if not provided)
            
        Returns:
            True if trigger should run, False otherwise
        """
        config = trigger.config
        
        if current_time is None:
            current_time = datetime.datetime.now()
        
        # Get interval in seconds
        interval = int(config.get("interval", 60))  # Default to 60 seconds
        
        # Get last run time from execution history
        last_run = config.get("_last_run")
        if not last_run:
            return True  # First run
        
        # Check if enough time has passed since last run
        time_diff = (current_time - last_run).total_seconds()
        return time_diff >= interval
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this trigger.
        
        Returns:
            Configuration schema
        """
        return {
            "interval": {
                "type": "integer",
                "description": "Time interval in seconds",
                "required": True
            },
            "start_delay": {
                "type": "integer",
                "description": "Delay before first execution in seconds",
                "required": False,
                "default": 0
            }
        } 