"""Flashscore scraper implementation using Playwright."""

import re  # For more flexible text matching
from datetime import datetime, timezone
from typing import List, Optional

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
    ElementHandle
)

from .base import BaseScraper
from ..core.models import TennisMatch, Player, Score, ScrapingResult, TournamentLevel, Surface


# Logger is inherited from BaseScraper


class FlashscoreScraper(BaseScraper):
    """Scraper for Flashscore ITF tennis matches using Playwright."""

    FLASHCORE_BASE_URL = "https://www.flashscore.com"
    ITF_MEN_URL_PATH = "/tennis/itf-men-singles/"

    async def get_source_name(self) -> str:
        return "flashscore"

    async def is_available(self) -> bool:
        return await self._check_site_availability(self.FLASHCORE_BASE_URL, timeout=self.request_timeout)

    async def scrape_matches(self) -> ScrapingResult:
        start_time_dt = datetime.now(timezone.utc)
        matches_found: List[TennisMatch] = []
        processed_elements_count = 0  # To track how many elements were looked at
        error_message: Optional[str] = None
        success = False
        source_name = await self.get_source_name()

        bet365_indicator_fragment = self.config.get('flashscore_bet365_indicator_fragment')
        match_tie_break_keywords = self.config.get('flashscore_match_tie_break_keywords', [])
        headless_mode = self.config.get('headless_browser', True)
        user_agent = self.config.get('user_agent',
                                     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
        initial_load_delay_ms = self.config.get('flashscore_initial_load_delay', 7) * 1000
        element_timeout_ms = self.config.get('flashscore_element_timeout', 25) * 1000

        playwright = None
        browser = None
        context = None
        page = None

        if not bet365_indicator_fragment:
            self.logger.warning(
                "Flashscore: Bet365 indicator fragment is not configured. Cannot filter for Bet365 matches.")
            # Depending on requirements, you could either return all matches or an error/empty list.
            # For now, let's assume it should return no matches if the key config is missing.
            return ScrapingResult(
                source=source_name, matches=[], success=True,  # Success because scraper ran, but criteria not met
                error_message="Bet365 indicator fragment not configured.",
                duration_seconds=(datetime.now(timezone.utc) - start_time_dt).total_seconds(),
                timestamp=datetime.now(timezone.utc)
            )
        self.logger.info(
            f"Flashscore: Filtering for matches with Bet365 indicator fragment: '{bet365_indicator_fragment}'")

        try:
            self.logger.info(f"Initializing Playwright for Flashscore (Headless: {headless_mode})...")
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=headless_mode)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True,
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = await context.new_page()

            full_url = f"{self.FLASHCORE_BASE_URL}{self.ITF_MEN_URL_PATH}"
            self.logger.info(f"Navigating to Flashscore URL: {full_url}")
            await page.goto(full_url, wait_until="networkidle", timeout=element_timeout_ms * 2)

            try:
                self.logger.debug("Attempting to handle cookie consent...")
                cookie_button_selector = "#onetrust-accept-btn-handler"
                cookie_button = page.locator(cookie_button_selector)
                if await cookie_button.is_visible(timeout=5000):  # Reduced timeout
                    await cookie_button.click(timeout=3000)
                    self.logger.info("Cookie consent accepted.")
                    await page.wait_for_timeout(1000)
                else:
                    self.logger.info("Cookie consent dialog not visible or timed out.")
            except Exception as e_cookie:
                self.logger.warning(f"Could not click cookie button (or not found): {e_cookie}")

            self.logger.debug("Attempting to locate match containers...")
            primary_match_container_selector = "div.sportName.tennis div.event__match[id^='g_3_']"  # Keep as primary attempt
            fallback_match_container_selector = "div[class*='event__match']"  # The one that worked

            match_elements: List[ElementHandle] = []
            used_selector = ""

            try:
                self.logger.info(f"Trying primary match selector: {primary_match_container_selector}")
                await page.wait_for_selector(primary_match_container_selector, state="attached",
                                             timeout=element_timeout_ms / 2)
                match_elements = await page.query_selector_all(primary_match_container_selector)
                used_selector = primary_match_container_selector
                if match_elements: self.logger.info(f"Found {len(match_elements)} matches using primary selector.")
            except PlaywrightTimeoutError:
                self.logger.warning(
                    f"Primary match selector ('{primary_match_container_selector}') timed out or found no elements.")
                self.logger.info(f"Trying fallback match selector: {fallback_match_container_selector}")
                try:
                    await page.wait_for_selector(fallback_match_container_selector, state="attached",
                                                 timeout=element_timeout_ms / 2)
                    match_elements = await page.query_selector_all(fallback_match_container_selector)
                    used_selector = fallback_match_container_selector
                    if match_elements: self.logger.info(f"Found {len(match_elements)} matches using fallback selector.")
                except PlaywrightTimeoutError:
                    self.logger.error(
                        f"Fallback match selector ('{fallback_match_container_selector}') also timed out or found no elements.")
                    success = True
                    error_message = f"No match elements found using primary or fallback selectors."
                    return ScrapingResult(
                        source=source_name, matches=[], success=success, error_message=error_message,
                        duration_seconds=(datetime.now(timezone.utc) - start_time_dt).total_seconds(),
                        timestamp=datetime.now(timezone.utc)
                    )

            if not match_elements:
                self.logger.warning(f"No match elements found on Flashscore page. Used: '{used_selector}'")

            processed_elements_count = len(match_elements)
            self.logger.info(
                f"Processing {processed_elements_count} potential match elements using selector: '{used_selector}'")

            for element_index, sel_element in enumerate(match_elements):
                try:
                    home_player_name = await self._get_text_from_selectors(sel_element, [".event__participant--home",
                                                                                         "div[class*='homeParticipantName']"])
                    away_player_name = await self._get_text_from_selectors(sel_element, [".event__participant--away",
                                                                                         "div[class*='awayParticipantName']"])

                    if not home_player_name or not away_player_name:
                        self.logger.debug(
                            f"Skipping element {element_index} (selector: '{used_selector}') due to missing player names. Home: '{home_player_name}', Away: '{away_player_name}'.")
                        continue

                    # --- Bet365 Indicator Check FIRST ---
                    has_bet365_indicator = False
                    # Ensure bet365_indicator_fragment is not None or empty before checking
                    if bet365_indicator_fragment:
                        element_html = await sel_element.inner_html()
                        if bet365_indicator_fragment in element_html:
                            has_bet365_indicator = True

                    # --- IF NOT A BET365 MATCH, SKIP IT ---
                    if not has_bet365_indicator:
                        self.logger.debug(
                            f"Skipping match (idx {element_index}): {home_player_name} vs {away_player_name} - No Bet365 indicator.")
                        continue

                    self.logger.info(
                        f"Bet365 Indicator FOUND for: {home_player_name} vs {away_player_name}. Proceeding with full parse.")

                    # --- Continue parsing ONLY if it's a Bet365 match ---
                    home_s = await self._get_text_from_selectors(sel_element,
                                                                 [".event__score--home", "span[class*='home_score']"])
                    away_s = await self._get_text_from_selectors(sel_element,
                                                                 [".event__score--away", "span[class*='away_score']"])
                    score_str = f"{home_s}-{away_s}" if home_s and away_s else ""

                    status_text = await self._get_text_from_selectors(sel_element,
                                                                      [".event__stage", ".event__statusText",
                                                                       ".event__time"],
                                                                      default="Scheduled")

                    match_id_raw = await sel_element.get_attribute("id")
                    if not match_id_raw: match_id_raw = await sel_element.get_attribute("data-event-id")

                    if match_id_raw:
                        id_part_match = re.search(r'([a-zA-Z0-9_-]+)$',
                                                  match_id_raw)  # Allow underscore and hyphen in ID
                        id_part = id_part_match.group(1) if id_part_match else match_id_raw
                        match_id = f"flashscore_{id_part}"
                    else:
                        match_id = f"flashscore_idx_{element_index}_{home_player_name[:3]}_{away_player_name[:3]}"
                        self.logger.warning(
                            f"Could not find standard ID for match {home_player_name} vs {away_player_name}. Generated: {match_id}")

                    is_match_tie_break = False
                    if status_text and match_tie_break_keywords:
                        status_lower = status_text.lower()
                        for keyword in match_tie_break_keywords:
                            if keyword.lower() in status_lower:
                                is_match_tie_break = True
                                break

                    metadata_dict = {
                        'flashscore_raw_id': match_id_raw if match_id_raw else f"index_{element_index}",
                        'has_bet365_indicator': True,  # We know this is true if we reached here
                        'is_match_tie_break': is_match_tie_break
                    }

                    tournament_name_assumed = "ITF Men Singles"
                    tournament_level = self._determine_tournament_level_flashscore(tournament_name_assumed)

                    match_obj = TennisMatch(
                        home_player=Player(name=self._parse_player_name(home_player_name)),
                        away_player=Player(name=self._parse_player_name(away_player_name)),
                        score=Score.from_string(score_str),
                        status=self._parse_match_status(status_text, score_str),
                        tournament=tournament_name_assumed,
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
                    self.logger.info(
                        f"Successfully parsed Bet365 match: {home_player_name} vs {away_player_name} (ID: {match_id})")

                except Exception as e_extract:
                    self.logger.warning(
                        f"Failed to extract data for a Bet365 match element (idx {element_index}, selector: '{used_selector}'): {e_extract}",
                        exc_info=True)
            success = True

        except PlaywrightTimeoutError as e_timeout:
            self.logger.error(f"Playwright operation timed out for Flashscore: {e_timeout}")
            error_message = f"Playwright timeout: {str(e_timeout)}"
        except Exception as e:
            self.logger.error(f"Error scraping Flashscore with Playwright: {e}", exc_info=True)
            error_message = str(e)
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e_pc:
                    self.logger.warning(f"Err page close: {e_pc}")
            if context:
                try:
                    await context.close()
                except Exception as e_cc: self.logger.warning(f"Err context close: {e_cc}")
            if browser:
                try:
                    await browser.close()
                except Exception as e_bc: self.logger.warning(f"Err browser close: {e_bc}")
            if playwright:
                try:
                    await playwright.stop()
                except Exception as e_ps:
                    self.logger.warning(f"Err playwright stop: {e_ps}")
            self.logger.info("Playwright resources for Flashscore cleaned up.")

        duration = (datetime.now(timezone.utc) - start_time_dt).total_seconds()
        self.logger.info(
            f"Flashscore scraping finished. Processed {processed_elements_count} elements. Found {len(matches_found)} Bet365 matches. Success: {success}. Duration: {duration:.2f}s. Error: {error_message}")
        return ScrapingResult(
            source=source_name, matches=matches_found, success=success, error_message=error_message,
            duration_seconds=duration, timestamp=datetime.now(timezone.utc)
        )

    async def _get_text_from_selectors(self, parent_element: ElementHandle, selectors: List[str],
                                       default: str = "") -> str:
        for selector in selectors:
            try:
                element = await parent_element.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
            except Exception as e:
                self.logger.debug(f"Selector '{selector}' failed or returned no text: {e}")
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
