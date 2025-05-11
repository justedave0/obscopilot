"""
Integration tests for workflow engine with Twitch and OBS.

This module contains tests that verify the workflow engine properly integrates
with Twitch and OBS services.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.workflows.models import (
    Workflow, Trigger, Action, TriggerType, ActionType
)
from obscopilot.workflows.engine import WorkflowEngine
from obscopilot.twitch.client import TwitchClient
from obscopilot.obs.client import OBSClient
from obscopilot.ai.openai import OpenAIClient
from obscopilot.ai.googleai import GoogleAIClient


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock(spec=Config)
    config.get.return_value = {}
    return config


@pytest.fixture
def mock_repositories():
    """Mock repositories."""
    workflow_repo = MagicMock()
    trigger_repo = MagicMock()
    action_repo = MagicMock() 
    workflow_execution_repo = MagicMock()
    return {
        "workflow_repo": workflow_repo,
        "trigger_repo": trigger_repo,
        "action_repo": action_repo,
        "workflow_execution_repo": workflow_execution_repo
    }


@pytest.fixture
def mock_twitch():
    """Mock Twitch client."""
    client = MagicMock(spec=TwitchClient)
    client.send_chat_message = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture
def mock_obs():
    """Mock OBS client."""
    client = MagicMock(spec=OBSClient)
    client.set_scene = AsyncMock()
    client.set_source_visibility = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture
def mock_ai_clients():
    """Mock AI clients."""
    openai = MagicMock(spec=OpenAIClient)
    openai.generate_response = AsyncMock(return_value="AI response")
    
    googleai = MagicMock(spec=GoogleAIClient)
    googleai.generate_response = AsyncMock(return_value="Google AI response")
    
    return {"openai": openai, "googleai": googleai}


@pytest.fixture
def workflow_engine(mock_config, mock_repositories, mock_twitch, mock_obs, mock_ai_clients):
    """Create workflow engine with mocked dependencies."""
    engine = WorkflowEngine(
        config=mock_config,
        workflow_repo=mock_repositories["workflow_repo"],
        trigger_repo=mock_repositories["trigger_repo"],
        action_repo=mock_repositories["action_repo"],
        workflow_execution_repo=mock_repositories["workflow_execution_repo"],
        twitch_client=mock_twitch,
        obs_client=mock_obs,
        openai_client=mock_ai_clients["openai"],
        googleai_client=mock_ai_clients["googleai"]
    )
    return engine


@pytest.fixture
def chat_message_workflow():
    """Create a workflow triggered by chat messages."""
    return Workflow(
        name="Chat Response",
        description="Respond to chat messages",
        triggers=[
            Trigger(
                type=TriggerType.TWITCH_CHAT_MESSAGE.value,
                name="Chat Command",
                config={"pattern": "!hello"}
            )
        ],
        actions=[
            Action(
                type=ActionType.TWITCH_SEND_CHAT_MESSAGE.value,
                name="Send Response",
                config={"message": "Hello, {user}!"}
            )
        ]
    )


@pytest.fixture
def scene_switch_workflow():
    """Create a workflow for scene switching."""
    return Workflow(
        name="Scene Switch",
        description="Switch scene on channel points redemption",
        triggers=[
            Trigger(
                type=TriggerType.TWITCH_CHANNEL_POINTS_REDEEM.value,
                name="Points Redemption",
                config={"reward_id": "12345"}
            )
        ],
        actions=[
            Action(
                type=ActionType.OBS_SWITCH_SCENE.value,
                name="Switch Scene",
                config={"scene_name": "Closeup"}
            )
        ]
    )


class TestWorkflowIntegration:
    """Integration tests for workflow engine."""
    
    @pytest.mark.asyncio
    async def test_chat_message_trigger(
        self, workflow_engine, chat_message_workflow, mock_twitch
    ):
        """Test chat message trigger with response."""
        # Register workflow
        workflow_engine.register_workflow(chat_message_workflow)
        
        # Create chat message event
        event = Event(
            EventType.TWITCH_CHAT_MESSAGE,
            {
                "message": "!hello",
                "user": "test_user",
                "channel": "test_channel",
                "is_mod": False,
                "is_sub": False,
                "bits": 0
            }
        )
        
        # Trigger event
        await workflow_engine._handle_event(event)
        
        # Verify Twitch client was called with correct message
        mock_twitch.send_chat_message.assert_called_once()
        args = mock_twitch.send_chat_message.call_args[0]
        assert "Hello, test_user!" in args[0]
    
    @pytest.mark.asyncio
    async def test_channel_points_scene_switch(
        self, workflow_engine, scene_switch_workflow, mock_obs
    ):
        """Test channel points redemption triggering scene switch."""
        # Register workflow
        workflow_engine.register_workflow(scene_switch_workflow)
        
        # Create channel points redemption event
        event = Event(
            EventType.TWITCH_CHANNEL_POINTS_REDEEM,
            {
                "user": "test_user",
                "channel": "test_channel",
                "reward_id": "12345",
                "reward_title": "Switch Scene",
                "user_input": ""
            }
        )
        
        # Trigger event
        await workflow_engine._handle_event(event)
        
        # Verify OBS client was called with correct scene
        mock_obs.set_scene.assert_called_once_with("Closeup")
    
    @pytest.mark.asyncio
    async def test_ai_integration_workflow(self, workflow_engine, mock_ai_clients):
        """Test workflow with AI integration."""
        # Create AI workflow
        ai_workflow = Workflow(
            name="AI Response",
            description="Generate AI response to questions",
            triggers=[
                Trigger(
                    type=TriggerType.TWITCH_CHAT_MESSAGE.value,
                    name="Question Trigger",
                    config={"pattern": "!ask "}
                )
            ],
            actions=[
                Action(
                    type=ActionType.AI_GENERATE_RESPONSE.value,
                    name="Generate AI Response",
                    config={
                        "prompt": "{message}",
                        "system_prompt": "You are a helpful assistant",
                        "provider": "openai"
                    }
                ),
                Action(
                    type=ActionType.TWITCH_SEND_CHAT_MESSAGE.value,
                    name="Send AI Response",
                    config={"message": "{ai_response}"}
                )
            ]
        )
        
        # Register workflow
        workflow_engine.register_workflow(ai_workflow)
        
        # Create chat message event with question
        event = Event(
            EventType.TWITCH_CHAT_MESSAGE,
            {
                "message": "!ask What is the capital of France?",
                "user": "test_user",
                "channel": "test_channel",
                "is_mod": False,
                "is_sub": False,
                "bits": 0
            }
        )
        
        # Trigger event
        await workflow_engine._handle_event(event)
        
        # Verify OpenAI client was called
        mock_ai_clients["openai"].generate_response.assert_called_once()
        
        # Check that a message was sent with the AI response
        args = workflow_engine.twitch_client.send_chat_message.call_args[0]
        assert "AI response" in args[0] 