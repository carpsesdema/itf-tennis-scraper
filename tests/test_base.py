"""
Tests for base scraper functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from tennis_scraper.scrapers.base import BaseScraper
from tennis_scraper.core.models import ScrapingResult


class TestBaseScraper:
    """Test BaseScraper functionality."""

    @pytest.fixture
    def base_scraper(self):
        """Create a concrete implementation of BaseScraper for testing."""

        class TestScraper(BaseScraper):
            async def get_source_name(self):
                return "test_scraper"

            async def scrape_matches(self):
                return ScrapingResult(source="test_scraper", success=True)

            async def is_available(self):
                return True

        config = {
            'request_timeout': 10,
            'max_retries': 3,
            'delay_between_requests': 1,
            'headless_browser': True
        }

        return TestScraper(config)

    @pytest.mark.asyncio
    async def test_get_session(self, base_scraper):
        """Test session creation."""
        session = await base_scraper._get_session()
        assert session is not None
        await session.close()

    @pytest.mark.asyncio
    async def test_check_site_availability(self, base_scraper, mock_aiohttp_session):
        """Test site availability check."""
        with patch.object(base_scraper, '_get_session', return_value=mock_aiohttp_session):
            # Mock successful response
            mock_aiohttp_session.head = Mock(return_value=AsyncContextManager(Mock(status=200)))

            available = await base_scraper._check_site_availability("https://example.com")
            assert available is True

    def test_parse_player_name(self, base_scraper):
        """Test player name parsing."""
        assert base_scraper._parse_player_name("  John Doe  ") == "John Doe"
        assert base_scraper._parse_player_name("Mr. John Doe") == "John Doe"
        assert base_scraper._parse_player_name("") == ""

    def test_parse_score(self, base_scraper):
        """Test score parsing."""
        score = base_scraper._parse_score("6-4 6-2")
        assert len(score.sets) == 2
        assert score.sets[0] == (6, 4)
        assert score.sets[1] == (6, 2)

    def test_parse_match_status(self, base_scraper):
        """Test match status parsing."""
        from tennis_scraper.core.models import MatchStatus

        assert base_scraper._parse_match_status("live") == MatchStatus.LIVE
        assert base_scraper._parse_match_status("finished") == MatchStatus.FINISHED
        assert base_scraper._parse_match_status("") == MatchStatus.SCHEDULED

    def test_create_match(self, base_scraper):
        """Test match creation."""
        match = base_scraper._create_match(
            home_player="John Doe",
            away_player="Jane Smith",
            score="6-4 6-2",
            status="finished",
            tournament="Test Tournament"
        )

        assert match.home_player.name == "John Doe"
        assert match.away_player.name == "Jane Smith"
        assert len(match.score.sets) == 2
        assert match.tournament == "Test Tournament"
        assert match.source == "test_scraper"

    @pytest.mark.asyncio
    async def test_scrape_with_retry_success(self, base_scraper):
        """Test successful scraping with retry logic."""
        result = await base_scraper.scrape_with_retry(max_retries=2)
        assert result.success is True
        assert result.source == "test_scraper"

    @pytest.mark.asyncio
    async def test_scrape_with_retry_failure(self, base_scraper):
        """Test scraping failure with retry logic."""
        # Mock scraper that always fails
        base_scraper.scrape_matches = AsyncMock(side_effect=Exception("Test error"))

        result = await base_scraper.scrape_with_retry(max_retries=1)
        assert result.success is False
        assert "Test error" in result.error_message

    @pytest.mark.asyncio
    async def test_cleanup(self, base_scraper):
        """Test cleanup functionality."""
        # Should not raise any exceptions
        await base_scraper.cleanup()