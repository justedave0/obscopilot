#!/usr/bin/env python3
"""
OBSCopilot - Simplified test application
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget

class SimpleMainWindow(QMainWindow):
    """Simple main window for testing."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("OBSCopilot Test")
        self.setMinimumSize(800, 600)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Create layout
        layout = QVBoxLayout(central)
        
        # Add label
        label = QLabel("OBSCopilot Test Application")
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        
        # Add info
        info = QLabel("This is a simplified version of OBSCopilot for testing.")
        layout.addWidget(info)

def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    window = SimpleMainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 