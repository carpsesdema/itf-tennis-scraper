"""
Main application window for ITF Tennis Scraper.
"""

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
from ..utils.logging import get_logger


class MainWindow(QMainWindow):
    """Main application window."""

    # Signals
    status_updated = Signal(str)
    matches_updated = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = get_logger(__name__)
        self.settings = QSettings("TennisScraper", "ITFScraper")

        # Core components
        self.engine = TennisScrapingEngine(config.to_dict())
        self.scraping_worker = None
        self.update_worker = None

        # UI components
        self.matches_table = None
        self.control_panel = None
        self.settings_panel = None
        self.status_bar = None

        # State
        self.is_scraping = False
        self.auto_refresh_timer = QTimer()

        self._init_ui()
        self._create_menu_bar()
        self._connect_signals()
        self._load_settings()
        self._setup_auto_refresh()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("ITF Tennis Match Scraper")
        self.setGeometry(100, 100, self.config.ui.window_width, self.config.ui.window_height)

        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_matches_tab()
        self._create_settings_tab()
        self._create_logs_tab()

        # Status bar
        self.status_bar = CustomStatusBar()
        self.setStatusBar(self.status_bar)

    def _create_matches_tab(self):
        """Create the matches display tab."""
        matches_widget = QWidget()
        layout = QVBoxLayout(matches_widget)

        # Create splitter for control panel and matches
        splitter = QSplitter(Qt.Vertical)

        # Control panel
        self.control_panel = ControlPanel(self.config)
        splitter.addWidget(self.control_panel)

        # Matches table
        self.matches_table = MatchesTable()
        splitter.addWidget(self.matches_table)

        # Set splitter proportions
        splitter.setStretchFactor(0, 0)  # Control panel fixed size
        splitter.setStretchFactor(1, 1)  # Matches table takes remaining space

        layout.addWidget(splitter)
        self.tab_widget.addTab(matches_widget, "Live Matches")

    def _create_settings_tab(self):
        """Create the settings tab."""
        self.settings_panel = SettingsPanel(self.config)
        self.tab_widget.addTab(self.settings_panel, "Settings")

    def _create_logs_tab(self):
        """Create the logs tab."""
        from .components.log_viewer import LogViewer
        self.log_viewer = LogViewer()
        self.tab_widget.addTab(self.log_viewer, "Logs")

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
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

        # View menu
        view_menu = menubar.addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence.Refresh)
        refresh_action.triggered.connect(self._refresh_matches)
        view_menu.addAction(refresh_action)

        view_menu.addSeparator()

        # Toggle auto-refresh
        self.auto_refresh_action = QAction("&Auto Refresh", self)
        self.auto_refresh_action.setCheckable(True)
        self.auto_refresh_action.setChecked(True)
        self.auto_refresh_action.triggered.connect(self._toggle_auto_refresh)
        view_menu.addAction(self.auto_refresh_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        update_action = QAction("Check for &Updates", self)
        update_action.triggered.connect(self.check_for_updates)
        tools_menu.addAction(update_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        """Connect signals and slots."""
        # Control panel signals
        self.control_panel.start_scraping.connect(self._start_scraping)
        self.control_panel.stop_scraping.connect(self._stop_scraping)
        self.control_panel.refresh_requested.connect(self._refresh_matches)
        self.control_panel.settings_changed.connect(self._on_settings_changed)

        # Settings panel signals
        self.settings_panel.settings_changed.connect(self._on_settings_changed)

        # Engine signals
        self.engine.on('scraping_completed', self._on_scraping_completed)
        self.engine.on('scraping_error', self._on_scraping_error)
        self.engine.on('scraper_completed', self._on_scraper_completed)

        # Auto-refresh timer
        self.auto_refresh_timer.timeout.connect(self._auto_refresh)

    def _setup_auto_refresh(self):
        """Setup automatic refresh timer."""
        interval_ms = self.config.ui.auto_refresh_interval * 1000
        self.auto_refresh_timer.setInterval(interval_ms)

    def _start_scraping(self):
        """Start the scraping process."""
        if self.is_scraping:
            return

        self.logger.info("Starting scraping process...")
        self.is_scraping = True

        # Update UI state
        self.control_panel.set_scraping_state(True)
        self.status_bar.show_progress("Starting scraping...")

        # Create and start worker
        self.scraping_worker = ScrapingWorker(self.engine)
        self.scraping_worker.matches_updated.connect(self._on_matches_updated)
        self.scraping_worker.status_updated.connect(self.status_bar.set_status)
        self.scraping_worker.error_occurred.connect(self._on_scraping_error)
        self.scraping_worker.finished.connect(self._on_scraping_finished)

        self.scraping_worker.start()

        # Start auto-refresh if enabled
        if self.auto_refresh_action.isChecked():
            self.auto_refresh_timer.start()

    def _stop_scraping(self):
        """Stop the scraping process."""
        if not self.is_scraping:
            return

        self.logger.info("Stopping scraping process...")

        # Stop timer
        self.auto_refresh_timer.stop()

        # Stop worker
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.scraping_worker.stop()
            self.scraping_worker.wait(5000)  # Wait up to 5 seconds

        self._on_scraping_finished()

    def _refresh_matches(self):
        """Refresh matches once."""
        if self.is_scraping:
            return

        self.logger.info("Manual refresh requested")
        self.status_bar.show_progress("Refreshing...")

        # Create one-time worker
        worker = ScrapingWorker(self.engine, single_run=True)
        worker.matches_updated.connect(self._on_matches_updated)
        worker.status_updated.connect(self.status_bar.set_status)
        worker.error_occurred.connect(self._on_scraping_error)
        worker.finished.connect(lambda: self.status_bar.hide_progress())

        worker.start()

    def _auto_refresh(self):
        """Perform automatic refresh."""
        if not self.is_scraping:
            return

        self.logger.debug("Auto-refresh triggered")
        self._refresh_matches()

    def _toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh on/off."""
        if enabled and self.is_scraping:
            self.auto_refresh_timer.start()
        else:
            self.auto_refresh_timer.stop()

        self.logger.info(f"Auto-refresh {'enabled' if enabled else 'disabled'}")

    def _on_matches_updated(self, matches: list):
        """Handle updated matches from worker."""
        self.matches_table.update_matches(matches)
        self.status_bar.set_status(f"Found {len(matches)} matches")

        # Update live match count
        live_count = len([m for m in matches if m.is_live])
        if live_count > 0:
            self.status_bar.set_live_count(live_count)

        self.matches_updated.emit(matches)

    def _on_scraping_completed(self, match_count: int, duration: float):
        """Handle scraping completion."""
        message = f"Scraping completed: {match_count} matches in {duration:.1f}s"
        self.status_bar.set_status(message)
        self.logger.info(message)

    def _on_scraping_error(self, error: str):
        """Handle scraping errors."""
        self.logger.error(f"Scraping error: {error}")
        self.status_bar.set_status(f"Error: {error}")
        self.error_occurred.emit(error)

        # Show error dialog for severe errors
        if "timeout" not in error.lower():
            QMessageBox.warning(self, "Scraping Error", f"An error occurred while scraping:\n\n{error}")

    def _on_scraper_completed(self, scraper_name: str, match_count: int):
        """Handle individual scraper completion."""
        self.logger.debug(f"Scraper {scraper_name} completed: {match_count} matches")

    def _on_scraping_finished(self):
        """Handle scraping process finished."""
        self.is_scraping = False
        self.control_panel.set_scraping_state(False)
        self.status_bar.hide_progress()
        self.auto_refresh_timer.stop()

        if self.scraping_worker:
            self.scraping_worker.deleteLater()
            self.scraping_worker = None

    def _on_settings_changed(self):
        """Handle settings changes."""
        self.logger.info("Settings changed, updating configuration...")

        # Update engine configuration
        self.engine = TennisScrapingEngine(self.config.to_dict())

        # Update auto-refresh interval
        self._setup_auto_refresh()

        # Restart auto-refresh if running
        if self.auto_refresh_action.isChecked() and self.is_scraping:
            self.auto_refresh_timer.start()

    def check_for_updates(self):
        """Check for application updates."""
        self.logger.info("Checking for updates...")

        if self.update_worker and self.update_worker.isRunning():
            return

        self.update_worker = UpdateWorker(self.config.updates)
        self.update_worker.update_available.connect(self._show_update_dialog)
        self.update_worker.no_update.connect(self._no_update_available)
        self.update_worker.check_failed.connect(self._update_check_failed)

        self.update_worker.start()
        self.status_bar.set_status("Checking for updates...")

    def _show_update_dialog(self, update_info: dict):
        """Show update available dialog."""
        self.status_bar.set_status("Update available!")
        dialog = UpdateDialog(update_info, self)
        dialog.show()

    def _no_update_available(self):
        """Handle no update available."""
        self.status_bar.set_status("You have the latest version!")
        QMessageBox.information(self, "Updates", "You are running the latest version!")

    def _update_check_failed(self, error: str):
        """Handle update check failure."""
        self.status_bar.set_status("Update check failed")
        self.logger.warning(f"Update check failed: {error}")

    def _show_export_dialog(self):
        """Show export dialog."""
        if not self.matches_table.get_match_count():
            QMessageBox.information(self, "Export", "No matches to export")
            return

        dialog = ExportDialog(self.matches_table.get_matches(), self)
        dialog.exec()

    def _show_about_dialog(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def save_settings(self):
        """Save application settings."""
        # Window geometry
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

        # Tab settings
        self.settings.setValue("currentTab", self.tab_widget.currentIndex())

        # Auto-refresh setting
        self.settings.setValue("autoRefresh", self.auto_refresh_action.isChecked())

        # Save component settings
        if self.control_panel:
            self.control_panel.save_settings(self.settings)
        if self.matches_table:
            self.matches_table.save_settings(self.settings)

        # Save configuration
        self.config.save_to_file()

        self.logger.info("Settings saved")

    def _load_settings(self):
        """Load application settings."""
        # Window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

        # Tab settings
        current_tab = self.settings.value("currentTab", 0, int)
        self.tab_widget.setCurrentIndex(current_tab)

        # Auto-refresh setting
        auto_refresh = self.settings.value("autoRefresh", True, bool)
        self.auto_refresh_action.setChecked(auto_refresh)

        # Load component settings
        if self.control_panel:
            self.control_panel.load_settings(self.settings)
        if self.matches_table:
            self.matches_table.load_settings(self.settings)

        self.logger.info("Settings loaded")

    def stop_all_workers(self):
        """Stop all running workers."""
        if self.scraping_worker and self.scraping_worker.isRunning():
            self.scraping_worker.stop()
            self.scraping_worker.wait(5000)

        if self.update_worker and self.update_worker.isRunning():
            self.update_worker.quit()
            self.update_worker.wait(3000)

        if self.engine:
            # This should be async, but for shutdown we'll run synchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.engine.cleanup())
            loop.close()

    def closeEvent(self, event):
        """Handle application close event."""
        self.logger.info("Application closing...")

        # Stop scraping
        if self.is_scraping:
            self._stop_scraping()

        # Stop all workers
        self.stop_all_workers()

        # Save settings
        self.save_settings()

        event.accept()