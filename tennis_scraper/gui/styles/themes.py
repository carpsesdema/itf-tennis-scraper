"""
Theme management system for the application.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

from ...utils.logging import get_logger


class Theme(ABC):
    """Abstract base class for application themes."""

    @abstractmethod
    def get_name(self) -> str:
        """Get theme name."""
        pass

    @abstractmethod
    def get_palette(self) -> QPalette:
        """Get the color palette for this theme."""
        pass

    @abstractmethod
    def get_stylesheet(self) -> str:
        """Get additional stylesheet for this theme."""
        pass

    def get_colors(self) -> Dict[str, str]:
        """Get theme color dictionary."""
        return {}


class ThemeManager:
    """Manage application themes."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.themes = {}
        self.current_theme = None
        self._register_default_themes()

    def _register_default_themes(self):
        """Register default themes."""
        from .dark_theme import DarkTheme
        from .light_theme import LightTheme

        self.register_theme(DarkTheme())
        self.register_theme(LightTheme())

    def register_theme(self, theme: Theme):
        """Register a new theme."""
        self.themes[theme.get_name().lower()] = theme
        self.logger.info(f"Registered theme: {theme.get_name()}")

    def get_theme(self, name: str) -> Theme:
        """Get a theme by name."""
        name_lower = name.lower()
        if name_lower not in self.themes:
            raise ValueError(f"Theme '{name}' not found")
        return self.themes[name_lower]

    def list_themes(self) -> list:
        """Get list of available theme names."""
        return list(self.themes.keys())

    def apply_theme(self, app: QApplication, theme_name: str):
        """Apply a theme to the application."""
        try:
            theme = self.get_theme(theme_name)

            # Apply palette
            app.setPalette(theme.get_palette())

            # Apply stylesheet
            stylesheet = theme.get_stylesheet()
            if stylesheet:
                app.setStyleSheet(stylesheet)

            self.current_theme = theme
            self.logger.info(f"Applied theme: {theme.get_name()}")

        except Exception as e:
            self.logger.error(f"Failed to apply theme '{theme_name}': {e}")
            # Fall back to default theme
            if theme_name.lower() != 'dark':
                self.apply_theme(app, 'dark')

    def get_current_theme(self) -> Theme:
        """Get currently applied theme."""
        return self.current_theme


# Global theme manager instance
theme_manager = ThemeManager()


def apply_theme(app: QApplication, theme_name: str = "dark"):
    """Apply a theme to the application."""
    theme_manager.apply_theme(app, theme_name)


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager."""
    return theme_manager