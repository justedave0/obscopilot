import tkinter as tk
from tkinter import ttk
from ui.settings import SettingsTab

import os
from services.twitch.credentials import TwitchCredentialsManager
from dotenv import load_dotenv
import sys

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ktinker OBS Controller")
        self.geometry("400x250")
        self._build_ui()

    def _build_ui(self):
        tab_control = ttk.Notebook(self)
        # Workflows Tab (empty)
        workflows_tab = ttk.Frame(tab_control)
        tab_control.add(workflows_tab, text="Workflows")
        # Settings Tab
        settings_tab = SettingsTab(tab_control)
        tab_control.add(settings_tab, text="Settings")
        tab_control.pack(expand=1, fill="both")

if __name__ == "__main__":
    if '--set-twitch-credentials' in sys.argv:
        load_dotenv()
        client_id = os.getenv('TWITCH_CLIENT_ID')
        client_secret = os.getenv('TWITCH_CLIENT_SECRET')
        if not client_id or not client_secret:
            print("TWITCH_CLIENT_ID and/or TWITCH_CLIENT_SECRET not found in .env file.")
            sys.exit(1)
        TwitchCredentialsManager().save_credentials(client_id, client_secret)
        print("Twitch credentials saved securely from .env!")
    else:
        app = MainApp()
        app.mainloop() 