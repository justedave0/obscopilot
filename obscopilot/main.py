#!/usr/bin/env python3
"""
OBSCopilot - Twitch Live Assistant
Main Application Entry Point
"""

import sys
import logging
import asyncio
import argparse
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from obscopilot import __version__
from obscopilot.core.config import Config
from obscopilot.core.events import event_bus
from obscopilot.storage.database import Database
from obscopilot.storage.repositories import (
    WorkflowRepository, TriggerRepository, ActionRepository,
    WorkflowExecutionRepository, SettingRepository, TwitchAuthRepository
)
from obscopilot.ui.main import MainWindow
from obscopilot.twitch.client import TwitchClient
from obscopilot.obs.client import OBSClient
from obscopilot.obs.stream_health import StreamHealthMonitor
from obscopilot.workflows.engine import WorkflowEngine
from obscopilot.ai.openai import OpenAIClient
from obscopilot.ai.googleai import GoogleAIClient
from obscopilot.twitch.viewer_stats import ViewerStatsTracker

logger = logging.getLogger(__name__)


async def async_cleanup(components):
    """Perform asynchronous cleanup of application components.
    
    Args:
        components: List of components to clean up
    """
    for component in components:
        if hasattr(component, 'cleanup') and callable(component.cleanup):
            try:
                if asyncio.iscoroutinefunction(component.cleanup):
                    await component.cleanup()
                else:
                    component.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up component {component}: {e}")


def setup_logging(verbosity: int = 0) -> None:
    """Set up logging for the application.
    
    Args:
        verbosity: Verbosity level (0-2)
    """
    log_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    log_level = log_levels[min(verbosity, len(log_levels) - 1)]
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('obscopilot').setLevel(log_level)
    
    # Set third-party loggers to be less verbose
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)


async def async_main(config_path: str = None, verbosity: int = 0) -> int:
    """Run the application asynchronously.
    
    Args:
        config_path: Path to the config file
        verbosity: Verbosity level (0-2)
        
    Returns:
        Exit code
    """
    # Set up logging
    setup_logging(verbosity)
    
    logger.info(f"Starting OBSCopilot v{__version__}")
    
    # Initialize event bus
    event_bus.start()
    
    # Initialize components
    components = []
    
    try:
        # Initialize config
        config = Config(config_path)
        components.append(config)
        
        # Initialize database
        database = Database(config.get('database', 'path', ':memory:'))
        components.append(database)
        
        # Initialize repositories
        workflow_repo = WorkflowRepository(database)
        trigger_repo = TriggerRepository(database)
        action_repo = ActionRepository(database)
        workflow_execution_repo = WorkflowExecutionRepository(database)
        setting_repo = SettingRepository(database)
        twitch_auth_repo = TwitchAuthRepository(database)
        
        # Initialize Twitch client with authentication
        twitch_client = TwitchClient(config, twitch_auth_repo)
        components.append(twitch_client)
        await twitch_client.initialize()
        
        # Initialize OBS client
        obs_client = OBSClient(config)
        components.append(obs_client)
        
        # Initialize OpenAI client
        openai_client = OpenAIClient(config)
        components.append(openai_client)
        
        # Initialize Google AI client
        googleai_client = GoogleAIClient(config)
        components.append(googleai_client)
        
        # Initialize workflow engine
        workflow_engine = WorkflowEngine(
            config, workflow_repo, trigger_repo, action_repo, 
            workflow_execution_repo, twitch_client, obs_client, openai_client,
            googleai_client
        )
        components.append(workflow_engine)
        
        # Initialize viewer stats
        viewer_stats = ViewerStatsTracker(database)
        await viewer_stats.start()
        
        # Initialize stream health monitor
        stream_health_monitor = StreamHealthMonitor(
            obs_client,
            database,
            config
        )
        await stream_health_monitor.start()
        
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Create main window
        main_window = MainWindow(config)
        
        # Set dependencies
        main_window.set_dependencies(
            database, twitch_client, obs_client, workflow_engine,
            openai_client, googleai_client, workflow_repo, setting_repo, twitch_auth_repo
        )
        
        # Show main window
        main_window.show()
        
        # Exit code
        exit_code = await asyncio.get_event_loop().run_in_executor(
            None, app.exec
        )
        
        return exit_code
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1
    finally:
        # Clean up components in reverse order
        await async_cleanup(reversed(components))
        
        # Stop event bus
        await event_bus.stop()
        
        logger.info("OBSCopilot stopped")


def main() -> int:
    """Entry point for the application.
    
    Returns:
        Exit code
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='OBSCopilot - Twitch Live Assistant')
    parser.add_argument(
        '--config', '-c',
        help='Path to config file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help='Increase verbosity (can be used multiple times)'
    )
    parser.add_argument(
        '--version', '-V',
        action='version',
        version=f'OBSCopilot v{__version__}'
    )
    
    args = parser.parse_args()
    
    # Run async main with asyncio
    try:
        if sys.platform == 'win32':
            # Use ProactorEventLoop on Windows
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        exit_code = asyncio.run(async_main(args.config, args.verbose))
        return exit_code
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, exiting...")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main()) 