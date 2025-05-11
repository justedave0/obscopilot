# OBSCopilot Documentation

Welcome to the OBSCopilot documentation. This guide will help you get started with OBSCopilot, a powerful streaming assistant application that integrates with OBS Studio and Twitch.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Workflows](#workflows)
5. [Stream Health Monitoring](#stream-health-monitoring)
6. [AI Integration](#ai-integration)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

## Introduction

OBSCopilot is a cross-platform Python application that serves as a Twitch live assistant with workflow automation capabilities. It helps streamers automate tasks, monitor stream health, interact with viewers through AI, and more.

Key features include:
- Twitch integration for chat, follows, subscriptions, and more
- OBS Studio control for scene switching, source visibility, and recording/streaming control
- Workflow automation system to trigger actions based on events
- Stream health monitoring to keep track of CPU usage, FPS, and dropped frames
- (optionnal) AI integration with OpenAI and Google AI for automated chat responses
- Customizable dashboard with live statistics
- Dark and light themes

## Installation

### System Requirements

- Python 3.9 or higher
- OBS Studio with WebSocket plugin (version 4.9.0 or higher)
- Twitch account with registered application

### Installing OBSCopilot

1. Download the latest release from the [releases page](https://github.com/yourusername/obscopilot/releases).
2. Extract the archive to a location of your choice.
3. Run the installer for your platform:
   - Windows: Double-click the `setup.exe` file.
   - macOS: Open the `.dmg` file and drag OBSCopilot to your Applications folder.
   - Linux: Extract the `.tar.gz` file and run `./install.sh`.

## Getting Started

### Connecting to Twitch

1. Open OBSCopilot and go to the Settings tab.
2. Enter your Twitch API credentials:
   - Client ID: Get this from the [Twitch Developer Console](https://dev.twitch.tv/console/apps).
   - Client Secret: Get this from the Twitch Developer Console.
   - Channel: Your Twitch channel name.
3. Click "Save Settings".
4. Go to the Connections tab and click "Connect to Twitch".

### Connecting to OBS

1. In OBS Studio, make sure the WebSocket plugin is installed and enabled.
2. Go to Tools > WebSocket Server Settings and note the server port and password (if set).
3. In OBSCopilot, go to the Settings tab.
4. Enter your OBS WebSocket details:
   - WebSocket URL: Usually `ws://localhost:4455` for local OBS installations.
   - Password: The password you set in OBS WebSocket settings (leave blank if none).
5. Click "Save Settings".
6. Go to the Connections tab and click "Connect to OBS".

## Workflows

Workflows are the heart of OBSCopilot's automation capabilities. A workflow consists of triggers and actions.

### Creating a Workflow

1. Go to the Workflows tab and click "Create Workflow".
2. Enter a name and description for your workflow.
3. Add triggers by clicking "Add Trigger":
   - Choose a trigger type (e.g., Twitch Follow, Chat Message, etc.).
   - Configure the trigger settings.
4. Add actions by clicking "Add Action":
   - Choose an action type (e.g., Send Chat Message, Switch Scene, etc.).
   - Configure the action settings.
5. Click "Save" to save your workflow.

### Example Workflows

#### Welcome New Followers

Trigger: Twitch Follow
Actions:
1. Show the follower alert source in OBS
2. Play a sound
3. Send a thank you message in chat

#### Scene Switching with Chat Commands

Trigger: Twitch Chat Message with pattern `!scene`
Actions:
1. Switch to the specified scene in OBS
2. Send a confirmation message in chat

## Stream Health Monitoring

OBSCopilot monitors various stream health metrics:

- CPU usage
- FPS
- Dropped frames
- Bitrate
- Stream status

The Stream Health tab shows real-time charts and alerts for these metrics. You can set custom thresholds for warnings and alerts in the Settings tab.

## AI Integration

OBSCopilot integrates with AI services to provide intelligent responses to chat messages.

### Setting up OpenAI

1. Get an API key from [OpenAI](https://platform.openai.com/account/api-keys).
2. In OBSCopilot, go to the Settings tab.
3. Enter your OpenAI API key.
4. Set your preferred model (default is gpt-3.5-turbo).
5. Click "Save Settings".

### Using AI in Workflows

You can use AI responses in your workflows:

1. Create a workflow with a Twitch Chat Message trigger.
2. Add an "AI Chat Response" action.
3. Configure the action with appropriate prompts and context.

## Troubleshooting

### Common Issues

#### Cannot Connect to Twitch

- Check that your Twitch API credentials are correct.
- Ensure your application is registered with the correct redirect URI.
- Check your internet connection.

#### Cannot Connect to OBS

- Make sure OBS is running and the WebSocket plugin is enabled.
- Verify the WebSocket server port and password.
- Check if any firewall is blocking the connection.

#### Workflows Not Triggering

- Check if the workflow is enabled.
- Verify that the trigger conditions are being met.
- Check the application logs for any errors.

### Logs

Logs are stored in the `logs` directory within the OBSCopilot installation folder. These logs can help diagnose issues with the application.

## API Reference

Detailed API documentation is available in the [API Reference](api_reference.md) document.

---

For more information, visit the [OBSCopilot website](https://obscopilot.example.com) or join our [Discord community](https://discord.gg/obscopilot). 