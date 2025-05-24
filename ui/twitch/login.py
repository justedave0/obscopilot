import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
from threading import Thread
from services.twitch.auth import TwitchAuthManager

class TwitchLoginFrame(ttk.LabelFrame):
    def __init__(self, parent, account_type='broadcaster'):
        label = f"Twitch Login ({'Broadcaster' if account_type == 'broadcaster' else 'Bot'})"
        super().__init__(parent, text=label)
        self.account_type = account_type
        self.status_var = tk.StringVar()
        self.login_in_progress = False
        self._build_ui()
        self.auth_manager = TwitchAuthManager(account_type, on_timeout=self._on_timeout)
        self._update_status()

    def _build_ui(self):
        self.login_btn = ttk.Button(self, text="Login", command=self._on_login)
        self.login_btn.grid(row=0, column=0, padx=5, pady=5)
        self.logout_btn = ttk.Button(self, text="Logout", command=self._on_logout)
        self.logout_btn.grid(row=0, column=1, padx=5, pady=5)
        self.cancel_btn = ttk.Button(self, text="Cancel Login", command=self._on_cancel_login)
        self.cancel_btn.grid(row=0, column=2, padx=5, pady=5)
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5)

    def _update_status(self):
        if self.login_in_progress:
            self.status_var.set("Login in progress...")
            self.login_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.NORMAL)
        elif self.auth_manager.is_logged_in():
            self.status_var.set("Logged in")
            self.login_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)
        else:
            self.status_var.set("Not logged in")
            self.login_btn.config(state=tk.NORMAL)
            self.logout_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.DISABLED)

    def _on_login(self):
        if self.login_in_progress:
            return  # Prevent double login
        self.login_in_progress = True
        self._update_status()
        def do_login():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.auth_manager.login())
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Twitch Login Error", str(err)))
            finally:
                self.login_in_progress = False
                self.after(0, self._update_status)
                loop.close()
        Thread(target=do_login, daemon=True).start()

    def _on_logout(self):
        self.auth_manager.logout()
        self._update_status()

    def _on_cancel_login(self):
        self.auth_manager.cancel_login()
        self.login_in_progress = False
        self._update_status()

    def _on_timeout(self):
        messagebox.showwarning("Twitch Login Timeout", "Twitch login timed out after 5 minutes. Please try again.")
        self.login_in_progress = False
        self._update_status() 