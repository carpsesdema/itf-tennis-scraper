import asyncio
import re
from typing import List, Optional, Dict, Any, Callable, Awaitable
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
    def __init__(self, page: Page, logger):
        self.page = page
        self.logger = logger

    async def click_live_tab(self) -> bool:
        strategies = [
            self._strategy_simple_text,
            self._strategy_javascript_click,
            self._strategy_force_click
        ]
        for i, strategy in enumerate(strategies, 1):
            self.logger.info(f"Trying LIVE tab strategy {i}/{len(strategies)}")
            try:
                success = await strategy()
                if success:
                    self.logger.info(f"✅ LIVE tab clicked successfully using strategy {i}")
                    await self.page.wait_for_timeout(5000)
                    return True
            except Exception as e:
                self.logger.debug(f"Strategy {i} failed: {e}")
        self.logger.error("🚨 All LIVE tab strategies failed.")
        return False

    async def _strategy_simple_text(self) -> bool:
        try:
            live_selectors = [
                "div.filters__tab *:has-text('LIVE')",
                "button.filters__tab *:has-text('LIVE')",
                "a.filters__tab *:has-text('LIVE')",
                ".filters__tab >> text=LIVE",
                "text=LIVE Games"
            ]
            for selector in live_selectors:
                self.logger.debug(f"Trying LIVE tab selector: {selector}")
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=3000):
                    if await element.is_enabled(timeout=1000):
                        await element.click(timeout=5000, force=True)
                        return True
            return False
        except Exception as e:
            self.logger.debug(f"Simple text strategy error: {e}")
            return False

    async def _strategy_javascript_click(self) -> bool:
        try:
            self.logger.debug("Trying JS click for LIVE tab")
            js_code = """
            () => {
                const keywords = ['LIVE', 'Live Games'];
                const elements = Array.from(document.querySelectorAll('button, a, div, span'));
                for (const el of elements) {
                    if (el.textContent && keywords.some(kw => el.textContent.trim().toUpperCase().includes(kw.toUpperCase()))) {
                        const classes = (el.className || '').toString().toLowerCase();
                        if ((classes.includes('tab') || classes.includes('filter') || classes.includes('filters__text')) && el.offsetParent !== null) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                el.click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            }
            """
            result = await self.page.evaluate(js_code)
            return bool(result)
        except Exception as e:
            self.logger.debug(f"JS click strategy error: {e}")
            return False

    async def _strategy_force_click(self) -> bool:
        try:
            self.logger.debug("Trying force click for LIVE tab")
            candidate_selectors = "button.filters__tab, a.filters__tab, div.filters__tab, div.tabs__tab"
            all_elements = await self.page.query_selector_all(candidate_selectors)

            if not all_elements:
                all_elements = await self.page.query_selector_all("button, a, div")

            for element in all_elements[:70]:
                try:
                    text_content = await element.text_content()
                    if text_content and "LIVE" in text_content.strip().upper():
                        tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                        class_name = await element.evaluate('el => el.className.toLowerCase()')
                        if tag_name in ['button', 'a'] or 'tab' in class_name or 'filter' in class_name:
                            await element.click(force=True, timeout=3000)
                            return True
                except Exception:
                    continue
            return False
        except Exception as e:
            self.logger.debug(f"Force click strategy error: {e}")
            return False


class FlashscoreScraper(BaseScraper):
    FLASHCORE_BASE_URL = "https://www.flashscoreusa.com"
    TENNIS_URL_PATH = "/tennis/"
    MAX_MATCHES_TO_PROCESS = 30
    MAX_ELEMENTS_TO_CHECK = 500
    SIMPLIFIED_TIE_BREAK_CHECK = True

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
        aggressive_blocks = ['analytics', 'ads', 'tracking', 'facebook', 'twitter', 'social', 'video', 'youtube',
                             'vimeo', 'advertisement', 'banner']
        for block_term in aggressive_blocks:
            if block_term in request_url_lower:
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
            pass

    async def _simplified_tie_break_detection(self, status_text: str, score_str: str,
                                              home_player_name: str, away_player_name: str) -> tuple[bool, str]:
        simple_keywords = ["match tie break", "match tie-break", "super tiebreak", "first to 10", "tie break"]
        if status_text:
            status_lower = status_text.lower()
            for keyword in simple_keywords:
                if keyword in status_lower:
                    self.logger.critical(
                        f"🚨 TIE BREAK (status): {home_player_name} vs {away_player_name} by status: '{keyword}'")
                    return True, f"status_{keyword.replace(' ', '_')}"
        if score_str and '[' in score_str and ']' in score_str:
            bracket_match = re.search(r'\[(\d+)-(\d+)\]', score_str)
            if bracket_match:
                home_tb, away_tb = int(bracket_match.group(1)), int(bracket_match.group(2))
                if (home_tb >= 7 or away_tb >= 7) and abs(home_tb - away_tb) >= 0:
                    self.logger.critical(
                        f"🚨 TIE BREAK (score): {home_player_name} vs {away_player_name} by score: [{home_tb}-{away_tb}]")
                    return True, f"score_bracket_{home_tb}_{away_tb}"
        if "tie" in status_text.lower() and "break" in status_text.lower():
            self.logger.critical(
                f"🚨 TIE BREAK (generic status): {home_player_name} vs {away_player_name} by status: '{status_text}'")
            return True, "status_generic_tie_break"
        return False, "none"

    async def _process_match_from_live_tab(self, match_element: ElementHandle, current_tournament_name: str,
                                           element_index: int, bookmaker_id_to_check: str, page_url: str) -> Optional[
        TennisMatch]:
        home_player_name = "N/A"
        away_player_name = "N/A"
        try:
            home_player_name = await self._get_text_from_element(match_element, ".event__participant--home")
            away_player_name = await self._get_text_from_element(match_element, ".event__participant--away")

            if not home_player_name or not away_player_name:
                self.logger.info(
                    f"Live Idx {element_index}: Skipping match in '{current_tournament_name}' (Players: {home_player_name}/{away_player_name}) due to missing player names.")
                return None

            home_score = await self._get_text_from_element(match_element, ".event__score--home")
            away_score = await self._get_text_from_element(match_element, ".event__score--away")
            score_str = f"{home_score}-{away_score}" if home_score is not None and away_score is not None else ""

            status_text_from_attr = ""
            status_element_on_score = await match_element.query_selector(".event__score[data-state]")
            if status_element_on_score:
                status_text_from_attr = (
                            await status_element_on_score.get_attribute("data-state") or "").strip().lower()

            status_text_from_stage_block = await self._get_text_from_element(match_element, ".event__stage--block",
                                                                             default="")
            if not status_text_from_stage_block:
                status_text_from_stage_block = await self._get_text_from_element(match_element, ".event__stage",
                                                                                 default="")
            final_status_text = status_text_from_attr if status_text_from_attr else status_text_from_stage_block

            is_match_tie_break, detection_method = await self._simplified_tie_break_detection(
                final_status_text, score_str, home_player_name, away_player_name
            )

            has_bet365_indicator = False
            self.logger.info(
                f"Live Idx {element_index} ({home_player_name} vs {away_player_name}) in '{current_tournament_name}': Checking for Bet365 ID '{bookmaker_id_to_check}'...")
            try:
                bet_wrappers = await match_element.query_selector_all("div.liveBetWrapper, [class*='liveBetWrapper']")
                if not bet_wrappers:
                    self.logger.info(f"Live Idx {element_index}: No .liveBetWrapper elements found.")
                else:
                    self.logger.info(
                        f"Live Idx {element_index}: Found {len(bet_wrappers)} liveBetWrapper-like elements.")
                    for i, wrapper in enumerate(bet_wrappers):
                        bookmaker_id_attr = await wrapper.get_attribute("data-bookmaker-id")
                        self.logger.info(
                            f"Live Idx {element_index}: Wrapper {i} data-bookmaker-id: '{bookmaker_id_attr}'")
                        if bookmaker_id_attr == bookmaker_id_to_check:
                            has_bet365_indicator = True
                            self.logger.info(
                                f"Live Idx {element_index}: Bet365 ID '{bookmaker_id_to_check}' FOUND in wrapper.")
                            break
                    if not has_bet365_indicator:
                        self.logger.info(
                            f"Live Idx {element_index}: Bet365 ID '{bookmaker_id_to_check}' NOT found in any wrapper's data-bookmaker-id.")

                if not has_bet365_indicator:
                    self.logger.info(
                        f"Live Idx {element_index}: Bet365 ID not in wrappers. Falling back to inner HTML check for '{bookmaker_id_to_check}' or 'bet365'.")
                    element_html = await match_element.inner_html()
                    if bookmaker_id_to_check in element_html or '549' in element_html or 'bet365' in element_html.lower():
                        has_bet365_indicator = True
                        self.logger.info(f"Live Idx {element_index}: Bet365 indicator FOUND in inner HTML.")
                    else:
                        self.logger.info(f"Live Idx {element_index}: Bet365 indicator NOT found in inner HTML.")
            except Exception as e_bet:
                self.logger.error(f"Live Idx {element_index}: Error during Bet365 check: {e_bet}", exc_info=True)

            if not has_bet365_indicator:
                self.logger.info(
                    f"Live Idx {element_index} ({home_player_name} vs {away_player_name}) in '{current_tournament_name}' does NOT have Bet365 ID '{bookmaker_id_to_check}'. Skipping.")
                return None
            else:
                self.logger.info(
                    f"Live Idx {element_index} ({home_player_name} vs {away_player_name}) in '{current_tournament_name}' HAS Bet365 indicator. Proceeding.")

            match_id_from_link = await match_element.get_attribute("aria-describedby")
            match_id_from_id_attr = await match_element.get_attribute("id")
            match_id = match_id_from_link or match_id_from_id_attr or f"flashscore_itf_{element_index}_{hash(home_player_name + away_player_name) % 10000}"
            if match_id.startswith("g_2_"):
                match_id = match_id[4:]

            metadata_dict = {
                'has_bet365_indicator': has_bet365_indicator,
                'is_match_tie_break': is_match_tie_break,
                'tie_break_detection_method': detection_method,
                'element_index': element_index,
                'tournament_name_header': current_tournament_name,
                'is_itf_match': True
            }

            source_name = await self.get_source_name()
            parsed_status = self._parse_match_status(final_status_text, score_str)

            match_obj = TennisMatch(
                home_player=Player(name=self._parse_player_name(home_player_name)),
                away_player=Player(name=self._parse_player_name(away_player_name)),
                score=Score.from_string(score_str),
                status=parsed_status,
                tournament=current_tournament_name,
                tournament_level=self._determine_tournament_level_flashscore(current_tournament_name),
                surface=self._determine_surface_from_name(current_tournament_name),
                source=source_name,
                source_url=page_url,
                match_id=match_id,
                scheduled_time=None,
                last_updated=datetime.now(timezone.utc),
                metadata=metadata_dict
            )
            return match_obj
        except Exception as e:
            self.logger.error(
                f"Error processing live match element {element_index} (Tourney: '{current_tournament_name}', Players: {home_player_name}v{away_player_name}): {e}",
                exc_info=True)
            return None

    def _determine_tournament_level_flashscore(self, tournament_name: str) -> TournamentLevel:
        if not tournament_name: return TournamentLevel.UNKNOWN
        name_lower = tournament_name.lower()
        if any(s in name_lower for s in ["m15", "w15", "15k"]): return TournamentLevel.ITF_15K
        if any(s in name_lower for s in ["m25", "w25", "25k"]): return TournamentLevel.ITF_25K
        if any(s in name_lower for s in ["m40", "w40", "40k"]): return TournamentLevel.ITF_40K
        if any(s in name_lower for s in ["m60", "w60", "60k"]): return TournamentLevel.ITF_60K
        if any(s in name_lower for s in ["m80", "w80", "80k"]): return TournamentLevel.ITF_80K
        if any(s in name_lower for s in ["m100", "w100", "100k"]): return TournamentLevel.ITF_100K
        if "itf men" in name_lower or "itf women" in name_lower or "itf" in name_lower:  # General ITF check
            if "men" in name_lower and "singles" in name_lower: return TournamentLevel.ITF_25K  # Default for ITF Men Singles
            # Could add more specific defaults for ITF Women or Doubles if needed
            return TournamentLevel.ITF_25K
        return TournamentLevel.UNKNOWN

    def _determine_surface_from_name(self, tournament_name: str) -> Surface:
        if not tournament_name: return Surface.UNKNOWN
        name_lower = tournament_name.lower()
        if "hard" in name_lower:
            return Surface.INDOOR_HARD if "indoor" in name_lower else Surface.HARD
        if "clay" in name_lower:
            return Surface.INDOOR_CLAY if "indoor" in name_lower else Surface.CLAY
        if "grass" in name_lower: return Surface.GRASS
        if "carpet" in name_lower: return Surface.CARPET
        return Surface.UNKNOWN

    async def _get_text_from_element(self, parent_element: ElementHandle, selector: str, default: str = "") -> str:
        try:
            element = await parent_element.query_selector(selector)
            if element:
                text = await element.text_content()
                if text is not None and text.strip():
                    return text.strip()
        except Exception as e:
            self.logger.debug(f"Could not get text for selector '{selector}' within parent: {e}")
        return default

    async def scrape_matches(self, progress_callback: Optional[
        Callable[[TennisMatch], Awaitable[None]]] = None) -> ScrapingResult:
        start_time_dt = datetime.now(timezone.utc)
        matches_found: List[TennisMatch] = []
        error_message: Optional[str] = None
        success = False
        source_name = await self.get_source_name()
        current_page_url = ""
        live_tab_successfully_clicked_flag = False

        bet365_indicator_fragment = self.config.get('flashscore_bet365_indicator_fragment', '/549/')
        bookmaker_id_to_check = "".join(filter(str.isdigit, bet365_indicator_fragment))
        if not bookmaker_id_to_check: bookmaker_id_to_check = "549"

        self.logger.info(
            f"🎯 ITF MEN-SINGLES SCRAPING (LIVE TAB STRATEGY) - Max {self.MAX_MATCHES_TO_PROCESS} matches. Bet365 ID: {bookmaker_id_to_check}")

        headless_mode = True
        user_agent_new = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        block_resource_types = ["image", "font", "media", "imageset", "websocket", "other"]
        block_resource_names = ["google-analytics.com", "googletagmanager.com", "facebook.com", "twitter.com",
                                "doubleclick", "adsystem"]
        element_timeout_ms = 45000

        playwright = None
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        processed_elements_count = 0
        total_elements_on_page = 0
        all_page_elements_list: List[ElementHandle] = []

        try:
            self.logger.info("🚀 Starting Playwright...")
            playwright = await async_playwright().start()
            browser_args = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                            '--disable-features=VizDisplayCompositor']
            browser = await playwright.chromium.launch(headless=headless_mode, args=browser_args)
            context = await browser.new_context(
                user_agent=user_agent_new, viewport={'width': 1366, 'height': 768},
                java_script_enabled=True, ignore_https_errors=True
            )
            await context.route("**/*",
                                lambda route: self._route_handler(route, block_resource_types, block_resource_names))
            page = await context.new_page()
            current_page_url = f"{self.FLASHCORE_BASE_URL}{self.TENNIS_URL_PATH}"
            self.logger.info(f"📍 Navigating to: {current_page_url}")
            await page.goto(current_page_url, wait_until="domcontentloaded", timeout=element_timeout_ms)

            try:
                cookie_btn_selectors = ["#onetrust-accept-btn-handler", "button:has-text('Accept All')"]
                for sel in cookie_btn_selectors:
                    cookie_btn = page.locator(sel).first
                    if await cookie_btn.is_visible(timeout=8000):
                        await cookie_btn.click(timeout=5000)
                        await page.wait_for_timeout(2000)
                        self.logger.info("Cookie banner accepted.")
                        break
            except Exception:
                self.logger.debug("Cookie handling skipped or failed.")

            live_tab_clicker = FlashscoreLiveTabClicker(page, self.logger)
            live_tab_successfully_clicked_flag = await live_tab_clicker.click_live_tab()

            if not live_tab_successfully_clicked_flag:
                self.logger.warning(
                    "⚠️ Failed to click LIVE tab. Scraping current page. Results might be limited or incorrect.")
            else:
                self.logger.info("✅ Successfully clicked LIVE tab. Waiting for content to fully load...")
                await page.wait_for_timeout(8000)

            current_page_url = page.url

            self.logger.info("📜 Scrolling down on current tab to load all matches...")
            for i in range(10):
                await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                self.logger.debug(f"Scroll attempt {i + 1}")
                await page.wait_for_timeout(1500)

            all_elements_selector = "div.wcl-header_uBhYi.wclLeagueHeader, a.eventRowLink, div.event__match, div.event__match--scheduled, div.event__match--live, div.event__match--static"
            all_page_elements_list = await page.query_selector_all(all_elements_selector)
            total_elements_on_page = len(all_page_elements_list)
            self.logger.info(
                f"Found {total_elements_on_page} potential header/match elements on the page using selector: '{all_elements_selector}'.")

            itf_bet365_matches_count = 0
            current_processing_tournament_context = "Unknown Tournament (Context Not Set)"
            is_context_itf_men_singles = False

            elements_to_iterate = all_page_elements_list[:self.MAX_ELEMENTS_TO_CHECK]
            processed_elements_count = len(elements_to_iterate)
            self.logger.info(
                f"Will process up to {processed_elements_count} elements (limited by MAX_ELEMENTS_TO_CHECK: {self.MAX_ELEMENTS_TO_CHECK}).")

            for idx, element in enumerate(elements_to_iterate):
                if itf_bet365_matches_count >= self.MAX_MATCHES_TO_PROCESS:
                    self.logger.info(f"Reached ITF MEN-SINGLES match limit ({self.MAX_MATCHES_TO_PROCESS}). Stopping.")
                    break

                element_classes = (await element.get_attribute("class") or "").lower()
                # Check if the element is a tournament header using the specific classes you found
                is_tournament_header_element = "wclleagueheader" in element_classes and "wcl-header_ubhyi" in element_classes

                if is_tournament_header_element:
                    title_box_el = await element.query_selector("div.event__titleBox")
                    extracted_full_tournament_name = ""
                    if title_box_el:
                        part1_el = await title_box_el.query_selector("span.wcl-overline_rOFfd")
                        part2_el = await title_box_el.query_selector("a.wcl-link_bLtj3")
                        part1_text = (await part1_el.text_content() or "").strip() if part1_el else ""
                        part2_text = (await part2_el.text_content() or "").strip() if part2_el else ""
                        if part1_text and part2_text:
                            extracted_full_tournament_name = f"{part1_text}: {part2_text}"
                        elif part1_text:
                            extracted_full_tournament_name = part1_text
                        elif part2_text:
                            extracted_full_tournament_name = part2_text

                    self.logger.info(
                        f"Element {idx} IS a Tournament Header. Extracted Name: '{extracted_full_tournament_name}'")
                    current_processing_tournament_context = extracted_full_tournament_name  # Update context with the new header

                    name_lower = current_processing_tournament_context.lower()
                    # Explicitly check for "ITF", "MEN", and "SINGLES"
                    if "itf" in name_lower and "men" in name_lower and "singles" in name_lower:
                        is_context_itf_men_singles = True
                        self.logger.info(
                            f"--- Context Updated: Now processing matches under ITF MEN - SINGLES Tournament: '{current_processing_tournament_context}' ---")
                    else:
                        is_context_itf_men_singles = False  # Reset if not ITF Men Singles
                        self.logger.info(
                            f"--- Context Updated: Header is NOT ITF MEN - SINGLES: '{current_processing_tournament_context}' (Setting ITF Men Singles Context to False) ---")
                    continue  # This element was a header, move to the next element in the main loop

                # If the element was not a header, then it might be a match row.
                # Only process it if the current context is an ITF MEN - SINGLES tournament.
                if is_context_itf_men_singles:
                    # Check if the element looks like a match row (e.g., contains participant info)
                    # This helps to avoid trying to process non-match elements that might be siblings to headers
                    home_participant_el = await element.query_selector(".event__participant--home")
                    if home_participant_el:  # It's likely a match row
                        self.logger.info(
                            f"Element {idx} is a match row under current ITF MEN - SINGLES context: '{current_processing_tournament_context}'. Processing...")
                        match_obj = await self._process_match_from_live_tab(
                            element,
                            current_processing_tournament_context,  # Pass the confirmed ITF Men Singles context
                            idx,
                            bookmaker_id_to_check,
                            current_page_url
                        )

                        if match_obj:
                            itf_bet365_matches_count += 1
                            matches_found.append(match_obj)
                            if progress_callback:
                                await progress_callback(match_obj)

                            if match_obj.metadata.get('is_match_tie_break'):
                                self.logger.critical(
                                    f"ITF MEN-SINGLES TIE BREAK #{itf_bet365_matches_count}: {match_obj.home_player.name} vs {match_obj.away_player.name} from '{match_obj.tournament}'")
                            else:
                                self.logger.info(
                                    f"ITF MEN-SINGLES BET365 MATCH #{itf_bet365_matches_count}: {match_obj.home_player.name} vs {match_obj.away_player.name} from '{match_obj.tournament}'")
                    # else:
                    # self.logger.debug(f"Element {idx} under ITF Men Singles context '{current_processing_tournament_context}' but doesn't look like a match row (no home participant). Skipping.")
                # else:
                # self.logger.debug(f"Element {idx} skipped: current context ('{current_processing_tournament_context}') is not ITF Men Singles.")

            success = True
            self.logger.info(
                f"✅ SCRAPING COMPLETE (LIVE TAB STRATEGY)! Processed {processed_elements_count} elements from page.")
            self.logger.info(f"📊 Found: {len(matches_found)} ITF MEN - SINGLES Bet365 matches.")
            tie_break_count = len([m for m in matches_found if m.metadata.get('is_match_tie_break')])
            if tie_break_count > 0:
                self.logger.critical(f"🚨 {tie_break_count} ITF MEN - SINGLES TIE BREAK MATCHES FOUND!")
            if not matches_found and total_elements_on_page > 0:
                self.logger.warning(
                    "Found elements on page, but none were classified as ITF MEN - SINGLES Bet365 matches. Check tournament header identification on LIVE tab, the MEN - SINGLES filter, and Bet365 indicator logic.")

        except Exception as e:
            self.logger.error(f"❌ Scraping error: {e}", exc_info=True)
            error_message = str(e)
            success = False
        finally:
            if page: await page.close()
            if context: await context.close()
            if browser: await browser.close()
            if playwright: await playwright.stop()

        duration = (datetime.now(timezone.utc) - start_time_dt).total_seconds()
        return ScrapingResult(
            source=source_name,
            matches=matches_found,
            success=success,
            error_message=error_message,
            duration_seconds=duration,
            timestamp=datetime.now(timezone.utc),
            metadata={
                'processed_elements_from_page': processed_elements_count,
                'total_elements_on_page': total_elements_on_page,
                'itf_men_singles_bet365_matches_found': len(matches_found),
                'tie_break_matches': len([m for m in matches_found if m.metadata.get('is_match_tie_break')]),
                'attempted_live_tab_click': True,
                'live_tab_successfully_clicked': live_tab_successfully_clicked_flag,
                'match_limit_applied': self.MAX_MATCHES_TO_PROCESS
            }
        )

    async def cleanup(self):
        self.logger.info("🧹 Cleaning up FlashscoreScraper...")
        await super().cleanup()