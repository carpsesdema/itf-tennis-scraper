"""Flashscore scraper implementation using Playwright, incorporating insights from previous project."""

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


# Logger is inherited from BaseScraper


class FlashscoreScraper(BaseScraper):
    """Scraper for Flashscore ITF tennis matches using Playwright."""

    FLASHCORE_BASE_URL = "https://www.flashscore.com"
    ITF_MEN_URL_PATH = "/tennis/itf-men-singles/"

    async def get_source_name(self) -> str:
        return "flashscore"

    async def is_available(self) -> bool:
        return await self._check_site_availability(self.FLASHCORE_BASE_URL, timeout=self.request_timeout)

    async def _route_handler(self, route: Route, block_types: List[str], block_names: List[str]):
        resource_type = route.request.resource_type.lower()
        request_url_lower = route.request.url.lower()
        if resource_type in block_types:
            try:
                await route.abort(); return
            except Exception:
                return
        for name_fragment in block_names:
            if name_fragment.lower() in request_url_lower:
                try:
                    await route.abort(); return
                except Exception:
                    return
        try:
            await route.continue_()
        except Exception:
            pass  # Ignore errors on continue, e.g., if navigation interrupted

    async def scrape_matches(self) -> ScrapingResult:
        start_time_dt = datetime.now(timezone.utc)
        matches_found: List[TennisMatch] = []
        processed_elements_count = 0
        error_message: Optional[str] = None
        success = False
        source_name = await self.get_source_name()

        bet365_indicator_fragment = self.config.get('flashscore_bet365_indicator_fragment', '/549/')
        bookmaker_id_to_check = "".join(filter(str.isdigit, bet365_indicator_fragment))

        if not bookmaker_id_to_check:
            self.logger.error(
                f"Flashscore: Could not extract a numeric bookmaker ID from fragment: '{bet365_indicator_fragment}'. Cannot reliably find Bet365 matches.")
            return ScrapingResult(source=source_name, matches=[], success=False,
                                  error_message="Invalid Bet365 indicator fragment for ID extraction.",
                                  duration_seconds=(datetime.now(timezone.utc) - start_time_dt).total_seconds(),
                                  timestamp=datetime.now(timezone.utc))
        self.logger.info(f"Flashscore: Filtering for matches with data-bookmaker-id='{bookmaker_id_to_check}'")

        match_tie_break_keywords = self.config.get('flashscore_match_tie_break_keywords', [])
        headless_mode = self.config.get('headless_browser', True)
        user_agent_new = self.config.get('user_agent',
                                         'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        block_resource_types_old = ["image", "stylesheet", "font", "media", "imageset"]
        block_resource_names_old = [
            "google-analytics.com", "googletagmanager.com", "scorecardresearch.com",
            "adservice.google.com", "doubleclick.net", "facebook.net", "twitter.com",
            "optimizely.com", "trackjs.com", "demdex.net", "omtrdc.net",
        ]
        element_timeout_ms = self.config.get('flashscore_element_timeout', 25) * 1000
        browser_launch_args = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
                               '--ignore-certificate-errors', '--disable-blink-features=AutomationControlled',
                               '--window-size=1920,1080']

        playwright = None  # Initialize for the finally block
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            self.logger.info(f"Initializing Playwright for Flashscore (Headless: {headless_mode})...")
            playwright = await async_playwright().start()  # Assign to the variable
            browser = await playwright.chromium.launch(headless=headless_mode, args=browser_launch_args)
            context = await browser.new_context(user_agent=user_agent_new, viewport={'width': 1920, 'height': 1080},
                                                java_script_enabled=True, ignore_https_errors=True, bypass_csp=True)
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            await context.route("**/*", lambda route: self._route_handler(route, block_resource_types_old,
                                                                          block_resource_names_old))
            self.logger.info("Resource blocking enabled.")
            page = await context.new_page()

            full_url = f"{self.FLASHCORE_BASE_URL}{self.ITF_MEN_URL_PATH}"
            self.logger.info(f"Navigating to Flashscore URL: {full_url}")
            await page.goto(full_url, wait_until="networkidle", timeout=element_timeout_ms * 2)

            try:
                self.logger.debug("Attempting to handle cookie consent...")
                cookie_btn_sel = "#onetrust-accept-btn-handler"
                cookie_button = page.locator(cookie_btn_sel)
                if await cookie_button.is_visible(timeout=5000):  # Quick check
                    await cookie_button.click(timeout=3000)
                    self.logger.info("Cookie consent accepted.")
                    await page.wait_for_timeout(1500)
                else:
                    self.logger.info("Cookie consent dialog not visible or timed out.")
            except Exception as e_cookie:
                self.logger.warning(f"Cookie button interaction error: {e_cookie}")

            # --- CLICK THE "LIVE" TAB (Using highly specific locator from provided HTML) ---
            try:
                self.logger.info("Attempting to click the 'LIVE' tab/filter...")
                # This locator targets the div.filters__tab that is NOT selected AND has the specific child text.
                live_tab_locator_str = "div.filters__group > div.filters__tab:not(.selected):has(div.filters__text--short:text-is('LIVE'))"
                # As an alternative, we can also try locating the inner text div and clicking its parent if the above is too complex or fails
                # live_tab_locator_alt_click_target = page.locator("div.filters__text--short:text-is('LIVE')").locator("xpath=ancestor::div[contains(@class, 'filters__tab')][1]")

                self.logger.debug(f"Using LIVE tab locator: \"{live_tab_locator_str}\"")
                live_tab_element = page.locator(live_tab_locator_str)

                if await live_tab_element.is_visible(timeout=10000):  # Increased visibility timeout
                    await live_tab_element.click(timeout=7000)
                    self.logger.info("'LIVE' tab clicked successfully.")
                    await page.wait_for_load_state("networkidle", timeout=20000)  # Increased wait after click
                    await page.wait_for_timeout(3000)
                else:
                    self.logger.error(
                        f"LIVE tab not found or not visible with locator: '{live_tab_locator_str}'. Proceeding with current page view. THIS IS LIKELY TO FAIL B365 MATCH FINDING.")
            except PlaywrightTimeoutError:
                self.logger.error("'LIVE' tab click or subsequent wait timed out. Proceeding with current view.")
            except Exception as e_live_tab:
                self.logger.error(f"Error clicking 'LIVE' tab: {e_live_tab}. Proceeding with current view.")
            # --- END CLICK "LIVE" TAB ---

            self.logger.debug("Attempting to locate match containers...")
            match_container_selector = "div[class*='event__match']"  # This worked previously
            match_elements: List[ElementHandle] = []
            try:
                await page.wait_for_selector(match_container_selector, state="attached", timeout=element_timeout_ms)
                match_elements = await page.query_selector_all(match_container_selector)
                self.logger.info(
                    f"Found {len(match_elements)} potential matches using selector: {match_container_selector}")
            except PlaywrightTimeoutError:
                self.logger.error(
                    f"Match container selector ('{match_container_selector}') timed out even after LIVE tab attempt.")
                success = True
                error_message = f"No match elements found using selector: {match_container_selector}"
                # No early return, let finally handle cleanup

            if not match_elements: self.logger.warning("No match elements found on page to process.")
            processed_elements_count = len(match_elements)

            for element_index, sel_element in enumerate(match_elements):
                try:
                    home_player_name = await self._get_text_from_selectors(sel_element, [".event__participant--home"])
                    away_player_name = await self._get_text_from_selectors(sel_element, [".event__participant--away"])

                    if not home_player_name or not away_player_name: continue

                    has_bet365_indicator = False
                    bet_indicator_selector_attr = f"div.liveBetWrapper[data-bookmaker-id='{bookmaker_id_to_check}'], a[data-bookmaker-id='{bookmaker_id_to_check}']"
                    bet_indicator_selector_alt = f".wcl-badgeLiveBet_1QP3r[data-bookmaker-id='{bookmaker_id_to_check}']"

                    b365_element = await sel_element.query_selector(bet_indicator_selector_attr)
                    if not b365_element:
                        b365_element = await sel_element.query_selector(bet_indicator_selector_alt)

                    if b365_element:
                        # self.logger.debug(f"MatchIdx {element_index}: B365 attribute element found. Checking visibility...")
                        # if await b365_element.is_visible(timeout=1000): # Quick check if it's actually visible
                        has_bet365_indicator = True
                        # self.logger.info(f"MatchIdx {element_index} ({home_player_name} vs {away_player_name}): Bet365 Indicator TRUE (found element with data-bookmaker-id='{bookmaker_id_to_check}')")
                        # else:
                        # self.logger.debug(f"MatchIdx {element_index}: B365 attribute element found but NOT VISIBLE.")

                    if not has_bet365_indicator:
                        continue  # Skip to next match if no B365 indicator

                    self.logger.info(f"Bet365 Match Found & Processing: {home_player_name} vs {away_player_name}")

                    home_s = await self._get_text_from_selectors(sel_element, [".event__score--home"])
                    away_s = await self._get_text_from_selectors(sel_element, [".event__score--away"])
                    score_str = f"{home_s}-{away_s}" if home_s and away_s else ""
                    status_text = await self._get_text_from_selectors(sel_element, [".event__stage", ".event__time"],
                                                                      default="Scheduled")
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

                    is_match_tie_break = False
                    if status_text and match_tie_break_keywords:
                        status_lower = status_text.lower()
                        for keyword in match_tie_break_keywords:
                            if keyword.lower() in status_lower: is_match_tie_break = True; break

                    metadata_dict = {'flashscore_raw_id': match_id_raw or f"index_{element_index}",
                                     'has_bet365_indicator': True, 'is_match_tie_break': is_match_tie_break}
                    tournament_name_assumed = "ITF Men Singles"
                    tournament_level = self._determine_tournament_level_flashscore(tournament_name_assumed)

                    match_obj = TennisMatch(
                        home_player=Player(name=self._parse_player_name(home_player_name)),
                        away_player=Player(name=self._parse_player_name(away_player_name)),
                        score=Score.from_string(score_str), status=self._parse_match_status(status_text, score_str),
                        tournament=tournament_name_assumed, tournament_level=tournament_level, surface=Surface.UNKNOWN,
                        source=source_name, source_url=page.url, match_id=match_id, scheduled_time=None,
                        last_updated=datetime.now(timezone.utc), metadata=metadata_dict)
                    matches_found.append(match_obj)
                except Exception as e_extract:
                    self.logger.warning(f"Extraction error for one Bet365 match (idx {element_index}): {e_extract}",
                                        exc_info=True)

            success = True
            if not error_message and not matches_found and processed_elements_count > 0:
                error_message = "Processed elements but no Bet365 matches met criteria after filtering."
            elif not error_message and not matches_found and processed_elements_count == 0 and (
                    not page or not page.is_closed()):
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
            if page:
                try:
                    await page.close()
                except Exception as e_pc: self.logger.debug(f"Ignoring page close error: {e_pc}")
            if context:
                try:
                    await context.close()
                except Exception as e_cc: self.logger.debug(f"Ignoring context close error: {e_cc}")
            if browser:
                try:
                    await browser.close()
                except Exception as e_bc: self.logger.debug(f"Ignoring browser close error: {e_bc}")
            if playwright:
                try:
                    await playwright.stop()
                except Exception as e_ps: self.logger.warning(f"Error stopping Playwright instance: {e_ps}")
            self.logger.info("Playwright resources for Flashscore cleaned up.")

        duration = (datetime.now(timezone.utc) - start_time_dt).total_seconds()
        self.logger.info(
            f"Flashscore: Processed {processed_elements_count} elements. Found {len(matches_found)} Bet365 matches. Success: {success}. Duration: {duration:.2f}s. Error: {error_message or 'None'}")
        return ScrapingResult(source=source_name, matches=matches_found, success=success, error_message=error_message,
                              duration_seconds=duration, timestamp=datetime.now(timezone.utc))

    async def _get_text_from_selectors(self, parent_element: ElementHandle, selectors: List[str],
                                       default: str = "") -> str:
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
        name_lower = tournament_name.lower()
        if "itf men" in name_lower or "itf women" in name_lower: return TournamentLevel.ITF_25K
        if any(s in name_lower for s in ["m15", "w15", "15k"]): return TournamentLevel.ITF_15K
        if any(s in name_lower for s in ["m25", "w25", "25k"]): return TournamentLevel.ITF_25K
        if any(s in name_lower for s in ["m40", "w40", "40k"]): return TournamentLevel.ITF_40K
        if any(s in name_lower for s in ["m60", "w60", "60k"]): return TournamentLevel.ITF_60K
        if any(s in name_lower for s in ["m80", "w80", "80k"]): return TournamentLevel.ITF_80K
        if any(s in name_lower for s in ["m100", "w100", "100k"]): return TournamentLevel.ITF_100K
        return TournamentLevel.UNKNOWN

    async def cleanup(self):
        self.logger.info(f"Running cleanup for {await self.get_source_name()}...")
        await super().cleanup()