#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OBSCopilot - A Python plugin for OBS Studio that integrates Twitch functionality
directly into OBS, allowing streamers to manage their stream without external tools.
"""

import os
import sys
import json
import time
import base64
import logging
import threading
import webbrowser
import http.server
import urllib.parse
from datetime import datetime
from functools import partial

# Import the OBS Python module
import obspython as obs

# Try to import optional dependencies
try:
    import obsws_python as obsws
    HAVE_OBSWS = True
except ImportError:
    HAVE_OBSWS = False
    print("OBSCopilot: obsws-python not found. Using limited OBS scripting API.")
    print("For full features, install: pip install obsws-python")

try:
    import twitchio
    from twitchio.ext import commands, eventsub
    HAVE_TWITCHIO = True
except ImportError:
    HAVE_TWITCHIO = False
    print("OBSCopilot: twitchio not found. Twitch integration disabled.")
    print("To enable Twitch integration: pip install twitchio")

# Plugin settings
SETTINGS = {
    "twitch_broadcaster_client_id": "",
    "twitch_broadcaster_client_secret": "",
    "twitch_broadcaster_access_token": "",
    "twitch_broadcaster_refresh_token": "",
    "twitch_bot_client_id": "",
    "twitch_bot_client_secret": "",
    "twitch_bot_access_token": "",
    "twitch_bot_refresh_token": "",
    "obsws_host": "localhost",
    "obsws_port": 4455,
    "obsws_password": "",
    "event_actions": []
}

# Global variables
script_path = os.path.dirname(__file__)
auth_server = None
bot = None
obsws_client = None
broadcaster_user_id = None
bot_user_id = None
event_history = []

# Logging setup
logger = logging.getLogger("OBSCopilot")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class TwitchAuthServer(http.server.HTTPServer):
    """Simple HTTP server to handle Twitch OAuth redirect"""
    
    def __init__(self, client_id, client_secret, server_address, handler_class, is_bot=False):
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
    
    def exchange_code(self, code):
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
            
            # Save token to settings
            if server.is_bot:
                SETTINGS["twitch_bot_access_token"] = token_data["access_token"]
                SETTINGS["twitch_bot_refresh_token"] = token_data["refresh_token"]
            else:
                SETTINGS["twitch_broadcaster_access_token"] = token_data["access_token"]
                SETTINGS["twitch_broadcaster_refresh_token"] = token_data["refresh_token"]
        else:
            logger.error(f"Failed to exchange code: {response.text}")
    
    def log_message(self, format, *args):
        """Suppress server logs"""
        return

class EventAction:
    """Represents an action to take when a Twitch event occurs"""
    
    def __init__(self, event_type, condition, action_type, action_data):
        self.event_type = event_type
        self.condition = condition
        self.action_type = action_type
        self.action_data = action_data
    
    def to_dict(self):
        """Convert to dictionary for storage"""
        return {
            "event_type": self.event_type,
            "condition": self.condition,
            "action_type": self.action_type,
            "action_data": self.action_data
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            data["event_type"],
            data["condition"],
            data["action_type"],
            data["action_data"]
        )
    
    def check_condition(self, event_data):
        """Check if the condition matches the event data"""
        # Simple condition matching for now
        if not self.condition:
            return True
        
        # Parse condition (format: "key=value")
        if "=" in self.condition:
            key, value = self.condition.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Check if key exists in event data and matches value
            if hasattr(event_data, key) and getattr(event_data, key) == value:
                return True
        
        return False
    
    def execute(self, event_data):
        """Execute the action based on the event data"""
        if not self.check_condition(event_data):
            return
        
        if self.action_type == "show_source":
            # Show a source in a scene
            scene_name = self.action_data.get("scene_name", "")
            source_name = self.action_data.get("source_name", "")
            if scene_name and source_name:
                set_source_visibility(scene_name, source_name, True)
        
        elif self.action_type == "hide_source":
            # Hide a source in a scene
            scene_name = self.action_data.get("scene_name", "")
            source_name = self.action_data.get("source_name", "")
            if scene_name and source_name:
                set_source_visibility(scene_name, source_name, False)
        
        elif self.action_type == "update_text":
            # Update a text source
            source_name = self.action_data.get("source_name", "")
            text_format = self.action_data.get("text", "")
            
            if source_name and text_format:
                # Replace placeholders with event data
                for key in dir(event_data):
                    if not key.startswith("_") and not callable(getattr(event_data, key)):
                        placeholder = f"{{{key}}}"
                        if placeholder in text_format:
                            text_format = text_format.replace(placeholder, str(getattr(event_data, key)))
                
                set_text_source_content(source_name, text_format)
        
        elif self.action_type == "switch_scene":
            # Switch to a different scene
            scene_name = self.action_data.get("scene_name", "")
            if scene_name:
                switch_to_scene(scene_name)

class TwitchBot(commands.Bot):
    """Twitch bot for handling chat commands and events"""
    
    def __init__(self, broadcaster_token, bot_token=None):
        # Initialize with broadcaster token
        self.broadcaster_token = broadcaster_token
        self.bot_token = bot_token
        
        # Determine which token to use for the bot
        token = bot_token if bot_token else broadcaster_token
        
        # Get client IDs from settings
        client_id = SETTINGS["twitch_bot_client_id"] if bot_token else SETTINGS["twitch_broadcaster_client_id"]
        client_secret = SETTINGS["twitch_bot_client_secret"] if bot_token else SETTINGS["twitch_broadcaster_client_secret"]
        
        super().__init__(
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            prefix="!",
        )
    
    async def event_ready(self):
        """Called once when the bot is connected"""
        global bot_user_id, broadcaster_user_id
        
        # Get bot user ID
        bot_user = await self.fetch_users([self.nick])
        if bot_user:
            bot_user_id = bot_user[0].id
            logger.info(f"Bot connected as {self.nick} (ID: {bot_user_id})")
        
        # Get broadcaster user ID if using different accounts
        if self.bot_token:
            user = await self.fetch_users(oauth_token=self.broadcaster_token)
            if user:
                broadcaster_user_id = user[0].id
                logger.info(f"Broadcaster identified as {user[0].name} (ID: {broadcaster_user_id})")
        else:
            # Bot and broadcaster are the same
            broadcaster_user_id = bot_user_id
        
        # Subscribe to events
        await self.subscribe_to_events()
    
    async def subscribe_to_events(self):
        """Subscribe to Twitch EventSub events"""
        try:
            # List of event subscriptions to create
            subscriptions = [
                # Channel events
                eventsub.ChannelFollowSubscription(broadcaster_user_id=broadcaster_user_id),
                eventsub.ChannelSubscribeSubscription(broadcaster_user_id=broadcaster_user_id),
                eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=broadcaster_user_id),
                eventsub.ChannelSubscriptionMessageSubscription(broadcaster_user_id=broadcaster_user_id),
                eventsub.ChannelCheerSubscription(broadcaster_user_id=broadcaster_user_id),
                eventsub.ChannelRaidSubscription(to_broadcaster_user_id=broadcaster_user_id),
                
                # Stream status
                eventsub.StreamOnlineSubscription(broadcaster_user_id=broadcaster_user_id),
                eventsub.StreamOfflineSubscription(broadcaster_user_id=broadcaster_user_id),
                
                # Channel points
                eventsub.ChannelPointsRewardAddSubscription(broadcaster_user_id=broadcaster_user_id),
                eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=broadcaster_user_id),
            ]
            
            # Subscribe to each event
            for subscription in subscriptions:
                try:
                    await self.subscribe_websocket(payload=subscription)
                    logger.info(f"Subscribed to {subscription.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Failed to subscribe to {subscription.__class__.__name__}: {e}")
            
            logger.info("Event subscriptions completed")
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
    
    async def event_message(self, message):
        """Handle incoming chat messages"""
        # Add message to event history
        event_history.append({
            "type": "chat_message",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": message.chatter.name,
                "message": message.content,
                "channel": message.broadcaster.name
            }
        })
        
        # Process commands if message starts with prefix
        await self.handle_commands(message)
    
    async def event_follow(self, event):
        """Handle follow events"""
        logger.info(f"New follower: {event.user_name}")
        
        # Add to event history
        event_history.append({
            "type": "follow",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "user_id": event.user_id
            }
        })
        
        # Execute actions for this event
        for action in SETTINGS["event_actions"]:
            if isinstance(action, dict):
                action = EventAction.from_dict(action)
            
            if action.event_type == "follow":
                action.execute(event)
    
    async def event_subscription(self, event):
        """Handle subscription events"""
        logger.info(f"New subscription: {event.user_name}")
        
        # Add to event history
        event_history.append({
            "type": "subscription",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "tier": event.tier,
                "is_gift": event.is_gift
            }
        })
        
        # Execute actions for this event
        for action in SETTINGS["event_actions"]:
            if isinstance(action, dict):
                action = EventAction.from_dict(action)
            
            if action.event_type == "subscription":
                action.execute(event)
    
    async def event_cheer(self, event):
        """Handle cheer/bits events"""
        logger.info(f"Cheer received: {event.user_name} cheered {event.bits} bits")
        
        # Add to event history
        event_history.append({
            "type": "cheer",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "username": event.user_name,
                "bits": event.bits,
                "message": event.message
            }
        })
        
        # Execute actions for this event
        for action in SETTINGS["event_actions"]:
            if isinstance(action, dict):
                action = EventAction.from_dict(action)
            
            if action.event_type == "cheer":
                action.execute(event)
    
    async def event_stream_online(self, event):
        """Handle stream online events"""
        logger.info(f"Stream went online: {event.broadcaster_user_name}")
        
        # Add to event history
        event_history.append({
            "type": "stream_online",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "broadcaster": event.broadcaster_user_name,
                "started_at": event.started_at.isoformat()
            }
        })
        
        # Execute actions for this event
        for action in SETTINGS["event_actions"]:
            if isinstance(action, dict):
                action = EventAction.from_dict(action)
            
            if action.event_type == "stream_online":
                action.execute(event)
    
    async def event_stream_offline(self, event):
        """Handle stream offline events"""
        logger.info(f"Stream went offline: {event.broadcaster_user_name}")
        
        # Add to event history
        event_history.append({
            "type": "stream_offline",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "broadcaster": event.broadcaster_user_name
            }
        })
        
        # Execute actions for this event
        for action in SETTINGS["event_actions"]:
            if isinstance(action, dict):
                action = EventAction.from_dict(action)
            
            if action.event_type == "stream_offline":
                action.execute(event)

# OBS WebSocket functions
def connect_to_obs_websocket():
    """Connect to OBS WebSocket server"""
    global obsws_client
    
    if not HAVE_OBSWS:
        logger.warning("obsws-python not installed, cannot connect to OBS WebSocket")
        return False
    
    try:
        # Disconnect existing client if any
        if obsws_client:
            obsws_client = None
        
        # Create new client
        obsws_client = obsws.ReqClient(
            host=SETTINGS["obsws_host"],
            port=SETTINGS["obsws_port"],
            password=SETTINGS["obsws_password"]
        )
        
        # Test connection with a simple request
        version = obsws_client.get_version()
        logger.info(f"Connected to OBS WebSocket: OBS {version.obs_version}, WebSocket {version.obs_web_socket_version}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to OBS WebSocket: {e}")
        obsws_client = None
        return False

def set_source_visibility(scene_name, source_name, visible):
    """Set visibility of a source in a scene"""
    try:
        if obsws_client:
            # Using WebSocket API
            obsws_client.set_scene_item_enabled(scene_name=scene_name, source_name=source_name, enabled=visible)
            logger.info(f"Set source '{source_name}' in scene '{scene_name}' visibility to {visible}")
        else:
            # Using OBS Python API
            current_scene = obs.obs_frontend_get_current_scene()
            if current_scene:
                scene = obs.obs_scene_from_source(current_scene)
                if scene:
                    scene_item = obs.obs_scene_find_source_recursive(scene, source_name)
                    if scene_item:
                        obs.obs_sceneitem_set_visible(scene_item, visible)
                        logger.info(f"Set source '{source_name}' visibility to {visible}")
                    else:
                        logger.warning(f"Source '{source_name}' not found in current scene")
                obs.obs_source_release(current_scene)
    except Exception as e:
        logger.error(f"Error setting source visibility: {e}")

def set_text_source_content(source_name, text):
    """Set the text of a text source"""
    try:
        if obsws_client:
            # Using WebSocket API
            source_settings = obsws_client.get_input_settings(source_name=source_name).input_settings
            source_settings["text"] = text
            obsws_client.set_input_settings(source_name=source_name, input_settings=source_settings)
            logger.info(f"Updated text for source '{source_name}'")
        else:
            # Using OBS Python API
            source = obs.obs_get_source_by_name(source_name)
            if source:
                settings = obs.obs_data_create()
                obs.obs_data_set_string(settings, "text", text)
                obs.obs_source_update(source, settings)
                obs.obs_data_release(settings)
                obs.obs_source_release(source)
                logger.info(f"Updated text for source '{source_name}'")
            else:
                logger.warning(f"Text source '{source_name}' not found")
    except Exception as e:
        logger.error(f"Error updating text source: {e}")

def switch_to_scene(scene_name):
    """Switch to a different scene"""
    try:
        if obsws_client:
            # Using WebSocket API
            obsws_client.set_current_program_scene(scene_name=scene_name)
            logger.info(f"Switched to scene '{scene_name}'")
        else:
            # Using OBS Python API
            scenes = obs.obs_frontend_get_scenes()
            for scene in scenes:
                name = obs.obs_source_get_name(scene)
                if name == scene_name:
                    obs.obs_frontend_set_current_scene(scene)
                    logger.info(f"Switched to scene '{scene_name}'")
                    break
            
            obs.source_list_release(scenes)
    except Exception as e:
        logger.error(f"Error switching scenes: {e}")

# Twitch authentication functions
def start_auth_server(is_bot=False):
    """Start the OAuth callback server"""
    global auth_server
    
    # Get client ID and secret
    client_id = SETTINGS["twitch_bot_client_id"] if is_bot else SETTINGS["twitch_broadcaster_client_id"]
    client_secret = SETTINGS["twitch_bot_client_secret"] if is_bot else SETTINGS["twitch_broadcaster_client_secret"]
    
    if not client_id or not client_secret:
        logger.error("Client ID and Client Secret must be set before authentication")
        return
    
    # Stop existing server if running
    if auth_server:
        auth_server.shutdown()
        auth_server = None
    
    # Create a new server on a random port
    server = TwitchAuthServer(client_id, client_secret, ("localhost", 0), TwitchAuthHandler, is_bot)
    port = server.server_address[1]
    
    # Start server in a thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    auth_server = server
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

def stop_auth_server():
    """Stop the OAuth callback server"""
    global auth_server
    
    if auth_server:
        auth_server.shutdown()
        auth_server = None
        logger.info("Auth server stopped")

def start_bot():
    """Start the Twitch bot"""
    global bot
    
    if not HAVE_TWITCHIO:
        logger.error("twitchio is not installed, cannot start bot")
        return
    
    # Check if we have valid tokens
    broadcaster_token = SETTINGS["twitch_broadcaster_access_token"]
    bot_token = SETTINGS["twitch_bot_access_token"] if SETTINGS["twitch_bot_access_token"] else None
    
    if not broadcaster_token:
        logger.error("Broadcaster access token is not set, cannot start bot")
        return
    
    # Start bot in a separate thread
    def run_bot():
        import asyncio
        
        async def async_run():
            global bot
            # Create and start the bot
            bot = TwitchBot(broadcaster_token, bot_token)
            
            try:
                await bot.start()
            except Exception as e:
                logger.error(f"Bot stopped with error: {e}")
            finally:
                logger.info("Bot stopped")
                bot = None
        
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

def stop_bot():
    """Stop the Twitch bot"""
    global bot
    
    if bot:
        # Bot cleanup will happen when the loop is closed
        logger.info("Stopping Twitch bot...")
        bot = None

# OBS Script callback functions
def script_description():
    """Return the description shown in the Script window"""
    if not HAVE_TWITCHIO:
        return """<h2>OBSCopilot</h2>
<p>Twitch integration for OBS Studio.</p>
<p style="color:red;"><b>Warning:</b> The twitchio module is not installed. Twitch integration is disabled.<br>
Please install it using: <code>pip install twitchio</code></p>
"""
    
    return """<h2>OBSCopilot</h2>
<p>Twitch integration for OBS Studio.</p>
<p>This plugin allows you to connect your Twitch account(s) and respond to Twitch events by controlling OBS.</p>
<p>See the <a href="https://github.com/splashxxx/obscopilot">GitHub repository</a> for more information.</p>
"""

def script_properties():
    """Define property controls shown in the script's Properties window"""
    props = obs.obs_properties_create()
    
    # Broadcaster account section
    broadcaster_group = obs.obs_properties_create()
    obs.obs_properties_add_text(broadcaster_group, "twitch_broadcaster_client_id", "Client ID", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(broadcaster_group, "twitch_broadcaster_client_secret", "Client Secret", obs.OBS_TEXT_PASSWORD)
    
    # Add auth button for broadcaster
    obs.obs_properties_add_button(broadcaster_group, "auth_broadcaster", "Authenticate Broadcaster Account", lambda props, prop: authenticate_twitch(False))
    
    # Display token info if available
    if SETTINGS["twitch_broadcaster_access_token"]:
        obs.obs_properties_add_text(broadcaster_group, "broadcaster_token_info", "Token Status", obs.OBS_TEXT_INFO)
    
    obs.obs_properties_add_group(props, "broadcaster_group", "Twitch Broadcaster Account", obs.OBS_GROUP_NORMAL, broadcaster_group)
    
    # Bot account section (optional)
    bot_group = obs.obs_properties_create()
    obs.obs_properties_add_text(bot_group, "twitch_bot_client_id", "Bot Client ID (Optional)", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(bot_group, "twitch_bot_client_secret", "Bot Client Secret (Optional)", obs.OBS_TEXT_PASSWORD)
    
    # Add auth button for bot
    obs.obs_properties_add_button(bot_group, "auth_bot", "Authenticate Bot Account", lambda props, prop: authenticate_twitch(True))
    
    # Display token info if available
    if SETTINGS["twitch_bot_access_token"]:
        obs.obs_properties_add_text(bot_group, "bot_token_info", "Bot Token Status", obs.OBS_TEXT_INFO)
    
    obs.obs_properties_add_group(props, "bot_group", "Twitch Bot Account (Optional)", obs.OBS_GROUP_NORMAL, bot_group)
    
    # OBS WebSocket section (if available)
    if HAVE_OBSWS:
        obsws_group = obs.obs_properties_create()
        obs.obs_properties_add_text(obsws_group, "obsws_host", "Host", obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_int(obsws_group, "obsws_port", "Port", 1, 65535, 1)
        obs.obs_properties_add_text(obsws_group, "obsws_password", "Password", obs.OBS_TEXT_PASSWORD)
        
        # Test connection button
        obs.obs_properties_add_button(obsws_group, "test_obsws", "Test Connection", lambda props, prop: test_obsws_connection())
        
        obs.obs_properties_add_group(props, "obsws_group", "OBS WebSocket (Advanced)", obs.OBS_GROUP_NORMAL, obsws_group)
    
    # Bot control buttons
    obs.obs_properties_add_button(props, "start_bot", "Start Bot", lambda props, prop: start_bot_clicked())
    obs.obs_properties_add_button(props, "stop_bot", "Stop Bot", lambda props, prop: stop_bot_clicked())
    
    # Event actions section
    event_group = obs.obs_properties_create()
    
    # Add button to create a new event action
    obs.obs_properties_add_button(event_group, "add_event_action", "Add Event Action", lambda props, prop: add_event_action())
    
    # Display current event actions
    obs.obs_properties_add_text(event_group, "event_actions_info", "Current Event Actions", obs.OBS_TEXT_INFO)
    
    obs.obs_properties_add_group(props, "event_group", "Event Actions", obs.OBS_GROUP_NORMAL, event_group)
    
    return props

def script_update(settings):
    """Called when the script's settings are changed"""
    # Save previous settings
    prev_settings = SETTINGS.copy()
    
    # Update settings
    SETTINGS["twitch_broadcaster_client_id"] = obs.obs_data_get_string(settings, "twitch_broadcaster_client_id")
    SETTINGS["twitch_broadcaster_client_secret"] = obs.obs_data_get_string(settings, "twitch_broadcaster_client_secret")
    SETTINGS["twitch_bot_client_id"] = obs.obs_data_get_string(settings, "twitch_bot_client_id")
    SETTINGS["twitch_bot_client_secret"] = obs.obs_data_get_string(settings, "twitch_bot_client_secret")
    
    if HAVE_OBSWS:
        SETTINGS["obsws_host"] = obs.obs_data_get_string(settings, "obsws_host")
        SETTINGS["obsws_port"] = obs.obs_data_get_int(settings, "obsws_port")
        SETTINGS["obsws_password"] = obs.obs_data_get_string(settings, "obsws_password")
    
    # Update token info text
    if SETTINGS["twitch_broadcaster_access_token"]:
        broadcaster_token_info = "Broadcaster Token: ✓ (Available)"
        obs.obs_data_set_string(settings, "broadcaster_token_info", broadcaster_token_info)
    
    if SETTINGS["twitch_bot_access_token"]:
        bot_token_info = "Bot Token: ✓ (Available)"
        obs.obs_data_set_string(settings, "bot_token_info", bot_token_info)
    
    # Update event actions info
    event_actions_info = f"Event Actions: {len(SETTINGS['event_actions'])}"
    for i, action in enumerate(SETTINGS["event_actions"]):
        if isinstance(action, dict):
            action_obj = EventAction.from_dict(action)
            event_actions_info += f"\n{i+1}. {action_obj.event_type}: {action_obj.action_type}"
        else:
            event_actions_info += f"\n{i+1}. {action.event_type}: {action.action_type}"
    
    obs.obs_data_set_string(settings, "event_actions_info", event_actions_info)
    
    # Check if WebSocket settings changed
    if (HAVE_OBSWS and
        (prev_settings["obsws_host"] != SETTINGS["obsws_host"] or
         prev_settings["obsws_port"] != SETTINGS["obsws_port"] or
         prev_settings["obsws_password"] != SETTINGS["obsws_password"])):
        # Try to reconnect
        connect_to_obs_websocket()

def script_load(settings):
    """Called when the script is loaded"""
    logger.info("OBSCopilot script loaded")
    
    # Load saved event actions
    actions_json = obs.obs_data_get_string(settings, "saved_event_actions")
    if actions_json:
        try:
            actions_data = json.loads(actions_json)
            SETTINGS["event_actions"] = [EventAction.from_dict(action) for action in actions_data]
            logger.info(f"Loaded {len(SETTINGS['event_actions'])} event actions")
        except Exception as e:
            logger.error(f"Error loading event actions: {e}")
    
    # Load saved tokens
    SETTINGS["twitch_broadcaster_access_token"] = obs.obs_data_get_string(settings, "twitch_broadcaster_access_token")
    SETTINGS["twitch_broadcaster_refresh_token"] = obs.obs_data_get_string(settings, "twitch_broadcaster_refresh_token")
    SETTINGS["twitch_bot_access_token"] = obs.obs_data_get_string(settings, "twitch_bot_access_token")
    SETTINGS["twitch_bot_refresh_token"] = obs.obs_data_get_string(settings, "twitch_bot_refresh_token")
    
    # Try to connect to OBS WebSocket if available
    if HAVE_OBSWS:
        connect_to_obs_websocket()

def script_save(settings):
    """Called when the script is saved"""
    # Save event actions
    try:
        actions_data = [
            action.to_dict() if isinstance(action, EventAction) else action
            for action in SETTINGS["event_actions"]
        ]
        actions_json = json.dumps(actions_data)
        obs.obs_data_set_string(settings, "saved_event_actions", actions_json)
    except Exception as e:
        logger.error(f"Error saving event actions: {e}")
    
    # Save tokens
    obs.obs_data_set_string(settings, "twitch_broadcaster_access_token", SETTINGS["twitch_broadcaster_access_token"])
    obs.obs_data_set_string(settings, "twitch_broadcaster_refresh_token", SETTINGS["twitch_broadcaster_refresh_token"])
    obs.obs_data_set_string(settings, "twitch_bot_access_token", SETTINGS["twitch_bot_access_token"])
    obs.obs_data_set_string(settings, "twitch_bot_refresh_token", SETTINGS["twitch_bot_refresh_token"])

def script_unload():
    """Called when the script is unloaded"""
    # Stop the authentication server if running
    stop_auth_server()
    
    # Stop the bot if running
    stop_bot()
    
    logger.info("OBSCopilot script unloaded")

# UI callback functions
def authenticate_twitch(is_bot):
    """Start the Twitch authentication process"""
    auth_url = start_auth_server(is_bot)
    if auth_url:
        account_type = "Bot" if is_bot else "Broadcaster"
        logger.info(f"Started {account_type} authentication process")
        return True
    return False

def test_obsws_connection():
    """Test the connection to OBS WebSocket"""
    if connect_to_obs_websocket():
        logger.info("OBS WebSocket connection successful")
        return True
    return False

def start_bot_clicked():
    """Start the Twitch bot from UI"""
    start_bot()
    return True

def stop_bot_clicked():
    """Stop the Twitch bot from UI"""
    stop_bot()
    return True

def add_event_action():
    """Add a new event action from UI"""
    # This would typically open a dialog or settings window
    # For now, we'll just add a sample action
    sample_action = EventAction(
        event_type="follow",
        condition="",
        action_type="show_source",
        action_data={
            "scene_name": "Main",
            "source_name": "Follow Alert"
        }
    )
    
    SETTINGS["event_actions"].append(sample_action)
    logger.info("Added sample event action")
    
    # Force refresh of properties
    obs.obs_properties_apply_settings(obs.obs_get_active_properties(), obs.obs_get_active_settings())
    
    return True 