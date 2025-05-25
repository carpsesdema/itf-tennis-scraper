"""Flashscore scraper implementation."""

import asyncio
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from ..core.interfaces import MatchScraper
from ..core.models import TennisMatch, MatchStatus
from ..utils.logging import get_logger


class FlashscoreScraper(MatchScraper):
    """Scraper for Flashscore ITF tennis matches."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.logger = get_logger(__name__)
        self.driver = None

    async def get_source_name(self) -> str:
        """Return the name of this scraping source."""
        return "flashscore"

    async def is_available(self) -> bool:
        """Check if this source is currently available."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.flashscore.com", timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False

    async def scrape_matches(self) -> List[TennisMatch]:
        """Scrape ITF matches from Flashscore."""
        matches = []

        try:
            self.logger.info("Scraping Flashscore ITF matches...")
            driver = await self._get_driver()

            # Navigate and scrape
            driver.get("https://www.flashscore.com/tennis/itf-men-singles/")
            await asyncio.sleep(3)

            # Implementation of scraping logic
            # ... (extract the scraping logic from original file)

        except Exception as e:
            self.logger.error(f"Error scraping Flashscore: {e}")

        return matches

    async def _get_driver(self):
        """Get or create Chrome driver."""
        if self.driver is None:
            options = Options()
            if self.config.get('headless_browser', True):
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            self.driver = webdriver.Chrome(options=options)

        return self.driver

    async def cleanup(self):
        """Cleanup resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None