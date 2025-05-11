# Contributing to OBSCopilot

First of all, thank you for considering contributing to OBSCopilot! We appreciate your time and effort, and we value any contribution, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Requests

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Pull Request Process

1. Update the README.md or documentation with details of changes if appropriate
2. Update the CHANGELOG.md with the details of your changes
3. The PR will be merged once it gets approved by a maintainer

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- OBS Studio (for testing)
- Twitch account (for testing)

### Setting up the Development Environment

1. Clone your fork of the repository:
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

3. Install development dependencies:
   ```
   pip install -r requirements-dev.txt
   ```

4. Install the package in development mode:
   ```
   pip install -e .
   ```

5. Run the application:
   ```
   python -m obscopilot.main
   ```

### Running Tests

```
python -m pytest
```

### Code Style

We follow the PEP 8 style guide for Python code. We use `black` for code formatting and `flake8` for linting.

To format your code:
```
black obscopilot tests
```

To lint your code:
```
flake8 obscopilot tests
```

## Issue Reporting

### Bug Reports

We use GitHub issues to track bugs. Report a bug by [opening a new issue](https://github.com/yourusername/obscopilot/issues/new).

When reporting a bug, please include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots if applicable
- Your environment (OS, Python version, OBS version, etc.)
- Any additional context

### Feature Requests

Feature requests are welcome! Please use the feature request template when creating a new issue and provide as much detail as possible.

## Extending OBSCopilot

### Adding New Trigger Types

1. Create a new class in `obscopilot/workflows/triggers/` that inherits from `BaseTrigger`.
2. Implement the required methods: `matches`, `config_schema`, etc.
3. Register the trigger in `obscopilot/workflows/registry.py`.
4. Add tests for your trigger in `tests/workflows/triggers/`.

### Adding New Action Types

1. Create a new class in `obscopilot/workflows/actions/` that inherits from `BaseAction`.
2. Implement the required methods: `execute`, `config_schema`, etc.
3. Register the action in `obscopilot/workflows/registry.py`.
4. Add tests for your action in `tests/workflows/actions/`.

### Adding New UI Components

1. Create a new module in `obscopilot/ui/` for your component.
2. Implement your component using PyQt6.
3. Integrate your component with the main UI.
4. Add documentation for your component.

## Community

Join our community channels to get help, discuss features, or just chat:

- [Discord](https://discord.gg/obscopilot)
- [Reddit](https://reddit.com/r/obscopilot)

## License

By contributing to OBSCopilot, you agree that your contributions will be licensed under the project's MIT License. 