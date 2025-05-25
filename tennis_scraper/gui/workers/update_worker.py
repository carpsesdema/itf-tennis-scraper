"""
UpdateWorker for checking and downloading application updates in a separate thread.
"""
import asyncio
from typing import Optional
from PySide6.QtCore import QThread, Signal

from ...updates.checker import GitHubUpdateChecker, UpdateInfo  # Adjusted import
from ...utils.logging import get_logger
from ... import __version__  # To get current app version


class UpdateWorker(QThread):
    """
    Worker thread for checking and downloading application updates.
    """
    update_available = Signal(dict)  # Emits UpdateInfo as a dict
    no_update = Signal()
    check_failed = Signal(str)
    download_progress = Signal(int)  # Percentage 0-100

    # download_complete = Signal(str) # Filepath - UpdateInfo from update_available can contain this
    # download_failed = Signal(str)   # Error message - check_failed can cover this too

    def __init__(self, update_config: dict, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        # Pass the 'updates' part of the main config, or specific fields needed by checker
        self.update_checker = GitHubUpdateChecker(update_config)
        self.update_checker.current_version = __version__  # Set current version
        self._loop = None
        self._action = "check"  # "check" or "download"
        self._update_info_to_download: Optional[UpdateInfo] = None

    def _run_check_for_updates(self):
        """Async task to check for updates."""

        async def check_async():
            try:
                self.logger.info("UpdateWorker: Checking for updates...")
                update_info: Optional[UpdateInfo] = await self.update_checker.check_for_updates()
                if update_info:
                    self.logger.info(f"UpdateWorker: Update found - {update_info.version}")
                    self.update_available.emit(update_info.__dict__)  # Emit as dict
                else:
                    self.logger.info("UpdateWorker: No new updates found.")
                    self.no_update.emit()
            except Exception as e:
                self.logger.error(f"UpdateWorker: Update check failed: {e}", exc_info=True)
                self.check_failed.emit(str(e))

        if not self._loop or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._loop.run_until_complete(check_async())

    def _run_download_update(self):
        """Async task to download an update."""

        async def download_async():
            if not self._update_info_to_download:
                self.check_failed.emit("No update information provided for download.")
                return
            try:
                self.logger.info(f"UpdateWorker: Downloading update {self._update_info_to_download.version}...")

                def progress_callback(progress_value: int):
                    self.download_progress.emit(progress_value)

                file_path: Optional[str] = await self.update_checker.download_update(
                    self._update_info_to_download,
                    progress_callback=progress_callback
                )
                if file_path:
                    self.logger.info(f"UpdateWorker: Download complete - {file_path}")
                    # The update_available signal is reused here to pass the UpdateInfo
                    # object which now includes the local_file path.
                    # Or, we could have a dedicated download_complete signal.
                    # For simplicity, let's assume the UpdateInfo object is updated by the downloader
                    # and re-emitted, or the receiver handles the file_path.
                    # Let's emit update_info again, assuming it might be augmented with local_file path
                    # by the download_update method (or we create a specific signal)

                    # Re-emit update_available with potentially augmented info (e.g., local file path)
                    # This is a bit of a misuse; a dedicated download_complete(str_filepath) would be cleaner.
                    # For now, let's assume the dialog handles the file path if it gets one.
                    # We'll emit the original update_info dict, the dialog can handle it.
                    augmented_info = self._update_info_to_download.__dict__.copy()
                    augmented_info['local_file'] = file_path  # Add local file path
                    self.update_available.emit(augmented_info)  # Re-emitting this for simplicity
                    # UpdateDialog expects a dict.
                else:
                    self.logger.error("UpdateWorker: Download failed, no file path returned.")
                    self.check_failed.emit("Download process failed.")  # Generic error
            except Exception as e:
                self.logger.error(f"UpdateWorker: Update download failed: {e}", exc_info=True)
                self.check_failed.emit(str(e))

        if not self._loop or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._loop.run_until_complete(download_async())

    def run(self):
        """Main execution method for the QThread."""
        self.logger.info(f"UpdateWorker thread started for action: {self._action}")
        try:
            if self._action == "check":
                self._run_check_for_updates()
            elif self._action == "download":
                self._run_download_update()
        except Exception as e:
            self.logger.critical(f"UpdateWorker: Unhandled exception in run loop: {e}", exc_info=True)
            self.check_failed.emit(f"Critical worker error: {e}")
        finally:
            if self._loop and self._loop.is_running():
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                self._loop.close()
            self.logger.info(f"UpdateWorker thread for action '{self._action}' finished.")

    def check_for_updates(self):
        """Public method to trigger an update check."""
        self._action = "check"
        self.start()  # QThread.start() calls run()

    def download_update(self, update_info_dict: dict):
        """Public method to trigger an update download."""
        try:
            # Reconstruct UpdateInfo object from dict
            # This is needed because QSignals can't directly pass complex custom objects
            # if they aren't registered with Qt's metatype system. Sending dicts is safer.
            self._update_info_to_download = UpdateInfo(**update_info_dict)
            self._action = "download"
            self.start()
        except TypeError as te:
            self.logger.error(f"Failed to reconstruct UpdateInfo from dict: {te} - Data: {update_info_dict}")
            self.check_failed.emit("Internal error: Invalid update data for download.")

    def stop(self):  # QThreads are often quit() then wait()
        self.logger.info("UpdateWorker: Stop requested (terminating loop if running).")
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.quit()  # Request thread termination