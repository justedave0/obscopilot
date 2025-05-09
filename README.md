# OBSCopilot

A Python plugin for OBS Studio that integrates Twitch functionality directly into OBS, allowing streamers to manage their stream without external tools like Streamer.bot.

## Features

- **Twitch Integration**: Connect your broadcaster account and optionally a separate bot account
- **Event Listening**: Respond to Twitch events like follows, subs, channel points redemptions, and more
- **OBS Control**: Trigger OBS actions when Twitch events occur:
  - Show/hide sources
  - Switch scenes
  - Update text content
- **Easy to Configure**: Simple UI directly within OBS
- **No External Apps**: Everything runs within OBS - no additional applications needed

## Requirements

- OBS Studio 28.0 or higher
- Python 3.7 or higher
- Active Twitch account with API access

## Installation

OBSCopilot provides multiple installation methods to suit different needs.

### Option 1: Easy Installer (Recommended)

The easiest way to install OBSCopilot is using the included installer script:

1. Download or clone this repository
2. Run the installer script:
   ```bash
   python install.py
   ```
3. Choose your preferred installation method from the menu
4. Follow the on-screen instructions

### Option 2: Manual Installation

If you prefer to install manually, follow these steps:

#### Dependencies

The plugin requires these Python packages:

```bash
pip install twitchio obsws-python requests
```

#### Installing the Plugin

1. Download the `obscopilot` folder from this repository
2. Copy the folder to your OBS scripts directory:
   - Windows: `%APPDATA%\obs-studio\scripts\`
   - macOS: `~/Library/Application Support/obs-studio/scripts/`
   - Linux: `~/.config/obs-studio/scripts/`
3. Open OBS Studio
4. Go to Tools → Scripts
5. Click the + button to add a new script
6. Navigate to and select the `obscopilot.py` file
7. The plugin should now appear in the scripts list

### Option 3: Embedded Virtual Environment

For a completely isolated installation that won't interfere with your system Python:

1. Download or clone this repository
2. Run the embedded installation script:
   ```bash
   python setup_embedded_venv.py
   ```
3. Open OBS Studio
4. Go to Tools → Scripts
5. Click the + button to add a new script
6. Navigate to and select the `obscopilot_launcher.py` file in your OBS scripts directory

This method creates a self-contained Python environment with all dependencies installed.

### Twitch Application Setup

1. Go to the [Twitch Developer Console](https://dev.twitch.tv/console/apps)
2. Click "Register Your Application"
3. Fill in the following:
   - Name: OBSCopilot (or any name you prefer)
   - OAuth Redirect URLs: `http://localhost`
   - Category: "Application Integration"
4. Click "Create"
5. Click "Manage" on your new application
6. Note down the Client ID
7. Click "New Secret" to generate a Client Secret, and note it down as well

### 4. Configure the Plugin

1. In OBS, go to Tools → Scripts
2. Select the OBSCopilot script
3. Enter your Twitch Client ID and Client Secret in the broadcaster section
4. Click "Authenticate Broadcaster Account" and complete the authentication flow in your browser
5. (Optional) Repeat the process for a bot account if you want to use a separate account for chat messages
6. Configure additional settings as needed

## Usage

### Creating Event Actions

The plugin allows you to respond to Twitch events by performing actions in OBS:

1. In the plugin settings, click "Add Event Action"
2. Follow the prompts to set up the trigger event and the corresponding action
3. You can create actions for events like:
   - New followers
   - New subscribers
   - Bits/cheers
   - Channel point redemptions
   - Stream going online/offline

### Example Uses

- Show a special overlay when someone follows your channel
- Change scenes when raid events occur
- Update text sources with the name of the latest subscriber
- Make sources visible when receiving bits

## Troubleshooting

### Plugin Not Loading

- Make sure Python is correctly installed and in your system PATH
- Ensure all required Python packages are installed
- Check the OBS log for any Python-related errors

### Authentication Failures

- Verify your Client ID and Client Secret are entered correctly
- Make sure your Twitch application has the correct redirect URI
- Check your internet connection

### Event Actions Not Working

- Ensure the source and scene names match exactly what's in OBS
- Verify the bot is running (click "Start Bot" if needed)
- Check if the action's conditions match the incoming events

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OBS Project for their excellent software and API
- TwitchIO developers for the Twitch integration library
- obsws-python creators for the OBS WebSocket client 