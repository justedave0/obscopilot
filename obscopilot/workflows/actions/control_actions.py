"""
Control flow actions for the workflow engine.

This module implements control flow workflow actions.
"""

import asyncio
import logging
import os
import subprocess
import aiohttp
import json
import time
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from obscopilot.workflows.models import WorkflowAction, WorkflowContext
from obscopilot.workflows.actions.base import BaseAction, TemplateableMixin, ConditionalMixin, RetryableMixin

logger = logging.getLogger(__name__)


class BaseControlAction(BaseAction, TemplateableMixin):
    """Base class for control flow actions."""
    pass


class DelayAction(BaseControlAction):
    """Action to delay workflow execution."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> bool:
        """Delay workflow execution.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            True always
        """
        try:
            config = action.config
            
            # Get delay duration in seconds
            duration_str = cls.resolve_template(str(config.get("duration", "1")), context)
            try:
                duration = float(duration_str)
            except ValueError:
                logger.warning(f"Invalid delay duration: {duration_str}, using default of 1 second")
                duration = 1.0
            
            # Ensure duration is positive
            duration = max(0.0, duration)
            
            logger.info(f"Delaying workflow for {duration} seconds")
            
            # Sleep for the specified duration
            await asyncio.sleep(duration)
            
            # Store the actual delay in the context
            context.set_variable(f"delay_duration_{action.id}", duration)
            
            return True
        except Exception as e:
            logger.error(f"Error in DelayAction: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "duration": {
                "type": "number",
                "description": "Delay duration in seconds",
                "default": 1.0,
                "minimum": 0.0,
                "required": True
            }
        }


class ConditionalAction(BaseControlAction, ConditionalMixin):
    """Action to conditionally execute other actions."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> bool:
        """Conditionally execute actions based on a condition.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            True if condition was evaluated, False on error
        """
        try:
            config = action.config
            
            # Get condition
            condition = config.get("condition", {})
            if not condition:
                logger.warning("No condition specified, defaulting to true")
                result = True
            else:
                # Evaluate condition
                result = cls.evaluate_condition(condition, context)
            
            # Store result in context variables
            context.set_variable(f"condition_result_{action.id}", result)
            
            # Log result
            condition_name = config.get("name", "Unnamed condition")
            logger.info(f"Condition '{condition_name}' evaluated to: {result}")
            
            # Return the result
            return result
        except Exception as e:
            logger.error(f"Error in ConditionalAction: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "name": {
                "type": "string",
                "description": "Name of the condition for logging",
                "default": "Unnamed condition",
                "required": False
            },
            "condition": {
                "type": "object",
                "description": "Condition to evaluate",
                "required": True,
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type of condition",
                        "enum": ["equals", "not_equals", "contains", "not_contains", "greater_than", "less_than", "regex_match"],
                        "default": "equals"
                    },
                    "left": {
                        "type": "string",
                        "description": "Left operand (can be a variable reference)",
                        "required": True
                    },
                    "right": {
                        "type": "string",
                        "description": "Right operand (can be a variable reference)",
                        "required": True
                    },
                    "convert_to_number": {
                        "type": "boolean",
                        "description": "Convert operands to numbers before comparison",
                        "default": False
                    }
                }
            }
        }


class WebhookAction(BaseControlAction, RetryableMixin):
    """Action to send a webhook request."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> Optional[Dict[str, Any]]:
        """Send a webhook request.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            Response data or None on error
        """
        try:
            config = action.config
            
            # Get URL
            url = cls.resolve_template(config.get("url", ""), context)
            if not url:
                logger.warning("No URL provided for webhook")
                return None
            
            # Get method
            method = config.get("method", "POST").upper()
            
            # Get headers
            headers = config.get("headers", {})
            # Resolve any template variables in headers
            resolved_headers = {}
            for key, value in headers.items():
                if isinstance(value, str):
                    resolved_headers[key] = cls.resolve_template(value, context)
                else:
                    resolved_headers[key] = value
            
            # Get payload
            payload = config.get("payload", {})
            # Resolve any template variables in payload
            resolved_payload = cls._resolve_payload(payload, context)
            
            # Get timeout
            timeout = float(config.get("timeout", 30.0))
            
            # Send request with retry logic
            logger.info(f"Sending webhook {method} request to {url}")
            
            async def _send_request():
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=resolved_headers,
                        json=resolved_payload if method in ["POST", "PUT", "PATCH"] else None,
                        params=resolved_payload if method == "GET" else None,
                        timeout=timeout
                    ) as response:
                        # Check if response was successful
                        response.raise_for_status()
                        
                        # Get response data
                        try:
                            data = await response.json()
                        except:
                            data = await response.text()
                        
                        return {
                            "status": response.status,
                            "data": data,
                            "headers": dict(response.headers)
                        }
            
            # Execute request with retry logic
            result = await cls.execute_with_retry(_send_request, action)
            
            # Store result in context variables
            context.set_variable(f"webhook_result_{action.id}", result)
            
            return result
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in WebhookAction: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in WebhookAction: {e}")
            return None
    
    @classmethod
    def _resolve_payload(cls, payload: Any, context: WorkflowContext) -> Any:
        """Recursively resolve template variables in payload.
        
        Args:
            payload: Payload to resolve
            context: Workflow context
            
        Returns:
            Resolved payload
        """
        if isinstance(payload, str):
            return cls.resolve_template(payload, context)
        elif isinstance(payload, dict):
            return {k: cls._resolve_payload(v, context) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [cls._resolve_payload(item, context) for item in payload]
        else:
            return payload
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "url": {
                "type": "string",
                "description": "Webhook URL",
                "required": True
            },
            "method": {
                "type": "string",
                "description": "HTTP method",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                "default": "POST",
                "required": False
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers",
                "default": {},
                "required": False
            },
            "payload": {
                "type": "object",
                "description": "Webhook payload",
                "default": {},
                "required": False
            },
            "timeout": {
                "type": "number",
                "description": "Request timeout in seconds",
                "default": 30.0,
                "minimum": 1.0,
                "required": False
            }
        }


class RunProcessAction(BaseControlAction):
    """Action to run an external process."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """Run an external process.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            Process result
        """
        try:
            config = action.config
            
            # Get command
            command = cls.resolve_template(config.get("command", ""), context)
            if not command:
                logger.warning("No command provided for process")
                return {"success": False, "error": "No command provided"}
            
            # Get working directory
            working_dir = cls.resolve_template(config.get("working_dir", ""), context)
            if working_dir and not os.path.isdir(working_dir):
                logger.warning(f"Working directory does not exist: {working_dir}")
                working_dir = None
            
            # Get environment variables
            env_vars = config.get("env", {})
            # Resolve any template variables in env vars
            resolved_env = {}
            for key, value in env_vars.items():
                if isinstance(value, str):
                    resolved_env[key] = cls.resolve_template(value, context)
                else:
                    resolved_env[key] = str(value)
            
            # Get timeout
            timeout = float(config.get("timeout", 60.0))
            
            # Check if we should capture output
            capture_output = config.get("capture_output", True)
            
            # Check if we should run in shell
            shell = config.get("shell", False)
            
            logger.info(f"Running process: {command}")
            
            # Run process
            start_time = time.time()
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                cwd=working_dir,
                env={**os.environ, **resolved_env} if resolved_env else None,
                shell=shell
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Build result
                result = {
                    "success": process.returncode == 0,
                    "return_code": process.returncode,
                    "stdout": stdout_str if capture_output else None,
                    "stderr": stderr_str if capture_output else None,
                    "execution_time": execution_time
                }
                
                # Store result in context variables
                context.set_variable(f"process_result_{action.id}", result)
                
                # Log result
                if process.returncode == 0:
                    logger.info(f"Process completed successfully in {execution_time:.2f}s")
                else:
                    logger.warning(f"Process failed with return code {process.returncode}")
                
                return result
                
            except asyncio.TimeoutError:
                # Process timed out
                logger.warning(f"Process timed out after {timeout}s: {command}")
                
                # Try to terminate the process
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if termination doesn't work
                    process.kill()
                
                result = {
                    "success": False,
                    "return_code": None,
                    "error": f"Process timed out after {timeout}s",
                    "stdout": None,
                    "stderr": None,
                    "execution_time": time.time() - start_time
                }
                
                # Store result in context variables
                context.set_variable(f"process_result_{action.id}", result)
                
                return result
            
        except Exception as e:
            logger.error(f"Error in RunProcessAction: {e}")
            
            result = {
                "success": False,
                "error": str(e)
            }
            
            # Store result in context variables
            context.set_variable(f"process_result_{action.id}", result)
            
            return result
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "command": {
                "type": "string",
                "description": "Command to run",
                "required": True
            },
            "working_dir": {
                "type": "string",
                "description": "Working directory for the process",
                "required": False
            },
            "env": {
                "type": "object",
                "description": "Environment variables",
                "default": {},
                "required": False
            },
            "timeout": {
                "type": "number",
                "description": "Process timeout in seconds",
                "default": 60.0,
                "minimum": 1.0,
                "required": False
            },
            "capture_output": {
                "type": "boolean",
                "description": "Whether to capture process output",
                "default": True,
                "required": False
            },
            "shell": {
                "type": "boolean",
                "description": "Whether to run the command in a shell",
                "default": False,
                "required": False
            }
        }


class SendEmailAction(BaseControlAction, RetryableMixin):
    """Action to send an email."""
    
    @classmethod
    async def execute(cls, action: WorkflowAction, context: WorkflowContext, **kwargs) -> bool:
        """Send an email.
        
        Args:
            action: Action configuration
            context: Workflow execution context
            
        Returns:
            True if email was sent, False otherwise
        """
        try:
            import smtplib
            from email.message import EmailMessage
            import asyncio
            
            config = action.config
            
            # Get recipient(s)
            to = cls.resolve_template(config.get("to", ""), context)
            if not to:
                logger.warning("No recipient provided for email")
                return False
            
            # Get subject
            subject = cls.resolve_template(config.get("subject", ""), context)
            
            # Get body
            body = cls.resolve_template(config.get("body", ""), context)
            
            # Get sender (if not using default)
            from_email = cls.resolve_template(config.get("from", ""), context)
            
            # Get SMTP settings from action config or kwargs
            smtp_config = config.get("smtp", {})
            if not smtp_config:
                # Try to get from kwargs
                smtp_config = kwargs.get("config", {}).get("email", {}).get("smtp", {})
            
            if not smtp_config:
                logger.warning("No SMTP configuration provided for email")
                return False
            
            # Get SMTP server settings
            smtp_host = smtp_config.get("host", "localhost")
            smtp_port = int(smtp_config.get("port", 25))
            smtp_user = smtp_config.get("username")
            smtp_pass = smtp_config.get("password")
            smtp_use_tls = smtp_config.get("use_tls", False)
            
            logger.info(f"Sending email to {to} with subject: {subject}")
            
            # Create email message
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = from_email if from_email else smtp_user
            msg['To'] = to
            msg.set_content(body)
            
            # Function to send email
            async def send_email():
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, cls._send_email_sync, 
                    msg, smtp_host, smtp_port, smtp_user, smtp_pass, smtp_use_tls)
            
            # Send email with retry if configured
            if action.retry and action.retry.get("max_attempts", 1) > 1:
                result = await cls.execute_with_retry(send_email, action)
            else:
                result = await send_email()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in SendEmailAction: {e}")
            return False
    
    @staticmethod
    def _send_email_sync(msg, smtp_host, smtp_port, smtp_user, smtp_pass, smtp_use_tls):
        """Send email synchronously.
        
        Args:
            msg: Email message
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_pass: SMTP password
            smtp_use_tls: Whether to use TLS
            
        Returns:
            True if email was sent, False otherwise
        """
        import smtplib
        
        try:
            # Connect to SMTP server
            if smtp_use_tls:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                
                # Start TLS if not using SSL but TLS is available
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    # TLS not supported, continue without it
                    pass
            
            # Login if credentials provided
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            
            # Send email
            server.send_message(msg)
            
            # Close connection
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get the configuration schema for this action.
        
        Returns:
            Configuration schema
        """
        return {
            "to": {
                "type": "string",
                "description": "Email recipient(s), comma-separated for multiple",
                "required": True
            },
            "subject": {
                "type": "string",
                "description": "Email subject",
                "required": True
            },
            "body": {
                "type": "string",
                "description": "Email body",
                "required": True
            },
            "from": {
                "type": "string",
                "description": "Email sender (if not using default)",
                "required": False
            },
            "smtp": {
                "type": "object",
                "description": "SMTP configuration (if not using global config)",
                "required": False,
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "SMTP server hostname",
                        "default": "localhost"
                    },
                    "port": {
                        "type": "integer",
                        "description": "SMTP server port",
                        "default": 25
                    },
                    "username": {
                        "type": "string",
                        "description": "SMTP username"
                    },
                    "password": {
                        "type": "string",
                        "description": "SMTP password"
                    },
                    "use_tls": {
                        "type": "boolean",
                        "description": "Whether to use TLS",
                        "default": false
                    }
                }
            }
        } 