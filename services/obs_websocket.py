try:
    from obswebsocket import obsws, requests
except ImportError:
    obsws = None
    requests = None

class OBSWebSocketService:
    def __init__(self):
        self.ws = None
        self.connected = False

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

    def disconnect(self):
        if self.ws and self.connected:
            self.ws.disconnect()
            self.connected = False
            self.ws = None 