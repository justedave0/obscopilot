import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from services.obs_websocket import OBSWebSocketService
from services.settings_manager import SettingsManager
from ui.twitch.login import TwitchLoginFrame

class OBSWebSocketConfig(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.connected = False
        self.ws_service = OBSWebSocketService()
        self.settings_manager = SettingsManager()
        self._build_ui()
        self._load_settings()
        self._try_autoconnect()
        self._register_close_handler()

    def _build_ui(self):
        # Host
        ttk.Label(self, text="Host (IP Address):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.host_var = tk.StringVar()
        self.host_var.trace_add('write', self._on_settings_change)
        ttk.Entry(self, textvariable=self.host_var).grid(row=0, column=1, pady=2)
        # Port
        ttk.Label(self, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.port_var = tk.IntVar()
        self.port_var.trace_add('write', self._on_settings_change)
        ttk.Entry(self, textvariable=self.port_var).grid(row=1, column=1, pady=2)
        # Password
        ttk.Label(self, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar()
        self.password_var.trace_add('write', self._on_settings_change)
        ttk.Entry(self, textvariable=self.password_var, show="*").grid(row=2, column=1, pady=2)
        # Connect/Disconnect Button
        self.connect_btn = ttk.Button(self, text="Connect", command=self._on_connect)
        self.connect_btn.grid(row=3, column=0, columnspan=2, pady=8)
        self.status_label = ttk.Label(self, text="Not connected", foreground="red")
        self.status_label.grid(row=4, column=0, columnspan=2)

    def _load_settings(self):
        config = self.settings_manager.get_obs_websocket_config()
        self.host_var.set(config.get('host', 'localhost'))
        self.port_var.set(config.get('port', 4455))
        self.password_var.set(config.get('password', ''))

    def _try_autoconnect(self):
        if self.settings_manager.get_obs_autoconnect():
            host = self.host_var.get()
            port = self.port_var.get()
            password = self.password_var.get()
            try:
                self.ws_service.connect(host, port, password)
                self.connected = True
                self.connect_btn.config(text="Disconnect", command=self._on_disconnect)
                self.status_label.config(text="Connected (auto)", foreground="green")
            except Exception:
                self.connected = False
                self.connect_btn.config(text="Connect", command=self._on_connect)
                self.status_label.config(text="Not connected", foreground="red")

    def _register_close_handler(self):
        root = self.winfo_toplevel()
        self._orig_close_handler = root.protocol("WM_DELETE_WINDOW", self._on_app_close)

    def _on_app_close(self):
        # Set auto-connect ON if connected, OFF if not connected
        self.settings_manager.set_obs_autoconnect(self.connected)
        root = self.winfo_toplevel()
        root.destroy()

    def _on_settings_change(self, *args):
        # Save settings automatically when any field changes
        self.settings_manager.set_obs_websocket_config(
            self.host_var.get(),
            self.port_var.get(),
            self.password_var.get()
        )

    def _on_connect(self):
        if not self.ws_service.is_available():
            messagebox.showerror("Dependency Error", "obs-websocket-py is not installed.")
            return
        if not self.connected:
            host = self.host_var.get()
            port = self.port_var.get()
            password = self.password_var.get()
            try:
                self.ws_service.connect(host, port, password)
                self.connected = True
                self.connect_btn.config(text="Disconnect", command=self._on_disconnect)
                self.status_label.config(text="Connected", foreground="green")
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
        else:
            self._on_disconnect()

    def _on_disconnect(self):
        try:
            self.ws_service.disconnect()
        except Exception:
            pass
        self.connected = False
        self.connect_btn.config(text="Connect", command=self._on_connect)
        self.status_label.config(text="Not connected", foreground="red")

class SettingsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # OBS WebSocket Section
        obs_section = ttk.LabelFrame(self, text="OBS WebSocket Settings")
        obs_config = OBSWebSocketConfig(obs_section)
        obs_config.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        obs_section.pack(fill=tk.X, expand=False, padx=10, pady=(10, 5))

        # Twitch Section
        twitch_section = ttk.LabelFrame(self, text="Twitch Settings")
        self.twitch_broadcaster = TwitchLoginFrame(twitch_section, account_type='broadcaster')
        self.twitch_broadcaster.pack(fill=tk.X, expand=False, padx=10, pady=(5, 2))
        self.twitch_bot = TwitchLoginFrame(twitch_section, account_type='bot')
        self.twitch_bot.pack(fill=tk.X, expand=False, padx=10, pady=(2, 10))
        twitch_section.pack(fill=tk.X, expand=False, padx=10, pady=(5, 10))

        # Placeholder for other settings
        other_section = ttk.LabelFrame(self, text="Other Settings (Coming Soon)")
        ttk.Label(other_section, text="More settings will be available here.").pack(padx=10, pady=10)
        other_section.pack(fill=tk.X, expand=False, padx=10, pady=(5, 10)) 