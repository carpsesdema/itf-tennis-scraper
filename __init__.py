"""
ITF Tennis Scraper - Professional Edition
"""

__version__ = "1.0.0"  # Initial version, can be updated by build script
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

# Core business logic for tennis match scraping.
# This __all__ list re-exports key components from the core module
# and other submodules for easier access if needed.

from .core.models import (
    TennisMatch, MatchStatus, TournamentLevel, Surface, Player, Score, ScrapingResult
)
from .core.interfaces import (
    MatchScraper, MatchFilter, DataExporter, UpdateChecker as CoreUpdateChecker,
    EventEmitter, Plugin
)
from .core.engine import TennisScrapingEngine
# Filters would be imported here if they were defined directly in core.filters
# For now, let's assume they are used within the GUI or engine context.

__all__ = [
    # Version and Info
    "__version__",
    "get_info",

    # Models
    "TennisMatch", "MatchStatus", "TournamentLevel", "Surface", "Player", "Score", "ScrapingResult",

    # Interfaces
    "MatchScraper", "MatchFilter", "DataExporter", "CoreUpdateChecker", "EventEmitter", "Plugin",

    # Engine
    "TennisScrapingEngine",

    # Placeholder for filters if they become part of the public API of this package
    # "LiveMatchFilter", "CompletedMatchFilter", # ... and so on
]