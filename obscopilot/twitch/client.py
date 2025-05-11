"""
Twitch API client for OBSCopilot.

This module provides Twitch API integration using TwitchIO.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Callable, Any

import twitchio
from twitchio.ext import commands, eventsub
from twitchio.ext.commands import Bot
from twitchio.models import ChatMessage

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.storage.repositories import TwitchAuthRepository
from obscopilot.twitch.auth import TwitchAuthManager

logger = logging.getLogger(__name__)


class TwitchClient:
    """Twitch API client for OBSCopilot."""
    
    def __init__(self, config: Config, auth_repo: TwitchAuthRepository):
        """Initialize Twitch client.
        
        Args:
            config: Application configuration
            auth_repo: Twitch authentication repository
        """
        self.config = config
        self.event_bus = event_bus
        self.auth_repo = auth_repo
        self.auth_manager = TwitchAuthManager(config, auth_repo)
        self.bot: Optional[OBSCopilotBot] = None
        self.connected = False
        self.event_subscriptions = {}  # Track active event subscriptions
    
    async def initialize(self) -> None:
        """Initialize the Twitch client and authentication systems."""
        # Start OAuth callback server
        await self.auth_manager.start_callback_server()
        
        # Check if we have valid tokens for broadcaster and bot
        broadcaster_authenticated = self.auth_manager.is_authenticated('broadcaster')
        bot_authenticated = self.auth_manager.is_authenticated('bot')
        
        logger.info(f"Broadcaster authenticated: {broadcaster_authenticated}")
        logger.info(f"Bot authenticated: {bot_authenticated}")
    
    async def connect(self) -> bool:
        """Connect to Twitch API.
        
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            logger.info("Connecting to Twitch API...")
            
            # Get credentials from config
            broadcaster_client_id = self.config.get('twitch', 'broadcaster_client_id')
            broadcaster_client_secret = self.config.get('twitch', 'broadcaster_client_secret')
            
            # Check if we have authenticated accounts
            broadcaster_id = self.config.get('twitch', 'broadcaster_id')
            bot_id = self.config.get('twitch', 'bot_id')
            
            if not broadcaster_id:
                logger.error("Cannot connect: No broadcaster account authenticated")
                return False
            
            # Create bot instance
            self.bot = OBSCopilotBot(
                client_id=broadcaster_client_id,
                client_secret=broadcaster_client_secret,
                broadcaster_id=broadcaster_id,
                bot_id=bot_id,
                config=self.config,
                event_bus=self.event_bus,
                auth_manager=self.auth_manager
            )
            
            # Connect to Twitch
            await self.bot.start()
            
            self.connected = True
            await self.event_bus.emit(Event(EventType.TWITCH_CONNECTED))
            
            logger.info("Connected to Twitch API")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Twitch API: {e}", exc_info=True)
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
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        # Stop OAuth callback server
        await self.auth_manager.stop_callback_server()
        
        # Disconnect from Twitch if connected
        if self.connected:
            await self.disconnect()
    
    async def authenticate_broadcaster(self, callback: Optional[Callable] = None) -> str:
        """Authenticate the broadcaster account using OAuth.
        
        Args:
            callback: Optional callback function to call when authentication is completed
            
        Returns:
            The URL to navigate to for authentication
        """
        return self.auth_manager.start_auth_flow('broadcaster', callback)
    
    async def authenticate_bot(self, callback: Optional[Callable] = None) -> str:
        """Authenticate the bot account using OAuth.
        
        Args:
            callback: Optional callback function to call when authentication is completed
            
        Returns:
            The URL to navigate to for authentication
        """
        return self.auth_manager.start_auth_flow('bot', callback)
    
    async def revoke_broadcaster_auth(self) -> bool:
        """Revoke the broadcaster's OAuth token.
        
        Returns:
            True if revocation was successful
        """
        broadcaster_id = self.config.get('twitch', 'broadcaster_id')
        if not broadcaster_id:
            logger.warning("No broadcaster account to revoke")
            return False
        
        return await self.auth_manager.revoke_token(broadcaster_id)
    
    async def revoke_bot_auth(self) -> bool:
        """Revoke the bot's OAuth token.
        
        Returns:
            True if revocation was successful
        """
        bot_id = self.config.get('twitch', 'bot_id')
        if not bot_id:
            logger.warning("No bot account to revoke")
            return False
        
        return await self.auth_manager.revoke_token(bot_id)
    
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
            
            # Get the bot ID to use as sender
            sender_id = self.config.get('twitch', 'bot_id') or self.config.get('twitch', 'broadcaster_id')
            
            # Send message
            await user.send_message(
                sender=sender_id,
                message=message
            )
            
            logger.debug(f"Sent message to {channel}: {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to {channel}: {e}")
            return False
    
    async def get_followers(self, count: int = 20) -> List[Dict[str, Any]]:
        """Get a list of recent followers for the broadcaster.
        
        Args:
            count: Maximum number of followers to retrieve
            
        Returns:
            List of follower data
        """
        if not self.bot or not self.connected:
            logger.error("Cannot get followers, bot not connected")
            return []
        
        try:
            broadcaster_id = self.config.get('twitch', 'broadcaster_id')
            if not broadcaster_id:
                logger.error("Broadcaster ID not found in config")
                return []
            
            followers = []
            async for follower in self.bot.fetch_users_follows(to_id=broadcaster_id, first=count):
                followers.append({
                    'user_id': follower.from_id,
                    'username': follower.from_name,
                    'followed_at': follower.followed_at.isoformat() if follower.followed_at else None
                })
            
            return followers
        except Exception as e:
            logger.error(f"Error getting followers: {e}")
            return []
    
    async def get_stream_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the broadcaster's current stream.
        
        Returns:
            Stream information if live, None otherwise
        """
        if not self.bot or not self.connected:
            logger.error("Cannot get stream info, bot not connected")
            return None
        
        try:
            broadcaster_id = self.config.get('twitch', 'broadcaster_id')
            if not broadcaster_id:
                logger.error("Broadcaster ID not found in config")
                return None
            
            streams = await self.bot.fetch_streams(user_ids=[broadcaster_id])
            if not streams:
                return None
            
            stream = streams[0]
            return {
                'id': stream.id,
                'title': stream.title,
                'game_name': stream.game_name,
                'viewer_count': stream.viewer_count,
                'started_at': stream.started_at.isoformat() if stream.started_at else None,
                'is_mature': stream.is_mature,
                'tags': stream.tags
            }
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return None


class OBSCopilotBot(Bot):
    """Custom Twitch bot implementation for OBSCopilot."""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        broadcaster_id: str,
        bot_id: Optional[str],
        config: Config,
        event_bus: EventType,
        auth_manager: TwitchAuthManager
    ):
        """Initialize the bot.
        
        Args:
            client_id: Twitch application client ID
            client_secret: Twitch application client secret
            broadcaster_id: Twitch broadcaster user ID
            bot_id: Twitch bot user ID (can be None if using broadcaster as bot)
            config: Application configuration
            event_bus: Event bus instance
            auth_manager: Twitch authentication manager
        """
        self.app_config = config
        self.event_bus = event_bus
        self.auth_manager = auth_manager
        self.broadcaster_id = broadcaster_id
        self.bot_id = bot_id or broadcaster_id  # Use broadcaster as bot if no bot ID provided
        
        # Initialize the bot
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=self.bot_id,
            prefix='!'
        )
        
        # Track custom event subscriptions
        self.event_subs = {}
    
    async def setup_hook(self) -> None:
        """Set up the bot after initialization."""
        # Subscribe to events
        logger.info("Setting up Twitch event subscriptions...")
        
        try:
            # Load access tokens for broadcaster and bot users
            await self._load_tokens()
            
            # Set up event subscriptions
            await self._setup_event_subscriptions()
        except Exception as e:
            logger.error(f"Error setting up bot: {e}", exc_info=True)
    
    async def _load_tokens(self) -> None:
        """Load access tokens for broadcaster and bot."""
        try:
            # Get broadcaster token
            broadcaster_token = await self.auth_manager.get_access_token(self.broadcaster_id)
            if broadcaster_token:
                await self.add_token(broadcaster_token, "refresh_tokens_not_needed_here")
                logger.info(f"Loaded broadcaster token for user ID: {self.broadcaster_id}")
            
            # Get bot token if different from broadcaster
            if self.bot_id != self.broadcaster_id:
                bot_token = await self.auth_manager.get_access_token(self.bot_id)
                if bot_token:
                    await self.add_token(bot_token, "refresh_tokens_not_needed_here")
                    logger.info(f"Loaded bot token for user ID: {self.bot_id}")
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            raise
    
    async def _setup_event_subscriptions(self) -> None:
        """Set up EventSub subscriptions for various events."""
        logger.info("Setting up Twitch event subscriptions...")
        
        # Subscribe to chat messages
        chat_sub = eventsub.ChatMessageSubscription(
            broadcaster_user_id=self.broadcaster_id,
            user_id=self.bot_id
        )
        await self.subscribe_websocket(payload=chat_sub)
        
        # Subscribe to stream online events
        online_sub = eventsub.StreamOnlineSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=online_sub)
        
        # Subscribe to stream offline events
        offline_sub = eventsub.StreamOfflineSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=offline_sub)
        
        # Subscribe to channel follows
        follow_sub = eventsub.ChannelFollowSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=follow_sub)
        
        # Subscribe to channel subscriptions
        sub_sub = eventsub.ChannelSubscribeSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=sub_sub)
        
        # Subscribe to channel points redemptions
        points_sub = eventsub.ChannelPointsCustomRewardRedemptionAddSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=points_sub)
        
        # Subscribe to channel cheers
        cheer_sub = eventsub.ChannelCheerSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=cheer_sub)
        
        # Subscribe to channel raids
        raid_sub = eventsub.ChannelRaidSubscription(
            to_broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=raid_sub)
        
        # Subscribe to hype train events
        hype_train_begin_sub = eventsub.HypeTrainBeginSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=hype_train_begin_sub)
        
        # Subscribe to poll events
        poll_begin_sub = eventsub.ChannelPollBeginSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=poll_begin_sub)
        
        # Subscribe to prediction events
        prediction_begin_sub = eventsub.ChannelPredictionBeginSubscription(
            broadcaster_user_id=self.broadcaster_id
        )
        await self.subscribe_websocket(payload=prediction_begin_sub)
        
        logger.info("Twitch event subscriptions set up successfully")
    
    async def event_token_refreshed(self, payload: twitchio.TokenRefreshedPayload) -> None:
        """Handle token refreshed event.
        
        Args:
            payload: Token refresh payload
        """
        logger.info(f"TwitchIO refreshed token for user ID: {payload.user_id}")
        
        # Update token in our auth manager
        # We don't need to do anything as we're managing token refresh ourselves
    
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
                'author_id': message.author.id,
                'content': message.content,
                'is_mod': message.author.is_mod,
                'is_subscriber': message.author.is_subscriber,
                'badges': message.author.badges,
                'timestamp': message.timestamp.isoformat() if message.timestamp else None,
                'raw': message.raw_data
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
                'followed_at': payload.followed_at.isoformat() if payload.followed_at else None
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
                'is_gift': payload.is_gift
            }
        ))
    
    async def event_subscription_gift(self, payload: twitchio.ChannelSubscriptionGift) -> None:
        """Handle subscription gift event.
        
        Args:
            payload: The subscription gift event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_SUBSCRIPTION_GIFT,
            data={
                'user_id': payload.user_id,
                'user_name': payload.user_name,
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'tier': payload.tier,
                'total': payload.total,
                'cumulative_total': payload.cumulative_total
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
                'is_anonymous': payload.is_anonymous
            }
        ))
    
    async def event_custom_redemption_add(self, payload: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Handle channel points redemption event.
        
        Args:
            payload: The channel points redemption event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_CHANNEL_POINTS_REDEEM,
            data={
                'user_id': payload.user_id,
                'user_name': payload.user_name,
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'reward_id': payload.reward.id,
                'reward_title': payload.reward.title,
                'reward_cost': payload.reward.cost,
                'reward_prompt': payload.reward.prompt,
                'user_input': payload.user_input,
                'status': payload.status
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
                'viewers': payload.viewers
            }
        ))
    
    async def event_hype_train(self, payload: twitchio.HypeTrainBegin) -> None:
        """Handle hype train begin event.
        
        Args:
            payload: The hype train event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_HYPE_TRAIN_BEGIN,
            data={
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'total': payload.total,
                'progress': payload.progress,
                'goal': payload.goal,
                'started_at': payload.started_at.isoformat() if payload.started_at else None,
                'expires_at': payload.expires_at.isoformat() if payload.expires_at else None,
                'last_contribution': {
                    'user_id': payload.last_contribution.user_id,
                    'user_name': payload.last_contribution.user_name,
                    'type': payload.last_contribution.type,
                    'total': payload.last_contribution.total
                }
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
                'type': payload.type,
                'started_at': payload.started_at.isoformat() if payload.started_at else None
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
                'broadcaster_name': payload.broadcaster_user_name
            }
        ))
    
    async def event_poll_begin(self, payload: twitchio.ChannelPollBegin) -> None:
        """Handle poll begin event.
        
        Args:
            payload: The poll begin event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_POLL_BEGIN,
            data={
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'poll_id': payload.id,
                'title': payload.title,
                'choices': [{'id': choice.id, 'title': choice.title} for choice in payload.choices],
                'bits_voting_enabled': payload.bits_voting.is_enabled,
                'bits_per_vote': payload.bits_voting.amount_per_vote if payload.bits_voting.is_enabled else 0,
                'channel_points_voting_enabled': payload.channel_points_voting.is_enabled,
                'channel_points_per_vote': payload.channel_points_voting.amount_per_vote if payload.channel_points_voting.is_enabled else 0,
                'started_at': payload.started_at.isoformat() if payload.started_at else None,
                'ends_at': payload.ends_at.isoformat() if payload.ends_at else None
            }
        ))
    
    async def event_prediction_begin(self, payload: twitchio.ChannelPredictionBegin) -> None:
        """Handle prediction begin event.
        
        Args:
            payload: The prediction begin event payload
        """
        await self.event_bus.emit(Event(
            EventType.TWITCH_PREDICTION_BEGIN,
            data={
                'broadcaster_id': payload.broadcaster_user_id,
                'broadcaster_name': payload.broadcaster_user_name,
                'prediction_id': payload.id,
                'title': payload.title,
                'outcomes': [{'id': outcome.id, 'title': outcome.title, 'color': outcome.color} for outcome in payload.outcomes],
                'prediction_window': payload.prediction_window,
                'started_at': payload.started_at.isoformat() if payload.started_at else None,
                'locks_at': payload.locks_at.isoformat() if payload.locks_at else None
            }
        )) 