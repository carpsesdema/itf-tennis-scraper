import re
import urllib.parse
from typing import Any, List, Tuple, Optional
from datetime import datetime

from .logging import get_logger


class ValidationError(Exception):
    """Custom validation error."""
    pass


class BaseValidator:
    """Base validator class."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a value.

        Returns:
            Tuple of (is_valid, error_message)
        """
        raise NotImplementedError

    def is_valid(self, value: Any) -> bool:
        """Check if value is valid."""
        valid, _ = self.validate(value)
        return valid


class URLValidator(BaseValidator):
    """Validate URLs."""

    def __init__(self, allowed_schemes: List[str] = None):
        super().__init__()
        self.allowed_schemes = allowed_schemes or ['http', 'https']

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate URL."""
        if not isinstance(value, str):
            return False, "URL must be a string"

        if not value.strip():
            return False, "URL cannot be empty"

        try:
            parsed = urllib.parse.urlparse(value)

            if not parsed.scheme:
                return False, "URL must include a scheme (http/https)"

            if parsed.scheme not in self.allowed_schemes:
                return False, f"URL scheme must be one of: {', '.join(self.allowed_schemes)}"

            if not parsed.netloc:
                return False, "URL must include a domain"

            return True, None

        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"


class VersionValidator(BaseValidator):
    """Validate version strings."""

    def __init__(self, allow_prerelease: bool = True):
        super().__init__()
        self.allow_prerelease = allow_prerelease

        # Semantic versioning pattern
        if allow_prerelease:
            self.pattern = re.compile(
                r'^(\d+)\.(\d+)\.(\d+)'
                r'(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
                r'(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
            )
        else:
            self.pattern = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate version string."""
        if not isinstance(value, str):
            return False, "Version must be a string"

        if not value.strip():
            return False, "Version cannot be empty"

        if not self.pattern.match(value):
            if self.allow_prerelease:
                return False, "Version must be in format X.Y.Z[-prerelease][+build]"
            else:
                return False, "Version must be in format X.Y.Z"

        return True, None

    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """

        def parse_version(version: str) -> Tuple[int, int, int]:
            match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
            if match:
                return tuple(map(int, match.groups()))
            raise ValueError(f"Invalid version format: {version}")

        try:
            v1 = parse_version(version1)
            v2 = parse_version(version2)

            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0

        except ValueError as e:
            self.logger.error(f"Version comparison failed: {e}")
            return 0


class EmailValidator(BaseValidator):
    """Validate email addresses."""

    def __init__(self):
        super().__init__()
        self.pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate email address."""
        if not isinstance(value, str):
            return False, "Email must be a string"

        if not value.strip():
            return False, "Email cannot be empty"

        if not self.pattern.match(value):
            return False, "Invalid email format"

        return True, None


class PlayerNameValidator(BaseValidator):
    """Validate tennis player names."""

    def __init__(self):
        super().__init__()
        # Allow letters, spaces, hyphens, apostrophes, and dots
        self.pattern = re.compile(r"^[a-zA-Z\s\-'\.]+$")

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate player name."""
        if not isinstance(value, str):
            return False, "Player name must be a string"

        name = value.strip()
        if not name:
            return False, "Player name cannot be empty"

        if len(name) < 2:
            return False, "Player name must be at least 2 characters"

        if len(name) > 100:
            return False, "Player name must be less than 100 characters"

        if not self.pattern.match(name):
            return False, "Player name contains invalid characters"

        return True, None


class RankingValidator(BaseValidator):
    """Validate tennis rankings."""

    def __init__(self, min_ranking: int = 1, max_ranking: int = 2000):
        super().__init__()
        self.min_ranking = min_ranking
        self.max_ranking = max_ranking

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate ranking."""
        if value is None:
            return True, None  # None is valid (unranked)

        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                return False, "Ranking must be a number"

        if value < self.min_ranking:
            return False, f"Ranking must be at least {self.min_ranking}"

        if value > self.max_ranking:
            return False, f"Ranking must be at most {self.max_ranking}"

        return True, None


class TournamentNameValidator(BaseValidator):
    """Validate tournament names."""

    def __init__(self):
        super().__init__()
        # Allow letters, numbers, spaces, and common punctuation
        self.pattern = re.compile(r"^[a-zA-Z0-9\s\-_'\".,()&]+$")

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate tournament name."""
        if not isinstance(value, str):
            return False, "Tournament name must be a string"

        name = value.strip()
        if not name:
            return False, "Tournament name cannot be empty"

        if len(name) < 3:
            return False, "Tournament name must be at least 3 characters"

        if len(name) > 200:
            return False, "Tournament name must be less than 200 characters"

        if not self.pattern.match(name):
            return False, "Tournament name contains invalid characters"

        return True, None


class ConfigValidator:
    """Validate configuration values."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.url_validator = URLValidator()
        self.version_validator = VersionValidator()

    def validate_scraping_config(self, config: dict) -> List[str]:
        """Validate scraping configuration."""
        errors = []

        # Delay validation
        delay = config.get('delay_between_requests', 0)
        if not isinstance(delay, int) or delay < 1 or delay > 60:
            errors.append("delay_between_requests must be between 1 and 60 seconds")

        # Timeout validation
        timeout = config.get('request_timeout', 0)
        if not isinstance(timeout, int) or timeout < 5 or timeout > 300:
            errors.append("request_timeout must be between 5 and 300 seconds")

        # Max retries validation
        retries = config.get('max_retries', 0)
        if not isinstance(retries, int) or retries < 1 or retries > 10:
            errors.append("max_retries must be between 1 and 10")

        # User agent validation
        user_agent = config.get('user_agent', '')
        if not isinstance(user_agent, str) or len(user_agent.strip()) < 10:
            errors.append("user_agent must be a valid user agent string")

        return errors

    def validate_ui_config(self, config: dict) -> List[str]:
        """Validate UI configuration."""
        errors = []

        # Window dimensions
        width = config.get('window_width', 0)
        if not isinstance(width, int) or width < 800 or width > 5000:
            errors.append("window_width must be between 800 and 5000 pixels")

        height = config.get('window_height', 0)
        if not isinstance(height, int) or height < 600 or height > 3000:
            errors.append("window_height must be between 600 and 3000 pixels")

        # Refresh interval
        interval = config.get('auto_refresh_interval', 0)
        if not isinstance(interval, int) or interval < 30 or interval > 3600:
            errors.append("auto_refresh_interval must be between 30 and 3600 seconds")

        # Theme validation
        theme = config.get('theme', '')
        if theme not in ['dark', 'light', 'system']:
            errors.append("theme must be 'dark', 'light', or 'system'")

        return errors

    def validate_update_config(self, config: dict) -> List[str]:
        """Validate update configuration."""
        errors = []

        # Frequency validation
        frequency = config.get('frequency', '')
        if frequency not in ['never', 'daily', 'weekly', 'monthly']:
            errors.append("update frequency must be 'never', 'daily', 'weekly', or 'monthly'")

        # GitHub repo validation
        repo = config.get('github_repo', '')
        if repo and not re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', repo):
            errors.append("github_repo must be in format 'owner/repo'")

        # Update URL validation
        url = config.get('update_url', '')
        if url:
            valid, error = self.url_validator.validate(url)
            if not valid:
                errors.append(f"update_url is invalid: {error}")

        return errors