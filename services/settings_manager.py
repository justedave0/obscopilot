import json
import os

class SettingsManager:
    SETTINGS_FILE = 'settings.json'

    def __init__(self):
        self.settings = self._load_settings()

    def _load_settings(self):
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def get_obs_websocket_config(self):
        return self.settings.get('obs_websocket', {
            'host': 'localhost',
            'port': 4455,
            'password': ''
        })

    def set_obs_websocket_config(self, host, port, password):
        self.settings['obs_websocket'] = {
            'host': host,
            'port': port,
            'password': password
        }
        self.save_settings()

    def get_obs_autoconnect(self):
        return self.settings.get('obs_autoconnect', False)

    def set_obs_autoconnect(self, value: bool):
        self.settings['obs_autoconnect'] = value
        self.save_settings() 