import sys
import asyncio
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QMenuBar, QMessageBox,
                               QSplitter, QDockWidget, QTabWidget, QApplication)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QTimer, Slot, QSettings

from ..config import Config
from ..core.engine import TennisScrapingEngine
from ..core.models import TennisMatch, MatchStatus
from ..utils.logging import get_logger
from .. import __version__, get_info

from .components.matches_table import MatchesTable
from .components.control_panel import ControlPanel
from .components.log_viewer import LogViewer
from .components.status_bar import CustomStatusBar
from .components.settings_panel import SettingsPanel

from .dialogs.about_dialog import AboutDialog
from .dialogs.export_dialog import ExportDialog
from .dialogs.update_dialog import UpdateDialog
from .workers.scraping_worker import ScrapingWorker
from .workers.update_worker import UpdateWorker  # Assuming UpdateInfo is correctly handled by UpdateWorker now
from ..updates.checker import UpdateInfo  # For type hint


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: Config, parent: None = None):
        super().__init__(parent)
        self.config = config
        self.app_info = get_info()
        self.logger = get_logger(__name__)

        self.engine = TennisScrapingEngine(self.config.to_dict())
        self.scraping_worker: Optional[ScrapingWorker] = None
        self.update_worker: Optional[UpdateWorker] = None

        self._current_matches_cache: Dict[str, TennisMatch] = {}  # Cache for individual updates

        self._init_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbars()  # Placeholder if you want toolbars
        self._connect_signals()

        self.load_settings()
        self.logger.info("MainWindow initialized.")
        self.status_bar.set_status(f"{self.app_info['name']} v{self.app_info['version']} ready.")

    def _init_ui(self):
        self.setWindowTitle(self.app_info['name'])
        # Window size will be loaded from settings or default to config

        # Main widget and layout
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Control Panel
        self.control_panel = ControlPanel(self.config, self)  # Pass config
        layout.addWidget(self.control_panel)

        # Splitter for Matches Table and Log/Info Tabs
        self.splitter = QSplitter(Qt.Orientation.Vertical, self)
        layout.addWidget(self.splitter)

        # Matches Table
        self.matches_table = MatchesTable(self)
        self.splitter.addWidget(self.matches_table)

        # Tab widget for Logs and other info
        self.info_tabs = QTabWidget(self)
        self.log_viewer = LogViewer(self)
        self.info_tabs.addTab(self.log_viewer, "Logs")
        # Add more tabs here if needed (e.g., Match Details, Stats)
        self.splitter.addWidget(self.info_tabs)

        # Initial splitter sizes (can be adjusted by user)
        self.splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])

        # Status Bar
        self.status_bar = CustomStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _create_actions(self):
        # File actions
        self.export_action = QAction(QIcon.fromTheme("document-save"), "&Export Matches...", self)
        self.settings_action = QAction(QIcon.fromTheme("preferences-system"), "&Settings...", self)
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "E&xit", self)

        # Help actions
        self.about_action = QAction(QIcon.fromTheme("help-about"), "&About...", self)
        self.check_updates_action = QAction(QIcon.fromTheme("system-software-update"), "Check for &Updates...", self)

        # View Actions
        self.toggle_logs_action = QAction("Show/Hide &Logs", self)
        self.toggle_logs_action.setCheckable(True)
        self.toggle_logs_action.setChecked(True)

    def _create_menus(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.toggle_logs_action)
        # Example: Add dock widget toggle
        # self.log_dock_widget = QDockWidget("Logs", self) # Create it first
        # self.log_dock_widget.setWidget(self.log_viewer)
        # self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock_widget)
        # view_menu.addAction(self.log_dock_widget.toggleViewAction())

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.check_updates_action)
        help_menu.addAction(self.about_action)

    def _create_toolbars(self):
        # Example: Main Toolbar (can be expanded)
        # main_toolbar = self.addToolBar("Main")
        # main_toolbar.addAction(self.export_action)
        # main_toolbar.addAction(self.settings_action)
        pass

    def _connect_signals(self):
        # Control Panel
        self.control_panel.start_scraping.connect(self._start_scraping)
        self.control_panel.stop_scraping.connect(self._stop_scraping)
        self.control_panel.refresh_requested.connect(self._refresh_matches_once)
        self.control_panel.settings_changed.connect(self._on_control_panel_settings_changed)

        # Menu Actions
        self.export_action.triggered.connect(self._export_matches)
        self.settings_action.triggered.connect(self._open_settings)
        self.exit_action.triggered.connect(self.close)
        self.about_action.triggered.connect(self._show_about_dialog)
        self.check_updates_action.triggered.connect(self.check_for_updates)
        self.toggle_logs_action.toggled.connect(self._toggle_log_viewer)

        # Engine Events
        self.engine.on("scraping_started", self._on_scraping_engine_event)
        self.engine.on("scraper_started", self._on_scraping_engine_event)
        self.engine.on("scraper_completed", self._on_scraper_completed_event)  # For full scrape
        self.engine.on("individual_match_found", self._on_individual_match_found_event)  # New
        self.engine.on("scraper_error", self._on_scraping_error_event)
        self.engine.on("scraping_completed_all", self._on_scraping_all_completed_event)

    @Slot()
    def _start_scraping(self):
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.logger.warning("Scraping process is already running.")
            return

        self.logger.info("Starting continuous scraping process...")
        self.status_bar.set_status("🚀 Starting scraping...", 0)  # Permanent until changed
        self.status_bar.show_progress("Scraping...", -1)  # Indeterminate progress
        self.control_panel.set_scraping_state(True)
        self._current_matches_cache.clear()  # Clear cache for new session
        self.matches_table.update_matches([])  # Clear table initially

        self.scraping_worker = ScrapingWorker(self.engine, single_run=False)  # Continuous
        self.scraping_worker.matches_updated.connect(
            self._on_matches_updated_from_worker)  # For final list from worker cycle
        self.scraping_worker.status_updated.connect(self._on_worker_status_update)
        self.scraping_worker.error_occurred.connect(self._on_worker_error)
        self.scraping_worker.scraping_really_finished.connect(self._on_scraping_finished)

        # Set refresh interval from control panel
        refresh_interval = self.control_panel.get_auto_refresh_interval()
        if not self.control_panel.is_auto_refresh_enabled():
            self.logger.info(
                "Auto-refresh is disabled by control panel. Worker will run once unless single_run=False, then it will use its default internal loop logic if applicable without external timer.")
            # If worker is continuous, it will use its internal loop.
            # If we wanted to truly disable looping, single_run would be True.
            # For continuous worker, we just inform about the GUI's auto-refresh state.
            self.scraping_worker.set_refresh_interval(self.config.ui.auto_refresh_interval)  # Default from config
        else:
            self.scraping_worker.set_refresh_interval(refresh_interval)

        self.scraping_worker.start()

    @Slot()
    def _stop_scraping(self):
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.logger.info("Stopping scraping process...")
            self.status_bar.set_status("🛑 Stopping scraping...", 0)
            self.scraping_worker.stop()  # This will emit scraping_really_finished when done
        else:
            self.logger.info("Scraping process is not running.")
            self._on_scraping_finished()  # Ensure UI updates if somehow stopped externally

    @Slot()
    def _refresh_matches_once(self):
        if self.scraping_worker and self.scraping_worker.isRunning():
            QMessageBox.information(self, "Scraping in Progress",
                                    "Cannot refresh while continuous scraping is active. Please stop it first.")
            return

        self.logger.info("Starting single refresh...")
        self.status_bar.set_status("🔄 Refreshing matches...", 0)
        self.status_bar.show_progress("Refreshing...", -1)
        self.control_panel.set_scraping_state(True)  # Show as busy
        self._current_matches_cache.clear()
        # self.matches_table.update_matches([]) # Don't clear table for single refresh, allow append

        self.scraping_worker = ScrapingWorker(self.engine, single_run=True)  # Single run
        self.scraping_worker.matches_updated.connect(self._on_matches_updated_from_worker)
        self.scraping_worker.status_updated.connect(self._on_worker_status_update)
        self.scraping_worker.error_occurred.connect(self._on_worker_error)
        self.scraping_worker.scraping_really_finished.connect(self._on_scraping_finished)
        self.scraping_worker.start()

    @Slot(list)
    def _on_matches_updated_from_worker(self, matches: List[TennisMatch]):
        self.logger.info(f"Worker sent final list of {len(matches)} matches for the cycle.")
        # This is the full list from a scrape cycle.
        # Individual updates are handled by _on_individual_match_found_event
        # For now, let's update the table with this full list to ensure it's current.
        # This might cause a full refresh after individual updates, which is acceptable.
        self._current_matches_cache = {(m.source, m.match_id or m.match_title): m for m in matches}
        self.matches_table.update_matches(list(self._current_matches_cache.values()))
        self.status_bar.set_live_count(len([m for m in matches if m.status == MatchStatus.LIVE]))
        self.status_bar.set_total_count(len(matches))

    @Slot(TennisMatch)
    def _on_individual_match_found_event(self, match: TennisMatch):
        """Handles individual matches found by the engine."""
        self.logger.info(f"GUI received individual match: {match.match_title} ({match.source})")

        match_key = (match.source, match.match_id or match.match_title)  # Use a unique key
        self._current_matches_cache[match_key] = match

        # Update the table with the current cache
        # This is more efficient than full clear and repopulate for each single match
        self.matches_table.update_matches(list(self._current_matches_cache.values()))

        # Update status bar counts (can be slightly delayed from table but ok)
        live_count = len([m for m in self._current_matches_cache.values() if m.status == MatchStatus.LIVE])
        total_count = len(self._current_matches_cache)
        self.status_bar.set_live_count(live_count)
        self.status_bar.set_total_count(total_count)
        self.status_bar.set_status(f"⚡ Match Update: {match.match_title}", 3000)

    @Slot()
    def _on_scraping_finished(self):
        self.logger.info("Scraping process has finished or was stopped.")
        self.control_panel.set_scraping_state(False)
        self.status_bar.hide_progress()
        self.status_bar.set_status(f"Idle. Last update yielded {self.matches_table.get_match_count()} matches.", 0)
        if self.scraping_worker:
            self.scraping_worker.deleteLater()  # Clean up worker
            self.scraping_worker = None

    @Slot(str)
    def _on_worker_status_update(self, message: str):
        self.status_bar.set_status(message, 5000)

    @Slot(str)
    def _on_worker_error(self, error_message: str):
        self.logger.error(f"Worker error: {error_message}")
        self.status_bar.set_status(f"Worker Error: {error_message}", 10000)
        QMessageBox.warning(self, "Scraping Error", f"An error occurred in the scraping worker:\n{error_message}")
        # Potentially stop scraping or handle more gracefully
        self._stop_scraping()  # Stop if worker reports critical error

    def _on_scraping_engine_event(self, event_name: str, *args):
        """Handle generic scraping engine events for status updates."""
        self.logger.debug(f"Engine Event: {event_name} - Args: {args}")
        if event_name == "scraping_started":
            self.status_bar.set_status("🚀 Scraping all sources...", 0)
        elif event_name == "scraper_started":
            source_name = args[0] if args else "Unknown"
            self.status_bar.set_status(f"🔍 Scraping {source_name}...", 0)

    def _on_scraper_completed_event(self, source_name: str, count: int, duration: Optional[float]):
        """Handle scraper completion for status and logging."""
        duration_str = f"in {duration:.2f}s" if duration is not None else "(duration N/A)"
        self.logger.info(f"Engine: Scraper '{source_name}' completed, found {count} matches {duration_str}.")
        # Status bar already shows overall progress or individual match updates
        # This is mostly for logging and final counts.

    def _on_scraping_all_completed_event(self, total_matches: int, total_duration: float):
        """Handle completion of all scrapers for a cycle."""
        self.logger.info(
            f"Engine: All scrapers finished cycle. Total unique matches: {total_matches} in {total_duration:.2f}s.")
        # Worker status will update based on its internal state or the match list it sends.
        # The `matches_updated` signal from the worker will trigger final table update and counts.

    def _on_scraping_error_event(self, source_name: str, error_msg: Optional[str] = None):
        """Handle errors from a specific scraper."""
        log_msg = f"Engine: Error scraping {source_name}"
        if error_msg: log_msg += f": {error_msg}"
        self.logger.error(log_msg)
        self.status_bar.set_status(f"❌ Error with {source_name}", 10000)

    @Slot()
    def _on_control_panel_settings_changed(self):
        """Handle settings changes from the ControlPanel (e.g., refresh interval)."""
        self.logger.info("ControlPanel settings changed by user.")
        if self.scraping_worker and self.scraping_worker.isRunning() and self.control_panel.is_auto_refresh_enabled():
            new_interval = self.control_panel.get_auto_refresh_interval()
            self.scraping_worker.set_refresh_interval(new_interval)
            self.status_bar.set_status(f"Refresh interval updated to {new_interval}s.", 3000)
        # Persist these specific UI settings from control panel to config
        self.config.ui.auto_refresh_interval = self.control_panel.get_auto_refresh_interval()
        # Consider if auto_refresh_enabled itself should be a config item if it's not implicitly
        # handled by the worker's single_run mode. For now, it controls the worker's timer.

    @Slot()
    def _open_settings(self):
        self.logger.debug("Opening settings dialog.")
        # Pass a copy of the config to avoid direct modification until "Save"
        settings_dialog = SettingsPanel(Config.load_from_file(self.config.get_default_config_path()),
                                         self)  # Load fresh for dialog
        if settings_dialog.exec():
            self.config = settings_dialog.get_current_settings()  # Get updated config
            self.config.save_to_file()  # Save it
            self._on_settings_changed()
            self.logger.info("Settings saved via dialog.")
            QMessageBox.information(self, "Settings Saved",
                                    "Settings have been saved. Some changes may require an application restart.")

    def _on_settings_changed(self):
        """Apply changes after settings are modified."""
        self.logger.info("Settings changed, updating configuration...")
        # Re-initialize engine with new config if necessary, or update relevant parts
        # For simplicity, if scrapers need re-init, stop and restart scraping.
        was_scraping = self.scraping_worker and self.scraping_worker.isRunning()
        if was_scraping:
            self._stop_scraping()  # Stop current scraping

        self.engine = TennisScrapingEngine(self.config.to_dict())  # Re-init engine
        # Re-connect engine events because self.engine instance changed
        self._connect_engine_events_only()  # Reconnect only engine events

        # Apply theme immediately if changed
        current_qapp_style = QApplication.instance().styleSheet()
        # This is a simple way to re-apply; a more robust way might involve theme manager directly
        from .styles.themes import apply_theme
        apply_theme(QApplication.instance(), self.config.ui.theme)

        if was_scraping:
            # QTimer.singleShot(1000, self._start_scraping) # Restart scraping after a short delay
            self.logger.info("Scraping needs to be restarted manually after settings change.")
            self.status_bar.set_status("Settings updated. Please restart scraping if it was active.", 5000)

    def _connect_engine_events_only(self):
        # Clear existing engine listeners to avoid duplicates if engine is re-instantiated
        if hasattr(self.engine, 'event_listeners'):  # Check if engine has listeners
            self.engine.event_listeners.clear()

        self.engine.on("scraping_started", self._on_scraping_engine_event)
        self.engine.on("scraper_started", self._on_scraping_engine_event)
        self.engine.on("scraper_completed", self._on_scraper_completed_event)
        self.engine.on("individual_match_found", self._on_individual_match_found_event)
        self.engine.on("scraper_error", self._on_scraping_error_event)
        self.engine.on("scraping_completed_all", self._on_scraping_all_completed_event)

    @Slot()
    def _export_matches(self):
        current_matches = self.matches_table.get_matches()
        if not current_matches:
            QMessageBox.information(self, "Export Matches", "No matches to export.")
            return

        export_dialog = ExportDialog(current_matches, self)
        export_dialog.exec()  # Modal execution

    @Slot()
    def _show_about_dialog(self):
        about_dialog = AboutDialog(self)
        about_dialog.exec()

    @Slot(bool)
    def _toggle_log_viewer(self, checked: bool):
        # If using QDockWidget, toggle its visibility:
        # self.log_dock_widget.setVisible(checked)
        # If log viewer is part of splitter:
        if checked:
            if self.info_tabs.isHidden():
                self.info_tabs.show()
                # Try to restore splitter sizes, or set a default
                sizes = self.splitter.sizes()
                if sum(sizes) > 0 and sizes[1] == 0:  # if bottom pane was collapsed
                    self.splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
        else:
            if not self.info_tabs.isHidden():
                # To "hide" in a splitter, give it minimal size or store and restore previous
                self.splitter.setSizes([self.splitter.height(), 0])  # Collapses bottom widget
                # self.info_tabs.hide() # This might remove it from splitter layout

    def check_for_updates(self, manual_check: bool = True):
        self.logger.info("Checking for updates...")
        if manual_check:
            self.status_bar.set_status("Checking for updates...", 5000)

        if self.update_worker and self.update_worker.isRunning():
            self.logger.warning("Update check already in progress.")
            if manual_check:
                QMessageBox.information(self, "Update Check", "An update check is already in progress.")
            return

        # Ensure config for worker is a dict
        update_config_dict = self.config.updates.to_dict() if hasattr(self.config.updates, 'to_dict') else vars(
            self.config.updates)

        self.update_worker = UpdateWorker(update_config_dict)  # Pass config dictionary
        self.update_worker.update_available.connect(self._on_update_available)
        self.update_worker.no_update.connect(self._on_no_update_available)
        self.update_worker.check_failed.connect(self._on_update_check_failed)
        self.update_worker.check_for_updates()  # Call method on worker

    @Slot(UpdateInfo)  # Expecting UpdateInfo object
    def _on_update_available(self, update_info: UpdateInfo):
        self.logger.info(f"Update available: {update_info.version}")
        self.status_bar.set_status(f"🎉 Update {update_info.version} available!", 0)

        update_dialog = UpdateDialog(update_info, self)  # Pass UpdateInfo object
        update_dialog.install_requested.connect(self._on_install_update_requested)
        update_dialog.exec()
        self.status_bar.clear_status()  # Clear "update available" after dialog

    @Slot(str)
    def _on_install_update_requested(self, file_path: str):
        self.logger.info(f"Install requested for update file: {file_path}")
        QMessageBox.information(self, "Install Update",
                                f"Update downloaded to:\n{file_path}\n\nThe application will now close to start the installer.")
        # Logic to launch installer and quit app
        # This is platform dependent. For now, just quit.
        # import subprocess, sys
        # if sys.platform == "win32":
        #     subprocess.Popen([file_path], shell=True)
        # elif sys.platform == "darwin": # macOS
        #     subprocess.Popen(["open", file_path])
        # else: # Linux
        #     subprocess.Popen(["xdg-open", file_path])
        QApplication.instance().quit()

    @Slot()
    def _on_no_update_available(self):
        self.logger.info("No update available.")
        self.status_bar.set_status("Application is up to date.", 5000)
        # Only show message box if it was a manual check
        if self.sender() and hasattr(self.sender(), 'property') and self.sender().property(
                'manual_check_flag'):  # Heuristic
            QMessageBox.information(self, "Update Check", "Your application is up to date.")

    @Slot(str)
    def _on_update_check_failed(self, error_message: str):
        self.logger.error(f"Update check failed: {error_message}")
        self.status_bar.set_status(f"Update check failed: {error_message}", 10000)
        # QMessageBox.warning(self, "Update Check Failed", f"Could not check for updates:\n{error_message}")

    def save_settings(self):
        self.logger.info("Saving main window settings...")
        settings = QSettings("TennisScraperOrg", self.app_info['name'])  # Use consistent names
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("splitterSizes", self.splitter.sizes())

        # Save control panel settings
        if self.control_panel:
            self.control_panel.save_settings(settings)

        # Save matches table settings
        if self.matches_table:
            self.matches_table.save_settings(settings)

        # Save main config file
        self.config.save_to_file()
        self.logger.info("Settings saved.")

    def load_settings(self):
        self.logger.info("Loading main window settings...")
        settings = QSettings("TennisScraperOrg", self.app_info['name'])
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(self.config.ui.window_width, self.config.ui.window_height)  # Default from config

        window_state = settings.value("windowState")
        if window_state: self.restoreState(window_state)

        splitter_sizes = settings.value("splitterSizes")
        if splitter_sizes and isinstance(splitter_sizes, list) and len(splitter_sizes) == 2:
            self.splitter.setSizes([int(s) for s in splitter_sizes])  # Ensure integers
        else:  # Default splitter sizes if not saved or invalid
            self.splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])

        # Load control panel settings
        if self.control_panel:
            self.control_panel.load_settings(settings)

        # Load matches table settings
        if self.matches_table:
            self.matches_table.load_settings(settings)
        self.logger.info("Settings loaded.")

    def stop_all_workers(self):
        """Stop all running worker threads."""
        self.logger.info("Stopping all workers...")
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.scraping_worker.stop()
            # self.scraping_worker.wait() # Wait for graceful exit if needed
        if self.update_worker and self.update_worker.isRunning():
            self.update_worker.quit()  # Request quit
            # self.update_worker.wait()
        self.logger.info("All workers signaled to stop.")

    def closeEvent(self, event):
        """Handle window close event."""
        self.logger.info("Application closeEvent triggered.")
        self.stop_all_workers()
        self.save_settings()

        # Clean up engine resources if it has a cleanup method
        if hasattr(self.engine, 'cleanup') and asyncio.iscoroutinefunction(self.engine.cleanup):
            try:
                # If in an event loop, create task, else run synchronously if possible or warn
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.engine.cleanup())
                else:  # Not ideal but try to run if loop not active
                    loop.run_until_complete(self.engine.cleanup())
            except Exception as e:
                self.logger.error(f"Error during engine cleanup on close: {e}")

        # Ensure log viewer worker is stopped
        if self.log_viewer and hasattr(self.log_viewer, 'monitor_worker') and self.log_viewer.monitor_worker:
            if self.log_viewer.monitor_worker.isRunning():
                self.log_viewer.monitor_worker.stop()
                self.log_viewer.monitor_worker.wait(1000)

        self.logger.info("Application shutdown sequence complete.")
        super().closeEvent(event)