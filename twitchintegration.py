"""
OBSCopilot Twitch Integration Module

This module handles the Twitch API integration, including authentication,
event subscription, and Twitch API calls.
"""

import os
import time
import logging
import asyncio
import threading
import webbrowser
import http.server
import urllib.parse
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union

# Configure logging
logger = logging.getLogger("OBSCopilot.TwitchIntegration")

# Try to import twitchio
try:
    import twitchio
    from twitchio.ext import commands, eventsub
    HAVE_TWITCHIO = True
except ImportError:
    HAVE_TWITCHIO = False
    logger.error("twitchio module not found, Twitch integration disabled")
    logger.error("Install with: pip install twitchio")

# Event history
event_history = []

class TwitchAuthServer(http.server.HTTPServer):
    """Simple HTTP server to handle Twitch OAuth redirect"""
    
    def __init__(self, client_id: str, client_secret: str, server_address: tuple, handler_class, is_bot: bool = False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.is_bot = is_bot
        self.auth_response = None
        super().__init__(server_address, handler_class)

class TwitchAuthHandler(http.server.BaseHTTPRequestHandler):
    """Handler for Twitch OAuth callback"""
    
    def do_GET(self):
        """Handle GET request"""
        try:
            # Parse URL and extract query parameters
            parsed_path = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_path.query)
            
            if parsed_path.path == '/callback' and 'code' in query:
                # Got authorization code, exchange for token
                auth_code = query['code'][0]
                self.exchange_code(auth_code)
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                response = """
                <html>
                <head><title>Authorization Successful</title></head>
                <body>
                <h1>Authorization Successful!</h1>
                <p>You can now close this window and return to OBS.</p>
                <script>window.close();</script>
                </body>
                </html>
                """
                self.wfile.write(response.encode())
            else:
                # Handle root or other paths
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><head><title>Waiting for authorization...</title></head><body><h1>Waiting for Twitch authorization...</h1></body></html>')
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.send_error(500)
    
    def exchange_code(self, code: str):
        """Exchange authorization code for access token"""
        server = self.server
        
        # Prepare token request
        token_url = "https://id.twitch.tv/oauth2/token"
        redirect_uri = f"http://localhost:{server.server_address[1]}/callback"
        
        # Make token request
        import requests
        response = requests.post(token_url, data={
            'client_id': server.client_id,
            'client_secret': server.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        })
        
        if response.status_code == 200:
            token_data = response.json()
            server.auth_response = token_data
            logger.info("Successfully obtained token")
            
            # Notify auth callback if registered
            if hasattr(server, 'auth_callback') and callable(server.auth_callback):
                account_type = "bot" if server.is_bot else "broadcaster"
                server.auth_callback(account_type, token_data)
        else:
            logger.error(f"Failed to exchange code: {response.text}")
    
    def log_message(self, format, *args):
        """Suppress server logs"""
        return

class TwitchBot(commands.Bot):
    """Twitch bot for handling chat commands and events"""
    
    def __init__(self, broadcaster_token: str, bot_token: Optional[str] = None,
                 client_id: str = "", client_secret: str = "", event_callback: Optional[Callable] = None):
        """Initialize the Twitch bot
        
        Args:
            broadcaster_token: The broadcaster's OAuth token
            bot_token: Optional separate bot account OAuth token
            client_id: Twitch API Client ID
            client_secret: Twitch API Client Secret
            event_callback: Optional callback function for events
        """
        # Store tokens
        self.broadcaster_token = broadcaster_token
        self.bot_token = bot_token
        
        # Determine which token to use for the bot
        token = bot_token if bot_token else broadcaster_token
        
        # Store callback
        self.event_callback = event_callback
        
        # User IDs (filled in on connection)
        self.broadcaster_user_id = None
        self.bot_user_id = None
        
        # Initialize the bot
        super().__init__(
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            prefix="!",
        )
    
    async def event_ready(self):
        """Called once when the bot is connected"""
        # Get bot user ID
        bot_user = await self.fetch_users([self.nick])
        if bot_user:
            self.bot_user_id = bot_user[0].id
            logger.info(f"Bot connected as {self.nick} (ID: {self.bot_user_id})")
            
            # If event callback is registered, call it
            if self.event_callback:
                self.event_callback('bot_connected', {
                    'username': self.nick,
                    'user_id': self.bot_user_id
                })
        
        # Get broadcaster user ID if using different accounts
        if self.bot_token:
            # Need to make a separate request with the broadcaster token
            user = await self.fetch_users(oauth_token=self.broadcaster_token)
            if user:
                self.broadcaster_user_id = user[0].id
                logger.info(f"Broadcaster identified as {user[0].name} (ID: {self.broadcaster_user_id})")
                
                # If event callback is registered, call it
                if self.event_callback:
                    self.event_callback('broadcaster_identified', {
                        'username': user[0].name,
                        'user_id': self.broadcaster_user_id
                    })
        else:
            # Bot and broadcaster are the same
            self.broadcaster_user_id = self.bot_user_id
        
        # Subscribe to events
        await self.subscribe_to_events()
    
    async def subscribe_to_events(self):
        """Subscribe to Twitch EventSub events"""
        try:
            if not self.broadcaster_user_id:
                logger.error("Cannot subscribe to events: broadcaster_user_id not set")
                return
            
            # List of event subscriptions to create
            subscriptions = [
                # Channel events
                eventsub.ChannelFollowSubscription(broadcaster_user_id=self.broadcaster_user_id),
                eventsub.ChannelSubscribeSubscription(broadcaster_user_id=self.broadcaster_user_id),
                eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=self.broadcaster_user_id),
                eventsub.ChannelSubscriptionMessageSubscription(broadcaster_user_id=self.broadcaster_user_id),
                eventsub.ChannelCheerSubscription(broadcaster_user_id=self.broadcaster_user_id),
                eventsub.ChannelRaidSubscription(to_broadcaster_user_id=self.broadcaster_user_id),
                
                # Stream status
                eventsub.StreamOnlineSubscription(broadcaster_user_id=self.broadcaster_user_id),
                eventsub.StreamOfflineSubscription(broadcaster_user_id=self.broadcaster_user_id),
                
                # Channel points
                eventsub.ChannelPointsRewardAddSubscription(broadcaster_user_id=self.broadcaster_user_id),
                eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=self.broadcaster_user_id),
            ]
            
            # Subscribe to each event
            for subscription in subscriptions:
                try:
                    await self.subscribe_websocket(payload=subscription)
                    logger.info(f"Subscribed to {subscription.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Failed to subscribe to {subscription.__class__.__name__}: {e}")
            
            logger.info("Event subscriptions completed")
            
            # If event callback is registered, call it
            if self.event_callback:
                self.event_callback('events_subscribed', {
                    'broadcaster_id': self.broadcaster_user_id
                })
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
    
    async def event_message(self, message):
        """Handle incoming chat messages"""
        # Add message to event history
        event_data = {
            "type": "chat_message",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": message.chatter.name,
                "message": message.content,
                "channel": message.broadcaster.name,
                "is_mod": message.chatter.is_mod,
                "is_subscriber": message.chatter.is_subscriber,
                "is_broadcaster": message.chatter.is_broadcaster
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('chat_message', event_data['data'])
        
        # Process commands if message starts with prefix
        await self.handle_commands(message)
    
    async def event_follow(self, event):
        """Handle follow events"""
        logger.info(f"New follower: {event.user_name}")
        
        # Add to event history
        event_data = {
            "type": "follow",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "user_id": event.user_id,
                "followed_at": event.followed_at.isoformat()
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('follow', event_data['data'], event)
    
    async def event_subscription(self, event):
        """Handle subscription events"""
        logger.info(f"New subscription: {event.user_name}")
        
        # Add to event history
        event_data = {
            "type": "subscription",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "user_id": event.user_id,
                "tier": event.tier,
                "is_gift": event.is_gift
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('subscription', event_data['data'], event)
    
    async def event_subscription_gift(self, event):
        """Handle subscription gift events"""
        logger.info(f"Subscription gift: {event.user_name} gifted {event.total} subs")
        
        # Add to event history
        event_data = {
            "type": "subscription_gift",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "user_id": event.user_id,
                "total": event.total,
                "tier": event.tier,
                "cumulative_total": event.cumulative_total
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('subscription_gift', event_data['data'], event)
    
    async def event_subscription_message(self, event):
        """Handle subscription message (resub) events"""
        logger.info(f"Resubscription: {event.user_name} (Streak: {event.streak})")
        
        # Add to event history
        event_data = {
            "type": "subscription_message",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "user_id": event.user_id,
                "tier": event.tier,
                "message": event.message,
                "cumulative_months": event.cumulative_months,
                "streak": event.streak
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('subscription_message', event_data['data'], event)
    
    async def event_cheer(self, event):
        """Handle cheer/bits events"""
        logger.info(f"Cheer received: {event.user_name} cheered {event.bits} bits")
        
        # Add to event history
        event_data = {
            "type": "cheer",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "user_id": event.user_id,
                "bits": event.bits,
                "message": event.message,
                "is_anonymous": event.is_anonymous
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('cheer', event_data['data'], event)
    
    async def event_raid(self, event):
        """Handle raid events"""
        logger.info(f"Raid from {event.from_broadcaster_user_name} with {event.viewers} viewers")
        
        # Add to event history
        event_data = {
            "type": "raid",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "raider_name": event.from_broadcaster_user_name,
                "raider_id": event.from_broadcaster_user_id,
                "viewers": event.viewers
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('raid', event_data['data'], event)
    
    async def event_custom_reward_redemption(self, event):
        """Handle channel point redemption events"""
        logger.info(f"Channel points redeemed: {event.user_name} redeemed {event.reward.title}")
        
        # Add to event history
        event_data = {
            "type": "channel_point_redemption",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "user_id": event.user_id,
                "reward_id": event.reward.id,
                "reward_title": event.reward.title,
                "reward_cost": event.reward.cost,
                "user_input": event.user_input,
                "status": event.status
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('channel_point_redemption', event_data['data'], event)
    
    async def event_stream_online(self, event):
        """Handle stream online events"""
        logger.info(f"Stream went online: {event.broadcaster_user_name}")
        
        # Add to event history
        event_data = {
            "type": "stream_online",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "broadcaster": event.broadcaster_user_name,
                "broadcaster_id": event.broadcaster_user_id,
                "started_at": event.started_at.isoformat()
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('stream_online', event_data['data'], event)
    
    async def event_stream_offline(self, event):
        """Handle stream offline events"""
        logger.info(f"Stream went offline: {event.broadcaster_user_name}")
        
        # Add to event history
        event_data = {
            "type": "stream_offline",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "broadcaster": event.broadcaster_user_name,
                "broadcaster_id": event.broadcaster_user_id
            }
        }
        
        event_history.append(event_data)
        
        # If event callback is registered, call it
        if self.event_callback:
            self.event_callback('stream_offline', event_data['data'], event)

class TwitchIntegration:
    """Main Twitch integration class"""
    
    def __init__(self, event_callback: Optional[Callable] = None):
        """Initialize Twitch integration
        
        Args:
            event_callback: Optional callback function for events
        """
        self.event_callback = event_callback
        self.auth_server = None
        self.bot = None
        self.auth_callback = None
        
        # Configuration
        self.broadcaster_client_id = ""
        self.broadcaster_client_secret = ""
        self.broadcaster_token = ""
        self.broadcaster_refresh_token = ""
        self.bot_client_id = ""
        self.bot_client_secret = ""
        self.bot_token = ""
        self.bot_refresh_token = ""
    
    def set_auth_callback(self, callback: Callable):
        """Set callback for authentication results
        
        Args:
            callback: Function to call with auth results (account_type, token_data)
        """
        self.auth_callback = callback
    
    def start_auth_server(self, is_bot: bool = False) -> str:
        """Start the OAuth callback server
        
        Args:
            is_bot: Whether this is for the bot account or broadcaster
            
        Returns:
            str: Authorization URL or empty string on failure
        """
        # Get client ID and secret
        client_id = self.bot_client_id if is_bot else self.broadcaster_client_id
        client_secret = self.bot_client_secret if is_bot else self.broadcaster_client_secret
        
        if not client_id or not client_secret:
            logger.error("Client ID and Client Secret must be set before authentication")
            return ""
        
        # Stop existing server if running
        if self.auth_server:
            self.auth_server.shutdown()
            self.auth_server = None
        
        # Create a new server on a random port
        server = TwitchAuthServer(client_id, client_secret, ("localhost", 0), TwitchAuthHandler, is_bot)
        port = server.server_address[1]
        
        # Register auth callback if one is set
        if self.auth_callback:
            server.auth_callback = self.auth_callback
        
        # Start server in a thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        self.auth_server = server
        logger.info(f"Auth server started on port {port}")
        
        # Build the authorization URL
        redirect_uri = f"http://localhost:{port}/callback"
        scopes = [
            "channel:read:subscriptions",
            "channel:read:redemptions",
            "channel:manage:redemptions",
            "chat:read",
            "chat:edit",
            "channel:moderate",
            "whispers:read",
            "whispers:edit",
            "moderator:read:followers",
            "user:read:broadcast",
            "channel:edit:commercial",
            "channel:read:hype_train",
            "channel:read:polls",
            "channel:read:predictions"
        ]
        
        auth_url = (
            f"https://id.twitch.tv/oauth2/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&response_type=code"
            f"&scope={urllib.parse.quote(' '.join(scopes))}"
        )
        
        # Open the URL in the default browser
        webbrowser.open(auth_url)
        logger.info(f"Opened authorization URL: {auth_url}")
        
        return auth_url
    
    def stop_auth_server(self):
        """Stop the OAuth callback server"""
        if self.auth_server:
            self.auth_server.shutdown()
            self.auth_server = None
            logger.info("Auth server stopped")
    
    def start_bot(self):
        """Start the Twitch bot"""
        if not HAVE_TWITCHIO:
            logger.error("twitchio is not installed, cannot start bot")
            return False
        
        # Check if we have valid tokens
        if not self.broadcaster_token:
            logger.error("Broadcaster access token is not set, cannot start bot")
            return False
        
        # Start bot in a separate thread
        def run_bot():
            import asyncio
            
            async def async_run():
                # Create and start the bot
                bot = TwitchBot(
                    broadcaster_token=self.broadcaster_token,
                    bot_token=self.bot_token if self.bot_token else None,
                    client_id=self.broadcaster_client_id if not self.bot_token else self.bot_client_id,
                    client_secret=self.broadcaster_client_secret if not self.bot_token else self.bot_client_secret,
                    event_callback=self.event_callback
                )
                
                self.bot = bot
                
                try:
                    await bot.start()
                except Exception as e:
                    logger.error(f"Bot stopped with error: {e}")
                finally:
                    logger.info("Bot stopped")
                    if self.bot == bot:
                        self.bot = None
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(async_run())
            except Exception as e:
                logger.error(f"Error running bot: {e}")
            finally:
                loop.close()
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        logger.info("Twitch bot starting...")
        return True
    
    def stop_bot(self):
        """Stop the Twitch bot"""
        if self.bot:
            # Bot cleanup will happen when the loop is closed
            logger.info("Stopping Twitch bot...")
            self.bot = None
            return True
        return False
    
    def is_bot_running(self) -> bool:
        """Check if the bot is running"""
        return self.bot is not None
    
    def send_chat_message(self, message: str) -> bool:
        """Send a chat message to the broadcaster's channel
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if the message was sent, False otherwise
        """
        if not self.bot or not self.bot.broadcaster_user_id:
            logger.error("Bot not running or broadcaster ID not set")
            return False
        
        # This has to be called in a thread since it's async
        def send_message_thread():
            import asyncio
            
            async def async_send():
                try:
                    # Create a partial user for the broadcaster
                    broadcaster = self.bot.create_partialuser(id=self.bot.broadcaster_user_id)
                    
                    # Send the message
                    sender_id = self.bot.bot_user_id if self.bot.bot_token else self.bot.broadcaster_user_id
                    await broadcaster.send_message(sender=sender_id, message=message)
                    logger.info(f"Message sent to channel: {message}")
                    return True
                except Exception as e:
                    logger.error(f"Error sending chat message: {e}")
                    return False
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(async_send())
            except Exception as e:
                logger.error(f"Error in send_message_thread: {e}")
                return False
            finally:
                loop.close()
        
        # Run in a thread and wait for result
        thread = threading.Thread(target=send_message_thread)
        thread.start()
        thread.join(timeout=5)  # Wait up to 5 seconds
        
        return True  # We can't really know if it succeeded
    
    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the broadcaster's channel
        
        Returns:
            dict: Channel information or None if not available
        """
        if not self.bot or not self.bot.broadcaster_user_id:
            logger.error("Bot not running or broadcaster ID not set")
            return None
        
        # This has to be called in a thread since it's async
        def get_info_thread():
            import asyncio
            
            async def async_get_info():
                try:
                    # Get the channel info
                    channel_info = await self.bot.fetch_channels([self.bot.broadcaster_user_id])
                    if channel_info:
                        # Convert to dictionary
                        info = {
                            "broadcaster_id": channel_info[0].broadcaster_id,
                            "broadcaster_name": channel_info[0].broadcaster_name,
                            "broadcaster_language": channel_info[0].broadcaster_language,
                            "game_id": channel_info[0].game_id,
                            "game_name": channel_info[0].game_name,
                            "title": channel_info[0].title,
                            "tags": channel_info[0].tags
                        }
                        return info
                    return None
                except Exception as e:
                    logger.error(f"Error getting channel info: {e}")
                    return None
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(async_get_info())
            except Exception as e:
                logger.error(f"Error in get_info_thread: {e}")
                return None
            finally:
                loop.close()
        
        # Run in a thread and wait for result
        thread = threading.Thread(target=get_info_thread)
        thread.start()
        thread.join(timeout=5)  # Wait up to 5 seconds
        
        # Check if the thread returned a result
        if hasattr(thread, 'result'):
            return thread.result
        
        # If the thread is still running or didn't set a result
        return None
    
    def update_channel_info(self, title: Optional[str] = None, game: Optional[str] = None) -> bool:
        """Update the broadcaster's channel information
        
        Args:
            title: New stream title (or None to leave unchanged)
            game: New game name (or None to leave unchanged)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.bot or not self.bot.broadcaster_user_id:
            logger.error("Bot not running or broadcaster ID not set")
            return False
        
        # This has to be called in a thread since it's async
        def update_info_thread():
            import asyncio
            
            async def async_update_info():
                try:
                    # First, if a game name is provided, we need to get the game ID
                    game_id = None
                    if game:
                        games = await self.bot.fetch_games(names=[game])
                        if games:
                            game_id = games[0].id
                        else:
                            logger.warning(f"Game '{game}' not found")
                            return False
                    
                    # Update the channel info
                    success = await self.bot.modify_channel_information(
                        broadcaster_id=self.bot.broadcaster_user_id,
                        title=title,
                        game_id=game_id
                    )
                    
                    if success:
                        logger.info(f"Channel information updated: title='{title}', game='{game}'")
                    return success
                except Exception as e:
                    logger.error(f"Error updating channel info: {e}")
                    return False
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(async_update_info())
            except Exception as e:
                logger.error(f"Error in update_info_thread: {e}")
                return False
            finally:
                loop.close()
        
        # Run in a thread and wait for result
        thread = threading.Thread(target=update_info_thread)
        thread.start()
        thread.join(timeout=5)  # Wait up to 5 seconds
        
        # Check if the thread returned a result
        if hasattr(thread, 'result'):
            return thread.result
        
        # If the thread is still running or didn't set a result
        return False
    
    def get_followers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the broadcaster's followers
        
        Args:
            limit: Maximum number of followers to retrieve
            
        Returns:
            list: List of follower information dictionaries
        """
        if not self.bot or not self.bot.broadcaster_user_id:
            logger.error("Bot not running or broadcaster ID not set")
            return []
        
        # This has to be called in a thread since it's async
        def get_followers_thread():
            import asyncio
            
            async def async_get_followers():
                try:
                    # Get the followers
                    followers = []
                    async for follower in self.bot.fetch_followers(
                        broadcaster_id=self.bot.broadcaster_user_id,
                        first=limit
                    ):
                        followers.append({
                            "user_id": follower.user_id,
                            "user_name": follower.user_name,
                            "followed_at": follower.followed_at.isoformat()
                        })
                        if len(followers) >= limit:
                            break
                    
                    return followers
                except Exception as e:
                    logger.error(f"Error getting followers: {e}")
                    return []
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(async_get_followers())
            except Exception as e:
                logger.error(f"Error in get_followers_thread: {e}")
                return []
            finally:
                loop.close()
        
        # Run in a thread and wait for result
        thread = threading.Thread(target=get_followers_thread)
        thread.start()
        thread.join(timeout=10)  # Wait up to 10 seconds (this might take longer)
        
        # Check if the thread returned a result
        if hasattr(thread, 'result'):
            return thread.result
        
        # If the thread is still running or didn't set a result
        return []
    
    def clear_event_history(self):
        """Clear the event history"""
        global event_history
        event_history = []
    
    def get_event_history(self) -> List[Dict[str, Any]]:
        """Get the event history
        
        Returns:
            list: List of event dictionaries
        """
        return event_history.copy()


# Create a global instance
if HAVE_TWITCHIO:
    twitch = TwitchIntegration()
else:
    twitch = None 