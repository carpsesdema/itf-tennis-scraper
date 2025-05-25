"""
Main application window for ITF Tennis Scraper.
"""
import asyncio

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget, QStatusBar,
    QProgressBar, QMenuBar, QMenu, QMessageBox, QSplitter
)
from PySide6.QtCore import QSettings, Signal, QTimer, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence

from ..config import Config
from ..core.engine import TennisScrapingEngine
from .components.matches_table import MatchesTable
from .components.control_panel import ControlPanel
from .components.settings_panel import SettingsPanel
from .components.status_bar import CustomStatusBar
from .dialogs.update_dialog import UpdateDialog
from .dialogs.export_dialog import ExportDialog
from .dialogs.about_dialog import AboutDialog
from .workers.scraping_worker import ScrapingWorker
from .workers.update_worker import UpdateWorker
from ..updates.checker import UpdateInfo # Import UpdateInfo
from ..utils.logging import get_logger


class MainWindow(QMainWindow):
    """Main application window."""

    status_updated = Signal(str)
    matches_updated = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = get_logger(__name__)
        self.settings = QSettings("TennisScraper", "ITFScraper")

        self.engine = TennisScrapingEngine(config.to_dict())
        self.scraping_worker = None
        self.update_worker = None

        self.matches_table = None
        self.control_panel = None
        self.settings_panel = None
        self.status_bar = None
        self.log_viewer = None # Added for consistency

        self.is_scraping = False
        self.auto_refresh_timer = QTimer()

        self._init_ui()
        self._create_menu_bar()
        self._connect_signals()
        self._load_settings()
        self._setup_auto_refresh()

    def _init_ui(self):
        self.setWindowTitle("ITF Tennis Match Scraper")
        self.setGeometry(100, 100, self.config.ui.window_width, self.config.ui.window_height)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self._create_matches_tab()
        self._create_settings_tab()
        self._create_logs_tab()

        self.status_bar = CustomStatusBar()
        self.setStatusBar(self.status_bar)

    def _create_matches_tab(self):
        matches_widget = QWidget()
        layout = QVBoxLayout(matches_widget)
        splitter = QSplitter(Qt.Vertical)
        self.control_panel = ControlPanel(self.config)
        splitter.addWidget(self.control_panel)
        self.matches_table = MatchesTable()
        splitter.addWidget(self.matches_table)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        self.tab_widget.addTab(matches_widget, "Live Matches")

    def _create_settings_tab(self):
        self.settings_panel = SettingsPanel(self.config)
        self.tab_widget.addTab(self.settings_panel, "Settings")

    def _create_logs_tab(self):
        from .components.log_viewer import LogViewer
        self.log_viewer = LogViewer()
        self.tab_widget.addTab(self.log_viewer, "Logs")

    def _create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        export_action = QAction("&Export Matches...", self)
        export_action.setShortcut(QKeySequence.Save)
        export_action.triggered.connect(self._show_export_dialog)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("&View")
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence.Refresh)
        refresh_action.triggered.connect(self._refresh_matches)
        view_menu.addAction(refresh_action)
        view_menu.addSeparator()
        self.auto_refresh_action = QAction("&Auto Refresh", self)
        self.auto_refresh_action.setCheckable(True)
        self.auto_refresh_action.setChecked(True)
        self.auto_refresh_action.triggered.connect(self._toggle_auto_refresh)
        view_menu.addAction(self.auto_refresh_action)

        tools_menu = menubar.addMenu("&Tools")
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1)) # Assuming settings is tab 1
        tools_menu.addAction(settings_action)
        tools_menu.addSeparator()
        update_action = QAction("Check for &Updates", self)
        update_action.triggered.connect(self.check_for_updates)
        tools_menu.addAction(update_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        self.control_panel.start_scraping.connect(self._start_scraping)
        self.control_panel.stop_scraping.connect(self._stop_scraping)
        self.control_panel.refresh_requested.connect(self._refresh_matches)
        self.control_panel.settings_changed.connect(self._on_settings_changed)

        self.settings_panel.settings_changed.connect(self._on_settings_changed)

        self.engine.on('scraping_completed_all', self._on_scraping_completed_all) # Adjusted event name
        self.engine.on('scraping_error', self._on_scraping_error)
        self.engine.on('scraper_completed', self._on_scraper_completed)

        self.auto_refresh_timer.timeout.connect(self._auto_refresh)

    def _setup_auto_refresh(self):
        interval_ms = self.config.ui.auto_refresh_interval * 1000
        self.auto_refresh_timer.setInterval(interval_ms)

    def _start_scraping(self):
        if self.is_scraping:
            return
        self.logger.info("Starting scraping process...")
        self.is_scraping = True
        self.control_panel.set_scraping_state(True)
        self.status_bar.show_progress("Starting scraping...")
        self.scraping_worker = ScrapingWorker(self.engine)
        self.scraping_worker.matches_updated.connect(self._on_matches_updated)
        self.scraping_worker.status_updated.connect(self.status_bar.set_status) # Direct status update
        self.scraping_worker.error_occurred.connect(self._on_scraping_error)
        self.scraping_worker.finished.connect(self._on_scraping_finished)
        self.scraping_worker.start()
        if self.auto_refresh_action.isChecked():
            self.auto_refresh_timer.start()

    def _stop_scraping(self):
        if not self.is_scraping:
            return
        self.logger.info("Stopping scraping process...")
        self.auto_refresh_timer.stop()
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.scraping_worker.stop() # Request stop
            # self.scraping_worker.wait(5000) # Wait for graceful exit
        # _on_scraping_finished will be called by the worker's finished signal

    def _refresh_matches(self):
        if self.is_scraping: # Don't manual refresh if continuous scraping is on
            self.logger.info("Manual refresh skipped: continuous scraping active.")
            return

        self.logger.info("Manual refresh requested")
        self.status_bar.show_progress("Refreshing...")
        self.control_panel.set_scraping_state(True) # Indicate activity

        # Use a one-time worker
        single_run_worker = ScrapingWorker(self.engine, single_run=True)
        single_run_worker.matches_updated.connect(self._on_matches_updated)
        single_run_worker.status_updated.connect(self.status_bar.set_status)
        single_run_worker.error_occurred.connect(self._on_scraping_error)
        single_run_worker.finished.connect(lambda: [
            self.status_bar.hide_progress(),
            self.control_panel.set_scraping_state(False) # Reset state after single run
        ])
        single_run_worker.start()

    def _auto_refresh(self):
        if not self.is_scraping: # Auto-refresh should only run if main scraping is "on"
            return
        self.logger.debug("Auto-refresh triggered")
        # Similar to manual refresh, but without GUI locks if already scraping
        # This logic might need refinement based on how continuous scraping is defined
        if self.scraping_worker and self.scraping_worker.isRunning():
             self.scraping_worker.request_single_run() # Ask existing worker to run again
        else:
            self._refresh_matches() # Or trigger a new one-off run if no worker active

    def _toggle_auto_refresh(self, enabled: bool):
        if enabled and self.is_scraping:
            self.auto_refresh_timer.start()
        else:
            self.auto_refresh_timer.stop()
        self.logger.info(f"Auto-refresh {'enabled' if enabled else 'disabled'}")
        # Persist this choice
        self.control_panel.auto_refresh_checkbox.setChecked(enabled)
        self.config.ui.show_live_only = enabled # Example: Tying to a config if needed

    def _on_matches_updated(self, matches: list):
        self.matches_table.update_matches(matches)
        live_count = len([m for m in matches if m.status == m.status.LIVE]) # Use MatchStatus enum
        total_count = len(matches)
        self.status_bar.set_live_count(live_count)
        self.status_bar.set_total_count(total_count)
        if not self.is_scraping: # If it was a single run
            self.status_bar.set_status(f"Refreshed: {total_count} matches, {live_count} live.")
            self.status_bar.hide_progress()
        else: # Continuous mode
            self.status_bar.set_status(f"Monitoring: {total_count} matches, {live_count} live.")

    def _on_scraping_completed_all(self, match_count: int, duration: float):
        message = f"Overall scraping completed: {match_count} matches in {duration:.1f}s"
        self.status_bar.set_status(message)
        self.logger.info(message)
        # This might not be the best place to hide progress if scraping is continuous

    def _on_scraping_error(self, error_msg: str, source_name: str = None): # Allow source_name
        full_error_msg = f"Error from {source_name}: {error_msg}" if source_name else f"Scraping error: {error_msg}"
        self.logger.error(full_error_msg)
        self.status_bar.set_status(f"Error: {error_msg[:50]}...", 5000) # Show brief error
        self.error_occurred.emit(full_error_msg) # Emit full error
        # Consider if this should stop scraping or just log and continue
        # For critical errors, QMessageBox.warning could be used.

    def _on_scraper_completed(self, scraper_name: str, match_count: int, duration_seconds: float):
        self.logger.debug(f"Scraper {scraper_name} completed: {match_count} matches in {duration_seconds:.2f}s")
        # Update progress bar if needed, or status

    def _on_scraping_finished(self):
        self.is_scraping = False
        self.control_panel.set_scraping_state(False)
        self.status_bar.hide_progress()
        self.status_bar.set_permanent_status("Scraping stopped.") # Or "Idle"
        self.auto_refresh_timer.stop()
        if self.scraping_worker:
            self.scraping_worker.deleteLater() # Clean up worker
            self.scraping_worker = None
        self.logger.info("Scraping process has finished or been stopped.")


    def _on_settings_changed(self):
        self.logger.info("Settings changed, updating configuration...")
        # self.config is already updated by SettingsPanel directly writing to it
        # Re-initialize engine with new config
        self.engine = TennisScrapingEngine(self.config.to_dict())
        self._setup_auto_refresh()
        if self.auto_refresh_action.isChecked() and self.is_scraping:
            self.auto_refresh_timer.start()

    def check_for_updates(self):
        self.logger.info("Checking for updates...")
        if self.update_worker and self.update_worker.isRunning():
            self.logger.info("Update check already in progress.")
            return

        # MainWindow passes its full Config object's 'updates' attribute.
        # UpdateWorker's __init__ expects a dictionary.
        update_cfg_dict = self.config.updates.__dict__ if hasattr(self.config.updates, '__dict__') else {}

        self.update_worker = UpdateWorker(update_cfg_dict)
        self.update_worker.update_available.connect(self._show_update_dialog)
        self.update_worker.no_update.connect(self._no_update_available)
        self.update_worker.check_failed.connect(self._update_check_failed)
        self.update_worker.check_for_updates() # Use the method to start the action
        self.status_bar.set_status("Checking for updates...")

    # --- MODIFIED: Expect UpdateInfo object ---
    def _show_update_dialog(self, update_info: UpdateInfo):
        self.status_bar.set_status("Update available!")
        # Pass the UpdateInfo object directly
        dialog = UpdateDialog(update_info, self)
        dialog.install_requested.connect(self._handle_install_request)
        dialog.show()
    # --- END MODIFICATION ---

    def _handle_install_request(self, file_path: str):
        self.logger.info(f"Install requested for: {file_path}. Closing application.")
        # Perform cleanup and close. The OS will handle installer launch.
        QMessageBox.information(self, "Update Installation",
                                f"The application will now close to install the update from:\n{file_path}\n"
                                "Please follow the installer prompts.")
        self.close() # Trigger application shutdown


    def _no_update_available(self):
        self.status_bar.set_status("You have the latest version!", 5000)
        QMessageBox.information(self, "Updates", "You are running the latest version!")

    def _update_check_failed(self, error: str):
        self.status_bar.set_status(f"Update check failed: {error[:30]}...", 5000)
        self.logger.warning(f"Update check failed: {error}")
        QMessageBox.warning(self, "Update Check Failed", f"Could not check for updates:\n{error}")


    def _show_export_dialog(self):
        if not self.matches_table or self.matches_table.get_match_count() == 0: # Check matches_table exists
            QMessageBox.information(self, "Export", "No matches to export.")
            return
        dialog = ExportDialog(self.matches_table.get_matches(), self)
        dialog.exec()

    def _show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def save_settings(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("currentTab", self.tab_widget.currentIndex())
        self.settings.setValue("autoRefresh", self.auto_refresh_action.isChecked())
        if self.control_panel: self.control_panel.save_settings(self.settings)
        if self.matches_table: self.matches_table.save_settings(self.settings)
        self.config.save_to_file()
        self.logger.info("Settings saved")

    def _load_settings(self):
        geometry = self.settings.value("geometry")
        if geometry: self.restoreGeometry(geometry)
        window_state = self.settings.value("windowState")
        if window_state: self.restoreState(window_state)
        current_tab = self.settings.value("currentTab", 0, int)
        self.tab_widget.setCurrentIndex(current_tab)
        auto_refresh = self.settings.value("autoRefresh", True, bool) # Default to True
        self.auto_refresh_action.setChecked(auto_refresh)
        if self.control_panel: self.control_panel.load_settings(self.settings)
        if self.matches_table: self.matches_table.load_settings(self.settings)
        self.logger.info("Settings loaded")

    def stop_all_workers(self):
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.scraping_worker.stop()
            self.scraping_worker.wait(3000) # Reduced wait
        if self.update_worker and self.update_worker.isRunning():
            self.update_worker.quit() # QThread quit
            self.update_worker.wait(1000) # Reduced wait
        if self.engine:
            async def do_cleanup(): # Define async cleanup locally
                await self.engine.cleanup()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(do_cleanup())
            except RuntimeError: # If no event loop is available or other issues
                 asyncio.run(do_cleanup()) # Fallback for simple cases
            finally:
                # If we created a new loop and it's not the main one, close it.
                # This part is tricky; be careful with event loop management.
                pass


    def closeEvent(self, event):
        self.logger.info("Application closeEvent triggered.")
        self.stop_all_workers()
        self.save_settings()
        self.logger.info("Application shutdown sequence complete.")
        event.accept()