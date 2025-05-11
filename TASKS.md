# OBSCopilot Development Roadmap

## Phase 1: Core Infrastructure
- [x] Project setup and dependencies
- [x] Configuration management
- [x] Event bus implementation
- [x] Basic GUI layout

## Phase 2: Service Integration
- [x] Twitch authentication and event handling
- [x] OBS WebSocket integration
- [x] OpenAI API integration
- [x] Google AI API integration

## Phase 3: Workflow Engine
- [x] Workflow model implementation
- [x] Trigger system
- [x] Action system
- [x] Workflow persistence

## Phase 4: Advanced Features
- [x] Custom chat commands
- [x] Viewer statistics tracking
- [x] Alert system
- [x] Stream health monitoring

## Phase 5: UI/UX Enhancements
- [ ] Workflow editor
- [ ] Dashboard customization
- [ ] Theming and styling
- [ ] Keyboard shortcuts

# OBSCopilot: Twitch Live Assistant

This document outlines the tasks for developing OBSCopilot, a cross-platform Python application that serves as a Twitch live assistant with workflow automation capabilities.

## 1. Core Architecture and Setup

- [x] Research Python libraries for Twitch API integration
- [x] Research Python GUI frameworks for cross-platform compatibility
- [x] Research OBS integration via websocket
- [x] Research workflow automation solutions
- [x] Set up project structure and virtual environment
- [x] Create requirements.txt with necessary dependencies
- [x] Design application architecture (MVC pattern)
- [x] Create CI/CD pipeline for cross-platform builds

## 2. Twitch API Integration

- [x] Implement Twitch API authentication (broadcaster and bot accounts)
- [x] Create connection management for Twitch accounts
- [x] Implement event listeners for all required Twitch events:
  - [x] Channel follows
  - [x] Subscriptions (new, gifts, resubs)
  - [x] Bits/Cheers
  - [x] Channel point redemptions
  - [x] Raids
  - [x] Chat messages
  - [x] Stream status changes (online/offline)
- [x] Design credentials storage and secure token refresh mechanisms
- [x] Implement error handling and reconnection strategies

## 3. Workflow Engine

- [x] Design workflow model (triggers, conditions, actions)
- [ ] Create visual workflow builder component
- [x] Implement workflow execution engine
- [x] Create standard action library:
  - [x] Chat messages (bot responses)
  - [x] OBS scene/source control
  - [x] External API calls
  - [x] Sound playback
  - [x] File operations
  - [x] Timer/delay functions
- [x] Implement workflow import/export functionality
- [x] Create workflow templates for common use cases

## 4. OBS Integration

- [ ] Implement OBS WebSocket client
- [ ] Create methods for:
  - [ ] Scene switching
  - [ ] Source visibility control
  - [ ] Media playback
  - [ ] Recording/streaming control
  - [ ] Audio control
- [ ] Add error handling for OBS connection issues
- [ ] Implement automatic reconnection

## 5.a OpenAI Integration

- [ ] Add OpenAI API client
- [ ] Create system prompt management interface
- [ ] Implement AI response generation for chat
- [ ] Add context tracking for conversations
- [ ] Create templating system for AI responses (including user info)
- [ ] Implement rate limiting and token usage tracking
- [ ] Add error handling for API failures

## 5.b Google AI Integration

- [ ] Add Google AI API client
- [ ] Implement AI response generation for chat
- [ ] Add context tracking for conversations
- [ ] Create templating system for AI responses (including user info) 

## 6. User Interface

- [ ] Design and implement main application window
- [ ] Create account connection interfaces
- [ ] Build workflow editor UI
- [ ] Implement dashboard with live stats
- [ ] Add event log viewer
- [ ] Create settings panel
- [ ] Design dark/light themes
- [ ] Ensure UI is responsive and accessible

## 7. Storage and Persistence

- [ ] Design database schema for workflows and settings
- [ ] Implement configuration storage
- [ ] Create backup/restore functionality
- [ ] Add workflow version control

## 8. Testing

- [ ] Write unit tests for core components
- [ ] Create integration tests for Twitch API interactions
- [ ] Implement UI tests
- [ ] Perform cross-platform testing (Windows, Mac, Linux)
- [ ] Conduct performance testing for workflow engine

## 9. Documentation

- [ ] Create user documentation
- [ ] Document API for extensibility
- [ ] Add inline code documentation
- [ ] Create tutorial videos/guides

## 10. Deployment

- [ ] Create installers for all platforms
- [ ] Set up update mechanism
- [ ] Create release pipeline
- [ ] Prepare for distribution

## Technology Choices

- **Python Version**: 3.9+
- **Twitch API Library**: TwitchIO or PyTwitchAPI
- **GUI Framework**: PyQt6 (cross-platform, modern UI)
- **OBS Integration**: obs-websocket-py 
- **Workflow Engine**: Custom implementation based on SpiffWorkflow
- **Database**: SQLite (for portability)
- **AI Integration**: OpenAI Python Client

## Example Use Cases

1. **Channel Point Redemption → OBS Action**
   - When viewer redeems "Show Bug" points reward
   - Toggle visibility of "Bug.mp4" source in OBS

2. **Subscription → AI Thank You Message**
   - When viewer subscribes to channel
   - Send AI-generated thank you message mentioning subscriber's name

3. **Chat Command → Scene Switch**
   - When moderator types command in chat
   - Switch to specified scene in OBS

4. **Raid → Welcome Sequence**
   - When channel receives raid
   - Play special animation, send welcome message, and switch scene

5. **Stream Start → Social Media Notification**
   - When stream goes live
   - Send notifications to connected platforms
