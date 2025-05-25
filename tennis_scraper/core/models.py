"""Data models for tennis matches and configuration."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class MatchStatus(Enum):
    """Match status enumeration."""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


@dataclass
class TennisMatch:
    """Data model for a tennis match."""
    home_player: str
    away_player: str
    score: str = ""
    status: MatchStatus = MatchStatus.SCHEDULED
    tournament: str = ""
    round_info: str = ""
    source: str = ""
    url: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_live(self) -> bool:
        """Check if match is currently live."""
        return self.status == MatchStatus.LIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "home_player": self.home_player,
            "away_player": self.away_player,
            "score": self.score,
            "status": self.status.value,
            "tournament": self.tournament,
            "round_info": self.round_info,
            "source": self.source,
            "url": self.url,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }