"""
ScrapingWorker for handling match scraping in a separate thread.
FIXED VERSION with proper continuous monitoring!
"""
import asyncio
import time
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition

from ...core.engine import TennisScrapingEngine
from ...utils.logging import get_logger


class ScrapingWorker(QThread):
    """
    Worker thread for performing tennis match scraping asynchronously.
    Now properly supports continuous monitoring!
    """
    matches_updated = Signal(list)  # Emits List[TennisMatch]
    status_updated = Signal(str)  # Emits status messages
    error_occurred = Signal(str)  # Emits error messages
    scraping_really_finished = Signal()  # To signal actual completion

    def __init__(self, engine: TennisScrapingEngine, single_run: bool = False, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.engine = engine
        self.single_run = single_run
        self.running = False
        self._loop = None

        # For graceful shutdown
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        self._stop_requested = False

        # Monitoring settings
        self.refresh_interval = 300  # 5 minutes default

    def set_refresh_interval(self, seconds: int):
        """Set the refresh interval for continuous monitoring."""
        self.refresh_interval = max(30, seconds)  # Minimum 30 seconds
        self.logger.info(f"Refresh interval set to {self.refresh_interval} seconds")

    async def _run_async_tasks(self):
        """The core async logic for scraping."""
        if self.single_run:
            # Single run mode
            await self._perform_single_scrape()
        else:
            # Continuous monitoring mode
            await self._perform_continuous_monitoring()

    async def _perform_single_scrape(self):
        """Perform a single scraping operation."""
        try:
            self.status_updated.emit("Scraping matches...")
            self.logger.info("ScrapingWorker: Starting single scrape.")

            matches = await self.engine.get_filtered_matches()

            if self._stop_requested:
                self.logger.info("ScrapingWorker: Stop requested during single scrape.")
                return

            self.matches_updated.emit(matches)
            self.status_updated.emit(f"Found {len(matches)} matches.")
            self.logger.info(f"ScrapingWorker: Single scrape completed - {len(matches)} matches.")

        except Exception as e:
            self.logger.error(f"ScrapingWorker: Error during single scrape: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
            self.status_updated.emit(f"Error: {e}")

    async def _perform_continuous_monitoring(self):
        """Perform continuous monitoring with periodic scraping."""
        try:
            self.logger.info(f"ScrapingWorker: Starting continuous monitoring (interval: {self.refresh_interval}s)")

            while self.running and not self._stop_requested:
                scrape_start_time = time.time()

                try:
                    self.status_updated.emit("Monitoring matches...")

                    # Perform scrape
                    matches = await self.engine.get_filtered_matches()

                    if self._stop_requested:
                        break

                    # Emit results
                    self.matches_updated.emit(matches)

                    # Update status with live count
                    live_count = len([m for m in matches if m.status.is_active])
                    tie_break_count = len([m for m in matches if m.metadata.get('is_match_tie_break')])

                    if tie_break_count > 0:
                        self.status_updated.emit(
                            f"🚨 {tie_break_count} TIE BREAKS! {live_count} live, {len(matches)} total")
                        self.logger.critical(f"🚨 {tie_break_count} TIE BREAK MATCHES DETECTED!")
                    else:
                        self.status_updated.emit(f"Monitoring: {live_count} live, {len(matches)} total matches")

                    scrape_duration = time.time() - scrape_start_time
                    self.logger.info(
                        f"ScrapingWorker: Scrape completed in {scrape_duration:.1f}s - {len(matches)} matches, {live_count} live")

                except Exception as e:
                    self.logger.error(f"ScrapingWorker: Error during monitoring cycle: {e}", exc_info=True)
                    self.error_occurred.emit(str(e))
                    self.status_updated.emit(f"Monitoring error: {str(e)[:50]}")

                # Wait for next cycle (with ability to be interrupted)
                if not self._stop_requested and self.running:
                    await self._interruptible_sleep(self.refresh_interval)

            self.logger.info("ScrapingWorker: Continuous monitoring stopped")

        except Exception as e:
            self.logger.error(f"ScrapingWorker: Critical error in continuous monitoring: {e}", exc_info=True)
            self.error_occurred.emit(f"Monitoring failed: {e}")

    async def _interruptible_sleep(self, seconds: int):
        """Sleep that can be interrupted by stop request."""
        for _ in range(seconds):
            if self._stop_requested or not self.running:
                break
            await asyncio.sleep(1)

    def run(self):
        """
        Main execution method for the QThread.
        Sets up an asyncio event loop to run the async scraping logic.
        """
        self.logger.info(f"ScrapingWorker thread started. Single run: {self.single_run}")
        self.running = True
        self._stop_requested = False

        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Run the main async task
            self._loop.run_until_complete(self._run_async_tasks())

        except Exception as e:
            self.logger.critical(f"ScrapingWorker: Unhandled exception in run loop: {e}", exc_info=True)
            self.error_occurred.emit(f"Critical worker error: {e}")
        finally:
            if self._loop and self._loop.is_running():
                self.logger.debug("ScrapingWorker: Shutting down async tasks and closing loop.")
                tasks = asyncio.all_tasks(self._loop)
                for task in tasks:
                    task.cancel()
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                self._loop.close()
            self.logger.info("ScrapingWorker thread finished.")
            self.running = False
            self.scraping_really_finished.emit()

    def stop(self):
        """Requests the worker to stop."""
        self.logger.info("ScrapingWorker: Stop requested.")
        self._mutex.lock()
        self.running = False
        self._stop_requested = True
        self._mutex.unlock()
        self._condition.wakeAll()

        self.logger.debug("ScrapingWorker: Stop request processed.")