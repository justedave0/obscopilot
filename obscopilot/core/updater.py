"""
Updater module for OBSCopilot.

This module provides functionality to check for and apply updates to the application.
"""

import logging
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import urllib.request
import urllib.error
import hashlib
from packaging import version

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)

# Official update server URL
UPDATE_SERVER_URL = "https://api.example.com/obscopilot/updates"


@dataclass
class UpdateInfo:
    """Information about an available update."""
    
    version: str
    release_notes: str
    download_url: str
    file_size: int
    file_hash: str
    release_date: str
    is_critical: bool = False
    requires_restart: bool = True


class Updater:
    """Application updater."""
    
    def __init__(self, config: Config):
        """Initialize updater.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.current_version = self._get_current_version()
        self.update_server_url = config.get(
            'updater', 'server_url', UPDATE_SERVER_URL
        )
        self.auto_check = config.get_bool('updater', 'auto_check', True)
        self.auto_download = config.get_bool('updater', 'auto_download', False)
        self.check_interval = config.get_int('updater', 'check_interval', 86400)  # 24 hours
        self.last_check = config.get_int('updater', 'last_check', 0)
        self.update_channel = config.get('updater', 'channel', 'stable')
        
        # Update info
        self.available_update: Optional[UpdateInfo] = None
        self.download_progress = 0
        self.is_downloading = False
        self.downloaded_file: Optional[str] = None
        
    def _get_current_version(self) -> str:
        """Get the current application version.
        
        Returns:
            Current version string
        """
        try:
            # Import version from version.py
            from obscopilot.version import __version__
            return __version__
        except ImportError:
            logger.warning("Could not determine version from version.py")
            return "0.0.0"
            
    def should_check_for_updates(self) -> bool:
        """Check if the application should check for updates.
        
        Returns:
            True if updates should be checked, False otherwise
        """
        if not self.auto_check:
            return False
            
        current_time = int(time.time())
        time_since_last_check = current_time - self.last_check
        
        return time_since_last_check >= self.check_interval
        
    async def check_for_updates(self) -> bool:
        """Check for available updates.
        
        Returns:
            True if an update is available, False otherwise
        """
        try:
            # Update last check time
            current_time = int(time.time())
            self.config.set('updater', 'last_check', str(current_time))
            self.last_check = current_time
            
            # Get system info
            system_info = {
                'os': platform.system().lower(),
                'arch': platform.machine().lower(),
                'version': self.current_version,
                'channel': self.update_channel
            }
            
            # Build query parameters
            params = '&'.join([f"{k}={v}" for k, v in system_info.items()])
            url = f"{self.update_server_url}?{params}"
            
            # Send request
            logger.info(f"Checking for updates: {url}")
            response = urllib.request.urlopen(url, timeout=10)
            
            if response.getcode() != 200:
                logger.error(f"Error checking for updates: {response.getcode()}")
                return False
                
            # Parse response
            data = json.loads(response.read().decode('utf-8'))
            
            # Check if update is available
            if not data.get('available', False):
                logger.info("No updates available")
                return False
                
            # Get update info
            update_version = data.get('version')
            
            # Compare versions
            if version.parse(update_version) <= version.parse(self.current_version):
                logger.info(f"Current version ({self.current_version}) is up to date")
                return False
                
            # Create update info
            self.available_update = UpdateInfo(
                version=update_version,
                release_notes=data.get('release_notes', ''),
                download_url=data.get('download_url', ''),
                file_size=data.get('file_size', 0),
                file_hash=data.get('file_hash', ''),
                release_date=data.get('release_date', ''),
                is_critical=data.get('is_critical', False),
                requires_restart=data.get('requires_restart', True)
            )
            
            logger.info(f"Update available: {update_version}")
            
            # Emit update available event
            await event_bus.emit(Event(
                EventType.UPDATE_AVAILABLE,
                {
                    'version': update_version,
                    'current_version': self.current_version,
                    'is_critical': self.available_update.is_critical
                }
            ))
            
            # Auto download if enabled
            if self.auto_download:
                await self.download_update()
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return False
            
    async def download_update(self) -> bool:
        """Download the available update.
        
        Returns:
            True if download was successful, False otherwise
        """
        if not self.available_update:
            logger.error("No update available to download")
            return False
            
        if self.is_downloading:
            logger.warning("Already downloading update")
            return False
            
        try:
            self.is_downloading = True
            self.download_progress = 0
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
                # Get download URL
                url = self.available_update.download_url
                file_size = self.available_update.file_size
                
                # Download file
                logger.info(f"Downloading update from {url}")
                
                # Open URL
                response = urllib.request.urlopen(url, timeout=30)
                
                if response.getcode() != 200:
                    logger.error(f"Error downloading update: {response.getcode()}")
                    self.is_downloading = False
                    return False
                    
                # Download with progress updates
                downloaded = 0
                block_size = 8192
                
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                        
                    tmp_file.write(buffer)
                    downloaded += len(buffer)
                    
                    # Update progress
                    if file_size > 0:
                        self.download_progress = min(100, downloaded * 100 // file_size)
                        
                        # Emit progress event every 5%
                        if self.download_progress % 5 == 0:
                            await event_bus.emit(Event(
                                EventType.UPDATE_DOWNLOAD_PROGRESS,
                                {
                                    'progress': self.download_progress,
                                    'downloaded': downloaded,
                                    'total': file_size
                                }
                            ))
                    
            # Verify file hash
            file_path = tmp_file.name
            if not self._verify_file_hash(file_path, self.available_update.file_hash):
                logger.error("Update file hash verification failed")
                os.unlink(file_path)
                self.is_downloading = False
                return False
                
            # Set downloaded file
            self.downloaded_file = file_path
            
            logger.info(f"Update downloaded to {file_path}")
            
            # Emit download complete event
            await event_bus.emit(Event(
                EventType.UPDATE_DOWNLOAD_COMPLETE,
                {
                    'file_path': file_path,
                    'version': self.available_update.version
                }
            ))
            
            self.is_downloading = False
            return True
            
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            self.is_downloading = False
            return False
            
    def _verify_file_hash(self, file_path: str, expected_hash: str) -> bool:
        """Verify the hash of a downloaded file.
        
        Args:
            file_path: Path to the file
            expected_hash: Expected file hash
            
        Returns:
            True if hash matches, False otherwise
        """
        try:
            if not expected_hash:
                logger.warning("No hash provided for verification")
                return True
                
            # Calculate SHA-256 hash
            sha256_hash = hashlib.sha256()
            
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
                    
            file_hash = sha256_hash.hexdigest()
            
            # Compare hashes
            if file_hash.lower() != expected_hash.lower():
                logger.error(f"Hash mismatch: expected {expected_hash}, got {file_hash}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error verifying file hash: {e}")
            return False
            
    def install_update(self) -> bool:
        """Install the downloaded update.
        
        Returns:
            True if installation started successfully, False otherwise
        """
        if not self.downloaded_file:
            logger.error("No update downloaded to install")
            return False
            
        if not os.path.exists(self.downloaded_file):
            logger.error(f"Downloaded file not found: {self.downloaded_file}")
            self.downloaded_file = None
            return False
            
        try:
            # Platform-specific installation
            system = platform.system().lower()
            
            if system == 'windows':
                # Run installer
                subprocess.Popen(
                    [self.downloaded_file],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            elif system == 'darwin':
                # Mount DMG and run installer
                mount_dir = tempfile.mkdtemp()
                subprocess.run(['hdiutil', 'attach', self.downloaded_file, '-mountpoint', mount_dir])
                
                # Find the .app file
                app_path = None
                for item in os.listdir(mount_dir):
                    if item.endswith('.app'):
                        app_path = os.path.join(mount_dir, item)
                        break
                
                if not app_path:
                    logger.error("Could not find .app file in DMG")
                    return False
                    
                # Copy to Applications folder
                subprocess.run(['cp', '-R', app_path, '/Applications/'])
                
                # Detach the DMG
                subprocess.run(['hdiutil', 'detach', mount_dir])
                
            elif system == 'linux':
                # Make the AppImage executable
                os.chmod(self.downloaded_file, 0o755)
                
                # Replace the current executable
                current_exe = sys.executable
                backup_exe = f"{current_exe}.bak"
                
                # Backup current executable
                shutil.copy2(current_exe, backup_exe)
                
                # Copy new executable
                shutil.copy2(self.downloaded_file, current_exe)
                
            logger.info("Update installed successfully")
            
            # Restart if required
            if self.available_update and self.available_update.requires_restart:
                logger.info("Restarting application...")
                self._restart_application()
                
            return True
            
        except Exception as e:
            logger.error(f"Error installing update: {e}")
            return False
            
    def _restart_application(self):
        """Restart the application."""
        try:
            # Platform-specific restart
            if getattr(sys, 'frozen', False):
                # Running as executable
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                # Running as script
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            logger.error(f"Error restarting application: {e}")
            
    def cancel_download(self):
        """Cancel the current download."""
        if self.is_downloading:
            self.is_downloading = False
            logger.info("Update download cancelled")
            
    def clear_update(self):
        """Clear the current update information."""
        if self.downloaded_file and os.path.exists(self.downloaded_file):
            try:
                os.unlink(self.downloaded_file)
            except Exception as e:
                logger.error(f"Error deleting downloaded update: {e}")
                
        self.downloaded_file = None
        self.available_update = None
        self.download_progress = 0
        
    async def check_and_notify(self):
        """Check for updates and notify the user."""
        if self.should_check_for_updates():
            update_available = await self.check_for_updates()
            
            if update_available and self.available_update:
                logger.info(f"New version available: {self.available_update.version}")
                return True
                
        return False


# Single instance for the application
_updater = None

def get_updater(config: Config = None) -> Updater:
    """Get the updater instance.
    
    Args:
        config: Application configuration
        
    Returns:
        Updater instance
    """
    global _updater
    if not _updater and config:
        _updater = Updater(config)
    return _updater 