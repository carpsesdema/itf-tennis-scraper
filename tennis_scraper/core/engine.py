import asyncio
import time
from typing import List, Dict, Any, Callable

from .models import TennisMatch, ScrapingResult
from .interfaces import MatchScraper, MatchFilter
from ..scrapers.flashscore import FlashscoreScraper
# Removed Sofascore import as it's not used
# from ..scrapers.sofascore import SofascoreScraper
from ..utils.logging import get_logger, PerformanceLogger


class TennisScrapingEngine:
    """Main engine for coordinating tennis match scraping."""

    def __init__(self, config: Dict[str, Any]):
        self.config_dict = config
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
            # 'sofascore': SofascoreScraper, # Removed as per your update
        }

        for name, ScraperClass in scraper_classes.items():
            if sources_enabled.get(name, False):
                cfg_for_scraper = self.scraping_config.copy()
                self.scrapers[name] = ScraperClass(cfg_for_scraper)
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
        unique_match_identifiers = set()

        tasks = []
        for source_name_key, scraper in self.scrapers.items():
            if await scraper.is_available():
                self.logger.info(f"Queueing scrape task for {source_name_key}")
                tasks.append(self._scrape_single_source(scraper))
            else:
                actual_scraper_name = await scraper.get_source_name()
                self.logger.warning(f"Source {actual_scraper_name} is not available, skipping.")
                self._emit("scraper_unavailable", actual_scraper_name)


        results: List[ScrapingResult] = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Exception during scraping gather: {result}", exc_info=True)
                self._emit("scraping_error", str(result))
                continue

            if not isinstance(result, ScrapingResult):
                self.logger.error(f"Unexpected result type from scraper: {type(result)}")
                continue

            source_name = result.source
            if result.success:
                if result.duration_seconds is not None:
                    self.logger.info(f"Successfully scraped {len(result.matches)} matches from {source_name} in {result.duration_seconds:.2f}s (Note: this count is from the end of the scrape, not individual emissions)")
                else:
                    self.logger.info(f"Successfully scraped {len(result.matches)} matches from {source_name} (duration not reported)")
                self._emit("scraper_completed", source_name, len(result.matches), result.duration_seconds)

                # The main list `all_scraped_matches` is populated at the end to ensure uniqueness
                # Individual matches are emitted by the `_on_individual_match_found` callback during the scrape
                for match in result.matches:
                    match_key_attrs = [
                        match.home_player.name,
                        match.away_player.name,
                        match.tournament,
                        match.scheduled_time.date() if match.scheduled_time else "NoTime"
                    ]
                    match_key_tuple = tuple(str(attr) if attr is not None else "None" for attr in match_key_attrs)

                    if match.match_id:
                        match_key = (match.source, match.match_id)
                    else:
                        match_key = (match.source, ) + match_key_tuple

                    if match_key not in unique_match_identifiers:
                        all_scraped_matches.append(match)
                        unique_match_identifiers.add(match_key)
                    else:
                        self.logger.debug(f"Duplicate match (in final consolidation) skipped: {match.match_title} from {match.source} with key {match_key}")
            else:
                self.logger.error(f"Failed to scrape {source_name}: {result.error_message}")
                self._emit("scraper_error", source_name, result.error_message)

        duration = time.monotonic() - start_time
        self.logger.info(f"Consolidated {len(all_scraped_matches)} unique matches from all sources in {duration:.2f}s")
        self._emit("scraping_completed_all", len(all_scraped_matches), duration)

        return all_scraped_matches

    async def _on_individual_match_found(self, match: TennisMatch):
        """Callback to be passed to scrapers, emits an event for each match."""
        self.logger.debug(f"Engine received individual match: {match.match_title} from {match.source}")
        self._emit("individual_match_found", match)


    async def _scrape_single_source(self, scraper: MatchScraper) -> ScrapingResult:
        source_name = await scraper.get_source_name()
        self.logger.info(f"Starting scrape for {source_name}...")
        self._emit("scraper_started", source_name)
        start_source_time = time.monotonic()
        try:
            if hasattr(scraper, 'scrape_with_retry') and asyncio.iscoroutinefunction(scraper.scrape_with_retry):
                self.logger.debug(f"Using scrape_with_retry for {source_name}")
                # Pass the callback to scrape_with_retry, which will pass it to scrape_matches
                scraping_result = await scraper.scrape_with_retry(progress_callback=self._on_individual_match_found)
            else:
                self.logger.debug(f"Using direct scrape_matches for {source_name}")
                 # Pass the callback directly to scrape_matches
                scraping_result = await scraper.scrape_matches(progress_callback=self._on_individual_match_found)

            if scraping_result.duration_seconds is None:
                scraping_result.duration_seconds = time.monotonic() - start_source_time
                self.logger.debug(f"Manually set duration for {source_name}: {scraping_result.duration_seconds:.2f}s")

            return scraping_result
        except Exception as e:
            self.logger.error(f"Critical error scraping {source_name}: {e}", exc_info=True)
            duration = time.monotonic() - start_source_time
            return ScrapingResult(
                source=source_name,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )

    async def get_filtered_matches(self) -> List[TennisMatch]:
        """Get matches with all filters applied."""
        matches = await self.scrape_all_sources() # This now just returns the final list
        self.logger.info(f"Applying {len(self.filters)} filters to {len(matches)} matches (post-scrape).")
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