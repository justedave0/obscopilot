import os
from cryptography.fernet import Fernet

class TwitchCredentialsManager:
    KEY_FILE = 'twitch_app.key'
    ENCRYPTED_CREDENTIALS_FILE = 'twitch_app_credentials.enc'

    def __init__(self):
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)

    def _load_or_create_key(self):
        if os.path.exists(self.KEY_FILE):
            with open(self.KEY_FILE, 'rb') as f:
                return f.read()
        key = Fernet.generate_key()
        with open(self.KEY_FILE, 'wb') as f:
            f.write(key)
        return key

    def save_credentials(self, client_id, client_secret):
        data = f'{client_id}\n{client_secret}'.encode()
        encrypted = self.fernet.encrypt(data)
        with open(self.ENCRYPTED_CREDENTIALS_FILE, 'wb') as f:
            f.write(encrypted)

    def load_credentials(self):
        if not os.path.exists(self.ENCRYPTED_CREDENTIALS_FILE):
            raise FileNotFoundError('Twitch app credentials not found.')
        with open(self.ENCRYPTED_CREDENTIALS_FILE, 'rb') as f:
            encrypted = f.read()
        data = self.fernet.decrypt(encrypted).decode().split('\n')
        return data[0], data[1]  # client_id, client_secret 