# OBSCopilot

A cross-platform Python application serving as a Twitch live assistant with workflow automation capabilities.

## Features

- Twitch integration for follows, subscriptions, chat, and point redemptions
- OBS control for scenes, sources, streaming/recording
- AI-generated responses using OpenAI
- Custom workflow automation system
- User-friendly GUI

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure your .env file with:
   ```
   TWITCH_CLIENT_ID=your_client_id
   TWITCH_CLIENT_SECRET=your_client_secret
   OPENAI_API_KEY=your_openai_key
   ```
4. Run the application:
   ```
   python main.py
   ```

## Requirements

- Python 3.8+
- OBS Studio with obs-websocket plugin installed
- Twitch account with developer application
- OpenAI API access (optional)

## Use Cases

- Trigger OBS sources when viewers redeem channel points
- Send automatic thank you messages for follows, subs, and raids
- Create interactive chat commands that control your stream
- Build complex workflows combining multiple triggers and actions
- Generate AI responses personalized to your viewers

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Twitch account(s) - broadcaster and optionally a bot account
- OBS Studio with obs-websocket plugin installed
- Optional: OpenAI API key for AI-generated responses

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/obscopilot.git
cd obscopilot
```

2. Create a virtual environment:
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example environment file:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your Twitch API credentials and other settings.

6. Run the application:
```bash
python -m obscopilot
```

## Development

See [TASKS.md](TASKS.md) for the development roadmap and current progress.

### Project Structure

```
obscopilot/
├── core/              # Core application components
│   ├── config.py      # Configuration management
│   ├── auth.py        # Authentication services
│   └── events.py      # Event system
├── twitch/            # Twitch API integration
│   ├── client.py      # Twitch client
│   └── events.py      # Twitch event handlers
├── obs/               # OBS integration
│   └── client.py      # OBS WebSocket client
├── workflows/         # Workflow engine
│   ├── engine.py      # Workflow execution engine
│   ├── models.py      # Workflow data models
│   └── actions/       # Standard actions
├── ai/                # AI integration
│   └── openai.py      # OpenAI API client
├── ui/                # User interface
│   ├── main.py        # Main window
│   ├── workflows.py   # Workflow editor
│   └── settings.py    # Settings panel
├── storage/           # Data persistence
│   ├── database.py    # Database management
│   └── models.py      # Database models
└── main.py            # Application entry point
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [TwitchIO](https://github.com/PythonistaGuild/TwitchIO) - Python library for Twitch API
- [PyQt](https://riverbankcomputing.com/software/pyqt/intro) - Python bindings for Qt
- [obs-websocket-py](https://github.com/Elektordi/obs-websocket-py) - Python client for OBS WebSocket
- [SpiffWorkflow](https://github.com/sartography/SpiffWorkflow) - Workflow engine for Python
