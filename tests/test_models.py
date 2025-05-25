"""
Tests for core data models.
"""

import pytest
from datetime import datetime

from tennis_scraper.core.models import (
    TennisMatch, Player, Score, MatchStatus, TournamentLevel, Surface
)


class TestPlayer:
    """Test Player model."""

    def test_create_player(self):
        player = Player("John Doe", "USA", 50)
        assert player.name == "John Doe"
        assert player.country == "USA"
        assert player.ranking == 50

    def test_player_display_name(self):
        player = Player("John Doe", "USA")
        assert player.display_name == "John Doe (USA)"

    def test_player_display_name_no_country(self):
        player = Player("John Doe")
        assert player.display_name == "John Doe"


class TestScore:
    """Test Score model."""

    def test_empty_score(self):
        score = Score()
        assert str(score) == "Not started"

    def test_score_with_sets(self):
        score = Score(sets=[(6, 4), (3, 6), (6, 2)])
        assert str(score) == "6-4 3-6 6-2"

    def test_score_from_string(self):
        score = Score.from_string("6-4 6-2")
        assert len(score.sets) == 2
        assert score.sets[0] == (6, 4)
        assert score.sets[1] == (6, 2)

    def test_score_from_invalid_string(self):
        score = Score.from_string("invalid")
        assert len(score.sets) == 0


class TestTennisMatch:
    """Test TennisMatch model."""

    def test_create_match(self):
        home_player = Player("John Doe")
        away_player = Player("Jane Smith")

        match = TennisMatch(
            home_player=home_player,
            away_player=away_player,
            status=MatchStatus.LIVE
        )

        assert match.home_player.name == "John Doe"
        assert match.away_player.name == "Jane Smith"
        assert match.is_live is True
        assert match.is_completed is False

    def test_match_with_string_players(self):
        match = TennisMatch(
            home_player="John Doe",
            away_player="Jane Smith"
        )

        assert isinstance(match.home_player, Player)
        assert isinstance(match.away_player, Player)
        assert match.home_player.name == "John Doe"

    def test_match_title(self):
        match = TennisMatch(
            home_player=Player("John Doe"),
            away_player=Player("Jane Smith")
        )

        assert match.match_title == "John Doe vs Jane Smith"

    def test_match_equality(self):
        match1 = TennisMatch(
            home_player=Player("John Doe"),
            away_player=Player("Jane Smith"),
            tournament="Test Tournament"
        )

        match2 = TennisMatch(
            home_player=Player("John Doe"),
            away_player=Player("Jane Smith"),
            tournament="Test Tournament"
        )

        assert match1 == match2

    def test_match_to_dict(self):
        match = TennisMatch(
            home_player=Player("John Doe", "USA"),
            away_player=Player("Jane Smith", "GBR"),
            status=MatchStatus.LIVE,
            tournament="Test Tournament"
        )

        data = match.to_dict()

        assert data["home_player"]["name"] == "John Doe"
        assert data["home_player"]["country"] == "USA"
        assert data["status"] == "live"
        assert data["tournament"] == "Test Tournament"

    def test_match_from_dict(self):
        data = {
            "home_player": {"name": "John Doe", "country": "USA"},
            "away_player": {"name": "Jane Smith", "country": "GBR"},
            "status": "live",
            "tournament": "Test Tournament"
        }

        match = TennisMatch.from_dict(data)

        assert match.home_player.name == "John Doe"
        assert match.home_player.country == "USA"
        assert match.status == MatchStatus.LIVE
        assert match.tournament == "Test Tournament"


class TestMatchStatus:
    """Test MatchStatus enum."""

    def test_status_properties(self):
        assert MatchStatus.LIVE.is_active is True
        assert MatchStatus.FINISHED.is_completed is True
        assert MatchStatus.SCHEDULED.is_active is False
        assert MatchStatus.SCHEDULED.is_completed is False

    def test_status_display_names(self):
        assert MatchStatus.LIVE.display_name == "🔴 Live"
        assert MatchStatus.FINISHED.display_name == "Finished"
        assert MatchStatus.SCHEDULED.display_name == "Scheduled"