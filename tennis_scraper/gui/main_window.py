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
from ..updates.checker import UpdateInfo  # Import UpdateInfo
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
        self.log_viewer = None  # Added for consistency

        self.is_scraping = False
        # Removed auto_refresh_timer since ScrapingWorker handles this internally

        self._init_ui()
        self._create_menu_bar()
        self._connect_signals()
        self._load_settings()

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
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))  # Assuming settings is tab 1
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

        self.engine.on('scraping_completed_all', self._on_scraping_completed_all)  # Adjusted event name
        self.engine.on('scraping_error', self._on_scraping_error)
        self.engine.on('scraper_completed', self._on_scraper_completed)

    def _start_scraping(self):
        """Start continuous scraping with the configured refresh interval."""
        if self.is_scraping:
            return

        self.logger.info("Starting continuous scraping process...")
        self.is_scraping = True
        self.control_panel.set_scraping_state(True)
        self.status_bar.show_progress("Starting continuous monitoring...")

        # Create worker for continuous monitoring (single_run=False)
        self.scraping_worker = ScrapingWorker(self.engine, single_run=False)

        # Set the refresh interval from control panel
        refresh_interval = self.control_panel.get_auto_refresh_interval()
        self.scraping_worker.set_refresh_interval(refresh_interval)

        # Connect signals
        self.scraping_worker.matches_updated.connect(self._on_matches_updated)
        self.scraping_worker.status_updated.connect(self.status_bar.set_status)
        self.scraping_worker.error_occurred.connect(self._on_scraping_error)
        self.scraping_worker.scraping_really_finished.connect(self._on_scraping_finished)

        # Start the worker
        self.scraping_worker.start()

    def _stop_scraping(self):
        """Stop continuous scraping."""
        if not self.is_scraping:
            return

        self.logger.info("Stopping continuous scraping process...")

        if self.scraping_worker and self.scraping_worker.isRunning():
            self.scraping_worker.stop()
            # Don't wait here - let the finished signal handle cleanup

    def _refresh_matches(self):
        """Perform a single refresh of matches."""
        if self.is_scraping:
            self.logger.info("Manual refresh skipped: continuous scraping is active.")
            self.status_bar.set_status("Manual refresh skipped - continuous monitoring active", 3000)
            return

        self.logger.info("Manual refresh requested")
        self.status_bar.show_progress("Refreshing matches...")

        # Create a single-run worker
        single_run_worker = ScrapingWorker(self.engine, single_run=True)
        single_run_worker.matches_updated.connect(self._on_matches_updated)
        single_run_worker.status_updated.connect(self.status_bar.set_status)
        single_run_worker.error_occurred.connect(self._on_scraping_error)
        single_run_worker.scraping_really_finished.connect(lambda: [
            self.status_bar.hide_progress(),
            self.status_bar.set_status("Refresh completed", 3000)
        ])
        single_run_worker.start()

    def _toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh setting."""
        # Update the control panel checkbox to match
        if self.control_panel:
            self.control_panel.auto_refresh_checkbox.setChecked(enabled)

        self.logger.info(f"Auto-refresh {'enabled' if enabled else 'disabled'}")

        # If we're currently scraping, we need to restart with new settings
        if self.is_scraping:
            self._stop_scraping()
            # The worker will restart automatically when it finishes if auto-refresh is enabled
            if enabled:
                QTimer.singleShot(1000, self._start_scraping)  # Restart after brief delay

    def _on_matches_updated(self, matches: list):
        """Handle updated matches from scraping worker."""
        self.matches_table.update_matches(matches)

        # Count live matches and tie breaks
        live_count = len([m for m in matches if m.status.is_active])
        tie_break_count = len([m for m in matches if m.metadata.get('is_match_tie_break')])
        total_count = len(matches)

        # Update status bar indicators
        self.status_bar.set_live_count(live_count)
        self.status_bar.set_total_count(total_count)

        # Special handling for tie break alerts
        if tie_break_count > 0:
            self.logger.critical(f"🚨 {tie_break_count} TIE BREAK MATCHES DETECTED!")
            self.status_bar.show_notification(f"🚨 {tie_break_count} TIE BREAKS FOUND!", 5000)

    def _on_scraping_completed_all(self, match_count: int, duration: float):
        """Handle completion of all scrapers."""
        message = f"Scraping cycle completed: {match_count} matches in {duration:.1f}s"
        self.logger.info(message)

    def _on_scraping_error(self, error_msg: str):
        """Handle scraping errors."""
        self.logger.error(f"Scraping error: {error_msg}")
        self.status_bar.set_status(f"Error: {error_msg[:50]}...", 5000)
        self.error_occurred.emit(error_msg)

    def _on_scraper_completed(self, scraper_name: str, match_count: int, duration_seconds: float):
        """Handle individual scraper completion."""
        self.logger.debug(f"Scraper {scraper_name} completed: {match_count} matches in {duration_seconds:.2f}s")

    def _on_scraping_finished(self):
        """Handle scraping worker finished."""
        self.is_scraping = False
        self.control_panel.set_scraping_state(False)
        self.status_bar.hide_progress()
        self.status_bar.set_status("Monitoring stopped")

        if self.scraping_worker:
            self.scraping_worker.deleteLater()
            self.scraping_worker = None

        self.logger.info("Scraping process has finished")

    def _on_settings_changed(self):
        """Handle settings changes."""
        self.logger.info("Settings changed, updating configuration...")

        # Re-initialize engine with new config
        self.engine = TennisScrapingEngine(self.config.to_dict())

        # If scraping is active, update the worker's refresh interval
        if self.is_scraping and self.scraping_worker:
            refresh_interval = self.control_panel.get_auto_refresh_interval()
            self.scraping_worker.set_refresh_interval(refresh_interval)

    def check_for_updates(self):
        """Check for application updates."""
        self.logger.info("Checking for updates...")
        if self.update_worker and self.update_worker.isRunning():
            self.logger.info("Update check already in progress.")
            return

        # Convert config to dict for UpdateWorker
        from dataclasses import asdict
        update_cfg_dict = asdict(self.config.updates)

        self.update_worker = UpdateWorker(update_cfg_dict)
        self.update_worker.update_available.connect(self._show_update_dialog)
        self.update_worker.no_update.connect(self._no_update_available)
        self.update_worker.check_failed.connect(self._update_check_failed)
        self.update_worker.check_for_updates()
        self.status_bar.set_status("Checking for updates...")

    def _show_update_dialog(self, update_info: UpdateInfo):
        """Show update dialog when update is available."""
        self.status_bar.set_status("Update available!")
        dialog = UpdateDialog(update_info, self)
        dialog.install_requested.connect(self._handle_install_request)
        dialog.show()

    def _handle_install_request(self, file_path: str):
        """Handle update installation request."""
        self.logger.info(f"Install requested for: {file_path}. Closing application.")
        QMessageBox.information(self, "Update Installation",
                                f"The application will now close to install the update from:\n{file_path}\n"
                                "Please follow the installer prompts.")
        self.close()

    def _no_update_available(self):
        """Handle no update available."""
        self.status_bar.set_status("You have the latest version!", 5000)
        QMessageBox.information(self, "Updates", "You are running the latest version!")

    def _update_check_failed(self, error: str):
        """Handle update check failure."""
        self.status_bar.set_status(f"Update check failed: {error[:30]}...", 5000)
        self.logger.warning(f"Update check failed: {error}")
        QMessageBox.warning(self, "Update Check Failed", f"Could not check for updates:\n{error}")

    def _show_export_dialog(self):
        """Show export dialog."""
        if not self.matches_table or self.matches_table.get_match_count() == 0:
            QMessageBox.information(self, "Export", "No matches to export.")
            return
        dialog = ExportDialog(self.matches_table.get_matches(), self)
        dialog.exec()

    def _show_about_dialog(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def save_settings(self):
        """Save application settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("currentTab", self.tab_widget.currentIndex())
        self.settings.setValue("autoRefresh", self.auto_refresh_action.isChecked())

        if self.control_panel:
            self.control_panel.save_settings(self.settings)
        if self.matches_table:
            self.matches_table.save_settings(self.settings)

        self.config.save_to_file()
        self.logger.info("Settings saved")

    def _load_settings(self):
        """Load application settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

        current_tab = self.settings.value("currentTab", 0, int)
        self.tab_widget.setCurrentIndex(current_tab)

        auto_refresh = self.settings.value("autoRefresh", True, bool)
        self.auto_refresh_action.setChecked(auto_refresh)

        if self.control_panel:
            self.control_panel.load_settings(self.settings)
        if self.matches_table:
            self.matches_table.load_settings(self.settings)

        self.logger.info("Settings loaded")

    def stop_all_workers(self):
        """Stop all running workers."""
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.scraping_worker.stop()
            self.scraping_worker.wait(3000)

        if self.update_worker and self.update_worker.isRunning():
            self.update_worker.quit()
            self.update_worker.wait(1000)

        if self.engine:
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule cleanup
                    asyncio.create_task(self.engine.cleanup())
                else:
                    # If loop is not running, run cleanup directly
                    loop.run_until_complete(self.engine.cleanup())
            except RuntimeError:
                # If no event loop exists, create one for cleanup
                asyncio.run(self.engine.cleanup())

    def closeEvent(self, event):
        """Handle application close event."""
        self.logger.info("Application closeEvent triggered.")
        self.stop_all_workers()
        self.save_settings()
        self.logger.info("Application shutdown sequence complete.")
        event.accept()