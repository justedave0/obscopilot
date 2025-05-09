#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OBSCopilot Installer

This script provides multiple installation options for OBSCopilot:
1. Simple installation - copies files to OBS scripts directory
2. Embedded virtual environment - creates an isolated Python environment 
"""

import os
import sys
import shutil
import platform
import argparse
from pathlib import Path

def get_obs_scripts_dir():
    """Get the OBS scripts directory for the current platform"""
    if platform.system() == "Windows":
        return Path(os.path.expandvars("%APPDATA%\\obs-studio\\scripts"))
    elif platform.system() == "Darwin":  # macOS
        return Path(os.path.expanduser("~/Library/Application Support/obs-studio/scripts"))
    else:  # Linux
        return Path(os.path.expanduser("~/.config/obs-studio/scripts"))

def simple_install():
    """Perform a simple installation (copy files only)"""
    print("Performing simple installation...")
    
    # Target directory
    obs_scripts_dir = get_obs_scripts_dir()
    obscopilot_dir = obs_scripts_dir / "obscopilot"
    
    # Create directory
    os.makedirs(obscopilot_dir, exist_ok=True)
    
    # Copy OBSCopilot files
    print("Copying OBSCopilot files...")
    python_files = ["obscopilot.py", "config.py", "obscontrol.py", "twitchintegration.py", "__init__.py"]
    for file in python_files:
        shutil.copy(file, obscopilot_dir)
    shutil.copy("README.md", obscopilot_dir)
    shutil.copy("requirements.txt", obscopilot_dir)
    
    print(f"\nOBSCopilot installed to {obscopilot_dir}")
    print("To use in OBS Studio:")
    print("1. Make sure you have installed the required packages:")
    print("   pip install twitchio obsws-python requests")
    print("2. Open OBS Studio")
    print("3. Go to Tools → Scripts")
    print("4. Add the script: " + str(obscopilot_dir / "obscopilot.py"))

def embedded_install():
    """Perform an installation with embedded virtual environment"""
    # Import the setup_embedded_venv module and run it
    try:
        from setup_embedded_venv import create_embedded_venv
        create_embedded_venv()
    except ImportError:
        print("Error: Could not import setup_embedded_venv module.")
        print("Make sure setup_embedded_venv.py is in the current directory.")
        sys.exit(1)

def main():
    """Main installer function"""
    parser = argparse.ArgumentParser(description="OBSCopilot Installer")
    parser.add_argument("--simple", action="store_true", help="Perform a simple installation (files only)")
    parser.add_argument("--embedded", action="store_true", help="Install with embedded virtual environment")
    
    args = parser.parse_args()
    
    # If no arguments, show menu
    if not args.simple and not args.embedded:
        print("\nOBSCopilot Installer")
        print("--------------------")
        print("Please choose an installation method:")
        print("1. Simple installation (requires manual dependency installation)")
        print("2. Embedded virtual environment (recommended)")
        print("3. Quit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            simple_install()
        elif choice == "2":
            embedded_install()
        elif choice == "3":
            print("Installation cancelled.")
            sys.exit(0)
        else:
            print("Invalid choice. Please run the installer again.")
            sys.exit(1)
    
    # Use command-line arguments if provided
    else:
        if args.simple:
            simple_install()
        elif args.embedded:
            embedded_install()

if __name__ == "__main__":
    main() 