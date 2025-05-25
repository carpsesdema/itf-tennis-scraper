"""
Configuration management for ITF Tennis Scraper.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Any, Optional, List # Added List

from .utils.logging import get_logger



@dataclass
class ScrapingConfig:
    """Configuration for scraping operations."""
    delay_between_requests: int = 2
    request_timeout: int = 10
    max_retries: int = 3
    headless_browser: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    sources_enabled: Dict[str, bool] = field(default_factory=lambda: {
        'flashscore': True,
        # Removed sofascore - only need flashscore for bet365 verification
    })
    flashscore_bet365_indicator_fragment: str = "/549/"
    flashscore_match_tie_break_keywords: List[str] = field(
        default_factory=lambda: [
            "match tie break",
            "match tie-break",
            "match tb",
            "super tiebreak",
            "super tie-break",
            "mtb",
            "stb",
            "first to 10",
            "race to 10"
        ]
    )


@dataclass
class UIConfig:
    """Configuration for user interface."""
    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    auto_refresh_interval: int = 300  # seconds
    show_live_only: bool = True


@dataclass
class UpdateConfig:
    """Configuration for update system."""
    check_on_startup: bool = True
    frequency: str = "weekly"  # never, daily, weekly, monthly
    auto_download: bool = False
    github_repo: str = "carpsesdema/itf-tennis-scraper"
    update_url: str = ""  # Will be set from github_repo


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    file_path: str = "tennis_scraper.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class ExportConfig:
    """Configuration for data export."""
    default_format: str = "csv"
    include_metadata: bool = True
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"


class Config:
    """Main configuration class."""

    def __init__(self):
        """Initialize configuration with defaults."""
        self.scraping = ScrapingConfig()
        self.ui = UIConfig()
        self.updates = UpdateConfig()
        self.logging = LoggingConfig()
        self.export = ExportConfig()

        # Set derived values
        if not self.updates.update_url:
            self.updates.update_url = f"https://api.github.com/repos/{self.updates.github_repo}/releases/latest"

        self.logger = get_logger(__name__)

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from file."""
        if config_path is None:
            config_path = cls.get_default_config_path()

        config_file = Path(config_path)
        config = cls()

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Update configuration from file
                config._update_from_dict(data)
                config.logger.info(f"Configuration loaded from {config_file}")

            except Exception as e:
                config.logger.warning(f"Failed to load config from {config_file}: {e}")
                config.logger.info("Using default configuration")
        else:
            config.logger.info("No config file found, using defaults")

        return config

    def save_to_file(self, config_path: Optional[str] = None):
        """Save configuration to file."""
        if config_path is None:
            config_path = self.get_default_config_path()

        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2)

            self.logger.info(f"Configuration saved to {config_file}")

        except Exception as e:
            self.logger.error(f"Failed to save config to {config_file}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'scraping': asdict(self.scraping),
            'ui': asdict(self.ui),
            'updates': asdict(self.updates),
            'logging': asdict(self.logging),
            'export': asdict(self.export)
        }

    def _update_from_dict(self, data: Dict[str, Any]):
        """Update configuration from dictionary."""
        if 'scraping' in data:
            self._update_dataclass(self.scraping, data['scraping'])

        if 'ui' in data:
            self._update_dataclass(self.ui, data['ui'])

        if 'updates' in data:
            self._update_dataclass(self.updates, data['updates'])
            # Update derived URL if repo changed
            if not data['updates'].get('update_url'): # type: ignore
                self.updates.update_url = f"https://api.github.com/repos/{self.updates.github_repo}/releases/latest"

        if 'logging' in data:
            self._update_dataclass(self.logging, data['logging'])

        if 'export' in data:
            self._update_dataclass(self.export, data['export'])

    def _update_dataclass(self, instance, data: Dict[str, Any]):
        """Update a dataclass instance from dictionary."""
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

    @staticmethod
    def get_default_config_path() -> str:
        """Get the default configuration file path."""
        # Use user's config directory
        config_dir = Path.home() / ".config" / "tennis_scraper"
        return str(config_dir / "config.json")

    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []

        # Validate scraping config
        if self.scraping.delay_between_requests < 1:
            errors.append("delay_between_requests must be at least 1 second")

        if self.scraping.request_timeout < 5:
            errors.append("request_timeout must be at least 5 seconds")

        # Validate UI config
        if self.ui.auto_refresh_interval < 30:
            errors.append("auto_refresh_interval must be at least 30 seconds")

        # Validate update config
        valid_frequencies = ['never', 'daily', 'weekly', 'monthly']
        if self.updates.frequency not in valid_frequencies:
            errors.append(f"update frequency must be one of: {valid_frequencies}")

        # Log errors
        for error in errors:
            self.logger.error(f"Configuration validation error: {error}")

        return len(errors) == 0

    def get_scraper_config(self, scraper_name: str) -> Dict[str, Any]:
        """Get configuration for a specific scraper."""
        # Base configuration common to all scrapers (or parts of scraping process)
        base_config = {
            'delay_between_requests': self.scraping.delay_between_requests,
            'request_timeout': self.scraping.request_timeout,
            'max_retries': self.scraping.max_retries,
            'headless_browser': self.scraping.headless_browser,
            'user_agent': self.scraping.user_agent,
            'enabled': self.scraping.sources_enabled.get(scraper_name, False)
        }
        # Add scraper-specific configurations
        if scraper_name == 'flashscore':
            base_config['flashscore_bet365_indicator_fragment'] = self.scraping.flashscore_bet365_indicator_fragment
            base_config['flashscore_match_tie_break_keywords'] = self.scraping.flashscore_match_tie_break_keywords
        # Add other scraper specific configs here if needed in the future
        # elif scraper_name == 'sofascore':
        #     base_config['sofascore_api_key'] = self.scraping.sofascore_api_key # Example

        return base_config

    def update_scraper_enabled(self, scraper_name: str, enabled: bool):
        """Update enabled status for a scraper."""
        self.scraping.sources_enabled[scraper_name] = enabled
        self.logger.info(f"Scraper '{scraper_name}' {'enabled' if enabled else 'disabled'}")

    def get_enabled_scrapers(self) -> list[str]:
        """Get list of enabled scrapers."""
        return [name for name, enabled in self.scraping.sources_enabled.items() if enabled]