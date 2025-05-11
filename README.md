# OBSCopilot

![OBSCopilot Logo](obscopilot/resources/logo.png)

OBSCopilot is a comprehensive streaming assistant that integrates with OBS Studio and Twitch to provide workflow automation, stream health monitoring, and AI-powered interaction with your audience.

## Features

- **Workflow Automation:** Create custom workflows triggered by Twitch events (follows, subscriptions, chat commands) to perform actions in OBS and more.
- **Stream Health Monitoring:** Keep track of CPU usage, FPS, dropped frames, and other important metrics to ensure your stream runs smoothly.
- **AI Integration:** Automatically generate chat responses using OpenAI and Google AI.
- **Twitch Integration:** Connect to Twitch for chat, follows, subscriptions, bits, and channel point redemptions.
- **OBS Control:** Switch scenes, control sources, manage recording/streaming, and more directly from the application.
- **User Statistics:** Track viewer engagement, watch time, and other metrics.
- **Dashboard:** Monitor real-time statistics and events through a comprehensive dashboard.
- **Customizable Themes:** Choose between dark and light themes to suit your preference.

## Installation

### System Requirements

- Python 3.9 or higher
- OBS Studio with WebSocket plugin (version 4.9.0 or higher)
- Twitch account with registered application

### Installing from Release

1. Download the latest release for your platform from the [Releases](https://github.com/yourusername/obscopilot/releases) page.
2. Install the application:
   - Windows: Run the installer (.exe)
   - macOS: Mount the DMG and drag the application to your Applications folder
   - Linux: Make the AppImage executable and run it

### Installing from Source

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/obscopilot.git
   cd obscopilot
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python -m obscopilot.main
   ```

## Getting Started

1. Configure your connections:
   - Set up your Twitch API credentials in the Settings tab
   - Configure your OBS WebSocket connection details

2. Connect to your services:
   - Click "Connect" for Twitch and OBS in the Connections tab

3. Create your first workflow:
   - Go to the Workflows tab
   - Click "Create Workflow"
   - Add triggers and actions
   - Save and enable your workflow

4. Start streaming and enjoy the automation!

## Development

### Project Structure

- `obscopilot/` - Main application code
  - `core/` - Core functionality and utilities
  - `workflows/` - Workflow engine and components
  - `twitch/` - Twitch API integration
  - `obs/` - OBS WebSocket integration
  - `ai/` - AI services integration
  - `ui/` - User interface components
  - `storage/` - Database and persistence
- `tests/` - Test suite
- `docs/` - Documentation
- `installer/` - Installer scripts

### Running Tests

```
python -m pytest
```

### Building Installers

```
python installer/build_installers.py
```

## Contributing

We welcome contributions to OBSCopilot! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OBS WebSocket](https://github.com/obsproject/obs-websocket) for enabling OBS control
- [TwitchIO](https://github.com/TwitchIO/TwitchIO) for Twitch API integration
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework
- All the amazing contributors and testers who've helped shape this project

## Contact

For support, feature requests, or bug reports, please [open an issue](https://github.com/yourusername/obscopilot/issues) on GitHub.
