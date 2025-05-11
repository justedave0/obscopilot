#!/usr/bin/env python3
"""
OBSCopilot - Build Script
This script packages the application using PyInstaller.
"""

import os
import sys
import uuid
import shutil
import argparse
import platform
import subprocess
from pathlib import Path

def run_command(command):
    """Run a command and print output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def main():
    """Main function to build the application."""
    parser = argparse.ArgumentParser(description='Build OBSCopilot application')
    parser.add_argument('--key', help='Encryption key for PyInstaller (will generate random one if not provided)')
    parser.add_argument('--name', default='OBSCopilot', help='Output name for the executable')
    parser.add_argument('--icon', help='Path to icon file (.ico for Windows, .icns for macOS)')
    parser.add_argument('--clean', action='store_true', help='Clean build directories before building')
    args = parser.parse_args()

    # Set up paths
    root_dir = Path(__file__).resolve().parent
    dist_dir = root_dir / 'dist'
    build_dir = root_dir / 'build'
    
    # Generate a random key if not provided
    encryption_key = args.key or str(uuid.uuid4()).replace('-', '')[:16]
    print(f"Using encryption key: {encryption_key}")
    
    # Clean directories if requested
    if args.clean and dist_dir.exists():
        print(f"Cleaning {dist_dir}")
        shutil.rmtree(dist_dir)
    if args.clean and build_dir.exists():
        print(f"Cleaning {build_dir}")
        shutil.rmtree(build_dir)
    
    # Create dist directory if it doesn't exist
    dist_dir.mkdir(exist_ok=True)
    
    # Check PyInstaller installation
    try:
        run_command("pyinstaller --version")
    except subprocess.CalledProcessError:
        print("PyInstaller not found. Installing...")
        run_command("pip install pyinstaller")
    
    # Determine system for icon
    system = platform.system()
    icon_param = ""
    if args.icon:
        if system == "Windows" and args.icon.endswith('.ico'):
            icon_param = f"--icon={args.icon}"
        elif system == "Darwin" and args.icon.endswith('.icns'):
            icon_param = f"--icon={args.icon}"
        elif system == "Linux" and args.icon.endswith('.png'):
            icon_param = f"--icon={args.icon}"
    
    # Build the command
    cmd = [
        "pyinstaller",
        "--onefile",
        f"--key={encryption_key}",
        "--clean",
        "--log-level=INFO",
        f"--name={args.name}",
    ]
    
    # Add icon if specified
    if icon_param:
        cmd.append(icon_param)
    
    # Add the main script
    cmd.append("run.py")
    
    # Join command parts
    cmd_str = " ".join(cmd)
    
    # Run PyInstaller
    print("Building application with PyInstaller...")
    output = run_command(cmd_str)
    print(output)
    
    # Verify the executable was created
    executable_name = args.name
    if system == "Windows":
        executable_name += ".exe"
    
    executable_path = dist_dir / executable_name
    if executable_path.exists():
        print(f"Successfully built {executable_path}")
    else:
        print(f"Error: Could not find built executable at {executable_path}")
        return 1
    
    print("\nBuild complete! Executable is in the 'dist' directory.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 