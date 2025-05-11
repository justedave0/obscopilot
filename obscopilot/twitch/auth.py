"""
Twitch authentication module for OBSCopilot.

This module provides OAuth authentication functionality for Twitch API integration.
"""

import asyncio
import datetime
import logging
import secrets
import webbrowser
from typing import Dict, List, Optional, Callable, Any, Tuple

import aiohttp
from aiohttp import web

from obscopilot.core.config import Config
from obscopilot.storage.repositories import TwitchAuthRepository
from obscopilot.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)

# Twitch OAuth endpoints
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
TWITCH_REVOKE_URL = "https://id.twitch.tv/oauth2/revoke"

# Default scopes needed for OBSCopilot functionality
DEFAULT_BROADCASTER_SCOPES = [
    "channel:read:subscriptions",
    "channel:read:redemptions",
    "channel:read:polls",
    "channel:read:predictions",
    "channel:read:hype_train",
    "channel:read:goals",
    "channel:manage:redemptions",
    "channel:manage:polls",
    "channel:manage:predictions",
    "channel:manage:broadcasts",
    "moderator:read:followers",
    "moderator:read:chatters",
    "chat:read",
    "chat:edit"
]

DEFAULT_BOT_SCOPES = [
    "chat:read",
    "chat:edit",
    "channel:moderate",
    "whispers:read",
    "whispers:edit"
]


class TwitchAuthManager:
    """Twitch authentication manager for handling OAuth authentication flows."""
    
    def __init__(self, config: Config, auth_repo: TwitchAuthRepository):
        """Initialize Twitch auth manager.
        
        Args:
            config: Application configuration
            auth_repo: Twitch auth repository for token storage
        """
        self.config = config
        self.auth_repo = auth_repo
        self.app_runner = None
        self.server_port = 8000  # Default port for callback server
        self.state_tokens = {}  # Track state tokens for security
        self.auth_callbacks = {}  # Callbacks for when auth is completed
        
        # Get client credentials from config
        self.broadcaster_client_id = self.config.get('twitch', 'broadcaster_client_id', '')
        self.broadcaster_client_secret = self.config.get('twitch', 'broadcaster_client_secret', '')
        self.bot_client_id = self.config.get('twitch', 'bot_client_id', '')
        self.bot_client_secret = self.config.get('twitch', 'bot_client_secret', '')
        
        # Callback URL (must match the one registered on Twitch Developer Console)
        self.redirect_uri = f"http://localhost:{self.server_port}/auth/callback"
    
    async def start_callback_server(self) -> None:
        """Start the callback server for handling OAuth redirects."""
        app = web.Application()
        app.add_routes([web.get('/auth/callback', self._handle_auth_callback)])
        
        self.app_runner = web.AppRunner(app)
        await self.app_runner.setup()
        
        site = web.TCPSite(self.app_runner, 'localhost', self.server_port)
        await site.start()
        
        logger.info(f"Started authentication callback server on port {self.server_port}")
    
    async def stop_callback_server(self) -> None:
        """Stop the callback server."""
        if self.app_runner:
            await self.app_runner.cleanup()
            logger.info("Stopped authentication callback server")
    
    def start_auth_flow(self, account_type: str = 'broadcaster', 
                      callback: Optional[Callable] = None,
                      force: bool = False) -> str:
        """Start the Twitch OAuth authentication flow.
        
        Args:
            account_type: Type of account to authenticate ('broadcaster' or 'bot')
            callback: Optional callback function to call when auth is completed
            force: Force re-authentication even if tokens exist
            
        Returns:
            The authorization URL to navigate to
        """
        # Determine client ID and scopes based on account type
        if account_type == 'broadcaster':
            client_id = self.broadcaster_client_id
            scopes = DEFAULT_BROADCASTER_SCOPES
        elif account_type == 'bot':
            client_id = self.bot_client_id
            scopes = DEFAULT_BOT_SCOPES
        else:
            raise ValueError(f"Invalid account type: {account_type}")
        
        # Generate state token for security
        state = secrets.token_urlsafe(16)
        self.state_tokens[state] = account_type
        
        # Store callback if provided
        if callback:
            self.auth_callbacks[state] = callback
        
        # Build authorization URL
        params = {
            'client_id': client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'state': state,
            'force_verify': 'true' if force else 'false'
        }
        
        auth_url = f"{TWITCH_AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        
        # Automatically open browser if possible
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
        
        logger.info(f"Started {account_type} authentication flow. URL: {auth_url}")
        return auth_url
    
    async def _handle_auth_callback(self, request: web.Request) -> web.Response:
        """Handle the OAuth callback from Twitch.
        
        Args:
            request: The HTTP request with auth code
            
        Returns:
            HTTP response
        """
        # Check for error
        error = request.query.get('error')
        if error:
            error_description = request.query.get('error_description', 'Unknown error')
            logger.error(f"Authentication error: {error} - {error_description}")
            return web.Response(
                text=f"<h1>Authentication Failed</h1><p>{error_description}</p>",
                content_type='text/html'
            )
        
        # Verify state token
        state = request.query.get('state')
        if not state or state not in self.state_tokens:
            logger.error("Invalid state token received")
            return web.Response(
                text="<h1>Authentication Failed</h1><p>Invalid state token</p>",
                content_type='text/html'
            )
        
        # Get auth code
        code = request.query.get('code')
        if not code:
            logger.error("No authorization code received")
            return web.Response(
                text="<h1>Authentication Failed</h1><p>No authorization code received</p>",
                content_type='text/html'
            )
        
        # Exchange code for token
        account_type = self.state_tokens.pop(state)
        try:
            user_info = await self._exchange_code_for_token(code, account_type)
            
            # Execute callback if present
            callback = self.auth_callbacks.pop(state, None)
            if callback:
                asyncio.create_task(callback(user_info))
            
            return web.Response(
                text=f"""
                <h1>Authentication Successful</h1>
                <p>You have successfully authenticated with Twitch as {user_info['username']}.</p>
                <p>You can close this window and return to OBSCopilot.</p>
                """,
                content_type='text/html'
            )
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {e}")
            return web.Response(
                text=f"<h1>Authentication Failed</h1><p>Error: {str(e)}</p>",
                content_type='text/html'
            )
    
    async def _exchange_code_for_token(self, code: str, account_type: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Twitch
            account_type: Type of account ('broadcaster' or 'bot')
            
        Returns:
            User info including tokens and user_id
        """
        # Determine client ID and secret based on account type
        if account_type == 'broadcaster':
            client_id = self.broadcaster_client_id
            client_secret = self.broadcaster_client_secret
        elif account_type == 'bot':
            client_id = self.bot_client_id
            client_secret = self.bot_client_secret
        else:
            raise ValueError(f"Invalid account type: {account_type}")
        
        # Exchange code for token
        async with aiohttp.ClientSession() as session:
            async with session.post(TWITCH_TOKEN_URL, data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise ValueError(f"Failed to get access token: {error_text}")
                
                token_data = await resp.json()
                
                # Get user info with the token
                user_info = await self._validate_token(token_data['access_token'], client_id)
                
                # Store tokens in database
                user_data = {
                    'user_id': user_info['user_id'],
                    'username': user_info['login'],
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data['refresh_token'],
                    'scope': token_data['scope'],
                    'expires_in': token_data['expires_in']
                }
                
                # Save to database
                await self._save_tokens(user_data, account_type)
                
                return user_data
    
    async def _validate_token(self, token: str, client_id: str) -> Dict[str, Any]:
        """Validate an access token and get user info.
        
        Args:
            token: Access token to validate
            client_id: Client ID used to get the token
            
        Returns:
            User info from token validation
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'OAuth {token}'
            }
            
            async with session.get(TWITCH_VALIDATE_URL, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise ValueError(f"Invalid token: {error_text}")
                
                data = await resp.json()
                
                # Ensure token was issued for our client
                if data['client_id'] != client_id:
                    raise ValueError("Token was not issued for this client")
                
                return data
    
    async def _save_tokens(self, user_data: Dict[str, Any], account_type: str) -> None:
        """Save tokens to the database.
        
        Args:
            user_data: User data including tokens
            account_type: Type of account ('broadcaster' or 'bot')
        """
        # Calculate token expiration time
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=user_data['expires_in'])
        
        # Save to database
        await asyncio.to_thread(
            self.auth_repo.save_auth_data,
            user_id=user_data['user_id'],
            username=user_data['username'],
            access_token=user_data['access_token'],
            refresh_token=user_data['refresh_token'],
            scope=' '.join(user_data['scope']) if isinstance(user_data['scope'], list) else user_data['scope'],
            expires_in=user_data['expires_in']
        )
        
        # Update config
        if account_type == 'broadcaster':
            self.config.set('twitch', 'broadcaster_id', user_data['user_id'])
            self.config.set('twitch', 'broadcaster_username', user_data['username'])
        elif account_type == 'bot':
            self.config.set('twitch', 'bot_id', user_data['user_id'])
            self.config.set('twitch', 'bot_username', user_data['username'])
        
        self.config.save()
        
        # Emit event
        await event_bus.emit(Event(
            EventType.TWITCH_AUTH_UPDATED,
            data={
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'account_type': account_type
            }
        ))
        
        logger.info(f"Saved {account_type} auth data for user {user_data['username']} (ID: {user_data['user_id']})")
    
    async def refresh_token(self, user_id: str) -> Tuple[str, str]:
        """Refresh an access token.
        
        Args:
            user_id: User ID to refresh token for
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        # Get existing token from database
        auth_data = await asyncio.to_thread(self.auth_repo.get_by_user_id, user_id)
        if not auth_data:
            raise ValueError(f"No auth data found for user {user_id}")
        
        # Determine if this is broadcaster or bot
        account_type = None
        client_id = None
        client_secret = None
        
        if user_id == self.config.get('twitch', 'broadcaster_id'):
            account_type = 'broadcaster'
            client_id = self.broadcaster_client_id
            client_secret = self.broadcaster_client_secret
        elif user_id == self.config.get('twitch', 'bot_id'):
            account_type = 'bot'
            client_id = self.bot_client_id
            client_secret = self.bot_client_secret
        else:
            # For other users, determine by looking at scopes
            scopes = auth_data.scope.split(' ')
            if set(DEFAULT_BROADCASTER_SCOPES).intersection(set(scopes)):
                account_type = 'broadcaster'
                client_id = self.broadcaster_client_id
                client_secret = self.broadcaster_client_secret
            else:
                account_type = 'bot'
                client_id = self.bot_client_id
                client_secret = self.bot_client_secret
        
        # Refresh token
        async with aiohttp.ClientSession() as session:
            async with session.post(TWITCH_TOKEN_URL, data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': auth_data.refresh_token
            }) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise ValueError(f"Failed to refresh token: {error_text}")
                
                token_data = await resp.json()
                
                # Update tokens in database
                user_data = {
                    'user_id': user_id,
                    'username': auth_data.username,
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data['refresh_token'],
                    'scope': token_data['scope'],
                    'expires_in': token_data['expires_in']
                }
                
                await self._save_tokens(user_data, account_type)
                
                # Emit token refreshed event
                await event_bus.emit(Event(
                    EventType.TWITCH_TOKEN_REFRESHED,
                    data={
                        'user_id': user_id,
                        'username': auth_data.username,
                        'account_type': account_type
                    }
                ))
                
                logger.info(f"Refreshed {account_type} token for user {auth_data.username} (ID: {user_id})")
                
                return token_data['access_token'], token_data['refresh_token']
    
    async def revoke_token(self, user_id: str) -> bool:
        """Revoke a user's access token.
        
        Args:
            user_id: User ID to revoke token for
            
        Returns:
            True if revocation was successful
        """
        # Get existing token from database
        auth_data = await asyncio.to_thread(self.auth_repo.get_by_user_id, user_id)
        if not auth_data:
            logger.warning(f"No auth data found for user {user_id}")
            return False
        
        # Determine client ID
        account_type = None
        client_id = None
        
        if user_id == self.config.get('twitch', 'broadcaster_id'):
            account_type = 'broadcaster'
            client_id = self.broadcaster_client_id
        elif user_id == self.config.get('twitch', 'bot_id'):
            account_type = 'bot'
            client_id = self.bot_client_id
        else:
            # For other users, determine by looking at scopes
            scopes = auth_data.scope.split(' ')
            if set(DEFAULT_BROADCASTER_SCOPES).intersection(set(scopes)):
                account_type = 'broadcaster'
                client_id = self.broadcaster_client_id
            else:
                account_type = 'bot'
                client_id = self.bot_client_id
        
        # Revoke token
        async with aiohttp.ClientSession() as session:
            async with session.post(TWITCH_REVOKE_URL, data={
                'client_id': client_id,
                'token': auth_data.access_token
            }) as resp:
                success = resp.status == 200
                
                if success:
                    # Delete from database
                    await asyncio.to_thread(self.auth_repo.delete, auth_data.id)
                    
                    # Emit event
                    await event_bus.emit(Event(
                        EventType.TWITCH_AUTH_REVOKED,
                        data={
                            'user_id': user_id,
                            'username': auth_data.username,
                            'account_type': account_type
                        }
                    ))
                    
                    logger.info(f"Revoked {account_type} token for user {auth_data.username} (ID: {user_id})")
                
                return success
    
    async def get_access_token(self, user_id: str) -> str:
        """Get a valid access token for the specified user.
        
        This will automatically refresh the token if it's expired.
        
        Args:
            user_id: User ID to get token for
            
        Returns:
            Valid access token
        """
        # Get existing token from database
        auth_data = await asyncio.to_thread(self.auth_repo.get_by_user_id, user_id)
        if not auth_data:
            raise ValueError(f"No auth data found for user {user_id}")
        
        # Check if token is expired
        if (auth_data.expires_at and 
            auth_data.expires_at < datetime.datetime.utcnow() + datetime.timedelta(minutes=5)):
            # Refresh token
            access_token, _ = await self.refresh_token(user_id)
            return access_token
        
        return auth_data.access_token
    
    def is_authenticated(self, account_type: str = 'broadcaster') -> bool:
        """Check if the specified account type is authenticated.
        
        Args:
            account_type: Type of account to check ('broadcaster' or 'bot')
            
        Returns:
            True if authenticated
        """
        if account_type == 'broadcaster':
            user_id = self.config.get('twitch', 'broadcaster_id')
        elif account_type == 'bot':
            user_id = self.config.get('twitch', 'bot_id')
        else:
            raise ValueError(f"Invalid account type: {account_type}")
        
        return bool(user_id) and self.auth_repo.get_by_user_id(user_id) is not None 