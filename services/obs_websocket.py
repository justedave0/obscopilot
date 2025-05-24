try:
    from obswebsocket import obsws, requests
    from obswebsocket.exceptions import ConnectionFailure
except ImportError:
    obsws = None
    requests = None
    ConnectionFailure = Exception

import threading
import time

class OBSWebSocketService:
    def __init__(self):
        self.ws = None
        self.connected = False
        self._monitor_thread = None
        self._stop_monitor = threading.Event()
        self.on_disconnect = None  # Callback for disconnect event

    def is_available(self):
        return obsws is not None

    def connect(self, host, port, password):
        if not self.is_available():
            raise RuntimeError("obs-websocket-py is not installed.")
        if self.connected:
            return
        self.ws = obsws(host, port, password)
        self.ws.connect()
        self.connected = True
        self._start_monitor()

    def disconnect(self):
        self._stop_monitor.set()
        if self.ws and self.connected:
            self.ws.disconnect()
            self.connected = False
            self.ws = None

    def _start_monitor(self):
        self._stop_monitor.clear()
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self._monitor_thread.start()

    def _monitor_connection(self):
        while not self._stop_monitor.is_set():
            if self.ws and self.connected:
                try:
                    # Try a simple request to check connection
                    self.ws.call(requests.GetVersion())
                except Exception:
                    self.connected = False
                    if self.on_disconnect:
                        self.on_disconnect()
                    break
            time.sleep(2) 