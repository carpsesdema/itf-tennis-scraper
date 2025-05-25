"""
Base class for web scrapers with common utilities.
"""

import asyncio
import aiohttp
from abc import abstractmethod
from typing import List, Optional, Dict, Any, Tuple
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
        # delay_between_requests is inherited from MatchScraper and set in its __init__

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            # You might want to configure connectors, timeouts, etc. here
            # For example, adding a TCPConnector with SSL verification options
            # connector = aiohttp.TCPConnector(ssl=False) # If facing SSL issues, but use with caution
            self._session = aiohttp.ClientSession(
                headers={'User-Agent': self.config.get('user_agent', 'Mozilla/5.0')}
            )
        return self._session

    async def _check_site_availability(self, url: str, timeout: int = 5) -> bool:
        """Check if the base site URL is reachable."""
        try:
            session = await self._get_session()
            async with session.head(url, timeout=timeout, allow_redirects=True) as response:
                return response.status < 400 # Typically 2xx or 3xx are OK
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
        # Common prefixes/suffixes to remove - this might need to be source-specific
        prefixes_suffixes = ["Mr.", "Ms.", "Jr.", "Sr."]
        for ps in prefixes_suffixes:
            if name.startswith(ps):
                name = name[len(ps):].strip()
            if name.endswith(ps): # Less common for suffix, but possible
                name = name[:-len(ps)].strip()
        return name if name else "Unknown Player"


    def _parse_score(self, score_str: Optional[str]) -> Score:
        """Parses a typical score string (e.g., "6-4 3-6") into a Score object."""
        if not score_str:
            return Score()
        return Score.from_string(score_str) # Delegate to Score model's parser

    def _parse_match_status(self, status_str: Optional[str], score_str: Optional[str] = None) -> MatchStatus:
        """
        Determines match status from a status string.
        Can be made more robust with source-specific keywords.
        """
        if not status_str:
            return MatchStatus.UNKNOWN

        s_lower = status_str.lower()

        if any(kw in s_lower for kw in ["live", "progress", "playing", "break", "game", "set", "'"]): # ' for current game time
            return MatchStatus.LIVE
        if any(kw in s_lower for kw in ["fin.", "finished", "completed", "ended", "full time"]):
            return MatchStatus.FINISHED
        if any(kw in s_lower for kw in ["sched.", "scheduled", "not started", "upcoming"]):
            return MatchStatus.SCHEDULED
        if any(kw in s_lower for kw in ["postp.", "postponed", "delayed"]):
            return MatchStatus.POSTPONED
        if any(kw in s_lower for kw in ["canc.", "cancelled", "canceled"]):
            return MatchStatus.CANCELLED
        if any(kw in s_lower for kw in ["walkover", "w.o.", "w/o"]):
            return MatchStatus.WALKOVER
        if any(kw in s_lower for kw in ["retired", "ret."]):
            return MatchStatus.RETIRED
        if any(kw in s_lower for kw in ["interrupted", "susp.", "suspended"]):
            return MatchStatus.INTERRUPTED
        if any(kw in s_lower for kw in ["awarded"]):
            return MatchStatus.AWARDED

        # Infer from score if status is ambiguous
        if score_str and any(char.isdigit() for char in score_str):
            return MatchStatus.LIVE # If there's a score, it's likely live or recently finished

        return MatchStatus.SCHEDULED # Default to scheduled if unsure

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
        """
        Helper to create a TennisMatch object.
        Additional kwargs are stored in metadata.
        """
        parsed_status = self._parse_match_status(status, score)
        parsed_score = self._parse_score(score)

        # Allow passing Player objects or names
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
            source="",  # Will be set by caller # This is tricky in a non-async helper
                                                        # Better to set source explicitly when calling
            source_url=source_url,
            match_id=match_id,
            last_updated=datetime.utcnow(),
            metadata=kwargs
        )

    async def scrape_with_retry(self, max_retries: Optional[int] = None) -> ScrapingResult:
        """
        Wraps the scrape_matches call with retry logic.
        Individual scrapers should implement scrape_matches.
        """
        retries = max_retries if max_retries is not None else self.max_retries
        source_name = await self.get_source_name()
        last_exception = None

        for attempt in range(retries + 1):
            try:
                self.logger.info(f"Attempt {attempt + 1}/{retries + 1} to scrape {source_name}")
                # scrape_matches should return a ScrapingResult
                result = await self.scrape_matches()
                if result.success:
                    return result
                else:
                    self.logger.warning(f"Scraping {source_name} failed on attempt {attempt + 1}: {result.error_message}")
                    last_exception = Exception(result.error_message) # Store as an exception
            except Exception as e:
                self.logger.error(f"Exception during scrape attempt {attempt + 1} for {source_name}: {e}", exc_info=True)
                last_exception = e

            if attempt < retries:
                sleep_duration = self.delay_between_requests * (2 ** attempt) # Exponential backoff
                self.logger.info(f"Retrying {source_name} in {sleep_duration} seconds...")
                await asyncio.sleep(sleep_duration)

        # If all retries fail
        error_msg = f"All {retries + 1} attempts to scrape {source_name} failed."
        if last_exception:
            error_msg += f" Last error: {str(last_exception)}"
        self.logger.error(error_msg)
        return ScrapingResult(source=source_name, success=False, error_message=error_msg)


    @abstractmethod
    async def scrape_matches(self) -> ScrapingResult:
        """
        Abstract method for scraping matches.
        Must be implemented by subclasses.
        Should return a ScrapingResult object.
        """
        pass

    async def cleanup(self):
        """Close the aiohttp session if it was created."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self.logger.info(f"Closed aiohttp session for {await self.get_source_name()}")