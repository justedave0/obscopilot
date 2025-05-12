#!/usr/bin/env python3
"""
OBSCopilot - Launcher script
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the obscopilot package
from obscopilot.ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication

def main():
    """Run a simplified version of the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 