"""Flashscore scraper implementation."""

import asyncio
import time  # Keep for sleeps if needed by Selenium
from typing import List, Optional, Dict
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import BaseScraper  # Inherit from BaseScraper
from ..core.models import TennisMatch, Player, Score, MatchStatus, ScrapingResult, TournamentLevel, Surface
from ..utils.logging import get_logger


class FlashscoreScraper(BaseScraper):  # Inherit from BaseScraper
    """Scraper for Flashscore ITF tennis matches."""

    # No need for __init__ if it just calls super and sets logger, BaseScraper handles that.
    # If you need Flashscore-specific initialization, you can add it.

    async def get_source_name(self) -> str:
        """Return the name of this scraping source."""
        return "flashscore"

    async def is_available(self) -> bool:
        """Check if this source is currently available using aiohttp from BaseScraper."""
        return await self._check_site_availability("https://www.flashscore.com", timeout=self.request_timeout)

    async def _init_driver(self):
        """Initialize Chrome driver for Selenium."""
        # This needs to run in a separate thread or be adapted for asyncio if possible.
        # For now, keeping it synchronous for simplicity within the async scrape_matches.
        # Consider using Playwright for better async browser automation if this becomes a bottleneck.
        loop = asyncio.get_event_loop()
        if getattr(self, '_driver', None) is None:
            self.logger.info("Initializing Selenium WebDriver for Flashscore...")
            options = ChromeOptions()
            if self.config.get('headless_browser', True):
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")  # Often recommended for headless
            options.add_argument("--window-size=1920x1080")  # Standard window size
            options.add_argument(f"--user-agent={self.config.get('user_agent', 'Mozilla/5.0')}")
            # Disable logging for Selenium itself to keep console clean
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

            try:
                # Run WebDriver creation in an executor to avoid blocking the event loop
                self._driver = await loop.run_in_executor(None, webdriver.Chrome, options)
                self.logger.info("Selenium WebDriver for Flashscore initialized.")
            except Exception as e:
                self.logger.error(f"Failed to initialize Selenium WebDriver: {e}")
                self._driver = None
                raise  # Re-raise to be caught by scrape_with_retry
        return self._driver

    async def scrape_matches(self) -> ScrapingResult:  # Changed to ScrapingResult
        """Scrape ITF matches from Flashscore."""
        start_time_dt = datetime.now(timezone.utc)
        matches_found: List[TennisMatch] = []
        driver = None
        error_message = None
        success = False

        try:
            driver = await self._init_driver()
            if not driver:
                raise ConnectionError("Failed to initialize WebDriver for Flashscore.")

            self.logger.info("Navigating to Flashscore ITF Men Singles page...")
            # Running synchronous Selenium calls in an executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, driver.get, "https://www.flashscore.com/tennis/itf-men-singles/")
            # Increased sleep for page load, especially with cookie banners
            await asyncio.sleep(self.config.get('flashscore_initial_load_delay', 7))

            # Handle cookie consent - run in executor
            try:
                self.logger.debug("Attempting to handle cookie consent...")
                cookie_btn_locator = (By.ID, "onetrust-accept-btn-handler")

                # WebDriverWait needs to be run in executor
                def find_and_click_cookie_btn():
                    wait = WebDriverWait(driver, 10)  # Timeout for cookie button
                    cookie_btn = wait.until(EC.element_to_be_clickable(cookie_btn_locator))
                    cookie_btn.click()
                    self.logger.info("Cookie consent accepted.")
                    time.sleep(2)  # Give time for overlay to disappear

                await loop.run_in_executor(None, find_and_click_cookie_btn)
            except TimeoutException:
                self.logger.info("Cookie consent dialog not found or timed out, proceeding.")
            except Exception as e_cookie:
                self.logger.warning(f"Could not click cookie button: {e_cookie}")

            # Wait for match elements to be present - run in executor
            self.logger.debug("Waiting for match elements to load...")

            def wait_for_match_elements():
                match_container_locator = (By.CSS_SELECTOR, "div.sportName.tennis div.event__match")
                WebDriverWait(driver, self.config.get('flashscore_element_timeout', 20)).until(
                    EC.presence_of_all_elements_located(match_container_locator)
                )
                return driver.find_elements(*match_container_locator)

            match_elements = await loop.run_in_executor(None, wait_for_match_elements)
            self.logger.info(f"Found {len(match_elements)} potential match elements on Flashscore.")

            if not match_elements:
                self.logger.warning("No match elements found on Flashscore page.")

            for element_index, element in enumerate(match_elements):
                try:
                    # Run individual element parsing in executor
                    match_data = await loop.run_in_executor(None, self._extract_match_data_from_element, element)
                    if match_data:
                        source_name = await self.get_source_name()  # Get source name
                        # Use the base class helper to create the match object
                        match = TennisMatch(
                            home_player=Player(name=match_data['home_player']),
                            away_player=Player(name=match_data['away_player']),
                            score=Score.from_string(match_data['score']),
                            status=self._parse_match_status(match_data['status'], match_data['score']),
                            tournament="ITF Men Singles",  # Flashscore page is specific
                            tournament_level=TournamentLevel.ITF_25K,  # Assuming, might need refinement
                            surface=Surface.UNKNOWN,  # Flashscore page may not specify surface easily
                            source=source_name,
                            source_url=driver.current_url,  # URL of the main page
                            match_id=match_data.get('id'),  # If an ID can be extracted
                            scheduled_time=None,  # Flashscore might not show scheduled time easily here
                            last_updated=datetime.now(timezone.utc),
                        )
                        matches_found.append(match)
                except Exception as e_extract:
                    self.logger.warning(f"Failed to extract match data for element {element_index}: {e_extract}")
            success = True
        except ConnectionError as e_conn:  # Specific for WebDriver init failure
            self.logger.error(f"Flashscore WebDriver connection error: {e_conn}")
            error_message = str(e_conn)
        except TimeoutException as e_timeout:
            self.logger.error(f"Flashscore scraping timed out: {e_timeout}")
            error_message = "Page element timed out."
        except Exception as e:
            self.logger.error(f"Error scraping Flashscore: {e}", exc_info=True)
            error_message = str(e)
        # No finally block for driver.quit() here, cleanup handles it

        duration = (datetime.now(timezone.utc) - start_time_dt).total_seconds()
        return ScrapingResult(
            source=await self.get_source_name(),
            matches=matches_found,
            success=success,
            error_message=error_message,
            duration_seconds=duration,
            timestamp=datetime.now(timezone.utc)
        )

    def _extract_match_data_from_element(self, element) -> Optional[Dict]:
        """
        Synchronous helper to extract match data from a single Selenium web element.
        This will be run in an executor by scrape_matches.
        """
        try:
            home_player_el = element.find_element(By.CSS_SELECTOR, "[class*='event__participant--home']")
            away_player_el = element.find_element(By.CSS_SELECTOR, "[class*='event__participant--away']")
            home_player = home_player_el.text.strip()
            away_player = away_player_el.text.strip()

            if not home_player or not away_player:
                self.logger.debug("Skipping element due to missing player names.")
                return None

            # Try to get score; might not exist for scheduled matches
            try:
                home_score_el = element.find_element(By.CSS_SELECTOR, "[class*='event__score--home']")
                away_score_el = element.find_element(By.CSS_SELECTOR, "[class*='event__score--away']")
                score = f"{home_score_el.text.strip()}-{away_score_el.text.strip()}"
            except NoSuchElementException:
                score = ""  # No score yet

            # Try to get status
            try:
                # Flashscore status is often within a specific stage class element
                # It could be "Finished", "1st Half", "09:30" (time), etc.
                status_el = element.find_element(By.CSS_SELECTOR, "[class*='event__stage']")
                status = status_el.text.strip()
            except NoSuchElementException:
                status = "Scheduled"  # Default if no explicit status found

            # Try to get a unique ID for the match from its href
            match_id = None
            try:
                # The match link is usually on an 'a' tag with class 'event__match' or similar within the element
                # Or sometimes the element itself is the 'a' tag
                if element.tag_name == 'a':
                    link_element = element
                else:
                    link_element = element.find_element(By.CSS_SELECTOR, "a[href*='/match/']")  # More specific selector

                href = link_element.get_attribute('href')
                if href and '/match/' in href:
                    # Example href: https://www.flashscore.com/match/abcdefgh/#match-summary
                    match_id_part = href.split('/match/')[1].split('/')[0]
                    if match_id_part:
                        match_id = f"flashscore_{match_id_part}"
            except NoSuchElementException:
                self.logger.debug("Could not find link element for match ID.")
            except Exception as e_id:
                self.logger.warning(f"Error extracting match_id from href: {e_id}")

            return {
                "home_player": home_player,
                "away_player": away_player,
                "score": score,
                "status": status,
                "id": match_id
            }

        except NoSuchElementException as e_nse:
            # This can happen if an element isn't a proper match structure
            self.logger.debug(f"Could not find expected sub-element, likely not a match row: {e_nse}")
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting data from single Flashscore element: {e}")
            return None

    async def cleanup(self):
        """Cleanup resources: close WebDriver if it exists."""
        self.logger.info("Cleaning up FlashscoreScraper resources...")
        if getattr(self, '_driver', None):
            self.logger.info("Quitting Flashscore WebDriver.")
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._driver.quit)
                self.logger.info("Flashscore WebDriver quit successfully.")
            except Exception as e:
                self.logger.error(f"Error quitting Flashscore WebDriver: {e}")
            finally:
                self._driver = None
        await super().cleanup()  # Call BaseScraper's cleanup for aiohttp session