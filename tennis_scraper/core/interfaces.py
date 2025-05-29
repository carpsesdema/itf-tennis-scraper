from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Awaitable

from .models import TennisMatch, ScrapingResult


class MatchScraper(ABC):
    """Abstract base class for match scrapers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        from ..utils.logging import get_logger
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.delay_between_requests = config.get('delay_between_requests', 1)


    @abstractmethod
    async def get_source_name(self) -> str:
        """Return the name of this scraping source."""
        pass

    @abstractmethod
    async def scrape_matches(self, progress_callback: Optional[Callable[[TennisMatch], Awaitable[None]]] = None) -> ScrapingResult:
        """Scrape matches from this source and return a ScrapingResult."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this source is currently available."""
        pass

    async def cleanup(self):
        """Cleanup resources (override if needed)."""
        pass


class MatchFilter(ABC):
    """Abstract base class for match filters."""

    @abstractmethod
    def filter_matches(self, matches: List[TennisMatch]) -> List[TennisMatch]:
        """Filter matches based on specific criteria."""
        pass

    @abstractmethod
    def get_filter_name(self) -> str:
        """Return the name of this filter."""
        pass


class DataExporter(ABC):
    """Abstract base class for data exporters."""

    @abstractmethod
    async def export_matches(self, matches: List[TennisMatch], output_path: str, **kwargs) -> bool:
        """Export matches to specified format and location."""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported export formats."""
        pass

    @abstractmethod
    def get_default_extension(self) -> str:
        """Return the default file extension for this exporter."""
        pass


class UpdateChecker(ABC):
    """Abstract base class for update checkers."""

    @abstractmethod
    async def check_for_updates(self) -> Optional[Any]:
        """Check for updates."""
        pass

    @abstractmethod
    async def download_update(self, update_info: Any, progress_callback=None) -> Optional[str]:
        """Download an update."""
        pass


class EventEmitter(ABC):
    """Abstract base class for event emitters."""

    @abstractmethod
    def on(self, event_name: str, callback: callable):
        """Register an event listener."""
        pass

    @abstractmethod
    def emit(self, event_name: str, *args, **kwargs):
        """Emit an event."""
        pass


class Plugin(ABC):
    """Abstract base class for plugins."""

    @abstractmethod
    def load(self):
        """Load the plugin."""
        pass

    @abstractmethod
    def unload(self):
        """Unload the plugin."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get plugin name."""
        pass