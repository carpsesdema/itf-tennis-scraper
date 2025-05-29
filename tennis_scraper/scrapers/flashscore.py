"""Flashscore scraper implementation - OPTIMIZED FOR SLOW COMPUTERS with ITF filtering."""

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
    """SIMPLIFIED tab clicker for slow computers."""

    def __init__(self, page: Page, logger):
        self.page = page
        self.logger = logger

    async def click_live_tab(self) -> bool:
        """Try only the most reliable strategies for slow computers."""

        # Only try the 3 most reliable strategies to save time
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
                    self.logger.info(f"✅ LIVE tab clicked successfully")
                    return True
            except Exception as e:
                self.logger.debug(f"Strategy failed: {e}")

        self.logger.error("🚨 LIVE tab strategies failed - continuing anyway")
        return False

    async def _strategy_simple_text(self) -> bool:
        """Strategy 1: Simple text-based selection."""
        try:
            live_selectors = [
                "text=LIVE",
                "text=Live",
                "*:has-text('LIVE')"
            ]

            for selector in live_selectors:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=5000):
                    await element.click(timeout=8000)
                    await self.page.wait_for_timeout(3000)
                    return True
            return False
        except Exception:
            return False

    async def _strategy_javascript_click(self) -> bool:
        """Strategy 2: JavaScript click."""
        try:
            js_code = """
            () => {
                const elements = document.querySelectorAll('*');
                for (let el of elements) {
                    if (el.textContent && el.textContent.includes('LIVE')) {
                        const classes = el.className || '';
                        if (classes.includes('tab') || classes.includes('filter') || 
                            el.tagName === 'BUTTON' || el.tagName === 'A') {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
            }
            """
            result = await self.page.evaluate(js_code)
            if result:
                await self.page.wait_for_timeout(3000)
                return True
            return False
        except Exception:
            return False

    async def _strategy_force_click(self) -> bool:
        """Strategy 3: Force click."""
        try:
            all_elements = await self.page.query_selector_all("*")
            # Only check first 50 elements to save time
            for element in all_elements[:50]:
                try:
                    text = await element.text_content()
                    if text and text.strip().upper() == "LIVE":
                        await element.click(force=True, timeout=3000)
                        await self.page.wait_for_timeout(3000)
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False


class FlashscoreScraper(BaseScraper):
    """OPTIMIZED Flashscore scraper for slow computers with ITF filtering."""

    FLASHCORE_BASE_URL = "https://www.flashscoreusa.com"
    TENNIS_URL_PATH = "/tennis/"

    # LIMITS for slow computers
    MAX_MATCHES_TO_PROCESS = 20  # Limit to first 20 ITF bet365 matches
    MAX_ELEMENTS_TO_CHECK = 100  # Only check first 100 page elements
    SIMPLIFIED_TIE_BREAK_CHECK = True  # Use simple tie-break detection

    async def get_source_name(self) -> str:
        return "flashscore"

    async def is_available(self) -> bool:
        return await self._check_site_availability(self.FLASHCORE_BASE_URL, timeout=self.request_timeout)

    async def _route_handler(self, route: Route, block_types: List[str], block_names: List[str]):
        """Block unnecessary resources - AGGRESSIVE blocking for slow computers."""
        resource_type = route.request.resource_type.lower()
        request_url_lower = route.request.url.lower()

        # AGGRESSIVE resource blocking for slow computers
        if resource_type in block_types:
            try:
                await route.abort()
                return
            except Exception:
                return

        # Block more aggressively
        aggressive_blocks = [
            'analytics', 'ads', 'tracking', 'facebook', 'twitter', 'social',
            'video', 'youtube', 'vimeo', 'advertisement', 'banner'
        ]

        for block_term in aggressive_blocks:
            if block_term in request_url_lower:
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

    async def _simplified_tie_break_detection(self, status_text: str, score_str: str,
                                              home_player_name: str, away_player_name: str) -> tuple[bool, str]:
        """SIMPLIFIED tie-break detection for slow computers."""

        # Only check the most obvious tie-break indicators
        simple_keywords = [
            "match tie break", "match tie-break", "super tiebreak", "first to 10"
        ]

        # Check status text
        if status_text:
            status_lower = status_text.lower()
            for keyword in simple_keywords:
                if keyword in status_lower:
                    self.logger.critical(f"🚨 TIE BREAK: {home_player_name} vs {away_player_name}")
                    return True, f"status_{keyword.replace(' ', '_')}"

        # Simple score pattern check - look for [10-8] style brackets
        if score_str and '[' in score_str and ']' in score_str:
            bracket_match = re.search(r'\[(\d+)-(\d+)\]', score_str)
            if bracket_match:
                home_tb, away_tb = int(bracket_match.group(1)), int(bracket_match.group(2))
                if home_tb >= 10 or away_tb >= 10:
                    self.logger.critical(
                        f"🚨 TIE BREAK: {home_player_name} vs {away_player_name} - [{home_tb}-{away_tb}]")
                    return True, f"score_bracket_{home_tb}_{away_tb}"

        return False, "none"

    async def _process_match_fast(self, sel_element: ElementHandle, element_index: int,
                                  bookmaker_id_to_check: str) -> Optional[TennisMatch]:
        """FAST match processing for slow computers with ITF filtering."""
        try:
            # FIRST: Check if this is an ITF match - SKIP if not
            tournament_selectors = [".event__tournament", "[class*='tournament']", ".event__title"]
            tournament_name = await self._get_text_fast(sel_element, tournament_selectors, default="")

            # Skip if not ITF
            if not tournament_name or "itf" not in tournament_name.lower():
                return None

            # Quick player name extraction
            home_selectors = [".event__participant--home", "[class*='home']"]
            away_selectors = [".event__participant--away", "[class*='away']"]

            home_player_name = await self._get_text_fast(sel_element, home_selectors)
            away_player_name = await self._get_text_fast(sel_element, away_selectors)

            if not home_player_name or not away_player_name:
                return None

            # Quick score and status
            score_selectors = [".event__score--home", "[class*='score']:nth-child(1)"]
            home_score = await self._get_text_fast(sel_element, score_selectors)

            score_selectors = [".event__score--away", "[class*='score']:nth-child(2)"]
            away_score = await self._get_text_fast(sel_element, score_selectors)

            score_str = f"{home_score}-{away_score}" if home_score and away_score else ""

            status_selectors = [".event__stage", ".event__time"]
            status_text = await self._get_text_fast(sel_element, status_selectors, default="")

            # SIMPLIFIED tie-break detection
            is_match_tie_break = False
            detection_method = "none"

            if self.SIMPLIFIED_TIE_BREAK_CHECK:
                is_match_tie_break, detection_method = await self._simplified_tie_break_detection(
                    status_text, score_str, home_player_name, away_player_name
                )

            # Generate simple match ID
            match_id = f"flashscore_itf_{element_index}_{hash(home_player_name + away_player_name) % 10000}"

            # Create metadata
            metadata_dict = {
                'has_bet365_indicator': True,
                'is_match_tie_break': is_match_tie_break,
                'tie_break_detection_method': detection_method,
                'element_index': element_index,
                'simplified_processing': True,
                'tournament_name': tournament_name,
                'is_itf_match': True
            }

            # Create match object
            source_name = await self.get_source_name()

            match_obj = TennisMatch(
                home_player=Player(name=self._parse_player_name(home_player_name)),
                away_player=Player(name=self._parse_player_name(away_player_name)),
                score=Score.from_string(score_str),
                status=self._parse_match_status(status_text, score_str),
                tournament=tournament_name,
                tournament_level=self._determine_tournament_level_flashscore(tournament_name),
                surface=Surface.UNKNOWN,
                source=source_name,
                source_url="",
                match_id=match_id,
                scheduled_time=None,
                last_updated=datetime.now(timezone.utc),
                metadata=metadata_dict
            )

            return match_obj

        except Exception as e:
            self.logger.debug(f"Fast processing failed for element {element_index}: {e}")
            return None

    def _determine_tournament_level_flashscore(self, tournament_name: str) -> TournamentLevel:
        """Determine tournament level from name."""
        if not tournament_name:
            return TournamentLevel.UNKNOWN

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
        return TournamentLevel.ITF_25K  # Default for ITF

    async def _get_text_fast(self, parent_element: ElementHandle, selectors: List[str], default: str = "") -> str:
        """FAST text extraction - only try first selector."""
        try:
            # Only try first selector to save time
            element = await parent_element.query_selector(selectors[0])
            if element:
                text = await element.text_content()
                return (text or default).strip()
        except Exception:
            pass
        return default

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
            bookmaker_id_to_check = "549"  # Default fallback

        self.logger.info(f"🎯 OPTIMIZED ITF SCRAPING for slow computer - Max {self.MAX_MATCHES_TO_PROCESS} matches")

        # OPTIMIZED settings for slow computers
        headless_mode = True  # Force headless for speed
        user_agent_new = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

        # AGGRESSIVE resource blocking
        block_resource_types = ["image", "stylesheet", "font", "media", "imageset", "websocket", "other"]
        block_resource_names = [
            "google-analytics.com", "googletagmanager.com", "facebook.com", "twitter.com",
            "ads", "advertising", "doubleclick", "adsystem", "googlesyndication"
        ]

        # INCREASED timeouts for slow computers
        element_timeout_ms = 45000  # 45 seconds

        playwright = None
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            self.logger.info("🚀 Starting optimized Playwright for slow computer...")
            playwright = await async_playwright().start()

            # Minimal browser args for slow computers
            browser_args = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                            '--disable-features=VizDisplayCompositor']

            browser = await playwright.chromium.launch(headless=headless_mode, args=browser_args)

            context = await browser.new_context(
                user_agent=user_agent_new,
                viewport={'width': 1280, 'height': 720},  # Smaller viewport
                java_script_enabled=True,
                ignore_https_errors=True
            )

            # AGGRESSIVE resource blocking
            await context.route("**/*",
                                lambda route: self._route_handler(route, block_resource_types, block_resource_names))

            page = await context.new_page()

            # Navigate to Flashscore USA Tennis section
            full_url = f"{self.FLASHCORE_BASE_URL}{self.TENNIS_URL_PATH}"
            self.logger.info(f"📍 Navigating to: {full_url}")
            await page.goto(full_url, wait_until="domcontentloaded", timeout=element_timeout_ms)

            # Handle cookies quickly
            try:
                cookie_btn = page.locator("#onetrust-accept-btn-handler")
                if await cookie_btn.is_visible(timeout=8000):
                    await cookie_btn.click(timeout=5000)
                    await page.wait_for_timeout(2000)
            except Exception:
                self.logger.debug("Cookie handling skipped")

            # Try to click LIVE tab
            self.logger.info("🎯 Clicking LIVE tab for live matches...")
            clicker = FlashscoreLiveTabClicker(page, self.logger)
            await clicker.click_live_tab()

            # Wait for content - shorter wait for slow computers
            await page.wait_for_timeout(5000)

            # Get match elements with limit
            self.logger.info(f"🔍 Looking for ITF match elements (max {self.MAX_ELEMENTS_TO_CHECK})...")

            match_elements: List[ElementHandle] = []
            selectors_to_try = ["div[class*='event__match']", "div[class*='event']", "[id*='g_']"]

            for selector in selectors_to_try:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        # LIMIT elements for slow computers
                        match_elements = elements[:self.MAX_ELEMENTS_TO_CHECK]
                        self.logger.info(f"📊 Using {len(match_elements)} elements (limited from {len(elements)})")
                        break
                except Exception:
                    continue

            if not match_elements:
                self.logger.warning("⚠️ No match elements found")
                success = True  # Don't fail completely
                error_message = "No match elements found but completed successfully"
            else:
                processed_elements_count = len(match_elements)
                itf_bet365_matches_found = 0

                # Process elements with STRICT LIMIT and ITF filtering
                for element_index, sel_element in enumerate(match_elements):
                    # STOP if we hit our match limit
                    if itf_bet365_matches_found >= self.MAX_MATCHES_TO_PROCESS:
                        self.logger.info(f"🛑 Reached ITF match limit ({self.MAX_MATCHES_TO_PROCESS}) - stopping")
                        break

                    try:
                        # Quick bet365 check
                        has_bet365 = False
                        try:
                            element_html = await sel_element.inner_html()
                            if bookmaker_id_to_check in element_html or 'bet365' in element_html.lower():
                                has_bet365 = True
                        except Exception:
                            continue

                        if not has_bet365:
                            continue

                        # Fast processing with ITF filtering
                        match_obj = await self._process_match_fast(sel_element, element_index, bookmaker_id_to_check)

                        if match_obj:  # Will be None if not ITF
                            itf_bet365_matches_found += 1
                            matches_found.append(match_obj)
                            match_obj.source_url = page.url

                            # Log tie breaks loudly
                            if match_obj.metadata.get('is_match_tie_break'):
                                self.logger.critical(
                                    f"🚨🚨🚨 ITF TIE BREAK #{itf_bet365_matches_found}: {match_obj.home_player.name} vs {match_obj.away_player.name}")
                            else:
                                self.logger.info(
                                    f"✅ ITF BET365 MATCH #{itf_bet365_matches_found}: {match_obj.home_player.name} vs {match_obj.away_player.name}")

                            # Brief pause to not overwhelm slow computer
                            if itf_bet365_matches_found % 5 == 0:
                                await asyncio.sleep(1)

                    except Exception as e:
                        self.logger.debug(f"Element {element_index} processing error: {e}")

                success = True
                self.logger.info(f"✅ OPTIMIZED ITF SCRAPING COMPLETE!")
                self.logger.info(f"📊 Processed: {processed_elements_count} elements")
                self.logger.info(f"🎯 Found: {len(matches_found)} ITF bet365 matches")

                tie_break_count = len([m for m in matches_found if m.metadata.get('is_match_tie_break')])
                if tie_break_count > 0:
                    self.logger.critical(f"🚨 {tie_break_count} ITF TIE BREAK MATCHES FOUND!")

        except Exception as e:
            self.logger.error(f"❌ Scraping error: {e}")
            error_message = str(e)
            success = False
        finally:
            # Cleanup
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

        duration = (datetime.now(timezone.utc) - start_time_dt).total_seconds()

        return ScrapingResult(
            source=source_name,
            matches=matches_found,
            success=success,
            error_message=error_message,
            duration_seconds=duration,
            timestamp=datetime.now(timezone.utc),
            metadata={
                'processed_elements': processed_elements_count,
                'itf_bet365_matches_found': len(matches_found),
                'tie_break_matches': len([m for m in matches_found if m.metadata.get('is_match_tie_break')]),
                'optimized_for_slow_computer': True,
                'match_limit_applied': self.MAX_MATCHES_TO_PROCESS,
                'elements_limit_applied': self.MAX_ELEMENTS_TO_CHECK,
                'itf_filtering_applied': True
            }
        )

    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("🧹 Cleaning up FlashscoreScraper...")
        await super().cleanup()