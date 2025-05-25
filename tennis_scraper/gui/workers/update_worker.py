"""
Worker threads for GUI operations.
"""
import asyncio
from PySide6.QtCore import QThread, Signal
from typing import Optional, Dict, Any

from ...updates.checker import GitHubUpdateChecker, UpdateInfo # Ensure UpdateInfo is imported
from ...updates.downloader import UpdateDownloader
from ...utils.logging import get_logger
from ...config import UpdateConfig # For type hinting if UpdateConfig object is passed
from dataclasses import asdict


class UpdateWorker(QThread):
    """Worker for checking and downloading updates."""

    update_available = Signal(UpdateInfo)  # Emits UpdateInfo OBJECT
    no_update = Signal()
    check_failed = Signal(str)

    download_progress = Signal(int)
    update_downloaded = Signal(UpdateInfo) # Emits UpdateInfo OBJECT with local_file_path
    download_failed = Signal(str)

    def __init__(self, update_config_data: Dict[str, Any]): # Expects a dict from Config.updates
        super().__init__()
        self.logger = get_logger(__name__)
        # GitHubUpdateChecker expects an UpdateConfig object, not a dict.
        # So we construct it here.
        try:
            self.update_config_obj = UpdateConfig(**update_config_data)
        except TypeError as e:
            self.logger.error(f"Failed to create UpdateConfig from dict: {update_config_data}. Error: {e}")
            # Fallback or re-raise
            self.update_config_obj = UpdateConfig() # Default fallback
            # It's critical this object is valid for GitHubUpdateChecker
        self.update_checker = GitHubUpdateChecker(self.update_config_obj)
        self.downloader = UpdateDownloader()
        self.action: Optional[str] = None
        self.update_info_to_download: Optional[UpdateInfo] = None

    def _check_async(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self.logger.info("UpdateWorker: Checking for updates...")
            update_info_obj: Optional[UpdateInfo] = loop.run_until_complete(self.update_checker.check_for_updates())
            if update_info_obj:
                self.logger.info(f"UpdateWorker: Update found - {update_info_obj.version}")
                self.update_available.emit(update_info_obj) # EMIT THE OBJECT
            else:
                self.logger.info("UpdateWorker: No update available.")
                self.no_update.emit()
        except Exception as e:
            self.logger.error(f"UpdateWorker: Update check failed: {e}", exc_info=True)
            self.check_failed.emit(str(e))
        finally:
            loop.close()

    def _download_async(self):
        if not self.update_info_to_download:
            self.logger.error("UpdateWorker: No UpdateInfo provided for download.")
            self.download_failed.emit("Internal error: Update information missing.")
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self.logger.info(f"UpdateWorker: Downloading update {self.update_info_to_download.version}...")
            def progress_cb(progress_val):
                self.download_progress.emit(progress_val)

            file_path: Optional[str] = loop.run_until_complete(
                self.downloader.download(self.update_info_to_download, progress_cb)
            )

            if file_path:
                self.logger.info(f"UpdateWorker: Download complete - {file_path}")
                self.update_info_to_download.local_file_path = file_path
                self.update_downloaded.emit(self.update_info_to_download) # EMIT THE OBJECT
            else:
                self.logger.error("UpdateWorker: Download failed (no file path returned).")
                self.download_failed.emit("Download operation failed to return a file path.")
        except Exception as e:
            self.logger.error(f"UpdateWorker: Update download failed: {e}", exc_info=True)
            self.download_failed.emit(str(e))
        finally:
            loop.close()

    def run(self):
        if not self.action:
            self.logger.error("UpdateWorker: No action specified.")
            return

        self.logger.info(f"UpdateWorker thread started for action: {self.action}")
        if self.action == 'check':
            self._check_async()
        elif self.action == 'download':
            if self.update_info_to_download:
                self._download_async()
            else:
                self.logger.error("UpdateWorker: Download action triggered but no UpdateInfo set.")
                self.download_failed.emit("Cannot download: Update details not provided.")
        else:
            self.logger.warning(f"UpdateWorker: Unknown action '{self.action}'")
        self.logger.info(f"UpdateWorker thread for action '{self.action}' finished.")

    def check_for_updates(self):
        self.action = "check"
        self.start()

    def trigger_download(self, update_info: UpdateInfo):
        self.action = "download"
        self.update_info_to_download = update_info
        self.start()