"""
Core scraping engine for ITF Tennis Scraper.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable

from .models import TennisMatch, ScrapingResult
from .interfaces import MatchScraper, MatchFilter
from ..scrapers.flashscore import FlashscoreScraper
from ..scrapers.sofascore import SofascoreScraper
# from ..scrapers.itf_official import ITFOfficialScraper # Assuming you'll create this later
from ..utils.logging import get_logger, PerformanceLogger


class TennisScrapingEngine:
    """Main engine for coordinating tennis match scraping."""

    def __init__(self, config: Dict[str, Any]):
        self.config_dict = config  # Store the raw config dict
        self.scraping_config = config.get('scraping', {})
        self.logger = get_logger(__name__)
        self.scrapers: Dict[str, MatchScraper] = {}
        self.filters: List[MatchFilter] = []
        self.event_listeners: Dict[str, List[Callable]] = {}
        self._init_scrapers()
        self.performance_logger = PerformanceLogger()

    def _init_scrapers(self):
        """Initialize available scrapers based on configuration."""
        sources_enabled = self.scraping_config.get('sources_enabled', {})

        scraper_classes = {
            'flashscore': FlashscoreScraper,
            'sofascore': SofascoreScraper,
            # 'itf_official': ITFOfficialScraper, # Add when implemented
        }

        for name, ScraperClass in scraper_classes.items():
            if sources_enabled.get(name, False):
                # Pass the 'scraping' part of the config to individual scrapers
                scraper_config = self.scraping_config
                self.scrapers[name] = ScraperClass(scraper_config)
                self.logger.info(f"Initialized scraper: {name}")
            else:
                self.logger.info(f"Scraper disabled by config: {name}")

    def on(self, event_name: str, callback: Callable):
        """Register an event listener."""
        if event_name not in self.event_listeners:
            self.event_listeners[event_name] = []
        self.event_listeners[event_name].append(callback)

    def _emit(self, event_name: str, *args, **kwargs):
        """Emit an event to all registered listeners."""
        if event_name in self.event_listeners:
            for callback in self.event_listeners[event_name]:
                try:
                    # If callback is async, schedule it
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(*args, **kwargs))
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Error in event listener for '{event_name}': {e}")

    async def scrape_all_sources(self) -> List[TennisMatch]:
        """
        Scrape matches from all enabled sources asynchronously.
        Returns a consolidated list of unique matches.
        """
        self.logger.info("Starting scrape_all_sources...")
        self._emit("scraping_started")
        start_time = time.monotonic()

        all_scraped_matches: List[TennisMatch] = []
        unique_match_identifiers = set() # To handle duplicates across sources

        tasks = []
        for source_name, scraper in self.scrapers.items():
            if await scraper.is_available():
                self.logger.info(f"Queueing scrape task for {source_name}")
                tasks.append(self._scrape_single_source(scraper))
            else:
                self.logger.warning(f"Source {scraper.get_source_name()} is not available, skipping.")
                self._emit("scraper_unavailable", await scraper.get_source_name())

        results: List[ScrapingResult] = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Exception during scraping gather: {result}")
                self._emit("scraping_error", str(result))
                continue # Skip to next result

            if not isinstance(result, ScrapingResult):
                self.logger.error(f"Unexpected result type from scraper: {type(result)}")
                continue

            source_name = result.source
            if result.success:
                self.logger.info(f"Successfully scraped {len(result.matches)} matches from {source_name} in {result.duration_seconds:.2f}s")
                self._emit("scraper_completed", source_name, len(result.matches), result.duration_seconds)

                # Add matches, ensuring uniqueness
                for match in result.matches:
                    # Use a tuple of key attributes for uniqueness check
                    match_key = (match.home_player.name, match.away_player.name, match.tournament, match.scheduled_time.date() if match.scheduled_time else None)
                    if match.match_id: # Prefer source-specific ID if available
                        match_key = (match.source, match.match_id)

                    if match_key not in unique_match_identifiers:
                        all_scraped_matches.append(match)
                        unique_match_identifiers.add(match_key)
                    else:
                        self.logger.debug(f"Duplicate match skipped: {match.match_title} from {match.source}")

            else:
                self.logger.error(f"Failed to scrape {source_name}: {result.error_message}")
                self._emit("scraper_error", source_name, result.error_message)

        duration = time.monotonic() - start_time
        self.logger.info(f"Consolidated {len(all_scraped_matches)} unique matches from all sources in {duration:.2f}s")
        self._emit("scraping_completed", len(all_scraped_matches), duration)

        return all_scraped_matches

    async def _scrape_single_source(self, scraper: MatchScraper) -> ScrapingResult:
        """Helper to scrape a single source and handle its result/errors."""
        source_name = await scraper.get_source_name()
        self.logger.info(f"Starting scrape for {source_name}...")
        self._emit("scraper_started", source_name)
        try:
            with self.performance_logger.time_block(f"scrape_{source_name}"):
                # The scraper's scrape_matches should return a ScrapingResult
                scraping_result = await scraper.scrape_matches()
            # Augment with duration if not set by scraper
            if scraping_result.duration_seconds is None:
                scraping_result.duration_seconds = self.performance_logger.get_last_duration(f"scrape_{source_name}")
            return scraping_result
        except Exception as e:
            self.logger.error(f"Critical error scraping {source_name}: {e}", exc_info=True)
            duration = self.performance_logger.get_last_duration(f"scrape_{source_name}")
            return ScrapingResult(
                source=source_name,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )

    async def get_filtered_matches(self) -> List[TennisMatch]:
        """Get matches with all filters applied."""
        matches = await self.scrape_all_sources()
        self.logger.info(f"Applying {len(self.filters)} filters to {len(matches)} matches.")
        self._emit("filters_applying", len(matches), len(self.filters))

        for filter_instance in self.filters:
            try:
                matches = filter_instance.filter_matches(matches)
                self.logger.info(f"Applied filter '{filter_instance.get_filter_name()}', {len(matches)} matches remaining")
                self._emit("filter_applied", filter_instance.get_filter_name(), len(matches))
            except Exception as e:
                self.logger.error(f"Error applying filter '{filter_instance.get_filter_name()}': {e}")
                self._emit("filter_error", filter_instance.get_filter_name(), str(e))

        self.logger.info(f"Filtering complete. {len(matches)} matches remaining.")
        self._emit("filters_completed", len(matches))
        return matches

    def add_filter(self, filter_instance: MatchFilter):
        """Add a filter to the engine."""
        if filter_instance not in self.filters:
            self.filters.append(filter_instance)
            self.logger.info(f"Added filter: {filter_instance.get_filter_name()}")
            self._emit("filter_added", filter_instance.get_filter_name())

    def remove_filter(self, filter_name: str):
        """Remove a filter from the engine by its name."""
        initial_len = len(self.filters)
        self.filters = [f for f in self.filters if f.get_filter_name() != filter_name]
        if len(self.filters) < initial_len:
            self.logger.info(f"Removed filter: {filter_name}")
            self._emit("filter_removed", filter_name)
        else:
            self.logger.warning(f"Filter not found for removal: {filter_name}")

    def clear_filters(self):
        """Remove all filters."""
        self.filters.clear()
        self.logger.info("All filters cleared.")
        self._emit("filters_cleared")

    async def cleanup(self):
        """Cleanup resources for all scrapers."""
        self.logger.info("Cleaning up scraper resources...")
        for scraper in self.scrapers.values():
            try:
                await scraper.cleanup()
            except Exception as e:
                scraper_name = "UnknownScraper"
                try:
                    scraper_name = await scraper.get_source_name()
                except: pass
                self.logger.error(f"Error during cleanup for {scraper_name}: {e}")
        self.logger.info("Scraper cleanup complete.")