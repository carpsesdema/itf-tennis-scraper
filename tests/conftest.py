"""
Pytest configuration and fixtures for tennis scraper tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import tempfile
import shutil

from tennis_scraper.config import Config
from tennis_scraper.core.models import TennisMatch, Player, MatchStatus
from tennis_scraper.core.engine import TennisScrapingEngine


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    config = Config()
    config.scraping.delay_between_requests = 1
    config.scraping.request_timeout = 5
    config.scraping.headless_browser = True
    return config


@pytest.fixture
def sample_matches():
    """Create sample tennis matches for testing."""
    matches = [
        TennisMatch(
            home_player=Player("John Doe"),
            away_player=Player("Jane Smith"),
            score="6-4 3-2",
            status=MatchStatus.LIVE,
            tournament="ITF Test Tournament",
            source="test"
        ),
        TennisMatch(
            home_player=Player("Bob Wilson"),
            away_player=Player("Alice Brown"),
            score="6-2 6-1",
            status=MatchStatus.FINISHED,
            tournament="ITF Test Tournament",
            source="test"
        ),
        TennisMatch(
            home_player=Player("Mike Johnson"),
            away_player=Player("Sarah Davis"),
            score="",
            status=MatchStatus.SCHEDULED,
            tournament="ITF Test Tournament",
            source="test"
        )
    ]
    return matches


@pytest.fixture
def mock_scraper():
    """Create a mock scraper for testing."""
    scraper = Mock()
    scraper.get_source_name = AsyncMock(return_value="mock_scraper")
    scraper.is_available = AsyncMock(return_value=True)
    scraper.scrape_matches = AsyncMock()
    scraper.cleanup = AsyncMock()
    return scraper


@pytest.fixture
def mock_engine(sample_config, mock_scraper):
    """Create a mock scraping engine for testing."""
    engine = TennisScrapingEngine(sample_config.to_dict())
    engine.scrapers = {"mock": mock_scraper}
    return engine


@pytest.fixture
def temp_directory():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_qt_app():
    """Create a mock Qt application for GUI tests."""
    from unittest.mock import Mock
    app = Mock()
    app.exec.return_value = 0
    return app


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Clean environment variables for each test."""
    # Remove any environment variables that might affect tests
    env_vars_to_remove = [
        'TENNIS_SCRAPER_CONFIG',
        'DEBUG',
        'LOG_LEVEL'
    ]

    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)


class AsyncContextManager:
    """Helper class for async context manager testing."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    session = Mock()

    def get_response(status=200, json_data=None, text_data=""):
        response = Mock()
        response.status = status
        response.json = AsyncMock(return_value=json_data or {})
        response.text = AsyncMock(return_value=text_data)
        response.raise_for_status = Mock()
        return AsyncContextManager(response)

    session.get = Mock(side_effect=get_response)
    session.close = AsyncMock()
    return session


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "gui: marks tests as GUI tests")
    config.addinivalue_line("markers", "network: marks tests that require network access")