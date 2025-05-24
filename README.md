# ObsCoPilot

ObsCoPilot is a versatile and user-friendly Streamer.bot alternative with AI functionalities. It provides workflow automation, stream management, and interactive features for content creators across different platforms.

## Features

- User-friendly interface with dedicated Dashboard, Workflows, and Settings
- Cross-platform support (Windows, macOS, Linux)
- AI-powered automation capabilities
- Customizable workflow system
- **OBS WebSocket integration with automatic settings save and auto-connect**

## OBS WebSocket Settings

- Configure OBS WebSocket host, port, and password in the Settings tab.
- Settings are saved automatically as you type—no save button required.
- **Auto-connect:**
  - If you close the app while connected to OBS, it will auto-connect on next launch.
  - If you close the app while not connected, auto-connect will be disabled for the next launch.

## Setup and Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python main.py
   ```