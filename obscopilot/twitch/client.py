"""
Twitch API client for OBSCopilot.

This module provides Twitch API integration using TwitchIO.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union

import twitchio
from twitchio.ext import commands, eventsub
from twitchio.ext.commands import Bot
from twitchio.models import ChatMessage

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventBus, EventType, event_bus

logger = logging.getLogger(__name__)


class TwitchClient:
    """Twitch API client for OBSCopilot."""
    
    def __init__(self, config: Config):
        """Initialize Twitch client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.event_bus = event_bus
        self.bot: Optional[OBSCopilotBot] = None
        self.connected = False
    
    async def connect(self) -> bool:
        """Connect to Twitch API.
        
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            logger.info("Connecting to Twitch API...")
            
            # Get credentials from config
            client_id = self.config.get('twitch', 'broadcaster_client_id')
            client_secret = self.config.get('twitch', 'broadcaster_client_secret')
            bot_id = self.config.get('twitch', 'bot_client_id')
            
            # Create bot instance
            self.bot = OBSCopilotBot(
                client_id=client_id,
                client_secret=client_secret,
                bot_id=bot_id,
                config=self.config,
                event_bus=self.event_bus
            )
            
            # Connect to Twitch
            await self.bot.start()
            
            self.connected = True
            await self.event_bus.emit(Event(EventType.TWITCH_CONNECTED))
            
            logger.info("Connected to Twitch API")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Twitch API: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Twitch API."""
        if self.bot and self.connected:
            try:
                logger.info("Disconnecting from Twitch API...")
                await self.bot.close()
                self.connected = False
                await self.event_bus.emit(Event(EventType.TWITCH_DISCONNECTED))
                logger.info("Disconnected from Twitch API")
            except Exception as e:
                logger.error(f"Error disconnecting from Twitch API: {e}")
    
    async def send_chat_message(self, channel: str, message: str) -> bool:
        """Send a message to a Twitch chat channel.
        
        Args:
            channel: Channel name to send message to
            message: Message content
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.bot or not self.connected:
            logger.error("Cannot send message, bot not connected")
            return False
        
        try:
            # Create a partial user for the channel
            user = self.bot.create_user(channel)
            
            # Send message as the bot
            await user.send_message(
                sender=self.bot.bot_id,
                message=message
            )
            
            logger.debug(f"Sent message to {channel}: {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to {channel}: {e}")
            return False


class OBSCopilotBot(Bot):
    """Custom Twitch bot implementation for OBSCopilot."""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        bot_id: str,
        config: Config,
        event_bus: EventBus
    ):
        """Initialize the bot.
        
        Args:
            client_id: Twitch application client ID
            client_secret: Twitch application client secret
            bot_id: Twitch bot user ID
            config: Application configuration
            event_bus: Event bus instance
        """
        self.app_config = config
        self.event_bus = event_bus
        
        # Initialize the bot
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            prefix='!'
        )
    
    async def setup_hook(self) -> None:
        """Set up the bot after initialization."""
        # Subscribe to events
        logger.info("Setting up Twitch event subscriptions...")
        
        try:
            # Get broadcaster ID from config
            broadcaster_id = self.app_config.get('twitch', 'broadcaster_id')
            
            if broadcaster_id:
                # Subscribe to chat messages
                chat_sub = eventsub.ChatMessageSubscription(
                    broadcaster_user_id=broadcaster_id,
                    user_id=self.bot_id
                )
                await self.subscribe_websocket(payload=chat_sub)
                
                # Subscribe to stream online events
                online_sub = eventsub.StreamOnlineSubscription(
                    broadcaster_user_id=broadcaster_id
                )
                await self.subscribe_websocket(payload=online_sub)
                
                # Subscribe to stream offline events
                offline_sub = eventsub.StreamOfflineSubscription(
                    broadcaster_user_id=broadcaster_id
                )
                await self.subscribe_websocket(payload=offline_sub)
                
                # Subscribe to channel follows
                follow_sub = eventsub.ChannelFollowSubscription(
                    broadcaster_user_id=broadcaster_id
                )
                await self.subscribe_websocket(payload=follow_sub)
                
                # Subscribe to channel subscriptions
                sub_sub = eventsub.ChannelSubscribeSubscription(
                    broadcaster_user_id=broadcaster_id
                )
                await self.subscribe_websocket(payload=sub_sub)
                
                # Subscribe to channel points redemptions
                points_sub = eventsub.ChannelPointsCustomRewardRedemptionAddSubscription(
                    broadcaster_user_id=broadcaster_id
                )
                await self.subscribe_websocket(payload=points_sub)
                
                # Subscribe to channel cheers
                cheer_sub = eventsub.ChannelCheerSubscription(
                    broadcaster_user_id=broadcaster_id
                )
                await self.subscribe_websocket(payload=cheer_sub)
                
                # Subscribe to channel raids
                raid_sub = eventsub.ChannelRaidSubscription(
                    to_broadcaster_user_id=broadcaster_id
                )
                await self.subscribe_websocket(payload=raid_sub)
                
                logger.info("Twitch event subscriptions set up successfully")
            else:
                logger.warning("Broadcaster ID not found in config, event subscriptions not set up")
        except Exception as e:
            logger.error(f"Error setting up Twitch event subscriptions: {e}")
    
    async def event_ready(self) -> None:
        """Handle bot ready event."""
        logger.info(f"Twitch bot logged in as {self.bot_id}")
        
        # Emit connected event
        await self.event_bus.emit(Event(EventType.TWITCH_CONNECTED))
    
    async def event_message(self, message: ChatMessage) -> None:
        """Handle chat message event.
        
        Args:
            message: The chat message
        """
        # Emit message event
        await self.event_bus.emit(Event(
            EventType.TWITCH_CHAT_MESSAGE,
            data={
                'channel': message.channel.name,
                'author': message.author.name,
                'content': message.content,
                'raw': message
            }
        ))
    
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        """Handle channel follow event.
        
        Args:
            payload: The follow event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_FOLLOW,
            data={
                'user_id': payload.user_id,
                'user_name': payload.user_name,
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'followed_at': payload.followed_at,
                'raw': payload
            }
        ))
    
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        """Handle channel subscription event.
        
        Args:
            payload: The subscription event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_SUBSCRIPTION,
            data={
                'user_id': payload.user_id,
                'user_name': payload.user_name,
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'tier': payload.tier,
                'is_gift': payload.is_gift,
                'raw': payload
            }
        ))
    
    async def event_cheer(self, payload: twitchio.ChannelCheer) -> None:
        """Handle channel cheer event.
        
        Args:
            payload: The cheer event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_BITS,
            data={
                'user_id': payload.user_id,
                'user_name': payload.user_name,
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'bits': payload.bits,
                'message': payload.message,
                'raw': payload
            }
        ))
    
    async def event_custom_redemption_add(self, payload: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Handle channel points redemption event.
        
        Args:
            payload: The redemption event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_CHANNEL_POINTS_REDEEM,
            data={
                'user_id': payload.user_id,
                'user_name': payload.user_login,
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_login,
                'reward_id': payload.reward.id,
                'reward_title': payload.reward.title,
                'reward_cost': payload.reward.cost,
                'user_input': payload.user_input,
                'status': payload.status,
                'raw': payload
            }
        ))
    
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        """Handle channel raid event.
        
        Args:
            payload: The raid event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_RAID,
            data={
                'from_user_id': payload.from_broadcaster_user_id,
                'from_user_name': payload.from_broadcaster_user_name,
                'to_user_id': payload.to_broadcaster_user_id,
                'to_user_name': payload.to_broadcaster_user_name,
                'viewers': payload.viewers,
                'raw': payload
            }
        ))
    
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        """Handle stream online event.
        
        Args:
            payload: The stream online event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_STREAM_ONLINE,
            data={
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'stream_type': payload.type,
                'started_at': payload.started_at,
                'raw': payload
            }
        ))
    
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        """Handle stream offline event.
        
        Args:
            payload: The stream offline event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_STREAM_OFFLINE,
            data={
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'raw': payload
            }
        )) 