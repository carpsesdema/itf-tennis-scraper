"""
ITF Tennis Scraper - Professional Edition
"""

__version__ = "1.0.0"  # Or your desired version
__author__ = "Your Name / Tennis Scraper Team"
__email__ = "your.email@example.com"


def get_info() -> dict:
    """Returns basic application information."""
    return {
        "name": "ITF Tennis Scraper - Professional Edition",
        "version": __version__,
        "description": "A comprehensive application for scraping and monitoring ITF tennis matches.",
        "author": __author__,
        "email": __email__,
    }


from .core.engine import TennisScrapingEngine
from .core.interfaces import (DataExporter, EventEmitter, MatchFilter,
                              MatchScraper, Plugin)
from .core.interfaces import UpdateChecker as CoreUpdateChecker
# Core business logic for tennis match scraping.
from .core.models import (MatchStatus, Player, Score, ScrapingResult, Surface,
                          TennisMatch, TournamentLevel)

__all__ = [
    "__version__",
    "get_info",
    "TennisMatch",
    "MatchStatus",
    "TournamentLevel",
    "Surface",
    "Player",
    "Score",
    "ScrapingResult",
    "MatchScraper",
    "MatchFilter",
    "DataExporter",
    "CoreUpdateChecker",
    "EventEmitter",
    "Plugin",
    "TennisScrapingEngine",
]
