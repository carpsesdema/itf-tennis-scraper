import json
from pathlib import Path
from typing import Any, Dict, Optional
from PySide6.QtCore import QSettings

from .logging import get_logger


class SettingsManager:
    """Manage application settings with multiple backends."""

    def __init__(self, app_name: str = "TennisScraper", org_name: str = "ITFScraper"):
        self.app_name = app_name
        self.org_name = org_name
        self.logger = get_logger(__name__)
        self.qt_settings = QSettings(org_name, app_name)

    def get(self, key: str, default: Any = None, value_type: type = None) -> Any:
        """Get a setting value."""
        try:
            if value_type:
                return self.qt_settings.value(key, default, value_type)
            else:
                return self.qt_settings.value(key, default)
        except Exception as e:
            self.logger.warning(f"Failed to get setting '{key}': {e}")
            return default

    def set(self, key: str, value: Any):
        """Set a setting value."""
        try:
            self.qt_settings.setValue(key, value)
            self.qt_settings.sync()
        except Exception as e:
            self.logger.error(f"Failed to set setting '{key}': {e}")

    def remove(self, key: str):
        """Remove a setting."""
        try:
            self.qt_settings.remove(key)
        except Exception as e:
            self.logger.warning(f"Failed to remove setting '{key}': {e}")

    def clear(self):
        """Clear all settings."""
        try:
            self.qt_settings.clear()
            self.logger.info("All settings cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear settings: {e}")

    def export_to_file(self, file_path: str) -> bool:
        """Export settings to JSON file."""
        try:
            settings_dict = {}
            for key in self.qt_settings.allKeys():
                settings_dict[key] = self.qt_settings.value(key)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, default=str)

            self.logger.info(f"Settings exported to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export settings: {e}")
            return False

    def import_from_file(self, file_path: str) -> bool:
        """Import settings from JSON file."""
        try:
            if not Path(file_path).exists():
                self.logger.warning(f"Settings file not found: {file_path}")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                settings_dict = json.load(f)

            for key, value in settings_dict.items():
                self.qt_settings.setValue(key, value)

            self.qt_settings.sync()
            self.logger.info(f"Settings imported from {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to import settings: {e}")
            return False

    def get_all_keys(self) -> list:
        """Get all setting keys."""
        return self.qt_settings.allKeys()

    def contains(self, key: str) -> bool:
        """Check if setting exists."""
        return self.qt_settings.contains(key)