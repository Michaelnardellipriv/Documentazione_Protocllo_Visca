#!/usr/bin/env python3
"""
VISCA Dual Camera Control Application

Main entry point for the camera control GUI application.
"""

import sys
from PyQt6.QtWidgets import QApplication

from main_window import MainWindow


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
