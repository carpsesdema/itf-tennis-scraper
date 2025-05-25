"""
ScrapingWorker for handling match scraping in a separate thread.
"""
import asyncio
import time
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition

from ...core.engine import TennisScrapingEngine
from ...utils.logging import get_logger


class ScrapingWorker(QThread):
    """
    Worker thread for performing tennis match scraping asynchronously.
    """
    matches_updated = Signal(list)  # Emits List[TennisMatch]
    status_updated = Signal(str)  # Emits status messages
    error_occurred = Signal(str)  # Emits error messages
    scraping_really_finished = Signal()  # To signal actual completion of run method

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

    async def _run_async_tasks(self):
        """The core async logic for scraping."""
        try:
            self.status_updated.emit("Scraping matches...")
            self.logger.info("ScrapingWorker: Starting async match retrieval.")

            # Connect to engine events if they are implemented and needed for detailed progress
            # self.engine.on('scraper_started', lambda name: self.status_updated.emit(f"Scraping {name}..."))
            # self.engine.on('scraper_completed', lambda name, count, dur: self.logger.info(f"{name} done: {count} in {dur:.2f}s"))

            matches = await self.engine.get_filtered_matches()  # This is an async call

            if self._stop_requested:
                self.logger.info("ScrapingWorker: Stop requested during match retrieval.")
                return

            self.matches_updated.emit(matches)
            self.status_updated.emit(f"Found {len(matches)} matches.")
            self.logger.info(f"ScrapingWorker: Emitted {len(matches)} matches.")

        except asyncio.CancelledError:
            self.logger.info("ScrapingWorker: Async task was cancelled.")
            self.status_updated.emit("Scraping cancelled.")
        except Exception as e:
            self.logger.error(f"ScrapingWorker: Error during async scraping: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
            self.status_updated.emit(f"Error: {e}")
        finally:
            self.logger.info("ScrapingWorker: Async task part finished.")

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

            if self.single_run:
                self.logger.debug("ScrapingWorker: Executing single run.")
                self._loop.run_until_complete(self._run_async_tasks())
            else:
                # This part is for continuous scraping if you re-implement that feature.
                # For now, assuming MainWindow controls periodic calls via single_run workers
                # or a QTimer that triggers single_run workers.
                # If you need continuous background loop here:
                # while self.running and not self._stop_requested:
                #     self.logger.debug("ScrapingWorker: Starting periodic scrape.")
                #     self._loop.run_until_complete(self._run_async_tasks())
                #     if self._stop_requested or not self.running: break
                #     # Wait for an interval or a signal to rescrape
                #     # This requires careful handling of self.running and _stop_requested
                #     # For example, using asyncio.sleep() or waiting on an asyncio.Event
                #     interval = getattr(self, 'interval_seconds', 300) # Example: get interval from an attribute
                #     self.logger.debug(f"ScrapingWorker: Waiting for {interval}s for next scrape.")
                #     for _ in range(interval): # Breakable sleep
                #         if self._stop_requested or not self.running: break
                #         time.sleep(1)
                self.logger.warning(
                    "ScrapingWorker: Continuous mode not fully implemented here, assuming single runs controlled externally.")
                # For now, if not single_run, it just does one run and exits.
                # MainWindow's timer should re-create and start this worker for periodic refreshes.
                if not self.single_run:  # Perform one run if started in non-single_run mode.
                    self._loop.run_until_complete(self._run_async_tasks())


        except Exception as e:
            self.logger.critical(f"ScrapingWorker: Unhandled exception in run loop: {e}", exc_info=True)
            self.error_occurred.emit(f"Critical worker error: {e}")
        finally:
            if self._loop and self._loop.is_running():
                self.logger.debug("ScrapingWorker: Shutting down async tasks and closing loop.")
                # Gather all remaining tasks and cancel them
                tasks = asyncio.all_tasks(self._loop)
                for task in tasks:
                    task.cancel()
                # Run loop until all tasks are cancelled
                # self._loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True)) # This line can hang if not careful
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())  # Ensure async generators are closed
                self._loop.close()
            self.logger.info("ScrapingWorker thread finished.")
            self.running = False
            self.scraping_really_finished.emit()  # Ensure this is emitted

    def stop(self):
        """Requests the worker to stop."""
        self.logger.info("ScrapingWorker: Stop requested.")
        self._mutex.lock()
        self.running = False
        self._stop_requested = True
        self._mutex.unlock()
        self._condition.wakeAll()  # Wake up if waiting on something

        if self._loop and self._loop.is_running():
            self.logger.debug("ScrapingWorker: Requesting stop via loop.call_soon_threadsafe.")
            # If the loop is running an async task, it needs to be interrupted.
            # This is complex. For now, rely on the task checking _stop_requested.
            # A more robust way would be to cancel the specific asyncio task.
            # self._loop.call_soon_threadsafe(self._loop.stop) # This stops the loop, might be too abrupt.
            pass

        self.logger.debug("ScrapingWorker: Stop request processed.")