"""Flashscore scraper implementation using Playwright with robust LIVE tab clicking."""

import asyncio
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Page,
    BrowserContext,
    Browser,
    ElementHandle,
    Route
)

from .base import BaseScraper
from ..core.models import TennisMatch, Player, Score, MatchStatus, ScrapingResult, TournamentLevel, Surface


class FlashscoreLiveTabClicker:
    """Multiple strategies to reliably click the LIVE tab on Flashscore."""

    def __init__(self, page: Page, logger):
        self.page = page
        self.logger = logger

    async def click_live_tab(self) -> bool:
        """Try multiple strategies to click the LIVE tab."""

        strategies = [
            self._strategy_simple_text,
            self._strategy_contains_text,
            self._strategy_xpath_text,
            self._strategy_data_attributes,
            self._strategy_css_nth_child,
            self._strategy_javascript_click,
            self._strategy_force_click
        ]

        for i, strategy in enumerate(strategies, 1):
            self.logger.info(f"Trying LIVE tab strategy {i}/{len(strategies)}: {strategy.__name__}")

            try:
                success = await strategy()
                if success:
                    self.logger.info(f"✅ LIVE tab clicked successfully with {strategy.__name__}")
                    return True
                else:
                    self.logger.debug(f"❌ Strategy {strategy.__name__} failed")
            except Exception as e:
                self.logger.debug(f"❌ Strategy {strategy.__name__} threw exception: {e}")

        self.logger.error("🚨 ALL LIVE tab strategies failed!")
        return False

    async def _strategy_simple_text(self) -> bool:
        """Strategy 1: Simple text-based selection."""
        try:
            live_selectors = [
                "text=LIVE",
                "[data-testid*='live']",
                ".filters__text--short:text('LIVE')",
                "*:has-text('LIVE')"
            ]

            for selector in live_selectors:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=3000):
                    await element.click(timeout=5000)
                    await self.page.wait_for_timeout(2000)
                    return True

            return False
        except Exception:
            return False

    async def _strategy_contains_text(self) -> bool:
        """Strategy 2: Find elements containing LIVE text."""
        try:
            elements = await self.page.query_selector_all("*")

            for element in elements:
                try:
                    text_content = await element.text_content()
                    if text_content and "LIVE" in text_content.upper():
                        class_name = await element.get_attribute("class") or ""
                        if any(keyword in class_name.lower() for keyword in ["tab", "filter", "button"]):
                            await element.click(timeout=3000)
                            await self.page.wait_for_timeout(2000)
                            return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    async def _strategy_xpath_text(self) -> bool:
        """Strategy 3: XPath-based text search."""
        try:
            xpath_selectors = [
                "//div[contains(text(), 'LIVE')]",
                "//span[contains(text(), 'LIVE')]",
                "//button[contains(text(), 'LIVE')]",
                "//a[contains(text(), 'LIVE')]",
                "//*[contains(@class, 'filter') and contains(text(), 'LIVE')]",
                "//*[contains(@class, 'tab') and contains(text(), 'LIVE')]"
            ]

            for xpath in xpath_selectors:
                element = self.page.locator(f"xpath={xpath}").first
                if await element.is_visible(timeout=3000):
                    await element.click(timeout=5000)
                    await self.page.wait_for_timeout(2000)
                    return True

            return False
        except Exception:
            return False

    async def _strategy_data_attributes(self) -> bool:
        """Strategy 4: Look for data attributes."""
        try:
            data_selectors = [
                "[data-tab='live']",
                "[data-filter='live']",
                "[data-type='live']",
                "[data-status='live']",
                "[data-testid*='live' i]"
            ]

            for selector in data_selectors:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=3000):
                    await element.click(timeout=5000)
                    await self.page.wait_for_timeout(2000)
                    return True

            return False
        except Exception:
            return False

    async def _strategy_css_nth_child(self) -> bool:
        """Strategy 5: Try common filter positions."""
        try:
            position_selectors = [
                ".filters__tab:nth-child(2)",
                ".filters__tab:nth-child(3)",
                ".filter-item:nth-child(2)",
                ".tab-item:nth-child(2)",
                "[role='tab']:nth-child(2)"
            ]

            for selector in position_selectors:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=3000):
                    text = await element.text_content()
                    if text and "LIVE" in text.upper():
                        await element.click(timeout=5000)
                        await self.page.wait_for_timeout(2000)
                        return True

            return False
        except Exception:
            return False

    async def _strategy_javascript_click(self) -> bool:
        """Strategy 6: Use JavaScript to find and click."""
        try:
            js_code = """
            () => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT,
                    null,
                    false
                );

                let node;
                while (node = walker.nextNode()) {
                    if (node.textContent && node.textContent.includes('LIVE')) {
                        const classes = node.className || '';
                        if (classes.includes('tab') || classes.includes('filter') || 
                            classes.includes('button') || node.tagName === 'BUTTON') {
                            node.click();
                            return true;
                        }
                    }
                }
                return false;
            }
            """

            result = await self.page.evaluate(js_code)
            if result:
                await self.page.wait_for_timeout(2000)
                return True

            return False
        except Exception:
            return False

    async def _strategy_force_click(self) -> bool:
        """Strategy 7: Force click with multiple attempts."""
        try:
            all_elements = await self.page.query_selector_all("*")

            for element in all_elements:
                try:
                    text = await element.text_content()
                    if text and text.strip().upper() == "LIVE":
                        await element.click(force=True, timeout=2000)
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    async def verify_live_tab_clicked(self) -> bool:
        """Verify that the LIVE tab was actually clicked and is active."""
        try:
            indicators = [
                ".filters__tab.selected:has-text('LIVE')",
                ".tab.active:has-text('LIVE')",
                ".filter.active:has-text('LIVE')",
                "[aria-selected='true']:has-text('LIVE')"
            ]

            for indicator in indicators:
                if await self.page.locator(indicator).is_visible(timeout=3000):
                    self.logger.info(f"✅ LIVE tab verified as active: {indicator}")
                    return True

            current_url = self.page.url
            if "live" in current_url.lower():
                self.logger.info("✅ LIVE tab verified via URL change")
                return True

            self.logger.debug("⚠️ Could not verify LIVE tab is active")
            return False

        except Exception as e:
            self.logger.debug(f"⚠️ Error verifying LIVE tab: {e}")
            return False


class FlashscoreScraper(BaseScraper):
    """Scraper for Flashscore ITF tennis matches using Playwright."""

    FLASHCORE_BASE_URL = "https://www.flashscore.com"
    ITF_MEN_URL_PATH = "/tennis/itf-men-singles/"

    async def get_source_name(self) -> str:
        return "flashscore"

    async def is_available(self) -> bool:
        return await self._check_site_availability(self.FLASHCORE_BASE_URL, timeout=self.request_timeout)

    async def _route_handler(self, route: Route, block_types: List[str], block_names: List[str]):
        """Block unnecessary resources to speed up scraping."""
        resource_type = route.request.resource_type.lower()
        request_url_lower = route.request.url.lower()

        if resource_type in block_types:
            try:
                await route.abort()
                return
            except Exception:
                return

        for name_fragment in block_names:
            if name_fragment.lower() in request_url_lower:
                try:
                    await route.abort()
                    return
                except Exception:
                    return

        try:
            await route.continue_()
        except Exception:
            pass

    async def _click_live_tab_robust(self, page: Page) -> bool:
        """Robust method to click the LIVE tab on Flashscore."""

        self.logger.info("🎯 Starting robust LIVE tab clicking process...")

        try:
            # Wait for page to be fully loaded
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(2000)

            # Initialize the clicker
            clicker = FlashscoreLiveTabClicker(page, self.logger)

            # Try to click the LIVE tab
            success = await clicker.click_live_tab()

            if success:
                # Wait for the page to update after clicking
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.wait_for_timeout(3000)

                # Verify it worked
                verified = await clicker.verify_live_tab_clicked()
                if verified:
                    self.logger.info("🎉 LIVE tab successfully clicked and verified!")
                    return True
                else:
                    self.logger.warning("⚠️ LIVE tab clicked but verification failed - proceeding anyway")
                    return True
            else:
                self.logger.error("❌ Failed to click LIVE tab with all strategies")
                return False

        except PlaywrightTimeoutError as e:
            self.logger.error(f"⏰ Timeout during LIVE tab clicking: {e}")
            return False
        except Exception as e:
            self.logger.error(f"💥 Unexpected error during LIVE tab clicking: {e}")
            return False

    async def scrape_matches(self) -> ScrapingResult:
        start_time_dt = datetime.now(timezone.utc)
        matches_found: List[TennisMatch] = []
        processed_elements_count = 0
        error_message: Optional[str] = None
        success = False
        source_name = await self.get_source_name()

        # Get config values
        bet365_indicator_fragment = self.config.get('flashscore_bet365_indicator_fragment', '/549/')
        bookmaker_id_to_check = "".join(filter(str.isdigit, bet365_indicator_fragment))

        if not bookmaker_id_to_check:
            self.logger.error(
                f"Flashscore: Could not extract numeric bookmaker ID from fragment: '{bet365_indicator_fragment}'")
            return ScrapingResult(
                source=source_name,
                matches=[],
                success=False,
                error_message="Invalid Bet365 indicator fragment for ID extraction.",
                duration_seconds=(datetime.now(timezone.utc) - start_time_dt).total_seconds(),
                timestamp=datetime.now(timezone.utc)
            )

        self.logger.info(f"Flashscore: Filtering for matches with data-bookmaker-id='{bookmaker_id_to_check}'")

        match_tie_break_keywords = self.config.get('flashscore_match_tie_break_keywords', [])
        headless_mode = self.config.get('headless_browser', True)
        user_agent_new = self.config.get('user_agent',
                                         'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

        # Resources to block for faster loading
        block_resource_types = ["image", "stylesheet", "font", "media", "imageset"]
        block_resource_names = [
            "google-analytics.com", "googletagmanager.com", "scorecardresearch.com",
            "adservice.google.com", "doubleclick.net", "facebook.net", "twitter.com",
            "optimizely.com", "trackjs.com", "demdex.net", "omtrdc.net",
        ]

        element_timeout_ms = self.config.get('flashscore_element_timeout', 25) * 1000
        browser_launch_args = [
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
            '--ignore-certificate-errors', '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080'
        ]

        playwright = None
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            self.logger.info(f"Initializing Playwright for Flashscore (Headless: {headless_mode})...")
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=headless_mode, args=browser_launch_args)

            context = await browser.new_context(
                user_agent=user_agent_new,
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True,
                ignore_https_errors=True,
                bypass_csp=True
            )

            # Add stealth script
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Setup resource blocking
            await context.route("**/*",
                                lambda route: self._route_handler(route, block_resource_types, block_resource_names))
            self.logger.info("Resource blocking enabled.")

            page = await context.new_page()

            # Navigate to Flashscore ITF page
            full_url = f"{self.FLASHCORE_BASE_URL}{self.ITF_MEN_URL_PATH}"
            self.logger.info(f"Navigating to Flashscore URL: {full_url}")
            await page.goto(full_url, wait_until="networkidle", timeout=element_timeout_ms * 2)

            # Handle cookie consent
            try:
                self.logger.debug("Attempting to handle cookie consent...")
                cookie_btn_sel = "#onetrust-accept-btn-handler"
                cookie_button = page.locator(cookie_btn_sel)
                if await cookie_button.is_visible(timeout=5000):
                    await cookie_button.click(timeout=3000)
                    self.logger.info("Cookie consent accepted.")
                    await page.wait_for_timeout(1500)
                else:
                    self.logger.info("Cookie consent dialog not found or timed out.")
            except Exception as e_cookie:
                self.logger.warning(f"Cookie button interaction error: {e_cookie}")

            # Click the LIVE tab with robust method
            live_tab_success = await self._click_live_tab_robust(page)
            if not live_tab_success:
                self.logger.error("Failed to click LIVE tab - proceeding anyway but results may be limited")

            # Wait for matches to load
            self.logger.debug("Waiting for match containers...")
            match_container_selector = "div[class*='event__match']"
            match_elements: List[ElementHandle] = []

            try:
                await page.wait_for_selector(match_container_selector, state="attached", timeout=element_timeout_ms)
                match_elements = await page.query_selector_all(match_container_selector)
                self.logger.info(
                    f"Found {len(match_elements)} potential matches using selector: {match_container_selector}")
            except PlaywrightTimeoutError:
                self.logger.error(f"Match container selector ('{match_container_selector}') timed out")
                success = True  # Don't fail completely, just return empty results
                error_message = f"No match elements found using selector: {match_container_selector}"

            if not match_elements:
                self.logger.warning("No match elements found on page to process.")

            processed_elements_count = len(match_elements)

            # Process each match element
            for element_index, sel_element in enumerate(match_elements):
                try:
                    # Extract player names
                    home_player_name = await self._get_text_from_selectors(sel_element, [".event__participant--home"])
                    away_player_name = await self._get_text_from_selectors(sel_element, [".event__participant--away"])

                    if not home_player_name or not away_player_name:
                        continue

                    # Check for bet365 indicator
                    has_bet365_indicator = False
                    bet_indicator_selectors = [
                        f"div.liveBetWrapper[data-bookmaker-id='{bookmaker_id_to_check}']",
                        f"a[data-bookmaker-id='{bookmaker_id_to_check}']",
                        f".wcl-badgeLiveBet_1QP3r[data-bookmaker-id='{bookmaker_id_to_check}']"
                    ]

                    for selector in bet_indicator_selectors:
                        b365_element = await sel_element.query_selector(selector)
                        if b365_element:
                            has_bet365_indicator = True
                            break

                    if not has_bet365_indicator:
                        continue  # Skip matches without bet365 indicator

                    self.logger.info(f"Bet365 Match Found & Processing: {home_player_name} vs {away_player_name}")

                    # Extract match details
                    home_score = await self._get_text_from_selectors(sel_element, [".event__score--home"])
                    away_score = await self._get_text_from_selectors(sel_element, [".event__score--away"])
                    score_str = f"{home_score}-{away_score}" if home_score and away_score else ""

                    status_text = await self._get_text_from_selectors(sel_element,
                                                                      [".event__stage", ".event__time"],
                                                                      default="Scheduled")

                    # Extract match ID
                    match_id_raw = await sel_element.get_attribute("id")
                    id_part_from_raw = ""
                    if match_id_raw:
                        id_match = re.search(r'g_\d_([a-zA-Z0-9]+)', match_id_raw)
                        if id_match:
                            id_part_from_raw = id_match.group(1)
                        else:
                            id_part_match_generic = re.search(r'([a-zA-Z0-9_-]+)$', match_id_raw)
                            id_part_from_raw = id_part_match_generic.group(1) if id_part_match_generic else match_id_raw

                    if id_part_from_raw:
                        match_id = f"flashscore_{id_part_from_raw}"
                    else:
                        match_id = f"flashscore_idx_{element_index}_{home_player_name[:3]}_{away_player_name[:3]}"
                        self.logger.warning(
                            f"Using fallback ID for {home_player_name} vs {away_player_name}: {match_id}")

                    # Check for match tie break
                    is_match_tie_break = False
                    if status_text and match_tie_break_keywords:
                        status_lower = status_text.lower()
                        for keyword in match_tie_break_keywords:
                            if keyword.lower() in status_lower:
                                is_match_tie_break = True
                                break

                    # Create metadata
                    metadata_dict = {
                        'flashscore_raw_id': match_id_raw or f"index_{element_index}",
                        'has_bet365_indicator': True,
                        'is_match_tie_break': is_match_tie_break
                    }

                    # Create match object
                    tournament_name = "ITF Men Singles"
                    tournament_level = self._determine_tournament_level_flashscore(tournament_name)

                    match_obj = TennisMatch(
                        home_player=Player(name=self._parse_player_name(home_player_name)),
                        away_player=Player(name=self._parse_player_name(away_player_name)),
                        score=Score.from_string(score_str),
                        status=self._parse_match_status(status_text, score_str),
                        tournament=tournament_name,
                        tournament_level=tournament_level,
                        surface=Surface.UNKNOWN,
                        source=source_name,
                        source_url=page.url,
                        match_id=match_id,
                        scheduled_time=None,
                        last_updated=datetime.now(timezone.utc),
                        metadata=metadata_dict
                    )

                    matches_found.append(match_obj)

                except Exception as e_extract:
                    self.logger.warning(f"Extraction error for match (idx {element_index}): {e_extract}", exc_info=True)

            success = True
            if not error_message and not matches_found and processed_elements_count > 0:
                error_message = "Processed elements but no Bet365 matches met criteria after filtering."
            elif not error_message and not matches_found and processed_elements_count == 0:
                error_message = "No match elements found on the page to process."

        except PlaywrightTimeoutError as e_timeout:
            self.logger.error(f"Playwright operation timed out: {e_timeout}")
            error_message = f"Playwright timeout: {str(e_timeout)}"
            success = False
        except Exception as e:
            self.logger.error(f"Main scraping error: {e}", exc_info=True)
            error_message = str(e)
            success = False
        finally:
            # Cleanup Playwright resources
            if page:
                try:
                    await page.close()
                except Exception as e_pc:
                    self.logger.debug(f"Ignoring page close error: {e_pc}")
            if context:
                try:
                    await context.close()
                except Exception as e_cc:
                    self.logger.debug(f"Ignoring context close error: {e_cc}")
            if browser:
                try:
                    await browser.close()
                except Exception as e_bc:
                    self.logger.debug(f"Ignoring browser close error: {e_bc}")
            if playwright:
                try:
                    await playwright.stop()
                except Exception as e_ps:
                    self.logger.warning(f"Error stopping Playwright instance: {e_ps}")

            self.logger.info("Playwright resources for Flashscore cleaned up.")

        duration = (datetime.now(timezone.utc) - start_time_dt).total_seconds()
        self.logger.info(
            f"Flashscore: Processed {processed_elements_count} elements. "
            f"Found {len(matches_found)} Bet365 matches. "
            f"Success: {success}. Duration: {duration:.2f}s. "
            f"Error: {error_message or 'None'}"
        )

        return ScrapingResult(
            source=source_name,
            matches=matches_found,
            success=success,
            error_message=error_message,
            duration_seconds=duration,
            timestamp=datetime.now(timezone.utc),
            metadata={
                'processed_elements': processed_elements_count,
                'bet365_matches_found': len(matches_found),
                'tie_break_matches': len([m for m in matches_found if m.metadata.get('is_match_tie_break')])
            }
        )

    async def _get_text_from_selectors(self, parent_element: ElementHandle, selectors: List[str],
                                       default: str = "") -> str:
        """Extract text using multiple selectors as fallbacks."""
        for selector in selectors:
            try:
                element = await parent_element.query_selector(selector)
                if element:
                    text = await element.text_content()
                    return (text or default).strip()
            except Exception:
                pass
        return default

    def _determine_tournament_level_flashscore(self, tournament_name: str) -> TournamentLevel:
        """Determine tournament level from name."""
        name_lower = tournament_name.lower()
        if "itf men" in name_lower or "itf women" in name_lower:
            return TournamentLevel.ITF_25K
        if any(s in name_lower for s in ["m15", "w15", "15k"]):
            return TournamentLevel.ITF_15K
        if any(s in name_lower for s in ["m25", "w25", "25k"]):
            return TournamentLevel.ITF_25K
        if any(s in name_lower for s in ["m40", "w40", "40k"]):
            return TournamentLevel.ITF_40K
        if any(s in name_lower for s in ["m60", "w60", "60k"]):
            return TournamentLevel.ITF_60K
        if any(s in name_lower for s in ["m80", "w80", "80k"]):
            return TournamentLevel.ITF_80K
        if any(s in name_lower for s in ["m100", "w100", "100k"]):
            return TournamentLevel.ITF_100K
        return TournamentLevel.UNKNOWN

    async def cleanup(self):
        """Cleanup resources for FlashscoreScraper."""
        self.logger.info(f"Running cleanup for {await self.get_source_name()}...")
        await super().cleanup()