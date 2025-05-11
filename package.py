#!/usr/bin/env python3
"""
OBSCopilot - Complete Packaging Script
This script handles the complete workflow from encoding credentials to packaging.
"""

import os
import sys
import base64
import shutil
import argparse
import tempfile
import subprocess
from pathlib import Path

# Ensure we can import the build and encode scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_command(command):
    """Run a command and print output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def load_env_file(env_path):
    """Load variables from a .env file."""
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        return {}
        
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                try:
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
                except ValueError:
                    continue  # Skip lines that don't have key=value format
    return env_vars

def encode_credentials(credentials):
    """Encode credentials to base64."""
    encoded = {}
    for key, value in credentials.items():
        if value:
            encoded_value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            encoded[key] = encoded_value
    return encoded

def update_source_code(simple_py_path, encoded_credentials):
    """Update the source code with encoded credentials."""
    if not simple_py_path.exists():
        print(f"Error: Source file not found at {simple_py_path}")
        return False
        
    # Read the source code
    with open(simple_py_path, 'r') as f:
        source = f.read()
    
    # Create backup
    backup_path = simple_py_path.with_suffix('.py.bak')
    shutil.copy2(simple_py_path, backup_path)
    print(f"Created backup at {backup_path}")
    
    # Update the encoded credentials in the source code
    # This is a simple find-and-replace, in a real application you might want to use AST
    try:
        twitch_id = encoded_credentials.get('TWITCH_CLIENT_ID', '')
        twitch_secret = encoded_credentials.get('TWITCH_CLIENT_SECRET', '')
        
        # Replace the encoded values
        source = source.replace(
            "encoded_id = b'eW91cl90d2l0Y2hfY2xpZW50X2lkX2hlcmU='",
            f"encoded_id = b'{twitch_id}'"
        )
        source = source.replace(
            "encoded_secret = b'eW91cl90d2l0Y2hfY2xpZW50X3NlY3JldF9oZXJl'",
            f"encoded_secret = b'{twitch_secret}'"
        )
        
        # Write the updated source code
        with open(simple_py_path, 'w') as f:
            f.write(source)
            
        print(f"Updated source code with encoded credentials")
        return True
    except Exception as e:
        print(f"Error updating source code: {e}")
        # Restore from backup
        shutil.copy2(backup_path, simple_py_path)
        print(f"Restored from backup due to error")
        return False

def main():
    """Main function to package the application."""
    parser = argparse.ArgumentParser(description='Package OBSCopilot with embedded credentials')
    parser.add_argument('--env', help='Path to .env file')
    parser.add_argument('--key', help='Encryption key for PyInstaller (will generate random one if not provided)')
    parser.add_argument('--name', default='OBSCopilot', help='Output name for the executable')
    parser.add_argument('--icon', help='Path to icon file (.ico for Windows, .icns for macOS)')
    parser.add_argument('--skip-credentials', action='store_true', help='Skip embedding credentials')
    parser.add_argument('--clean', action='store_true', help='Clean build directories before building')
    args = parser.parse_args()
    
    # Set up paths
    root_dir = Path(__file__).resolve().parent
    simple_py_path = root_dir / 'obscopilot' / 'ui' / 'simple.py'
    
    # Step 1: Load and encode credentials
    if not args.skip_credentials:
        # Determine .env file path
        env_path = Path(args.env) if args.env else root_dir / '.env'
        
        print(f"Loading credentials from {env_path}")
        credentials = load_env_file(env_path)
        
        # Check if we have credentials
        if not credentials:
            print("No credentials found in .env file.")
            choice = input("Continue without embedding credentials? (y/n): ")
            if choice.lower() != 'y':
                return 1
        else:
            # Check for Twitch credentials
            if 'TWITCH_CLIENT_ID' not in credentials or 'TWITCH_CLIENT_SECRET' not in credentials:
                print("Warning: Missing required Twitch credentials (TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)")
                choice = input("Continue anyway? (y/n): ")
                if choice.lower() != 'y':
                    return 1
            
            # Encode credentials
            encoded = encode_credentials(credentials)
            
            # Update source code
            if not update_source_code(simple_py_path, encoded):
                return 1
    
    # Step 2: Build the application using PyInstaller
    print("\nBuilding the application...")
    
    # Build the command
    cmd = [sys.executable, "build.py"]
    
    if args.key:
        cmd.append(f"--key={args.key}")
    if args.name:
        cmd.append(f"--name={args.name}")
    if args.icon:
        cmd.append(f"--icon={args.icon}")
    if args.clean:
        cmd.append("--clean")
    
    # Join command parts and run
    cmd_str = " ".join(cmd)
    try:
        output = run_command(cmd_str)
        print(output)
    except Exception as e:
        print(f"Error building application: {e}")
        return 1
    
    print("\nPackaging complete! Executable is in the 'dist' directory.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 