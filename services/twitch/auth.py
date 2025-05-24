import asyncio
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.type import AuthScope
from pathlib import Path
from services.twitch.credentials import TwitchCredentialsManager
import socket
import threading
import webbrowser
import urllib.parse
from aiohttp import web
import aiohttp  # Added for manual token exchange
import logging
import sys
import time
import json  # Added for saving tokens

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('TwitchAuth')

# Using only the two required ports
TWITCH_API_DEFAULT_PORTS = [17563, 17564]  # Reduced to just two ports
OAUTH_BROADCASTER_PORT = 17563  # Changed to match first port
OAUTH_BOT_PORT = 17564  # Changed to match second port
OAUTH_TIMEOUT_SECONDS = 300  # 5 minutes

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

class OAuthResult:
    def __init__(self):
        self.code = None
        self.error = None
        self.error_description = None
        self.event = threading.Event()

class TwitchAuthManager:
    _active_login = {}  # class-level dict to prevent parallel logins per port
    _aiohttp_runners = []  # Track all active runners for cleanup
    _event_loop = None  # Class-level event loop

    @classmethod
    def get_event_loop(cls):
        """Get or create the class-level event loop"""
        if cls._event_loop is None or cls._event_loop.is_closed():
            cls._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._event_loop)
        return cls._event_loop

    def __init__(self, account_type='broadcaster', on_timeout=None):
        self.account_type = account_type  # 'broadcaster' or 'bot'
        self.token_file = f'twitch_{account_type}_token.json'
        if self.account_type == 'broadcaster':
            self.scopes = [
                AuthScope.CHANNEL_READ_REDEMPTIONS,
                AuthScope.CHANNEL_MANAGE_REDEMPTIONS,
                AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
                AuthScope.CHANNEL_MANAGE_BROADCAST,
                AuthScope.CHANNEL_READ_POLLS,
                AuthScope.CHANNEL_MANAGE_POLLS,
                AuthScope.CHANNEL_READ_PREDICTIONS,
                AuthScope.CHANNEL_MANAGE_PREDICTIONS,
                AuthScope.CHANNEL_MANAGE_SCHEDULE,
                AuthScope.USER_READ_BROADCAST,
                AuthScope.USER_READ_CHAT,
                AuthScope.CHAT_EDIT,
                AuthScope.CHAT_READ,
                AuthScope.MODERATION_READ,
                AuthScope.MODERATOR_MANAGE_BANNED_USERS,
                AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS,
                AuthScope.MODERATOR_READ_CHAT_SETTINGS,
                AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS,
                AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES,
                AuthScope.MODERATOR_READ_CHAT_MESSAGES,
                # Add more as needed for streamer.bot alternative
            ]
            self.oauth_port = OAUTH_BROADCASTER_PORT
        else:  # bot
            self.scopes = [
                AuthScope.CHAT_READ,
                AuthScope.CHAT_EDIT,
                AuthScope.USER_READ_CHAT,
                AuthScope.MODERATION_READ,
                AuthScope.MODERATOR_MANAGE_BANNED_USERS,
                AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS,
                AuthScope.MODERATOR_READ_CHAT_SETTINGS,
                AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS,
                AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES,
                AuthScope.MODERATOR_READ_CHAT_MESSAGES,
                # Add more as needed for bot automation/moderation
            ]
            self.oauth_port = OAUTH_BOT_PORT
        self.credentials_manager = TwitchCredentialsManager()
        self.twitch = None
        self.helper = None
        self.oauth_timer = None
        self.on_timeout = on_timeout
        self._login_cancelled = False
        self._oauth_result = None
        # Persistent login: restore tokens if file exists
        if Path(self.token_file).exists():
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                client_id, client_secret = self.credentials_manager.load_credentials()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                twitch = loop.run_until_complete(Twitch(client_id, client_secret, authenticate_app=False))
                loop.run_until_complete(
                    twitch.set_user_authentication(
                        token_data['access_token'],
                        self.scopes,
                        token_data['refresh_token']
                    )
                )
                self.twitch = twitch
                loop.close()
            except Exception as e:
                logging.error(f"Failed to restore Twitch authentication: {e}")
                self.twitch = None
        
    async def _setup_aiohttp_servers(self, oauth_result, primary_port):
        """Start server and handle the OAuth callback"""
        async def handle(request):
            logger.info(f"Request received on port {request.transport.get_extra_info('sockname')[1]} path: {request.path}")
            params = request.rel_url.query
            
            # Check for errors first
            error = params.get('error')
            error_description = params.get('error_description')
            if error:
                logger.error(f"Received OAuth error: {error} - {error_description}")
                oauth_result.error = error
                oauth_result.error_description = error_description
                oauth_result.event.set()
                html = """
                <html><head><title>OBS Copilot Login Error</title></head>
                <body style='font-family:sans-serif;text-align:center;margin-top:10em;'>
                <h1>Login Failed</h1>
                <p style='color:red;'>There was an error during the login process. Please check the application for details.</p>
                </body></html>
                """
                return web.Response(text=html, content_type='text/html')
            
            # Handle successful code
            code = params.get('code')
            if code:
                logger.info("Received OAuth code")
                oauth_result.code = code
                oauth_result.event.set()
                html = """
                <html><head><title>OBS Copilot Login</title></head>
                <body style='font-family:sans-serif;text-align:center;margin-top:10em;'>
                <h1>Login successful!</h1>
                <p>Login to OBS Copilot is completed. You may close this page.</p>
                </body></html>
                """
                return web.Response(text=html, content_type='text/html')
            
            return web.Response(text="Waiting for OAuth response...", content_type='text/plain')
        
        app = web.Application()
        app.router.add_get('/', handle)
        app.router.add_get('/{tail:.*}', handle)
        
        # Only use the designated port
        port = primary_port
        try:
            if is_port_in_use(port):
                logger.warning(f"Port {port} is already in use, trying to force release it")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        s.bind(('localhost', port))
                    except:
                        logger.error(f"Could not forcibly take port {port}")
                        raise RuntimeError(f"Port {port} is already in use and could not be released. Please restart the application.")
                    
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', port)
            await site.start()
            TwitchAuthManager._aiohttp_runners.append(runner)
            logger.info(f"Started server on port {port}")
        except Exception as e:
            logger.error(f"Failed to start server on port {port}: {e}")
            raise RuntimeError(f"Could not start HTTP server on port {port}: {e}")
            
        while not oauth_result.event.is_set() and not self._login_cancelled:
            await asyncio.sleep(0.1)

    def _start_servers_and_browser(self, oauth_result, oauth_url):
        """Start HTTP server and open browser"""
        def run_servers():
            loop = TwitchAuthManager.get_event_loop()
            try:
                loop.run_until_complete(self._setup_aiohttp_servers(oauth_result, self.oauth_port))
            except Exception as e:
                logger.error(f"Server thread error: {e}")
                oauth_result.event.set()
            finally:
                async def cleanup_runners():
                    for runner in TwitchAuthManager._aiohttp_runners:
                        try:
                            await runner.cleanup()
                        except Exception as e:
                            logger.error(f"Error cleaning up runner: {e}")
                try:
                    loop.run_until_complete(cleanup_runners())
                except Exception as e:
                    logger.error(f"Error in cleanup: {e}")
                finally:
                    TwitchAuthManager._aiohttp_runners = []
                
        server_thread = threading.Thread(target=run_servers, daemon=True)
        server_thread.start()
        
        logger.info("Waiting for server to start before opening browser")
        time.sleep(1.5)
        
        logger.info(f"Opening browser with URL: {oauth_url}")
        webbrowser.open(oauth_url)
        return server_thread

    async def login(self):
        logger.info(f"Starting login process for {self.account_type} account")
        if TwitchAuthManager._active_login.get(self.oauth_port, False):
            logger.error(f"Login already in progress for port {self.oauth_port}")
            raise RuntimeError(f"A login attempt is already in progress for port {self.oauth_port}. Please wait or close any previous login windows.")
            
        TwitchAuthManager._active_login[self.oauth_port] = True
        
        try:
            client_id, client_secret = self.credentials_manager.load_credentials()
            logger.info("Loaded Twitch API credentials")
            
            self.twitch = await Twitch(client_id, client_secret, authenticate_app=False)
            logger.info("Created Twitch API instance")
                
            redirect_url = f"http://localhost:{self.oauth_port}"  # No trailing slash
            scope_str = ' '.join([s.value for s in self.scopes])
            
            oauth_url = (
                f'https://id.twitch.tv/oauth2/authorize?response_type=code'
                f'&client_id={client_id}'
                f'&redirect_uri={urllib.parse.quote(redirect_url)}'
                f'&scope={urllib.parse.quote(scope_str)}'
                f'&force_verify=true'
            )
            
            self._login_cancelled = False
            self._oauth_result = OAuthResult()
            
            logger.info(f"Starting server thread for port {self.oauth_port}")
            server_thread = self._start_servers_and_browser(self._oauth_result, oauth_url)
            
            self.oauth_timer = threading.Timer(OAUTH_TIMEOUT_SECONDS, self._timeout_handler, args=(None,))
            self.oauth_timer.start()
            
            try:
                logger.info("Waiting for OAuth response")
                while not self._oauth_result.event.is_set() and not self._login_cancelled:
                    await asyncio.sleep(0.1)
                    
                if self._login_cancelled:
                    logger.info("Login was cancelled")
                    raise RuntimeError("Login was cancelled.")
                    
                if self._oauth_result.error:
                    error_msg = f"Twitch OAuth error: {self._oauth_result.error}"
                    if self._oauth_result.error_description:
                        error_msg += f" - {self._oauth_result.error_description}"
                    logger.error(error_msg)
                    if self._oauth_result.error == "redirect_mismatch":
                        error_msg += "\nPlease ensure the redirect URI matches exactly what is registered in your Twitch application settings."
                    raise RuntimeError(error_msg)
                    
                if not self._oauth_result.code:
                    logger.error("No code received from Twitch")
                    raise RuntimeError("No code received from Twitch.")
                    
                logger.info("Exchanging OAuth code for tokens")
                try:
                    async with aiohttp.ClientSession() as session:
                        token_url = "https://id.twitch.tv/oauth2/token"
                        payload = {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "code": self._oauth_result.code,
                            "grant_type": "authorization_code",
                            "redirect_uri": redirect_url
                        }
                        async with session.post(token_url, data=payload) as resp:
                            if resp.status != 200:
                                text = await resp.text()
                                logger.error(f"Failed to get token: {resp.status} {text}")
                                raise RuntimeError(f"Failed to get token: {resp.status} {text}")
                            token_data = await resp.json()
                    await self.twitch.set_user_authentication(token_data['access_token'], self.scopes, token_data['refresh_token'])
                    logger.info("Successfully exchanged code for tokens")
                except Exception as e:
                    logger.error(f"Failed to exchange code: {e}")
                    raise RuntimeError(f"Error in token exchange: {e}")
                
                if self.oauth_timer:
                    self.oauth_timer.cancel()
                    
                logger.info("OAuth login successful")
                
                # Save tokens to file so is_logged_in() works
                with open(self.token_file, 'w') as f:
                    json.dump({
                        'access_token': token_data['access_token'],
                        'refresh_token': token_data['refresh_token'],
                        'scopes': [s.value for s in self.scopes]
                    }, f)
                
                return self.twitch
            except Exception as e:
                logger.error(f"Error in login process: {e}")
                raise
            finally:
                await self._cleanup_login()
        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self._cleanup_login()
            raise

    def cancel_login(self):
        logger.info(f"Cancelling login on port {self.oauth_port}")
        self._login_cancelled = True
        if self.oauth_timer:
            self.oauth_timer.cancel()
        asyncio.run(self._cleanup_login())

    def _timeout_handler(self, _):
        logger.info(f"OAuth login timed out after {OAUTH_TIMEOUT_SECONDS} seconds on port {self.oauth_port}")
        self._login_cancelled = True
        if self.oauth_timer:
            self.oauth_timer.cancel()
        asyncio.run(self._cleanup_login())
        if self.on_timeout:
            self.on_timeout()

    async def _cleanup_login(self):
        logger.info(f"Cleaning up login state for port {self.oauth_port}")
        TwitchAuthManager._active_login[self.oauth_port] = False
        self.oauth_timer = None
        self._login_cancelled = False
        self._oauth_result = None
        
        async def cleanup_runners():
            for runner in TwitchAuthManager._aiohttp_runners:
                try:
                    await runner.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up runner: {e}")
        
        try:
            await cleanup_runners()
        finally:
            TwitchAuthManager._aiohttp_runners = []

    def is_logged_in(self):
        return Path(self.token_file).exists()

    def logout(self):
        logger.info(f"Logging out {self.account_type} account")
        if Path(self.token_file).exists():
            Path(self.token_file).unlink()
        asyncio.run(self._cleanup_login()) 