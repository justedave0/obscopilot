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
from obscopilot.workflows.engine import WorkflowEngine
from obscopilot.ai.openai import OpenAIClient


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path.home() / '.obscopilot' / 'obscopilot.log')
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='OBSCopilot - Twitch Live Assistant'
    )
    parser.add_argument(
        '--version', 
        action='version', 
        version=f'OBSCopilot {__version__}'
    )
    parser.add_argument(
        '--config', 
        type=str, 
        help='Path to config file'
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug logging'
    )
    return parser.parse_args()


async def cleanup():
    """Clean up resources before exit."""
    logger.info("Shutting down event bus")
    await event_bus.stop()
    logger.info("Cleanup completed")


def main():
    """Main application entry point."""
    # Parse command line arguments
    args = parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting OBSCopilot {__version__}")
    
    # Ensure config directory exists
    config_dir = Path.home() / '.obscopilot'
    config_dir.mkdir(exist_ok=True)
    
    # Load configuration
    config_path = args.config if args.config else config_dir / 'config.toml'
    config = Config(config_path)
    
    # Initialize database
    database = Database(config)
    
    # Initialize repositories
    workflow_repo = WorkflowRepository(database)
    trigger_repo = TriggerRepository(database)
    action_repo = ActionRepository(database)
    execution_repo = WorkflowExecutionRepository(database)
    setting_repo = SettingRepository(database)
    twitch_auth_repo = TwitchAuthRepository(database)
    
    # Start the event bus
    logger.info("Starting event bus")
    event_bus.start()
    
    # Initialize clients
    twitch_client = TwitchClient(config)
    obs_client = OBSClient(config)
    openai_client = OpenAIClient(config)
    
    # Initialize workflow engine
    workflow_engine = WorkflowEngine(config, twitch_client, obs_client)
    
    # Initialize application
    app = QApplication(sys.argv)
    app.setApplicationName("OBSCopilot")
    app.setApplicationVersion(__version__)
    
    # Create main window
    window = MainWindow(config)
    
    # Set up dependencies
    window.set_dependencies(
        database=database,
        twitch_client=twitch_client,
        obs_client=obs_client,
        workflow_engine=workflow_engine,
        openai_client=openai_client,
        workflow_repo=workflow_repo,
        setting_repo=setting_repo,
        twitch_auth_repo=twitch_auth_repo
    )
    
    window.show()
    
    # Load workflows
    asyncio.create_task(workflow_engine.load_workflows())
    
    # Set up cleanup on application exit
    app.aboutToQuit.connect(lambda: asyncio.run(cleanup()))
    
    # Run application
    return app.exec()


if __name__ == "__main__":
    sys.exit(main()) 