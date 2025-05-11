#!/usr/bin/env python3
"""
OBSCopilot - Credential Encoder
This script encodes credentials from a .env file for embedding in the application.
"""

import os
import base64
import argparse
from pathlib import Path

def load_env_file(env_path):
    """Load variables from a .env file."""
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        return {}
        
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value
    return env_vars

def encode_credentials(credentials):
    """Encode credentials to base64."""
    encoded = {}
    for key, value in credentials.items():
        if value:
            encoded_value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            encoded[key] = encoded_value
    return encoded

def print_code_snippet(encoded_credentials):
    """Print a code snippet to embed in the application."""
    print("\nCopy and paste this into obscopilot/ui/simple.py in the _set_default_twitch_credentials method:\n")
    
    print("# These are base64 encoded credentials - replace with your actual encoded values")
    print(f"encoded_id = b'{encoded_credentials.get('TWITCH_CLIENT_ID', '')}' " + 
          "# Your encoded client ID")
    print(f"encoded_secret = b'{encoded_credentials.get('TWITCH_CLIENT_SECRET', '')}' " + 
          "# Your encoded client secret")

def main():
    """Main function to encode credentials."""
    parser = argparse.ArgumentParser(description='Encode Twitch credentials for embedding')
    parser.add_argument('--env', help='Path to .env file')
    args = parser.parse_args()
    
    # Determine .env file path
    env_path = Path(args.env) if args.env else Path.cwd() / '.env'
    
    print(f"Loading credentials from {env_path}")
    credentials = load_env_file(env_path)
    
    # Check if we have credentials
    if not credentials:
        print("No credentials found. Please create a .env file or specify path with --env.")
        return 1
        
    # Check for Twitch credentials
    if 'TWITCH_CLIENT_ID' not in credentials or 'TWITCH_CLIENT_SECRET' not in credentials:
        print("Warning: Missing required Twitch credentials (TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)")
    
    # Encode credentials
    encoded = encode_credentials(credentials)
    
    # Print code snippet
    print_code_snippet(encoded)
    
    print("\nRemember to keep your credentials secure!")
    return 0

if __name__ == "__main__":
    main() 