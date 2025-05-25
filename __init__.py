"""
Core business logic for tennis match scraping.
"""

from .models import TennisMatch, MatchStatus, TournamentLevel, Surface, Player, Score, ScrapingResult
from .interfaces import MatchScraper, MatchFilter, DataExporter, UpdateChecker, EventEmitter, Plugin
from .engine import TennisScrapingEngine
from .filters import (
    LiveMatchFilter, CompletedMatchFilter, ScheduledMatchFilter,
    PlayerNameFilter, CountryFilter, TournamentFilter, TournamentLevelFilter,
    RankingFilter, TimeRangeFilter, RecentActivityFilter, SourceFilter,
    RegexFilter, CompositeFilter
)

__all__ = [
    # Models
    "TennisMatch", "MatchStatus", "TournamentLevel", "Surface", "Player", "Score", "ScrapingResult",

    # Interfaces
    "MatchScraper", "MatchFilter", "DataExporter", "UpdateChecker", "EventEmitter", "Plugin",

    # Engine
    "TennisScrapingEngine",

    # Filters
    "LiveMatchFilter", "CompletedMatchFilter", "ScheduledMatchFilter",
    "PlayerNameFilter", "CountryFilter", "TournamentFilter", "TournamentLevelFilter",
    "RankingFilter", "TimeRangeFilter", "RecentActivityFilter", "SourceFilter",
    "RegexFilter", "CompositeFilter"
]