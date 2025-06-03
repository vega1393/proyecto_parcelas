"""
Main entry point for the PyQt6 Parcel Generator GUI application.
"""

import sys
from src.ui.app import ParcelGeneratorApp
from PyQt6.QtWidgets import QApplication


def main() -> None:
    """
    Launches the PyQt6 GUI application.
    """
    app = QApplication(sys.argv)
    window = ParcelGeneratorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 