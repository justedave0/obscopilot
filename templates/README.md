# OBSCopilot Workflow Templates

This directory contains ready-to-use workflow templates for common streaming scenarios. These templates can be imported into OBSCopilot to quickly set up automations for your streams.

## Available Templates

1. **New Follower Alert**
   - File: `workflows/new_follower_alert.json`
   - Description: Displays an on-screen alert with sound when someone follows your channel
   - Requirements: OBS source named "FollowerAlert" and "FollowerAlertText"

2. **Subscription Alert**
   - File: `workflows/subscriber_alert.json`
   - Description: Displays an on-screen alert with sound and sends a chat message when someone subscribes
   - Requirements: OBS source named "SubscriptionAlert" and "SubscriptionAlertText"

3. **Raid Welcome Sequence**
   - File: `workflows/raid_welcome.json`
   - Description: Switches scene, plays animation, and sends AI-generated welcome message when your channel gets raided
   - Requirements: OBS scene named "Raid Welcome" and text source named "RaidWelcomeText"

4. **Channel Points Reward Action**
   - File: `workflows/channel_points_reward.json`
   - Description: Performs custom actions when viewers redeem channel points rewards
   - Requirements: OBS source named "RewardImage" and "RedeemerText", configured channel point reward

5. **Stream Start Automation**
   - File: `workflows/stream_start_automation.json`
   - Description: Automates scene switching, music, chat messages, and social media notifications when you start streaming
   - Requirements: OBS scenes named "Stream Starting" and "Main"

## How to Use Templates

1. In OBSCopilot, go to the Workflows tab
2. Click "Load Workflow"
3. Browse to the template JSON file you want to use
4. Click "Open" to import the workflow
5. The workflow will appear in your workflow list
6. Edit the workflow to customize it for your specific setup

## Customizing Templates

All templates include placeholders and configurable options. After importing a template, review and update:

- Source names to match your OBS configuration
- Scene names to match your OBS scenes
- File paths for sounds and images
- Text messages and formatting
- Delay durations
- External API endpoints and authentication

## Creating Your Own Templates

To create your own workflow templates:

1. Build and test your workflow in OBSCopilot
2. Export the workflow to a JSON file
3. Place the file in the templates/workflows directory
4. Add documentation to this README

## Requirements

These templates require OBSCopilot v0.1.0 or higher and are compatible with OBS Studio 28+ with WebSocket plugin v5.0+.

## Contributing

If you've created a useful workflow template, please consider sharing it with the community by submitting a pull request to add it to this collection. 