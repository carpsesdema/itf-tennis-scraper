"""Abstract interfaces for the tennis scraper system."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .models import TennisMatch


class MatchScraper(ABC):
    """Abstract base class for match scrapers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def get_source_name(self) -> str:
        """Return the name of this scraping source."""
        pass

    @abstractmethod
    async def scrape_matches(self) -> List[TennisMatch]:
        """Scrape matches from this source."""
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
    async def export_matches(self, matches: List[TennisMatch], output_path: str) -> bool:
        """Export matches to specified format and location."""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported export formats."""
        pass