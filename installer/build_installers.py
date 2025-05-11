#!/usr/bin/env python3
"""
OBSCopilot Installer Builder

This script builds installers for OBSCopilot for Windows, macOS, and Linux.
"""

import os
import sys
import argparse
import shutil
import subprocess
import platform
from pathlib import Path

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent.absolute()

# Output directory for the installers
OUTPUT_DIR = ROOT_DIR / "dist"

# Application version (read from version.py)
VERSION = "1.0.0"
try:
    with open(ROOT_DIR / "obscopilot" / "version.py", "r") as f:
        for line in f:
            if line.startswith("__version__"):
                VERSION = line.split("=")[1].strip().strip('"\'')
                break
except:
    print("Warning: Could not determine version from version.py")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Build OBSCopilot installers")
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux", "all"],
        default="all",
        help="Platform to build installer for",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts before building",
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign the installers (requires certificates)",
    )
    return parser.parse_args()


def clean():
    """Clean build artifacts."""
    print("Cleaning build artifacts...")
    
    # Remove build directory
    if os.path.exists(ROOT_DIR / "build"):
        shutil.rmtree(ROOT_DIR / "build")
        
    # Remove dist directory
    if os.path.exists(ROOT_DIR / "dist"):
        shutil.rmtree(ROOT_DIR / "dist")
        
    # Remove __pycache__ directories
    for root, dirs, files in os.walk(ROOT_DIR):
        for dir in dirs:
            if dir == "__pycache__":
                shutil.rmtree(os.path.join(root, dir))
                
    print("Build artifacts cleaned")


def build_pyinstaller():
    """Build the application using PyInstaller."""
    print("Building application with PyInstaller...")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--name", f"OBSCopilot-{VERSION}",
        "--add-data", f"obscopilot/resources:resources",
        "--add-data", f"obscopilot/ui/resources:ui/resources",
        "--hidden-import", "obscopilot.core",
        "--hidden-import", "obscopilot.workflows",
        "--hidden-import", "obscopilot.twitch",
        "--hidden-import", "obscopilot.obs",
        "--hidden-import", "obscopilot.ai",
        "--hidden-import", "obscopilot.ui",
        "--hidden-import", "obscopilot.storage",
        "--icon", "obscopilot/resources/icon.ico",
        "obscopilot/main.py",
    ]
    
    # Add platform-specific options
    if platform.system() == "Windows":
        cmd.extend(["--windowed"])
    elif platform.system() == "Darwin":
        cmd.extend(["--windowed", "--osx-bundle-identifier", "com.example.obscopilot"])
    
    # Run PyInstaller
    subprocess.run(cmd, check=True)
    
    print("PyInstaller build completed")


def build_windows_installer():
    """Build Windows installer using NSIS."""
    print("Building Windows installer...")
    
    # Check if NSIS is installed
    nsis_command = shutil.which("makensis")
    if not nsis_command:
        print("NSIS not found. Please install NSIS.")
        return False
    
    # Create NSIS script
    nsis_script = ROOT_DIR / "installer" / "windows" / "installer.nsi"
    
    # Set version in NSIS script
    with open(nsis_script, "r") as f:
        content = f.read()
    
    content = content.replace("{{VERSION}}", VERSION)
    
    with open(nsis_script, "w") as f:
        f.write(content)
    
    # Run NSIS
    subprocess.run([nsis_command, str(nsis_script)], check=True)
    
    # Move installer to output directory
    installer_name = f"OBSCopilot-{VERSION}-setup.exe"
    src = ROOT_DIR / "installer" / "windows" / installer_name
    dst = OUTPUT_DIR / installer_name
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"Windows installer created: {dst}")
        return True
    else:
        print("Failed to create Windows installer")
        return False


def build_macos_installer():
    """Build macOS installer (DMG)."""
    print("Building macOS installer...")
    
    # Check if create-dmg is installed
    create_dmg = shutil.which("create-dmg")
    if not create_dmg:
        print("create-dmg not found. Please install create-dmg.")
        return False
    
    # Get app path
    app_path = ROOT_DIR / "dist" / f"OBSCopilot-{VERSION}.app"
    
    if not os.path.exists(app_path):
        print(f"App not found: {app_path}")
        return False
    
    # Create DMG
    dmg_name = f"OBSCopilot-{VERSION}.dmg"
    cmd = [
        "create-dmg",
        "--volname", f"OBSCopilot {VERSION}",
        "--window-pos", "200", "100",
        "--window-size", "800", "400",
        "--icon-size", "100",
        "--icon", f"OBSCopilot-{VERSION}.app", "200", "190",
        "--hide-extension", f"OBSCopilot-{VERSION}.app",
        "--app-drop-link", "600", "190",
        f"{OUTPUT_DIR}/{dmg_name}",
        str(app_path),
    ]
    
    subprocess.run(cmd, check=True)
    
    print(f"macOS installer created: {OUTPUT_DIR}/{dmg_name}")
    return True


def build_linux_installer():
    """Build Linux installer (AppImage)."""
    print("Building Linux installer...")
    
    # Check if appimagetool is installed
    appimagetool = shutil.which("appimagetool")
    if not appimagetool:
        print("appimagetool not found. Please install appimagetool.")
        return False
    
    # Get app directory
    app_dir = ROOT_DIR / "dist" / f"OBSCopilot-{VERSION}"
    
    if not os.path.exists(app_dir):
        print(f"App directory not found: {app_dir}")
        return False
    
    # Create AppDir structure
    appdir = ROOT_DIR / "build" / "AppDir"
    os.makedirs(appdir, exist_ok=True)
    
    # Copy application files
    shutil.copytree(app_dir, appdir / "usr", dirs_exist_ok=True)
    
    # Create desktop file
    os.makedirs(appdir / "usr" / "share" / "applications", exist_ok=True)
    with open(appdir / "usr" / "share" / "applications" / "obscopilot.desktop", "w") as f:
        f.write(f"""[Desktop Entry]
Name=OBSCopilot
Comment=Twitch Live Assistant
Exec=obscopilot
Icon=obscopilot
Type=Application
Categories=Utility;
""")
    
    # Copy icon
    os.makedirs(appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps", exist_ok=True)
    shutil.copy(
        ROOT_DIR / "obscopilot" / "resources" / "icon.png",
        appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / "obscopilot.png"
    )
    
    # Create AppRun script
    with open(appdir / "AppRun", "w") as f:
        f.write("""#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/obscopilot" "$@"
""")
    
    os.chmod(appdir / "AppRun", 0o755)
    
    # Create symlinks
    os.symlink("usr/share/applications/obscopilot.desktop", appdir / "obscopilot.desktop")
    os.symlink("usr/share/icons/hicolor/256x256/apps/obscopilot.png", appdir / "obscopilot.png")
    
    # Run appimagetool
    appimage_name = f"OBSCopilot-{VERSION}-x86_64.AppImage"
    subprocess.run([
        appimagetool,
        "-n",
        str(appdir),
        str(OUTPUT_DIR / appimage_name)
    ], check=True)
    
    print(f"Linux installer created: {OUTPUT_DIR}/{appimage_name}")
    return True


def main():
    """Main function."""
    args = parse_args()
    
    if args.clean:
        clean()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Build application
    build_pyinstaller()
    
    # Build installers
    if args.platform in ["windows", "all"] and platform.system() == "Windows":
        build_windows_installer()
    
    if args.platform in ["macos", "all"] and platform.system() == "Darwin":
        build_macos_installer()
    
    if args.platform in ["linux", "all"] and platform.system() == "Linux":
        build_linux_installer()
    
    # Sign installers if requested
    if args.sign:
        print("Signing installers is not implemented yet")
    
    print("Build process completed")


if __name__ == "__main__":
    main() 