"""
ScrapingWorker for handling match scraping - OPTIMIZED FOR SLOW COMPUTERS!
"""
import asyncio
import time
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition

from ...core.engine import TennisScrapingEngine
from ...utils.logging import get_logger


class ScrapingWorker(QThread):
    """
    OPTIMIZED Worker thread for slow computers.
    Reduces UI spam, longer intervals, gentler processing.
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

        # OPTIMIZED settings for slow computers
        self.refresh_interval = 600  # 10 minutes default (was 5 minutes)
        self.min_refresh_interval = 300  # Minimum 5 minutes (was 30 seconds)
        self.last_ui_update = 0  # Throttle UI updates
        self.ui_update_throttle = 10  # Only update UI every 10 seconds max

    def set_refresh_interval(self, seconds: int):
        """Set refresh interval with minimum for slow computers."""
        self.refresh_interval = max(self.min_refresh_interval, seconds)
        self.logger.info(f"🐌 Slow computer mode: Refresh interval set to {self.refresh_interval} seconds")

    async def _run_async_tasks(self):
        """Core async logic - OPTIMIZED for slow computers."""
        if self.single_run:
            await self._perform_single_scrape_slow()
        else:
            await self._perform_gentle_monitoring()

    async def _perform_single_scrape_slow(self):
        """Single scrape with slow computer optimizations."""
        try:
            self._throttled_status_update("🐌 Starting gentle scrape for slow computer...")
            self.logger.info("ScrapingWorker: Starting SLOW COMPUTER optimized single scrape")

            matches = await self.engine.get_filtered_matches()

            if self._stop_requested:
                self.logger.info("Stop requested during single scrape")
                return

            # Only update UI if we have meaningful results
            if matches:
                self.matches_updated.emit(matches)
                tie_break_count = len([m for m in matches if m.metadata.get('is_match_tie_break')])

                if tie_break_count > 0:
                    self._throttled_status_update(f"🚨 {tie_break_count} TIE BREAKS! Found {len(matches)} total matches")
                else:
                    self._throttled_status_update(f"✅ Found {len(matches)} bet365 matches")

                self.logger.info(f"Single scrape completed - {len(matches)} matches, {tie_break_count} tie breaks")
            else:
                self._throttled_status_update("No matches found")

        except Exception as e:
            self.logger.error(f"Single scrape error: {e}", exc_info=True)
            self.error_occurred.emit(f"Scrape failed: {str(e)[:100]}")
            self._throttled_status_update(f"❌ Error: {str(e)[:50]}")

    async def _perform_gentle_monitoring(self):
        """GENTLE monitoring for slow computers."""
        try:
            self.logger.info(f"🐌 Starting GENTLE monitoring for slow computer (interval: {self.refresh_interval}s)")

            cycle_count = 0

            while self.running and not self._stop_requested:
                cycle_count += 1
                scrape_start_time = time.time()

                self.logger.info(f"🔄 Monitoring cycle #{cycle_count} starting...")

                try:
                    self._throttled_status_update(f"🐌 Gentle monitoring cycle #{cycle_count}...")

                    # Get matches with gentle processing
                    matches = await self.engine.get_filtered_matches()

                    if self._stop_requested:
                        break

                    # Process results gently
                    if matches:
                        # Throttled UI update
                        self._throttled_ui_update(matches)

                        # Count important matches
                        live_count = len([m for m in matches if m.status.is_active])
                        tie_break_count = len([m for m in matches if m.metadata.get('is_match_tie_break')])
                        total_count = len(matches)

                        # Status message with tie break priority
                        if tie_break_count > 0:
                            status_msg = f"🚨 {tie_break_count} TIE BREAKS! {live_count} live, {total_count} total"
                            self.logger.critical(f"🚨 CYCLE #{cycle_count}: {tie_break_count} TIE BREAK MATCHES!")
                        else:
                            status_msg = f"🐌 Cycle #{cycle_count}: {live_count} live, {total_count} total"

                        self._throttled_status_update(status_msg)

                        scrape_duration = time.time() - scrape_start_time
                        self.logger.info(
                            f"Cycle #{cycle_count} completed in {scrape_duration:.1f}s - {total_count} matches")
                    else:
                        self._throttled_status_update(f"🐌 Cycle #{cycle_count}: No matches found")

                except Exception as e:
                    self.logger.error(f"Error in monitoring cycle #{cycle_count}: {e}", exc_info=True)
                    self.error_occurred.emit(f"Cycle {cycle_count} failed: {str(e)[:80]}")
                    self._throttled_status_update(f"❌ Cycle #{cycle_count} error: {str(e)[:30]}")

                # GENTLE wait with interrupt ability
                if not self._stop_requested and self.running:
                    self.logger.info(f"💤 Gentle sleep for {self.refresh_interval} seconds...")
                    await self._gentle_sleep(self.refresh_interval)

            self.logger.info(f"Gentle monitoring stopped after {cycle_count} cycles")

        except Exception as e:
            self.logger.error(f"Critical error in gentle monitoring: {e}", exc_info=True)
            self.error_occurred.emit(f"Monitoring system failed: {e}")

    async def _gentle_sleep(self, seconds: int):
        """Gentle sleep that can be interrupted and doesn't overwhelm slow systems."""
        # Sleep in 5-second chunks so we can be interrupted
        chunks = max(1, seconds // 5)
        chunk_size = seconds / chunks

        for i in range(int(chunks)):
            if self._stop_requested or not self.running:
                self.logger.info(f"Sleep interrupted after {i * chunk_size:.1f}s")
                break
            await asyncio.sleep(chunk_size)

    def _throttled_status_update(self, message: str):
        """Throttled status updates to not overwhelm slow UI."""
        current_time = time.time()
        if current_time - self.last_ui_update >= 5:  # Max one status update per 5 seconds
            self.status_updated.emit(message)
            self.last_ui_update = current_time
        else:
            # Just log it instead of spamming UI
            self.logger.debug(f"Throttled status: {message}")

    def _throttled_ui_update(self, matches):
        """Throttled UI updates for slow computers."""
        current_time = time.time()
        # Only update matches UI every 10 seconds max
        if current_time - self.last_ui_update >= self.ui_update_throttle:
            self.matches_updated.emit(matches)
            self.last_ui_update = current_time
            self.logger.debug(f"UI updated with {len(matches)} matches")
        else:
            self.logger.debug(f"UI update throttled - {len(matches)} matches ready")

    def run(self):
        """
        Main execution method - OPTIMIZED for slow computers.
        """
        self.logger.info(f"🐌 ScrapingWorker starting in SLOW COMPUTER mode. Single run: {self.single_run}")
        self.running = True
        self._stop_requested = False

        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Give slow computer a moment to breathe
            time.sleep(2)

            # Run the main async task
            self._loop.run_until_complete(self._run_async_tasks())

        except Exception as e:
            self.logger.critical(f"Unhandled exception in worker: {e}", exc_info=True)
            self.error_occurred.emit(f"Worker crashed: {e}")
        finally:
            if self._loop and not self._loop.is_closed():
                try:
                    # Gentle cleanup
                    self.logger.debug("Shutting down async tasks...")
                    pending_tasks = asyncio.all_tasks(self._loop)
                    for task in pending_tasks:
                        task.cancel()

                    # Give tasks time to cancel
                    if pending_tasks:
                        self._loop.run_until_complete(asyncio.sleep(1))

                    self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                    self._loop.close()
                except Exception as e:
                    self.logger.warning(f"Cleanup error: {e}")

            self.logger.info("🐌 ScrapingWorker finished gracefully")
            self.running = False
            self.scraping_really_finished.emit()

    def stop(self):
        """Request worker to stop gently."""
        self.logger.info("🛑 ScrapingWorker: Gentle stop requested for slow computer")
        self._mutex.lock()
        self.running = False
        self._stop_requested = True
        self._mutex.unlock()
        self._condition.wakeAll()

        # Give slow computer extra time to process stop request
        time.sleep(1)
        self.logger.debug("Stop request processed for slow computer mode")