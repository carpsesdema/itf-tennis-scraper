"""
Main application class for ITF Tennis Scraper.
"""

import sys
import logging
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from .config import Config
from .gui.main_window import MainWindow
from .gui.styles.themes import apply_theme
from .utils.logging import get_logger


class TennisScraperApp:
    """Main application class that coordinates all components."""

    def __init__(self, config: Config):
        """Initialize the application with configuration."""
        self.config = config
        self.logger = get_logger(__name__)
        self.qt_app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None

    def run(self) -> int:
        """Run the application and return exit code."""
        try:
            self.logger.info("Initializing Qt application...")

            # Create Qt application
            self.qt_app = QApplication(sys.argv)
            self.qt_app.setStyle('Fusion')  # Use Fusion style for better theming

            # Apply theme
            apply_theme(self.qt_app, self.config.ui.theme)

            # Create main window
            self.main_window = MainWindow(self.config)
            self.main_window.show()

            # Setup auto-update check if enabled
            if self.config.updates.check_on_startup:
                QTimer.singleShot(3000, self._check_for_updates)

            # Connect shutdown handler
            self.qt_app.aboutToQuit.connect(self._on_shutdown)

            self.logger.info("Application started successfully")

            # Run the application
            return self.qt_app.exec()

        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            return 1

    def _check_for_updates(self):
        """Check for updates on startup."""
        if self.main_window:
            self.main_window.check_for_updates()

    def _on_shutdown(self):
        """Handle application shutdown."""
        self.logger.info("Application shutting down...")

        if self.main_window:
            # Stop any running workers
            self.main_window.stop_all_workers()

            # Save settings
            self.main_window.save_settings()

    def get_version(self) -> str:
        """Get application version."""
        from . import __version__
        return __version__