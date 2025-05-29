"""
Configuration management for ITF Tennis Scraper - OPTIMIZED FOR SLOW COMPUTERS.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Any, Optional, List

from .utils.logging import get_logger


@dataclass
class ScrapingConfig:
    """Configuration for scraping operations - OPTIMIZED FOR SLOW SYSTEMS."""
    # INCREASED delays and timeouts for slow computers
    delay_between_requests: int = 8  # Increased from 2 to 8 seconds
    request_timeout: int = 45  # Increased from 10 to 45 seconds
    max_retries: int = 2  # Reduced from 3 to 2 retries to save time
    headless_browser: bool = True  # Force headless for performance
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # ONLY flashscore enabled - removed other sources for speed
    sources_enabled: Dict[str, bool] = field(default_factory=lambda: {
        'flashscore': True,
    })

    # Flashscore-specific settings - OPTIMIZED for slow computers
    flashscore_bet365_indicator_fragment: str = "/549/"
    flashscore_match_tie_break_keywords: List[str] = field(
        default_factory=lambda: [
            "match tie break",
            "match tie-break",
            "super tiebreak",
            "first to 10"
        ]
    )

    # NEW: Slow computer specific settings
    flashscore_element_timeout: int = 60  # 60 seconds for slow computers
    flashscore_max_matches_to_process: int = 25  # Limit matches processed
    flashscore_max_elements_to_check: int = 100  # Limit page elements checked
    flashscore_simplified_processing: bool = True  # Use simplified processing


@dataclass
class UIConfig:
    """Configuration for user interface - OPTIMIZED FOR SLOW COMPUTERS."""
    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    auto_refresh_interval: int = 120  # 2 minutes instead of 10 for slow computers
    show_live_only: bool = True

    # NEW: Slow computer UI optimizations
    throttle_ui_updates: bool = True  # Throttle UI updates
    ui_update_interval: int = 10  # Update UI max every 10 seconds
    reduce_animations: bool = True  # Reduce animations for performance
    limit_log_lines: int = 500  # Limit log viewer lines (was 1000)


@dataclass
class UpdateConfig:
    """Configuration for update system - SIMPLIFIED FOR SLOW COMPUTERS."""
    check_on_startup: bool = False  # Disabled for slow computers to speed startup
    frequency: str = "never"  # Disabled updates for slow computers
    auto_download: bool = False
    github_repo: str = "carpsesdema/itf-tennis-scraper"
    update_url: str = ""


@dataclass
class LoggingConfig:
    """Configuration for logging - OPTIMIZED FOR SLOW COMPUTERS."""
    level: str = "INFO"  # Keep INFO level but optimize file handling
    file_path: str = "tennis_scraper.log"
    max_file_size: int = 5 * 1024 * 1024  # Reduced from 10MB to 5MB
    backup_count: int = 3  # Reduced from 5 to 3 backups

    # NEW: Slow computer logging optimizations
    reduce_debug_logging: bool = True  # Reduce verbose logging
    async_logging: bool = False  # Disable async logging for simplicity


@dataclass
class ExportConfig:
    """Configuration for data export - SIMPLIFIED FOR SLOW COMPUTERS."""
    default_format: str = "csv"  # CSV is fastest
    include_metadata: bool = False  # Reduce metadata to speed up exports
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"

    # NEW: Export optimizations for slow computers
    limit_export_rows: int = 1000  # Limit exports to 1000 rows max
    simple_export_format: bool = True  # Use simplified export format


class Config:
    """Main configuration class - OPTIMIZED FOR SLOW COMPUTERS."""

    def __init__(self):
        """Initialize configuration with slow computer optimizations."""
        self.scraping = ScrapingConfig()
        self.ui = UIConfig()
        self.updates = UpdateConfig()
        self.logging = LoggingConfig()
        self.export = ExportConfig()

        # Set derived values
        if not self.updates.update_url:
            self.updates.update_url = f"https://api.github.com/repos/{self.updates.github_repo}/releases/latest"

        self.logger = get_logger(__name__)

        # Log slow computer mode
        self.logger.info("🐌 Configuration optimized for SLOW COMPUTER mode")

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from file with slow computer defaults."""
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
                config.logger.info(f"🐌 Slow computer config loaded from {config_file}")

            except Exception as e:
                config.logger.warning(f"Failed to load config from {config_file}: {e}")
                config.logger.info("Using slow computer defaults")
        else:
            config.logger.info("🐌 No config file found, using slow computer defaults")

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

            self.logger.info(f"🐌 Slow computer config saved to {config_file}")

        except Exception as e:
            self.logger.error(f"Failed to save config to {config_file}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'scraping': asdict(self.scraping),
            'ui': asdict(self.ui),
            'updates': asdict(self.updates),
            'logging': asdict(self.logging),
            'export': asdict(self.export),
            'slow_computer_mode': True  # Mark as slow computer config
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
            if not data['updates'].get('update_url'):
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
        config_dir = Path.home() / ".config" / "tennis_scraper"
        return str(config_dir / "slow_computer_config.json")

    def validate(self) -> bool:
        """Validate configuration values with slow computer considerations - AUTO-FIX bad values."""
        errors = []
        fixed_values = []

        # Auto-fix values that are too small for slow computers
        if self.scraping.delay_between_requests < 5:
            self.scraping.delay_between_requests = 8
            fixed_values.append("delay_between_requests auto-fixed to 8 seconds")

        if self.scraping.request_timeout < 30:
            self.scraping.request_timeout = 45
            fixed_values.append("request_timeout auto-fixed to 45 seconds")

        if self.ui.auto_refresh_interval < 60:
            self.ui.auto_refresh_interval = 120
            fixed_values.append("auto_refresh_interval auto-fixed to 120 seconds (2 minutes)")

        # Log auto-fixes
        for fix in fixed_values:
            self.logger.info(f"🐌 Slow computer auto-fix: {fix}")

        # Only log actual errors (none for now since we auto-fix)
        for error in errors:
            self.logger.error(f"🐌 Slow computer config validation error: {error}")

        # Always return True since we auto-fix problems
        if fixed_values:
            self.logger.info("🐌 Config auto-fixed for slow computer - saving updates...")
            try:
                self.save_to_file()
            except Exception as e:
                self.logger.warning(f"Could not save auto-fixed config: {e}")

        return True  # Always pass validation after auto-fixing

    def get_scraper_config(self, scraper_name: str) -> Dict[str, Any]:
        """Get configuration for a specific scraper with slow computer optimizations."""
        base_config = {
            'delay_between_requests': self.scraping.delay_between_requests,
            'request_timeout': self.scraping.request_timeout,
            'max_retries': self.scraping.max_retries,
            'headless_browser': True,  # Force headless for slow computers
            'user_agent': self.scraping.user_agent,
            'enabled': self.scraping.sources_enabled.get(scraper_name, False),
            'slow_computer_mode': True  # Flag for scrapers
        }

        # Add scraper-specific slow computer optimizations
        if scraper_name == 'flashscore':
            base_config.update({
                'flashscore_bet365_indicator_fragment': self.scraping.flashscore_bet365_indicator_fragment,
                'flashscore_match_tie_break_keywords': self.scraping.flashscore_match_tie_break_keywords,
                'flashscore_element_timeout': self.scraping.flashscore_element_timeout,
                'flashscore_max_matches_to_process': self.scraping.flashscore_max_matches_to_process,
                'flashscore_max_elements_to_check': self.scraping.flashscore_max_elements_to_check,
                'flashscore_simplified_processing': self.scraping.flashscore_simplified_processing
            })

        return base_config

    def update_scraper_enabled(self, scraper_name: str, enabled: bool):
        """Update enabled status for a scraper."""
        self.scraping.sources_enabled[scraper_name] = enabled
        self.logger.info(f"🐌 Slow computer mode: Scraper '{scraper_name}' {'enabled' if enabled else 'disabled'}")

    def get_enabled_scrapers(self) -> list[str]:
        """Get list of enabled scrapers."""
        enabled = [name for name, enabled in self.scraping.sources_enabled.items() if enabled]
        self.logger.info(f"🐌 Enabled scrapers for slow computer: {enabled}")
        return enabled

    def optimize_for_slow_computer(self):
        """Apply additional optimizations for very slow computers."""
        self.logger.info("🐌🐌 Applying EXTRA slow computer optimizations...")

        # Extra conservative settings
        self.scraping.delay_between_requests = max(10, self.scraping.delay_between_requests)
        self.scraping.request_timeout = max(60, self.scraping.request_timeout)
        self.scraping.max_retries = 1  # Only 1 retry for very slow computers

        self.ui.auto_refresh_interval = max(300, self.ui.auto_refresh_interval)  # 5 minutes minimum for very slow
        self.ui.throttle_ui_updates = True
        self.ui.ui_update_interval = 15  # Update UI max every 15 seconds

        # Disable updates completely
        self.updates.check_on_startup = False
        self.updates.frequency = "never"

        # Reduce logging
        self.logging.level = "WARNING"  # Only warnings and errors
        self.logging.reduce_debug_logging = True

        self.logger.warning("🐌🐌 EXTRA slow computer mode activated!")

    def is_slow_computer_mode(self) -> bool:
        """Check if running in slow computer mode."""
        return (self.scraping.delay_between_requests >= 8 and
                self.scraping.request_timeout >= 45 and
                self.ui.auto_refresh_interval >= 600)