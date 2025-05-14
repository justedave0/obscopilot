# ObsCoPilot

ObsCoPilot is a versatile and user-friendly Streamer.bot alternative with AI functionalities. It provides workflow automation, stream management, and interactive features for content creators across different platforms.

## Features

- User-friendly interface with dedicated Dashboard, Workflows, and Settings
- Cross-platform support (Windows, macOS, Linux)
- AI-powered automation capabilities
- Customizable workflow system

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/obscopilot.git
cd obscopilot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

## Requirements

- Python 3.8 or higher
- PyQt6

## Testing

The project includes a comprehensive test suite. To run the tests:

```bash
# Run all tests
python -m pytest

# Run tests with verbose output
python -m pytest -v

# Run tests in a specific file
python -m pytest tests/test_settings_tab.py

# Run a specific test
python -m pytest tests/test_obs_websocket.py::TestOBSWebSocketService::test_connect_success

# Run tests with coverage report
python -m pytest --cov=services --cov=ui --cov-report=term --cov-report=html
```

The test coverage report will be generated in the `htmlcov` directory.