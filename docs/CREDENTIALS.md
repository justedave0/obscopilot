# Secure API Credential Handling

This document outlines how to securely handle API credentials in OBSCopilot.

## Overview

OBSCopilot requires API credentials for services like Twitch, OpenAI, and Google AI. These credentials need to be securely managed and not exposed to end users. The application implements a secure credential handling system that supports multiple approaches.

## Twitch Credentials

### Setting Up Twitch Developer Application

1. Go to the [Twitch Developer Console](https://dev.twitch.tv/console/apps)
2. Click "Register Your Application"
3. Fill in the application details:
   - Name: "OBSCopilot" (or your preferred name)
   - OAuth Redirect URLs: `http://localhost:8000/auth/callback`
   - Category: "Application Integration"
4. Click "Create"
5. Once created, click "Manage" and note your Client ID
6. Click "New Secret" to generate a Client Secret

### Configuring Credentials in OBSCopilot

There are several ways to configure Twitch credentials, with a recommended workflow from development to distribution:

#### 1. Using a .env File (Recommended for Development)

Create a `.env` file in the root directory of the project with your credentials:

```
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret
```

Make sure to add `.env` to your `.gitignore` file to prevent accidentally committing credentials:

```
# Add to .gitignore
.env
```

The application will automatically load credentials from this file if it exists.

#### 2. Environment Variables (Alternative for Development)

Set environment variables if you prefer not to use a .env file:

```bash
# Linux/macOS
export TWITCH_CLIENT_ID=your_client_id
export TWITCH_CLIENT_SECRET=your_client_secret

# Windows PowerShell
$env:TWITCH_CLIENT_ID="your_client_id"
$env:TWITCH_CLIENT_SECRET="your_client_secret"
```

#### 3. Base64 Encoded Credentials (For Distribution)

Before packaging the application for distribution, update the encoded credentials in `obscopilot/ui/simple.py`:

```python
# Generate these with: base64.b64encode(b"your_client_id").decode('utf-8')
encoded_id = b'...'  # Your encoded client ID
encoded_secret = b'...'  # Your encoded client secret
```

To generate these values:

```python
import base64
print(base64.b64encode(b"your_client_id").decode('utf-8'))
print(base64.b64encode(b"your_client_secret").decode('utf-8'))
```

#### 4. PyInstaller Compilation (Most Secure for Distribution)

The most secure approach for distribution is to use PyInstaller with the `--key` option to create a compiled executable with encrypted bytecode:

```bash
pip install pyinstaller
pyinstaller --onefile --key=YOUR_RANDOM_KEY run.py
```

This encrypts the bundled Python bytecode (including your embedded credentials), making it significantly harder to extract.

### Recommended Development-to-Distribution Workflow

1. **During development**:
   - Use a `.env` file to store your credentials
   - Add `.env` to `.gitignore`
   - Develop and test your application

2. **Before distribution**:
   - Generate base64 encoded versions of your credentials
   - Update the encoded credentials in the code
   - Use PyInstaller with the `--key` option to create a secure executable
   - Distribute the compiled executable

This workflow keeps your development environment clean and flexible while producing a secure distribution.

## About Twitch Authentication

It's important to understand that your Twitch Client ID and Secret identify **your application** to Twitch, not the individual users. These are the credentials for your application registration with Twitch, and all your users will use the same application credentials.

When a user clicks "Login" in your application:
1. They're redirected to Twitch's authentication page
2. They grant your application permission to access their Twitch account
3. They're redirected back to your application with an access token
4. Your application uses this token to make API calls on behalf of the user

This is why you only need one set of application credentials embedded in your code, and your end users never see or need to enter these credentials.

## OpenAI and Google AI Credentials

OpenAI and Google AI credentials are handled through the UI since most users will have their own API keys for these services. If you wish to provide default credentials for these services as well, you can follow a similar pattern as used for Twitch credentials.

## Best Practices

1. **Never commit real credentials to version control**
2. **Rotate credentials regularly** and when team members leave
3. **Use the most restrictive permissions** possible for your API keys
4. **Consider a credential management service** like HashiCorp Vault for enterprise deployments
5. **Monitor for credential leaks** using services like GitHub's secret scanning

## Security Considerations

Basic obfuscation (like base64 encoding) provides only minimal protection against casual inspection. For higher security requirements, consider:

1. Using a dedicated secret management solution
2. Implementing a proper backend service that handles API calls
3. Using a compiled executable with byte-code encryption
4. Implementing more sophisticated encryption for credential storage

Remember that no client-side security measure is completely unbreakable - these measures are deterrents that raise the bar for credential extraction, but a determined attacker with sufficient skills could still potentially extract them. 