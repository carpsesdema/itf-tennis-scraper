import asyncio
import aiohttp
from abc import abstractmethod
from typing import List, Optional, Dict, Any, Tuple, Callable, Awaitable
from datetime import datetime

from ..core.interfaces import MatchScraper
from ..core.models import TennisMatch, Player, Score, MatchStatus, ScrapingResult, TournamentLevel, Surface
from ..utils.logging import get_logger


class BaseScraper(MatchScraper):
    """
    Base class for specific website scrapers.
    Provides common utilities like HTTP session management, retries,
    and basic data parsing helpers.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self.request_timeout = config.get('request_timeout', 10)
        self.max_retries = config.get('max_retries', 3)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={'User-Agent': self.config.get('user_agent', 'Mozilla/5.0')}
            )
        return self._session

    async def _check_site_availability(self, url: str, timeout: int = 5) -> bool:
        """Check if the base site URL is reachable."""
        try:
            session = await self._get_session()
            async with session.head(url, timeout=timeout, allow_redirects=True) as response:
                return response.status < 400
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout checking availability for {url}")
            return False
        except aiohttp.ClientError as e:
            self.logger.warning(f"Client error checking availability for {url}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error checking availability for {url}: {e}")
            return False

    def _parse_player_name(self, raw_name: str) -> str:
        """Basic parsing for player names."""
        if not raw_name:
            return "Unknown Player"
        name = raw_name.strip()
        prefixes_suffixes = ["Mr.", "Ms.", "Jr.", "Sr."]
        for ps in prefixes_suffixes:
            if name.startswith(ps):
                name = name[len(ps):].strip()
            if name.endswith(ps):
                name = name[:-len(ps)].strip()
        return name if name else "Unknown Player"


    def _parse_score(self, score_str: Optional[str]) -> Score:
        """Parses a typical score string (e.g., "6-4 3-6") into a Score object."""
        if not score_str:
            return Score()
        return Score.from_string(score_str)

    def _parse_match_status(self, status_str: Optional[str], score_str: Optional[str] = None) -> MatchStatus:
        """
        IMPROVED match status parsing with better logic.
        """
        if not status_str:
            if score_str and score_str.strip() and score_str != "-":
                return MatchStatus.LIVE
            return MatchStatus.SCHEDULED

        s_lower = status_str.lower().strip()
        s_lower = s_lower.replace("'", "").replace('"', '')

        finished_keywords = [
            "fin.", "finished", "completed", "ended", "full time", "ft",
            "final", "result", "won", "lost", "victory", "defeat"
        ]
        if any(kw in s_lower for kw in finished_keywords):
            return MatchStatus.FINISHED

        live_keywords = [
            "live", "playing", "in progress", "ongoing", "current",
            "1st set", "2nd set", "3rd set", "4th set", "5th set",
            "break", "serving", "match point", "set point", "game point",
            "deuce", "advantage", "ad", "break point"
        ]
        if any(kw in s_lower for kw in live_keywords):
            return MatchStatus.LIVE

        time_patterns = [
            r'\d{1,2}:\d{2}',
            r'\d{1,2}h\d{2}',
            r'\d{1,2}\.\d{2}',
        ]
        import re
        for pattern in time_patterns:
            if re.search(pattern, s_lower):
                return MatchStatus.SCHEDULED

        if any(kw in s_lower for kw in ["postp.", "postponed", "delayed"]):
            return MatchStatus.POSTPONED
        if any(kw in s_lower for kw in ["canc.", "cancelled", "canceled"]):
            return MatchStatus.CANCELLED
        if any(kw in s_lower for kw in ["walkover", "w.o.", "w/o", "wo"]):
            return MatchStatus.WALKOVER
        if any(kw in s_lower for kw in ["retired", "ret.", "retirement"]):
            return MatchStatus.RETIRED
        if any(kw in s_lower for kw in ["interrupted", "susp.", "suspended", "rain", "weather"]):
            return MatchStatus.INTERRUPTED
        if any(kw in s_lower for kw in ["awarded", "def.", "default"]):
            return MatchStatus.AWARDED

        scheduled_keywords = [
            "sched.", "scheduled", "not started", "upcoming", "soon",
            "today", "tomorrow", "vs", "v", "-", "tbd", "tba"
        ]
        if any(kw in s_lower for kw in scheduled_keywords):
            return MatchStatus.SCHEDULED

        if len(s_lower) <= 2 or s_lower in ["-", "vs", "v", ""]:
            return MatchStatus.SCHEDULED

        if score_str:
            score_clean = score_str.strip()
            if score_clean and score_clean != "-" and score_clean != "0-0":
                score_parts = score_clean.split()
                if len(score_parts) >= 2:
                    try:
                        sets_parsed = 0
                        for part in score_parts:
                            if '-' in part and len(part.split('-')) == 2:
                                home, away = map(int, part.split('-'))
                                if (home >= 6 and home - away >= 2) or \
                                   (away >= 6 and away - home >= 2) or \
                                   home == 7 or away == 7:
                                    sets_parsed += 1
                        if sets_parsed >= 2:
                            return MatchStatus.FINISHED
                        elif sets_parsed >= 1:
                            return MatchStatus.LIVE
                    except (ValueError, IndexError):
                        pass
                return MatchStatus.LIVE
            else:
                return MatchStatus.SCHEDULED

        if len(s_lower) > 10:
            return MatchStatus.LIVE
        return MatchStatus.SCHEDULED

    def _create_match(self,
                      home_player: str,
                      away_player: str,
                      score: str = "",
                      status: str = "scheduled",
                      tournament: str = "",
                      round_info: str = "",
                      source_url: Optional[str] = None,
                      match_id: Optional[str] = None,
                      scheduled_time_utc: Optional[datetime] = None,
                      **kwargs) -> TennisMatch:
        parsed_status = self._parse_match_status(status, score)
        parsed_score = self._parse_score(score)
        home_p_obj = home_player if isinstance(home_player, Player) else Player(name=self._parse_player_name(home_player))
        away_p_obj = away_player if isinstance(away_player, Player) else Player(name=self._parse_player_name(away_player))

        return TennisMatch(
            home_player=home_p_obj,
            away_player=away_p_obj,
            score=parsed_score,
            status=parsed_status,
            tournament=tournament.strip(),
            round_info=round_info.strip(),
            scheduled_time=scheduled_time_utc,
            source="",
            source_url=source_url,
            match_id=match_id,
            last_updated=datetime.utcnow(),
            metadata=kwargs
        )

    async def scrape_with_retry(self,
                                max_retries: Optional[int] = None,
                                progress_callback: Optional[Callable[[TennisMatch], Awaitable[None]]] = None
                                ) -> ScrapingResult:
        retries = max_retries if max_retries is not None else self.max_retries
        source_name = await self.get_source_name()
        last_exception = None

        for attempt in range(retries + 1):
            try:
                self.logger.info(f"Attempt {attempt + 1}/{retries + 1} to scrape {source_name}")
                result = await self.scrape_matches(progress_callback=progress_callback)
                if result.success:
                    return result
                else:
                    self.logger.warning(f"Scraping {source_name} failed on attempt {attempt + 1}: {result.error_message}")
                    last_exception = Exception(result.error_message)
            except Exception as e:
                self.logger.error(f"Exception during scrape attempt {attempt + 1} for {source_name}: {e}", exc_info=True)
                last_exception = e

            if attempt < retries:
                sleep_duration = self.delay_between_requests * (2 ** attempt)
                self.logger.info(f"Retrying {source_name} in {sleep_duration} seconds...")
                await asyncio.sleep(sleep_duration)

        error_msg = f"All {retries + 1} attempts to scrape {source_name} failed."
        if last_exception:
            error_msg += f" Last error: {str(last_exception)}"
        self.logger.error(error_msg)
        return ScrapingResult(source=source_name, success=False, error_message=error_msg)


    @abstractmethod
    async def scrape_matches(self, progress_callback: Optional[Callable[[TennisMatch], Awaitable[None]]] = None) -> ScrapingResult:
        """
        Abstract method for scraping matches.
        Must be implemented by subclasses.
        Should return a ScrapingResult object.
        The progress_callback can be called with a TennisMatch object after each match is found.
        """
        pass

    async def cleanup(self):
        """Close the aiohttp session if it was created."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self.logger.info(f"Closed aiohttp session for {await self.get_source_name()}")