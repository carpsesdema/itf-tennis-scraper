"""Flashscore scraper implementation using Playwright with ENHANCED tie break detection."""

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
                "text=Live",
                "[data-testid*='live']",
                ".filters__text--short:text('LIVE')",
                "*:has-text('LIVE')",
                "a:has-text('LIVE')",
                "div:has-text('LIVE')",
                "span:has-text('LIVE')"
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
                "//*[contains(@class, 'tab') and contains(text(), 'LIVE')]",
                "//div[text()='LIVE']",
                "//a[text()='LIVE']"
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
                            classes.includes('button') || node.tagName === 'BUTTON' ||
                            node.tagName === 'A') {
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

    async def _debug_page_content(self, page: Page):
        """Debug function to analyze page content and structure."""
        self.logger.info("🔍 DEBUGGING PAGE CONTENT...")

        try:
            # Check current URL
            current_url = page.url
            self.logger.info(f"Current URL: {current_url}")

            # Check for ITF matches in page content
            page_content = await page.content()
            itf_mentions = page_content.lower().count('itf')
            self.logger.info(f"ITF mentions in page: {itf_mentions}")

            # Look for match containers with various selectors
            match_selectors = [
                "div[class*='event__match']",
                "div[class*='event']",
                ".event",
                "[id*='g_']",
                "div[class*='match']",
                ".match"
            ]

            for selector in match_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    self.logger.info(f"Found {len(elements)} elements with selector '{selector}'")

                    # Sample first few elements
                    for i, element in enumerate(elements[:3]):
                        try:
                            text = await element.text_content()
                            class_attr = await element.get_attribute("class")
                            id_attr = await element.get_attribute("id")
                            self.logger.info(
                                f"  Element {i}: class='{class_attr}', id='{id_attr}', text='{text[:100] if text else 'None'}'")
                        except:
                            pass
                except:
                    pass

            # Look for bet365 indicators with expanded selectors
            bet365_selectors = [
                "div.liveBetWrapper",
                "[data-bookmaker-id]",
                "[class*='bet']",
                "[class*='odds']",
                "img[alt*='bet365']",
                "a[href*='bet365']"
            ]

            for selector in bet365_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    self.logger.info(f"Found {len(elements)} bet365-related elements with selector '{selector}'")

                    for i, element in enumerate(elements[:5]):
                        try:
                            attrs = {}
                            for attr in ['data-bookmaker-id', 'class', 'href', 'alt']:
                                val = await element.get_attribute(attr)
                                if val:
                                    attrs[attr] = val
                            self.logger.info(f"  Bet365 element {i}: {attrs}")
                        except:
                            pass
                except:
                    pass

        except Exception as e:
            self.logger.error(f"Error during page debugging: {e}")

    async def _detect_match_tie_break_comprehensive(self, sel_element: ElementHandle, status_text: str, score_str: str,
                                                    home_player_name: str, away_player_name: str) -> tuple[bool, str]:
        """
        COMPREHENSIVE match tie break detection - checks multiple sources.
        Returns (is_tie_break, detection_method)
        """
        tie_break_keywords = self.config.get('flashscore_match_tie_break_keywords', [
            "match tie break", "match tie-break", "match tb", "super tiebreak",
            "super tie-break", "mtb", "stb", "first to 10", "race to 10",
            "match tiebreak", "supertiebreak", "super tb", "match-tb",
            "deciding tb", "final tb", "championship tb"
        ])

        detection_methods = []

        # METHOD 1: Status text keyword matching (original)
        if status_text:
            status_lower = status_text.lower()
            for keyword in tie_break_keywords:
                if keyword.lower() in status_lower:
                    detection_methods.append(f"status_text: '{keyword}' found in '{status_text}'")
                    self.logger.critical(
                        f"🚨 TIE BREAK DETECTED via STATUS: {home_player_name} vs {away_player_name} - '{keyword}' in '{status_text}'")
                    return True, f"status_keyword_{keyword}"

        # METHOD 2: Score analysis - look for tie break score patterns
        if score_str:
            # Pattern 1: Brackets indicate tie break scores [10-8], [15-13], etc.
            bracket_pattern = r'\[(\d+)-(\d+)\]'
            bracket_matches = re.findall(bracket_pattern, score_str)
            if bracket_matches:
                for home_tb, away_tb in bracket_matches:
                    home_tb_int, away_tb_int = int(home_tb), int(away_tb)
                    # Match tie breaks are typically first to 10 (must win by 2)
                    if (home_tb_int >= 10 or away_tb_int >= 10) and abs(home_tb_int - away_tb_int) >= 2:
                        detection_methods.append(f"score_bracket: [{home_tb}-{away_tb}] indicates match tie break")
                        self.logger.critical(
                            f"🚨 TIE BREAK DETECTED via SCORE BRACKET: {home_player_name} vs {away_player_name} - [{home_tb}-{away_tb}]")
                        return True, f"score_bracket_{home_tb}_{away_tb}"

            # Pattern 2: Current score analysis - if sets are tied and we're in a long tie break
            # Example: "6-4 4-6 12-10" could indicate a match tie break in progress
            score_parts = score_str.split()
            if len(score_parts) >= 2:
                try:
                    # Check if sets are even and last set has high scores
                    sets_won_home = sets_won_away = 0
                    last_set_home = last_set_away = 0

                    for part in score_parts:
                        if '-' in part:
                            home_games, away_games = map(int, part.split('-'))
                            if home_games > away_games:
                                sets_won_home += 1
                            elif away_games > home_games:
                                sets_won_away += 1
                            last_set_home, last_set_away = home_games, away_games

                    # If sets are tied and current "set" has scores ≥10, likely a match tie break
                    if (sets_won_home == sets_won_away and
                            (last_set_home >= 10 or last_set_away >= 10)):
                        detection_methods.append(
                            f"score_analysis: Sets tied {sets_won_home}-{sets_won_away}, current: {last_set_home}-{last_set_away}")
                        self.logger.critical(
                            f"🚨 TIE BREAK DETECTED via SCORE ANALYSIS: {home_player_name} vs {away_player_name} - Sets {sets_won_home}-{sets_won_away}, TB: {last_set_home}-{last_set_away}")
                        return True, f"score_analysis_sets_tied_{last_set_home}_{last_set_away}"

                except (ValueError, IndexError):
                    pass  # Skip if score parsing fails

        # METHOD 3: Element HTML content analysis
        try:
            element_html = await sel_element.inner_html()
            element_html_lower = element_html.lower()

            # Look for tie break indicators in HTML
            html_tie_break_indicators = [
                "match tie", "match tb", "super tie", "mtb", "stb",
                "first to 10", "race to 10", "deciding tb", "final tb"
            ]

            for indicator in html_tie_break_indicators:
                if indicator in element_html_lower:
                    detection_methods.append(f"html_content: '{indicator}' found in element HTML")
                    self.logger.critical(
                        f"🚨 TIE BREAK DETECTED via HTML: {home_player_name} vs {away_player_name} - '{indicator}' in HTML")
                    return True, f"html_content_{indicator.replace(' ', '_')}"

            # Look for specific CSS classes that might indicate tie breaks
            tie_break_classes = [
                "tiebreak", "tie-break", "match-tb", "super-tb", "mtb", "stb"
            ]

            for cls in tie_break_classes:
                if f'class="{cls}"' in element_html_lower or f"class='{cls}'" in element_html_lower:
                    detection_methods.append(f"css_class: '{cls}' found in element")
                    self.logger.critical(
                        f"🚨 TIE BREAK DETECTED via CSS CLASS: {home_player_name} vs {away_player_name} - class '{cls}'")
                    return True, f"css_class_{cls}"

        except Exception as e:
            self.logger.debug(f"HTML analysis failed for tie break detection: {e}")

        # METHOD 4: Text content analysis (broader than just status)
        try:
            full_text = await sel_element.text_content()
            if full_text:
                full_text_lower = full_text.lower()
                for keyword in tie_break_keywords:
                    if keyword.lower() in full_text_lower:
                        detection_methods.append(f"full_text: '{keyword}' found in element text")
                        self.logger.critical(
                            f"🚨 TIE BREAK DETECTED via FULL TEXT: {home_player_name} vs {away_player_name} - '{keyword}' in text")
                        return True, f"full_text_{keyword.replace(' ', '_')}"
        except Exception as e:
            self.logger.debug(f"Full text analysis failed for tie break detection: {e}")

        # METHOD 5: Check for specific numeric patterns that indicate match tie breaks
        # Look for scores like "10-8", "12-10", "15-13" which are common in match tie breaks
        all_text = f"{status_text} {score_str}".lower()
        tie_break_score_patterns = [
            r'\b(1[0-9])-([8-9]|1[0-9])\b',  # 10-8, 11-9, 12-10, etc.
            r'\b([8-9]|1[0-9])-(1[0-9])\b',  # 8-10, 9-11, 10-12, etc.
        ]

        for pattern in tie_break_score_patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                for match in matches:
                    score1, score2 = int(match[0]), int(match[1])
                    # Match tie break scoring: first to 10, must win by 2
                    if (score1 >= 10 or score2 >= 10) and abs(score1 - score2) >= 1:
                        detection_methods.append(f"score_pattern: {score1}-{score2} matches tie break pattern")
                        self.logger.critical(
                            f"🚨 TIE BREAK DETECTED via SCORE PATTERN: {home_player_name} vs {away_player_name} - {score1}-{score2}")
                        return True, f"score_pattern_{score1}_{score2}"

        # Log detection attempts for debugging
        if detection_methods:
            self.logger.debug(
                f"Tie break detection methods tried for {home_player_name} vs {away_player_name}: {detection_methods}")

        return False, "none"

    async def _enhanced_match_processing(self, sel_element: ElementHandle, element_index: int,
                                         bookmaker_id_to_check: str) -> Optional[TennisMatch]:
        """Enhanced match processing with comprehensive tie break detection."""
        try:
            # Extract player names with multiple selectors
            home_selectors = [".event__participant--home", "[class*='home']", "[class*='participant']:nth-child(1)"]
            away_selectors = [".event__participant--away", "[class*='away']", "[class*='participant']:nth-child(2)"]

            home_player_name = await self._get_text_from_selectors(sel_element, home_selectors)
            away_player_name = await self._get_text_from_selectors(sel_element, away_selectors)

            if not home_player_name or not away_player_name:
                self.logger.debug(f"Skipping match {element_index} - missing player names")
                return None

            # Extract scores and status
            score_selectors = [".event__score--home", "[class*='score']:nth-child(1)"]
            home_score = await self._get_text_from_selectors(sel_element, score_selectors)

            score_selectors = [".event__score--away", "[class*='score']:nth-child(2)"]
            away_score = await self._get_text_from_selectors(sel_element, score_selectors)

            score_str = f"{home_score}-{away_score}" if home_score and away_score else ""

            status_selectors = [".event__stage", ".event__time", "[class*='status']", "[class*='time']"]
            status_text = await self._get_text_from_selectors(sel_element, status_selectors, default="")

            # COMPREHENSIVE TIE BREAK DETECTION
            is_match_tie_break, detection_method = await self._detect_match_tie_break_comprehensive(
                sel_element, status_text, score_str, home_player_name, away_player_name
            )

            # Extract match ID
            match_id_raw = await sel_element.get_attribute("id")
            match_id = self._generate_match_id(match_id_raw, element_index, home_player_name, away_player_name)

            # Create metadata with enhanced tie break info
            metadata_dict = {
                'flashscore_raw_id': match_id_raw or f"index_{element_index}",
                'has_bet365_indicator': True,
                'is_match_tie_break': is_match_tie_break,
                'tie_break_detection_method': detection_method,
                'bet365_bookmaker_id': bookmaker_id_to_check,
                'element_index': element_index,
                'raw_status_text': status_text,
                'raw_score_text': score_str,
                'detection_strategy': 'comprehensive_tie_break_v2'
            }

            # Create match object
            tournament_name = "ITF Men Singles"
            tournament_level = self._determine_tournament_level_flashscore(tournament_name)
            source_name = await self.get_source_name()

            match_obj = TennisMatch(
                home_player=Player(name=self._parse_player_name(home_player_name)),
                away_player=Player(name=self._parse_player_name(away_player_name)),
                score=Score.from_string(score_str),
                status=self._parse_match_status(status_text, score_str),
                tournament=tournament_name,
                tournament_level=tournament_level,
                surface=Surface.UNKNOWN,
                source=source_name,
                source_url="",  # Will be set by caller
                match_id=match_id,
                scheduled_time=None,
                last_updated=datetime.now(timezone.utc),
                metadata=metadata_dict
            )

            # CRITICAL ALERT for tie breaks
            if is_match_tie_break:
                self.logger.critical(f"🚨🚨🚨 MATCH TIE BREAK ALERT 🚨🚨🚨")
                self.logger.critical(f"MATCH: {home_player_name} vs {away_player_name}")
                self.logger.critical(f"SCORE: {score_str}")
                self.logger.critical(f"STATUS: {status_text}")
                self.logger.critical(f"DETECTION: {detection_method}")
                self.logger.critical(f"🚨🚨🚨 END TIE BREAK ALERT 🚨🚨🚨")

            return match_obj

        except Exception as e:
            self.logger.error(f"Enhanced match processing failed for element {element_index}: {e}", exc_info=True)
            return None

    def _generate_match_id(self, match_id_raw: str, element_index: int, home_player: str, away_player: str) -> str:
        """Generate a consistent match ID."""
        if match_id_raw:
            id_match = re.search(r'g_\d_([a-zA-Z0-9]+)', match_id_raw)
            if id_match:
                return f"flashscore_{id_match.group(1)}"
            else:
                id_part_match = re.search(r'([a-zA-Z0-9_-]+)$', match_id_raw)
                if id_part_match:
                    return f"flashscore_{id_part_match.group(1)}"

        # Fallback ID
        return f"flashscore_bet365_{element_index}_{home_player[:3]}_{away_player[:3]}"

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

        self.logger.info(f"Flashscore: Looking for bet365 matches with bookmaker-id='{bookmaker_id_to_check}'")

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

            # DEBUG: Analyze page before clicking LIVE tab
            await self._debug_page_content(page)

            # Click the LIVE tab with robust method
            live_tab_success = await self._click_live_tab_robust(page)
            if not live_tab_success:
                self.logger.error("Failed to click LIVE tab - proceeding anyway but results may be limited")

            # DEBUG: Analyze page after clicking LIVE tab
            self.logger.info("🔍 PAGE CONTENT AFTER LIVE TAB CLICK...")
            await self._debug_page_content(page)

            # Try scrolling down to load more matches
            self.logger.info("📜 Scrolling to load more matches...")
            for i in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                self.logger.info(f"Scroll {i + 1}/3 completed")

            # Wait for matches to load with multiple selector attempts
            self.logger.debug("Waiting for match containers...")
            match_container_selectors = [
                "div[class*='event__match']",
                "div[class*='event']",
                ".event",
                "[id*='g_']"
            ]

            match_elements: List[ElementHandle] = []

            for selector in match_container_selectors:
                try:
                    await page.wait_for_selector(selector, state="attached", timeout=10000)
                    elements = await page.query_selector_all(selector)
                    self.logger.info(f"Found {len(elements)} potential matches using selector: {selector}")
                    if elements:
                        match_elements = elements
                        break
                except PlaywrightTimeoutError:
                    self.logger.debug(f"Selector '{selector}' timed out")
                    continue

            if not match_elements:
                self.logger.warning("No match elements found with any selector - trying fallback approach")
                # Fallback: get all divs and filter by content
                all_divs = await page.query_selector_all("div")
                for div in all_divs:
                    try:
                        text = await div.text_content()
                        if text and any(word in text.lower() for word in ['vs', 'set', 'game']):
                            match_elements.append(div)
                    except:
                        continue
                self.logger.info(f"Fallback approach found {len(match_elements)} potential match elements")

            processed_elements_count = len(match_elements)

            # Process each match element with ENHANCED TIE BREAK DETECTION
            bet365_matches_found = 0
            total_bet_wrappers_found = 0

            for element_index, sel_element in enumerate(match_elements):
                try:
                    # ENHANCED BET365 DETECTION (existing logic)
                    has_bet365_indicator = False
                    debug_info = []

                    # Strategy 1: Original liveBetWrapper approach
                    try:
                        bet_wrappers = await sel_element.query_selector_all("div.liveBetWrapper")
                        total_bet_wrappers_found += len(bet_wrappers)

                        if bet_wrappers:
                            debug_info.append(f"Found {len(bet_wrappers)} liveBetWrapper elements")
                            for wrapper in bet_wrappers:
                                bookmaker_id = await wrapper.get_attribute("data-bookmaker-id")
                                debug_info.append(f"  Bookmaker ID: {bookmaker_id}")
                                if bookmaker_id == bookmaker_id_to_check:
                                    has_bet365_indicator = True
                                    debug_info.append(f"  ✅ MATCH! Found bet365 via liveBetWrapper")
                                    break
                    except Exception as e:
                        debug_info.append(f"liveBetWrapper strategy failed: {e}")

                    # Strategy 2: Look for any bet365 indicators in the match element
                    if not has_bet365_indicator:
                        try:
                            # Check for bet365 in text content
                            element_html = await sel_element.inner_html()
                            if '549' in element_html or 'bet365' in element_html.lower():
                                has_bet365_indicator = True
                                debug_info.append("✅ MATCH! Found bet365 via HTML content")

                            # Check for data attributes containing bet365 reference
                            all_attrs = await page.evaluate("""
                                (element) => {
                                    const attrs = {};
                                    for (let attr of element.attributes) {
                                        attrs[attr.name] = attr.value;
                                    }
                                    return attrs;
                                }
                            """, sel_element)

                            for attr_name, attr_value in all_attrs.items():
                                if '549' in str(attr_value) or 'bet365' in str(attr_value).lower():
                                    has_bet365_indicator = True
                                    debug_info.append(f"✅ MATCH! Found bet365 via attribute {attr_name}={attr_value}")
                                    break

                        except Exception as e:
                            debug_info.append(f"HTML content strategy failed: {e}")

                    # Strategy 3: Check parent elements for bet365 indicators
                    if not has_bet365_indicator:
                        try:
                            parent = await sel_element.query_selector("xpath=..")
                            if parent:
                                parent_html = await parent.inner_html()
                                if '549' in parent_html or 'bet365' in parent_html.lower():
                                    has_bet365_indicator = True
                                    debug_info.append("✅ MATCH! Found bet365 via parent element")
                        except Exception as e:
                            debug_info.append(f"Parent element strategy failed: {e}")

                    # Skip if no bet365 indicator
                    if not has_bet365_indicator:
                        if element_index < 3:  # Only log first few for debugging
                            self.logger.debug(f"Skipping match {element_index} - no bet365 indicator")
                        continue

                    # PROCESS MATCH WITH ENHANCED TIE BREAK DETECTION
                    match_obj = await self._enhanced_match_processing(sel_element, element_index, bookmaker_id_to_check)

                    if match_obj:
                        bet365_matches_found += 1
                        matches_found.append(match_obj)

                        # Set the source URL
                        match_obj.source_url = page.url

                        # EXTRA LOUD ALERTS FOR TIE BREAKS
                        if match_obj.metadata.get('is_match_tie_break'):
                            self.logger.critical("=" * 80)
                            self.logger.critical(f"🚨 CRITICAL ALERT: MATCH TIE BREAK DETECTED 🚨")
                            self.logger.critical(
                                f"PLAYERS: {match_obj.home_player.name} vs {match_obj.away_player.name}")
                            self.logger.critical(f"TOURNAMENT: {match_obj.tournament}")
                            self.logger.critical(f"SCORE: {match_obj.display_score}")
                            self.logger.critical(f"STATUS: {match_obj.metadata.get('raw_status_text', 'Unknown')}")
                            self.logger.critical(
                                f"DETECTION METHOD: {match_obj.metadata.get('tie_break_detection_method', 'Unknown')}")
                            self.logger.critical(f"MATCH ID: {match_obj.match_id}")
                            self.logger.critical(f"SOURCE URL: {match_obj.source_url}")
                            self.logger.critical("=" * 80)

                        # Regular bet365 match logging
                        else:
                            self.logger.info(
                                f"🎯 BET365 MATCH #{bet365_matches_found}: {match_obj.home_player.name} vs {match_obj.away_player.name}")

                except Exception as e_extract:
                    self.logger.warning(f"Extraction error for match (idx {element_index}): {e_extract}", exc_info=True)

            success = True

            # Enhanced logging
            self.logger.info(f"📊 SCRAPING SUMMARY:")
            self.logger.info(f"  Total match elements processed: {processed_elements_count}")
            self.logger.info(f"  Total liveBetWrapper elements found: {total_bet_wrappers_found}")
            self.logger.info(f"  Bet365 matches found (ID={bookmaker_id_to_check}): {len(matches_found)}")

            tie_break_matches = [m for m in matches_found if m.metadata.get('is_match_tie_break')]
            if tie_break_matches:
                self.logger.critical(f"🚨 {len(tie_break_matches)} TIE BREAK MATCHES FOUND WITH BET365!")

            if not error_message and not matches_found and processed_elements_count > 0:
                error_message = f"Processed {processed_elements_count} elements but no bet365 matches found (bookmaker-id={bookmaker_id_to_check})"
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
                'tie_break_matches': len([m for m in matches_found if m.metadata.get('is_match_tie_break')]),
                'bookmaker_id_searched': bookmaker_id_to_check
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