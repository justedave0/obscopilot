#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import ObsCoPilotApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ObsCoPilotApp()
    window.show()
    sys.exit(app.exec()) 