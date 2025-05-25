"""Data models for tennis matches and configuration."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class MatchStatus(Enum):
    """Match status enumeration."""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    WALKOVER = "walkover" # Added Walkover
    INTERRUPTED = "interrupted"
    RETIRED = "retired"
    AWARDED = "awarded"
    UNKNOWN = "unknown"

    @property
    def display_name(self) -> str:
        """Get a user-friendly display name for the status."""
        status_map = {
            MatchStatus.SCHEDULED: "Scheduled",
            MatchStatus.LIVE: "🔴 Live",
            MatchStatus.FINISHED: "Finished",
            MatchStatus.POSTPONED: "Postponed",
            MatchStatus.CANCELLED: "Cancelled",
            MatchStatus.WALKOVER: "Walkover",
            MatchStatus.INTERRUPTED: "Interrupted",
            MatchStatus.RETIRED: "Retired",
            MatchStatus.AWARDED: "Awarded",
            MatchStatus.UNKNOWN: "Unknown",
        }
        return status_map.get(self, self.value.title())

    @property
    def is_active(self) -> bool:
        """Check if the match status indicates an active (live or interrupted) match."""
        return self in [MatchStatus.LIVE, MatchStatus.INTERRUPTED]

    @property
    def is_completed(self) -> bool:
        """Check if the match status indicates a completed match."""
        return self in [MatchStatus.FINISHED, MatchStatus.WALKOVER, MatchStatus.RETIRED, MatchStatus.AWARDED]


class TournamentLevel(Enum):
    """Tournament level enumeration."""
    ITF_15K = "ITF 15K"
    ITF_25K = "ITF 25K"
    ITF_40K = "ITF 40K" # WTT new category
    ITF_60K = "ITF 60K"
    ITF_80K = "ITF 80K" # WTT new category
    ITF_100K = "ITF 100K"
    CHALLENGER = "Challenger"
    ATP_250 = "ATP 250"
    ATP_500 = "ATP 500"
    ATP_1000 = "ATP 1000" # Masters
    GRAND_SLAM = "Grand Slam"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class Surface(Enum):
    """Tennis court surface enumeration."""
    HARD = "Hard"
    CLAY = "Clay"
    GRASS = "Grass"
    CARPET = "Carpet"
    INDOOR_HARD = "Indoor Hard"
    INDOOR_CLAY = "Indoor Clay"
    UNKNOWN = "Unknown"


@dataclass
class Player:
    """Data model for a tennis player."""
    name: str
    country_code: Optional[str] = None # e.g., "USA", "SRB"
    ranking: Optional[int] = None
    player_id: Optional[str] = None # Source-specific ID
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """Get a user-friendly display name for the player."""
        if self.country_code:
            return f"{self.name} ({self.country_code})"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "country_code": self.country_code,
            "ranking": self.ranking,
            "player_id": self.player_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        return cls(
            name=data.get("name", "Unknown Player"),
            country_code=data.get("country_code"),
            ranking=data.get("ranking"),
            player_id=data.get("player_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Score:
    """Data model for a tennis match score."""
    sets: List[Tuple[int, int]] = field(default_factory=list)  # List of (home_score, away_score) for each set
    current_game: Optional[Tuple[str, str]] = None  # (home_points, away_points) e.g., ("40", "AD")
    server: Optional[Player] = None # Who is currently serving
    set_winners: List[Optional[str]] = field(default_factory=list) # 'home' or 'away' for each set

    def __str__(self) -> str:
        if not self.sets:
            return "Not started"
        set_scores = ["{}-{}".format(s[0], s[1]) for s in self.sets]
        score_str = " ".join(set_scores)
        if self.current_game:
            score_str += f" ({self.current_game[0]}-{self.current_game[1]})"
        return score_str

    @classmethod
    def from_string(cls, score_str: str) -> 'Score':
        """Parses a score string like '6-4 3-6' into a Score object."""
        sets = []
        parts = score_str.split()
        for part in parts:
            if '-' in part:
                try:
                    home, away = map(int, part.split('-'))
                    sets.append((home, away))
                except ValueError:
                    pass # Ignore parts that are not valid set scores
        return cls(sets=sets)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sets": self.sets,
            "current_game": self.current_game,
            "server_name": self.server.name if self.server else None,
            "set_winners": self.set_winners,
        }


@dataclass
class TennisMatch:
    """Data model for a tennis match."""
    home_player: Player
    away_player: Player
    score: Score = field(default_factory=Score)
    status: MatchStatus = MatchStatus.SCHEDULED
    tournament: str = ""
    tournament_level: TournamentLevel = TournamentLevel.UNKNOWN
    surface: Surface = Surface.UNKNOWN
    round_info: str = "" # e.g., "Quarterfinals", "R16"
    scheduled_time: Optional[datetime] = None # UTC
    actual_start_time: Optional[datetime] = None # UTC
    source: str = ""
    source_url: Optional[str] = None
    match_id: Optional[str] = None # Unique ID from the source
    last_updated: datetime = field(default_factory=datetime.utcnow) # UTC timestamp of last update
    metadata: Dict[str, Any] = field(default_factory=dict) # For any other source-specific data

    def __post_init__(self):
        # Ensure players are Player objects if strings were passed
        if isinstance(self.home_player, str):
            self.home_player = Player(name=self.home_player)
        if isinstance(self.away_player, str):
            self.away_player = Player(name=self.away_player)

    @property
    def is_live(self) -> bool:
        """Check if match is currently live."""
        return self.status == MatchStatus.LIVE

    @property
    def is_completed(self) -> bool:
        """Check if the match status indicates a completed match."""
        return self.status in [MatchStatus.FINISHED, MatchStatus.WALKOVER, MatchStatus.RETIRED, MatchStatus.AWARDED]

    @property
    def display_score(self) -> str:
        """Get a string representation of the score."""
        return str(self.score)

    @property
    def match_title(self) -> str:
        """Get a user-friendly title for the match."""
        return f"{self.home_player.name} vs {self.away_player.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "match_id": self.match_id,
            "home_player": self.home_player.to_dict(),
            "away_player": self.away_player.to_dict(),
            "score": self.score.to_dict(),
            "status": self.status.value,
            "tournament": self.tournament,
            "tournament_level": self.tournament_level.value,
            "surface": self.surface.value,
            "round_info": self.round_info,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "actual_start_time": self.actual_start_time.isoformat() if self.actual_start_time else None,
            "source": self.source,
            "source_url": self.source_url,
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TennisMatch':
        return cls(
            match_id=data.get("match_id"),
            home_player=Player.from_dict(data.get("home_player", {})),
            away_player=Player.from_dict(data.get("away_player", {})),
            score=Score(
                sets=data.get("score", {}).get("sets", []),
                current_game=tuple(data.get("score", {}).get("current_game")) if data.get("score", {}).get("current_game") else None
            ), # Simplified for now
            status=MatchStatus(data.get("status", "unknown")),
            tournament=data.get("tournament", ""),
            tournament_level=TournamentLevel(data.get("tournament_level", "Unknown")),
            surface=Surface(data.get("surface", "Unknown")),
            round_info=data.get("round_info", ""),
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]) if data.get("scheduled_time") else None,
            actual_start_time=datetime.fromisoformat(data["actual_start_time"]) if data.get("actual_start_time") else None,
            source=data.get("source", ""),
            source_url=data.get("source_url"),
            last_updated=datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )

    def __eq__(self, other):
        if not isinstance(other, TennisMatch):
            return NotImplemented
        # Define equality based on key identifiers, e.g., source and match_id
        # Or home/away player names and tournament if ID is not always present
        return (self.source == other.source and
                self.match_id == other.match_id and
                self.home_player.name == other.home_player.name and # Fallback if no ID
                self.away_player.name == other.away_player.name and
                self.tournament == other.tournament)

    def __hash__(self):
        # Hash based on the same key identifiers used in __eq__
        return hash((self.source, self.match_id, self.home_player.name, self.away_player.name, self.tournament))


@dataclass
class ScrapingResult:
    """Result of a scraping operation for a single source."""
    source: str
    matches: List[TennisMatch] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None # Time taken for this source
    metadata: Dict[str, Any] = field(default_factory=dict) # e.g., num_api_calls

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "matches": [match.to_dict() for match in self.matches],
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }