#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OBSCopilot Embedded Virtual Environment Setup

This script creates an embedded virtual environment for OBSCopilot in the OBS scripts directory.
It installs all required dependencies in an isolated environment and creates a launcher script.
"""

import os
import sys
import venv
import shutil
import platform
import subprocess
from pathlib import Path

def get_obs_scripts_dir():
    """Get the OBS scripts directory for the current platform"""
    if platform.system() == "Windows":
        return Path(os.path.expandvars("%APPDATA%\\obs-studio\\scripts"))
    elif platform.system() == "Darwin":  # macOS
        return Path(os.path.expanduser("~/Library/Application Support/obs-studio/scripts"))
    else:  # Linux
        return Path(os.path.expanduser("~/.config/obs-studio/scripts"))

def create_embedded_venv():
    """Create an embedded virtual environment for OBSCopilot"""
    # Target directories
    obs_scripts_dir = get_obs_scripts_dir()
    obscopilot_dir = obs_scripts_dir / "obscopilot"
    venv_dir = obscopilot_dir / "venv"
    
    # Create directories
    os.makedirs(obscopilot_dir, exist_ok=True)
    
    print(f"Creating virtual environment in {venv_dir}...")
    
    # Create virtual environment
    venv.create(venv_dir, with_pip=True)
    
    # Get path to pip in the virtual environment
    if platform.system() == "Windows":
        pip_path = venv_dir / "Scripts" / "pip.exe"
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
    
    # Install required packages
    print("Installing required packages...")
    subprocess.check_call([str(pip_path), "install", "-r", "requirements.txt"])
    
    # Copy OBSCopilot files
    print("Copying OBSCopilot files...")
    python_files = ["obscopilot.py", "config.py", "obscontrol.py", "twitchintegration.py", "__init__.py"]
    for file in python_files:
        shutil.copy(file, obscopilot_dir)
    shutil.copy("README.md", obscopilot_dir)
    shutil.copy("requirements.txt", obscopilot_dir)
    
    # Create launcher script
    create_launcher_script(obscopilot_dir, python_path)
    
    print(f"\nOBSCopilot installed with embedded virtual environment to {obscopilot_dir}")
    print("To use in OBS Studio:")
    print("1. Open OBS Studio")
    print("2. Go to Tools → Scripts")
    print("3. Add the launcher script: obscopilot_launcher.py")

def create_launcher_script(obscopilot_dir, python_path):
    """Create a launcher script that uses the embedded Python"""
    launcher_path = get_obs_scripts_dir() / "obscopilot_launcher.py"
    
    launcher_code = f"""#!/usr/bin/env python
# OBSCopilot Launcher - Uses embedded virtual environment

import os
import sys
import importlib.util

def script_description():
    return "OBSCopilot - Twitch integration for OBS Studio (Launcher)"

def script_load(settings):
    # Path to main script
    main_script = r"{str(obscopilot_dir / 'obscopilot.py')}"
    
    # Add the virtual environment's site-packages to Python path
    venv_site_packages = os.path.join(
        r"{str(obscopilot_dir / 'venv')}",
        "Lib" if sys.platform == "win32" else "lib",
        f"python{{sys.version_info.major}}.{{sys.version_info.minor}}",
        "site-packages"
    )
    
    if venv_site_packages not in sys.path:
        sys.path.insert(0, venv_site_packages)
    
    # Add the OBSCopilot directory to the path
    obscopilot_dir_path = r"{str(obscopilot_dir)}"
    if obscopilot_dir_path not in sys.path:
        sys.path.insert(0, obscopilot_dir_path)
    
    # Load and execute the main script
    try:
        spec = importlib.util.spec_from_file_location("obscopilot", main_script)
        obscopilot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(obscopilot_module)
        print("OBSCopilot loaded successfully using embedded Python")
    except Exception as e:
        print(f"Error loading OBSCopilot: {{e}}")
        import traceback
        traceback.print_exc()
"""
    
    with open(launcher_path, 'w') as f:
        f.write(launcher_code)
    
    print(f"Created launcher script: {launcher_path}")

if __name__ == "__main__":
    create_embedded_venv() 