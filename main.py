import sys
import json
import time
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                               QWidget, QPushButton, QTableWidget, QTableWidgetItem,
                               QTextEdit, QLabel, QSpinBox, QCheckBox, QComboBox,
                               QGroupBox, QSplitter, QStatusBar, QProgressBar,
                               QTabWidget, QFormLayout, QLineEdit, QFileDialog,
                               QMessageBox)
from PySide6.QtCore import QTimer, QThread, Signal, QSettings, Qt
from PySide6.QtGui import QFont, QIcon, QPalette, QColor


# ================================================================================================
# DATA MODELS
# ================================================================================================

@dataclass
class TennisMatch:
    """Data model for a tennis match"""
    home_player: str
    away_player: str
    score: str = ""
    status: str = ""
    tournament: str = ""
    round_info: str = ""
    is_live: bool = False
    source: str = ""
    url: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ScrapingConfig:
    """Configuration for scraping operations"""
    delay_between_requests: int = 2
    request_timeout: int = 10
    max_retries: int = 3
    headless_browser: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    sources_enabled: Dict[str, bool] = None

    def __post_init__(self):
        if self.sources_enabled is None:
            self.sources_enabled = {
                'flashscore': True,
                'sofascore': True,
                'itf_official': False  # Often requires API access
            }


# ================================================================================================
# CORE INTERFACES
# ================================================================================================

class MatchScraper(ABC):
    """Abstract base class for match scrapers"""

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of this scraping source"""
        pass

    @abstractmethod
    def scrape_matches(self) -> List[TennisMatch]:
        """Scrape matches from this source"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is currently available"""
        pass


class MatchFilter(ABC):
    """Abstract base class for match filters"""

    @abstractmethod
    def filter_matches(self, matches: List[TennisMatch]) -> List[TennisMatch]:
        """Filter matches based on specific criteria"""
        pass

    @abstractmethod
    def get_filter_name(self) -> str:
        """Return the name of this filter"""
        pass


# ================================================================================================
# SCRAPER IMPLEMENTATIONS
# ================================================================================================

class FlashscoreScraper(MatchScraper):
    """Scraper for Flashscore ITF tennis matches"""

    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.driver = None

    def get_source_name(self) -> str:
        return "flashscore"

    def is_available(self) -> bool:
        try:
            response = requests.get("https://www.flashscore.com", timeout=5)
            return response.status_code == 200
        except:
            return False

    def _init_driver(self):
        """Initialize Chrome driver"""
        if self.driver is None:
            options = Options()
            if self.config.headless_browser:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--user-agent={self.config.user_agent}")
            self.driver = webdriver.Chrome(options=options)
        return self.driver

    def scrape_matches(self) -> List[TennisMatch]:
        """Scrape ITF matches from Flashscore"""
        matches = []
        driver = self._init_driver()

        try:
            self.logger.info("Scraping Flashscore ITF matches...")
            driver.get("https://www.flashscore.com/tennis/itf-men-singles/")
            time.sleep(3)

            # Handle cookie consent
            try:
                cookie_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
                cookie_btn.click()
            except TimeoutException:
                pass

            # Find match elements
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='event']"))
            )

            match_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='event__match']")

            for element in match_elements:
                try:
                    match = self._extract_match_data(element)
                    if match:
                        matches.append(match)
                except Exception as e:
                    self.logger.warning(f"Failed to extract match: {e}")

        except Exception as e:
            self.logger.error(f"Error scraping Flashscore: {e}")

        return matches

    def _extract_match_data(self, element) -> Optional[TennisMatch]:
        """Extract match data from a web element"""
        try:
            home_player = element.find_element(By.CSS_SELECTOR, "[class*='participant--home']").text
            away_player = element.find_element(By.CSS_SELECTOR, "[class*='participant--away']").text

            # Get score
            try:
                home_score = element.find_element(By.CSS_SELECTOR, "[class*='score--home']").text
                away_score = element.find_element(By.CSS_SELECTOR, "[class*='score--away']").text
                score = f"{home_score}-{away_score}"
            except NoSuchElementException:
                score = "Not started"

            # Get status
            try:
                status_elem = element.find_element(By.CSS_SELECTOR, "[class*='stage']")
                status = status_elem.text
                is_live = "'" in status or "SET" in status.upper()
            except NoSuchElementException:
                status = "Scheduled"
                is_live = False

            return TennisMatch(
                home_player=home_player,
                away_player=away_player,
                score=score,
                status=status,
                is_live=is_live,
                source=self.get_source_name(),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract match data: {e}")
            return None

    def __del__(self):
        if self.driver:
            self.driver.quit()


class SofascoreScraper(MatchScraper):
    """Scraper for SofaScore ITF tennis matches"""

    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.user_agent})

    def get_source_name(self) -> str:
        return "sofascore"

    def is_available(self) -> bool:
        try:
            response = self.session.get("https://www.sofascore.com", timeout=5)
            return response.status_code == 200
        except:
            return False

    def scrape_matches(self) -> List[TennisMatch]:
        """Scrape ITF matches from SofaScore"""
        matches = []
        try:
            self.logger.info("Scraping SofaScore ITF matches...")
            # Implementation would go here based on SofaScore's actual structure
            # This is a placeholder that would need to be developed based on their API/HTML
            pass
        except Exception as e:
            self.logger.error(f"Error scraping SofaScore: {e}")

        return matches


# ================================================================================================
# FILTER IMPLEMENTATIONS
# ================================================================================================

class LiveMatchFilter(MatchFilter):
    """Filter to show only live matches"""

    def get_filter_name(self) -> str:
        return "Live Matches Only"

    def filter_matches(self, matches: List[TennisMatch]) -> List[TennisMatch]:
        return [match for match in matches if match.is_live]


class PlayerNameFilter(MatchFilter):
    """Filter matches by player name"""

    def __init__(self, player_name: str):
        self.player_name = player_name.lower()

    def get_filter_name(self) -> str:
        return f"Player: {self.player_name}"

    def filter_matches(self, matches: List[TennisMatch]) -> List[TennisMatch]:
        return [match for match in matches
                if self.player_name in match.home_player.lower() or
                self.player_name in match.away_player.lower()]


# ================================================================================================
# CORE SCRAPING ENGINE
# ================================================================================================

class TennisScrapingEngine:
    """Main engine for coordinating tennis match scraping"""

    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.scrapers: List[MatchScraper] = []
        self.filters: List[MatchFilter] = []
        self._init_scrapers()

    def _init_scrapers(self):
        """Initialize available scrapers"""
        if self.config.sources_enabled.get('flashscore', False):
            self.scrapers.append(FlashscoreScraper(self.config))
        if self.config.sources_enabled.get('sofascore', False):
            self.scrapers.append(SofascoreScraper(self.config))

    def add_filter(self, filter_instance: MatchFilter):
        """Add a filter to the engine"""
        self.filters.append(filter_instance)

    def remove_filter(self, filter_instance: MatchFilter):
        """Remove a filter from the engine"""
        if filter_instance in self.filters:
            self.filters.remove(filter_instance)

    def scrape_all_sources(self) -> List[TennisMatch]:
        """Scrape matches from all enabled sources"""
        all_matches = []

        for scraper in self.scrapers:
            if scraper.is_available():
                try:
                    matches = scraper.scrape_matches()
                    all_matches.extend(matches)
                    self.logger.info(f"Got {len(matches)} matches from {scraper.get_source_name()}")
                    time.sleep(self.config.delay_between_requests)
                except Exception as e:
                    self.logger.error(f"Failed to scrape {scraper.get_source_name()}: {e}")
            else:
                self.logger.warning(f"Source {scraper.get_source_name()} is not available")

        return all_matches

    def get_filtered_matches(self) -> List[TennisMatch]:
        """Get matches with all filters applied"""
        matches = self.scrape_all_sources()

        for filter_instance in self.filters:
            matches = filter_instance.filter_matches(matches)
            self.logger.info(f"Applied filter '{filter_instance.get_filter_name()}', {len(matches)} matches remaining")

        return matches


# ================================================================================================
# SCRAPING WORKER THREAD
# ================================================================================================

class ScrapingWorker(QThread):
    """Worker thread for scraping operations"""

    matches_updated = Signal(list)
    status_updated = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, engine: TennisScrapingEngine):
        super().__init__()
        self.engine = engine
        self.running = False
        self.interval = 300  # 5 minutes default

    def set_interval(self, seconds: int):
        """Set scraping interval in seconds"""
        self.interval = seconds

    def start_scraping(self):
        """Start continuous scraping"""
        self.running = True
        self.start()

    def stop_scraping(self):
        """Stop continuous scraping"""
        self.running = False
        self.quit()
        self.wait()

    def run(self):
        """Main worker thread loop"""
        while self.running:
            try:
                self.status_updated.emit("Scraping matches...")
                matches = self.engine.get_filtered_matches()
                self.matches_updated.emit(matches)
                self.status_updated.emit(f"Found {len(matches)} matches")

                # Wait for interval or until stopped
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                self.error_occurred.emit(str(e))
                time.sleep(10)  # Wait before retrying on error


# ================================================================================================
# GUI APPLICATION
# ================================================================================================

class TennisScraperGUI(QMainWindow):
    """Main GUI application for tennis scraping"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("TennisScraper", "ITFScraper")
        self.config = ScrapingConfig()
        self.engine = TennisScrapingEngine(self.config)
        self.worker = ScrapingWorker(self.engine)
        self.update_checker = UpdateChecker()
        self.setup_logging()
        self.init_ui()
        self.connect_signals()
        self.load_settings()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('tennis_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ITF Tennis Match Scraper")
        self.setGeometry(100, 100, 1200, 800)
        self.apply_dark_theme()

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Matches tab
        matches_tab = self.create_matches_tab()
        tab_widget.addTab(matches_tab, "Live Matches")

        # Settings tab
        settings_tab = self.create_settings_tab()
        tab_widget.addTab(settings_tab, "Settings")

        # Updates tab
        updates_tab = self.create_updates_tab()
        tab_widget.addTab(updates_tab, "Updates")

        # Logs tab
        logs_tab = self.create_logs_tab()
        tab_widget.addTab(logs_tab, "Logs")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def create_matches_tab(self) -> QWidget:
        """Create the matches display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Control panel
        control_panel = QGroupBox("Controls")
        control_layout = QHBoxLayout(control_panel)

        self.start_btn = QPushButton("Start Scraping")
        self.stop_btn = QPushButton("Stop Scraping")
        self.stop_btn.setEnabled(False)
        self.refresh_btn = QPushButton("Refresh Now")

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(30, 3600)
        self.interval_spin.setValue(300)
        self.interval_spin.setSuffix(" seconds")

        self.live_only_cb = QCheckBox("Live matches only")
        self.live_only_cb.setChecked(True)

        control_layout.addWidget(QLabel("Refresh interval:"))
        control_layout.addWidget(self.interval_spin)
        control_layout.addWidget(self.live_only_cb)
        control_layout.addStretch()
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.refresh_btn)

        layout.addWidget(control_panel)

        # Matches table
        self.matches_table = QTableWidget()
        self.matches_table.setColumnCount(7)
        self.matches_table.setHorizontalHeaderLabels([
            "Home Player", "Away Player", "Score", "Status", "Tournament", "Source", "Time"
        ])
        self.matches_table.setAlternatingRowColors(True)
        self.matches_table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.matches_table)

        return widget

    def create_updates_tab(self) -> QWidget:
        """Create the updates management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Current version info
        version_group = QGroupBox("Version Information")
        version_layout = QFormLayout(version_group)

        current_version_label = QLabel(f"v{UpdateChecker.CURRENT_VERSION}")
        current_version_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

        build_date_label = QLabel("2025-05-24")  # Update this with actual build date

        version_layout.addRow("Current Version:", current_version_label)
        version_layout.addRow("Build Date:", build_date_label)

        # Update settings
        update_settings_group = QGroupBox("Update Settings")
        update_settings_layout = QFormLayout(update_settings_group)

        self.auto_check_cb = QCheckBox("Check for updates on startup")
        self.auto_check_cb.setChecked(True)

        self.update_frequency_combo = QComboBox()
        self.update_frequency_combo.addItems(["Never", "Daily", "Weekly", "Monthly"])
        self.update_frequency_combo.setCurrentText("Weekly")

        update_settings_layout.addRow(self.auto_check_cb)
        update_settings_layout.addRow("Check frequency:", self.update_frequency_combo)

        # Update actions
        update_actions_group = QGroupBox("Actions")
        update_actions_layout = QVBoxLayout(update_actions_group)

        check_now_btn = QPushButton("Check for Updates Now")
        check_now_btn.clicked.connect(self.check_for_updates)

        self.update_status_label = QLabel("Click 'Check for Updates Now' to check for updates")
        self.update_status_label.setStyleSheet("color: #888; font-style: italic;")

        update_actions_layout.addWidget(check_now_btn)
        update_actions_layout.addWidget(self.update_status_label)

        # Update history (placeholder for future enhancement)
        history_group = QGroupBox("Update History")
        history_layout = QVBoxLayout(history_group)

        history_text = QTextEdit()
        history_text.setMaximumHeight(150)
        history_text.setReadOnly(True)
        history_text.setPlainText("Update history will appear here after updates are installed.")

        history_layout.addWidget(history_text)

        layout.addWidget(version_group)
        layout.addWidget(update_settings_group)
        layout.addWidget(update_actions_group)
        layout.addWidget(history_group)
        layout.addStretch()

        return widget

    def create_settings_tab(self) -> QWidget:
        """Create the settings configuration tab"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Source settings
        sources_group = QGroupBox("Data Sources")
        sources_layout = QFormLayout(sources_group)

        self.flashscore_cb = QCheckBox("Enable Flashscore")
        self.flashscore_cb.setChecked(True)
        self.sofascore_cb = QCheckBox("Enable SofaScore")
        self.sofascore_cb.setChecked(True)
        self.itf_official_cb = QCheckBox("Enable ITF Official")
        self.itf_official_cb.setChecked(False)

        sources_layout.addRow(self.flashscore_cb)
        sources_layout.addRow(self.sofascore_cb)
        sources_layout.addRow(self.itf_official_cb)

        # Request settings
        request_group = QGroupBox("Request Settings")
        request_layout = QFormLayout(request_group)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 30)
        self.delay_spin.setValue(2)
        self.delay_spin.setSuffix(" seconds")

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 60)
        self.timeout_spin.setValue(10)
        self.timeout_spin.setSuffix(" seconds")

        self.headless_cb = QCheckBox("Headless browser")
        self.headless_cb.setChecked(True)

        request_layout.addRow("Delay between requests:", self.delay_spin)
        request_layout.addRow("Request timeout:", self.timeout_spin)
        request_layout.addRow(self.headless_cb)

        # Save/Load settings
        settings_buttons = QHBoxLayout()
        save_settings_btn = QPushButton("Save Settings")
        load_settings_btn = QPushButton("Load Settings")
        export_btn = QPushButton("Export Matches")

        save_settings_btn.clicked.connect(self.save_settings)
        load_settings_btn.clicked.connect(self.load_settings)
        export_btn.clicked.connect(self.export_matches)

        settings_buttons.addWidget(save_settings_btn)
        settings_buttons.addWidget(load_settings_btn)
        settings_buttons.addWidget(export_btn)
        settings_buttons.addStretch()

        layout.addRow(sources_group)
        layout.addRow(request_group)
        layout.addRow(settings_buttons)

        return widget

    def create_logs_tab(self) -> QWidget:
        """Create the logs display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))

        log_controls = QHBoxLayout()
        clear_logs_btn = QPushButton("Clear Logs")
        clear_logs_btn.clicked.connect(self.log_text.clear)
        log_controls.addWidget(clear_logs_btn)
        log_controls.addStretch()

        layout.addWidget(self.log_text)
        layout.addLayout(log_controls)

        return widget

    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))

        self.setPalette(dark_palette)

    def connect_signals(self):
        """Connect signals and slots"""
        self.start_btn.clicked.connect(self.start_scraping)
        self.stop_btn.clicked.connect(self.stop_scraping)
        self.refresh_btn.clicked.connect(self.refresh_matches)
        self.live_only_cb.toggled.connect(self.update_filters)
        self.interval_spin.valueChanged.connect(self.update_interval)

        self.worker.matches_updated.connect(self.update_matches_table)
        self.worker.status_updated.connect(self.status_bar.showMessage)
        self.worker.error_occurred.connect(self.handle_error)

    def start_scraping(self):
        """Start the scraping process"""
        self.update_config_from_ui()
        self.update_filters()
        self.worker.start_scraping()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Started scraping...")

    def stop_scraping(self):
        """Stop the scraping process"""
        self.worker.stop_scraping()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Scraping stopped")
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Stopped scraping")

    def refresh_matches(self):
        """Refresh matches once"""
        self.update_config_from_ui()
        self.update_filters()
        try:
            matches = self.engine.get_filtered_matches()
            self.update_matches_table(matches)
            self.status_bar.showMessage(f"Refreshed: {len(matches)} matches found")
        except Exception as e:
            self.handle_error(str(e))

    def check_for_updates(self):
        """Check for application updates"""
        self.update_status_label.setText("Checking for updates...")
        self.update_status_label.setStyleSheet("color: #2196F3;")

        # Use a separate thread for update checking
        self.update_thread = UpdateCheckThread(self.update_checker)
        self.update_thread.update_found.connect(self.show_update_dialog)
        self.update_thread.no_update.connect(self.no_update_available)
        self.update_thread.check_failed.connect(self.update_check_failed)
        self.update_thread.start()

    def show_update_dialog(self, version_info: VersionInfo):
        """Show update available dialog"""
        self.update_status_label.setText(f"Update available: v{version_info.version}")
        self.update_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")

        # Check if this version was previously skipped
        skipped_version = self.settings.value("skipped_version", "")
        if skipped_version == version_info.version and not version_info.critical:
            return

        update_dialog = UpdateDialog(version_info, self)
        update_dialog.show()

    def no_update_available(self):
        """Handle no update available"""
        self.update_status_label.setText("You have the latest version!")
        self.update_status_label.setStyleSheet("color: #4CAF50;")

    def update_check_failed(self, error: str):
        """Handle update check failure"""
        self.update_status_label.setText(f"Update check failed: {error}")
        self.update_status_label.setStyleSheet("color: #F44336;")

    def update_filters(self):
        """Update active filters"""
        self.engine.filters.clear()
        if self.live_only_cb.isChecked():
            self.engine.add_filter(LiveMatchFilter())

    def update_interval(self):
        """Update scraping interval"""
        self.worker.set_interval(self.interval_spin.value())

    def update_config_from_ui(self):
        """Update configuration from UI settings"""
        self.config.sources_enabled = {
            'flashscore': self.flashscore_cb.isChecked(),
            'sofascore': self.sofascore_cb.isChecked(),
            'itf_official': self.itf_official_cb.isChecked()
        }
        self.config.delay_between_requests = self.delay_spin.value()
        self.config.request_timeout = self.timeout_spin.value()
        self.config.headless_browser = self.headless_cb.isChecked()

        # Reinitialize engine with new config
        self.engine = TennisScrapingEngine(self.config)
        self.worker = ScrapingWorker(self.engine)
        self.worker.matches_updated.connect(self.update_matches_table)
        self.worker.status_updated.connect(self.status_bar.showMessage)
        self.worker.error_occurred.connect(self.handle_error)

    def update_matches_table(self, matches: List[TennisMatch]):
        """Update the matches table with new data"""
        self.matches_table.setRowCount(len(matches))

        for row, match in enumerate(matches):
            self.matches_table.setItem(row, 0, QTableWidgetItem(match.home_player))
            self.matches_table.setItem(row, 1, QTableWidgetItem(match.away_player))
            self.matches_table.setItem(row, 2, QTableWidgetItem(match.score))
            self.matches_table.setItem(row, 3, QTableWidgetItem(match.status))
            self.matches_table.setItem(row, 4, QTableWidgetItem(match.tournament))
            self.matches_table.setItem(row, 5, QTableWidgetItem(match.source))
            self.matches_table.setItem(row, 6, QTableWidgetItem(
                datetime.fromisoformat(match.timestamp).strftime('%H:%M:%S')
            ))

            # Highlight live matches
            if match.is_live:
                for col in range(self.matches_table.columnCount()):
                    item = self.matches_table.item(row, col)
                    if item:
                        item.setBackground(QColor(0, 100, 0, 100))

        self.matches_table.resizeColumnsToContents()

    def handle_error(self, error_message: str):
        """Handle errors from the worker thread"""
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {error_message}")
        QMessageBox.warning(self, "Error", f"An error occurred: {error_message}")

    def export_matches(self):
        """Export current matches to CSV"""
        if self.matches_table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No matches to export")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Matches",
            f"itf_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )

        if filename:
            try:
                matches = []
                for row in range(self.matches_table.rowCount()):
                    match_data = {}
                    headers = ["home_player", "away_player", "score", "status", "tournament", "source", "time"]
                    for col, header in enumerate(headers):
                        item = self.matches_table.item(row, col)
                        match_data[header] = item.text() if item else ""
                    matches.append(match_data)

                import pandas as pd
                df = pd.DataFrame(matches)
                df.to_csv(filename, index=False)
                QMessageBox.information(self, "Export", f"Matches exported to {filename}")

            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

    def save_settings(self):
        """Save current settings"""
        self.settings.setValue("flashscore_enabled", self.flashscore_cb.isChecked())
        self.settings.setValue("sofascore_enabled", self.sofascore_cb.isChecked())
        self.settings.setValue("itf_official_enabled", self.itf_official_cb.isChecked())
        self.settings.setValue("delay", self.delay_spin.value())
        self.settings.setValue("timeout", self.timeout_spin.value())
        self.settings.setValue("headless", self.headless_cb.isChecked())
        self.settings.setValue("interval", self.interval_spin.value())
        self.settings.setValue("live_only", self.live_only_cb.isChecked())

        # Update settings
        self.settings.setValue("check_updates_on_startup", self.auto_check_cb.isChecked())
        self.settings.setValue("update_frequency", self.update_frequency_combo.currentText())

        QMessageBox.information(self, "Settings", "Settings saved successfully")

    def load_settings(self):
        """Load saved settings"""
        self.flashscore_cb.setChecked(self.settings.value("flashscore_enabled", True, bool))
        self.sofascore_cb.setChecked(self.settings.value("sofascore_enabled", True, bool))
        self.itf_official_cb.setChecked(self.settings.value("itf_official_enabled", False, bool))
        self.delay_spin.setValue(self.settings.value("delay", 2, int))
        self.timeout_spin.setValue(self.settings.value("timeout", 10, int))
        self.headless_cb.setChecked(self.settings.value("headless", True, bool))
        self.interval_spin.setValue(self.settings.value("interval", 300, int))
        self.live_only_cb.setChecked(self.settings.value("live_only", True, bool))

        # Update settings (only load if widgets exist)
        if hasattr(self, 'auto_check_cb'):
            self.auto_check_cb.setChecked(self.settings.value("check_updates_on_startup", True, bool))
        if hasattr(self, 'update_frequency_combo'):
            frequency = self.settings.value("update_frequency", "Weekly", str)
            index = self.update_frequency_combo.findText(frequency)
            if index >= 0:
                self.update_frequency_combo.setCurrentIndex(index)

    def closeEvent(self, event):
        """Handle application close event"""
        if self.worker.running:
            self.stop_scraping()
        event.accept()


# ================================================================================================
# UPDATE SYSTEM
# ================================================================================================

@dataclass
class VersionInfo:
    """Version information structure"""
    version: str
    build_date: str
    download_url: str
    changelog: str
    critical: bool = False  # Force update if True
    min_version: str = ""  # Minimum supported version


class UpdateChecker:
    """Handles application updates"""

    CURRENT_VERSION = "1.0.0"
    UPDATE_URL = "https://api.github.com/repos/YOUR_USERNAME/itf-tennis-scraper/releases/latest"

    # Alternative: Use your own server: "https://yourserver.com/updates/version.json"

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session = requests.Session()
        self.session.timeout = 10

    def check_for_updates(self) -> Optional[VersionInfo]:
        """Check if updates are available"""
        try:
            self.logger.info("Checking for updates...")

            # GitHub releases API approach
            response = self.session.get(self.UPDATE_URL)
            response.raise_for_status()

            data = response.json()
            latest_version = data["tag_name"].lstrip('v')

            if self._compare_versions(latest_version, self.CURRENT_VERSION) > 0:
                return VersionInfo(
                    version=latest_version,
                    build_date=data["published_at"],
                    download_url=data["assets"][0]["browser_download_url"] if data["assets"] else "",
                    changelog=data["body"],
                    critical=self._is_critical_update(data["body"])
                )

            return None

        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
            return None

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""

        def version_tuple(v):
            return tuple(map(int, (v.split("."))))

        v1_tuple = version_tuple(version1)
        v2_tuple = version_tuple(version2)

        if v1_tuple > v2_tuple:
            return 1
        elif v1_tuple < v2_tuple:
            return -1
        else:
            return 0

    def _is_critical_update(self, changelog: str) -> bool:
        """Determine if update is critical based on changelog"""
        critical_keywords = ["critical", "security", "urgent", "hotfix", "vulnerability"]
        return any(keyword in changelog.lower() for keyword in critical_keywords)

    def download_update(self, version_info: VersionInfo, progress_callback=None) -> Optional[str]:
        """Download update file"""
        try:
            response = self.session.get(version_info.download_url, stream=True)
            response.raise_for_status()

            # Create updates directory
            updates_dir = Path("updates")
            updates_dir.mkdir(exist_ok=True)

            filename = f"TennisScraperUpdate_v{version_info.version}.exe"
            filepath = updates_dir / filename

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(int((downloaded / total_size) * 100))

            return str(filepath)

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None


class UpdateDialog(QWidget):
    """Dialog for showing update information"""

    def __init__(self, version_info: VersionInfo, parent=None):
        super().__init__(parent)
        self.version_info = version_info
        self.init_ui()

    def init_ui(self):
        """Initialize update dialog UI"""
        self.setWindowTitle("Update Available")
        self.setFixedSize(500, 400)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Version {self.version_info.version} Available!")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Current vs new version
        version_layout = QHBoxLayout()
        current_label = QLabel(f"Current: v{UpdateChecker.CURRENT_VERSION}")
        new_label = QLabel(f"New: v{self.version_info.version}")
        version_layout.addWidget(current_label)
        version_layout.addStretch()
        version_layout.addWidget(new_label)
        layout.addLayout(version_layout)

        # Changelog
        changelog_label = QLabel("What's New:")
        changelog_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(changelog_label)

        changelog_text = QTextEdit()
        changelog_text.setPlainText(self.version_info.changelog)
        changelog_text.setMaximumHeight(200)
        changelog_text.setReadOnly(True)
        layout.addWidget(changelog_text)

        # Critical update warning
        if self.version_info.critical:
            warning = QLabel("⚠️ This is a critical security update!")
            warning.setStyleSheet(
                "color: #FF5722; font-weight: bold; background: #FFF3E0; padding: 8px; border-radius: 4px;")
            layout.addWidget(warning)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()

        self.download_btn = QPushButton("Download & Install")
        self.download_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 8px 16px; border-radius: 4px;")

        self.later_btn = QPushButton("Remind Me Later")
        self.skip_btn = QPushButton("Skip This Version")

        if self.version_info.critical:
            self.later_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)

        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.later_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.download_btn)

        layout.addLayout(button_layout)

        # Connect signals
        self.download_btn.clicked.connect(self.download_update)
        self.later_btn.clicked.connect(self.close)
        self.skip_btn.clicked.connect(self.skip_version)

    def download_update(self):
        """Handle update download"""
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        # Start download in thread
        self.download_thread = UpdateDownloadThread(self.version_info)
        self.download_thread.progress_updated.connect(self.progress_bar.setValue)
        self.download_thread.download_completed.connect(self.on_download_complete)
        self.download_thread.download_failed.connect(self.on_download_failed)
        self.download_thread.start()

    def on_download_complete(self, filepath: str):
        """Handle successful download"""
        reply = QMessageBox.question(
            self, "Download Complete",
            f"Update downloaded successfully!\n\nWould you like to install it now?\n\n"
            f"The application will close and the installer will run.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            import subprocess
            subprocess.Popen([filepath])
            QApplication.quit()
        else:
            QMessageBox.information(
                self, "Update Ready",
                f"Update file saved to:\n{filepath}\n\nYou can install it later."
            )

        self.close()

    def on_download_failed(self, error: str):
        """Handle download failure"""
        QMessageBox.critical(self, "Download Failed", f"Failed to download update:\n{error}")
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def skip_version(self):
        """Skip this version"""
        settings = QSettings("TennisScraper", "ITFScraper")
        settings.setValue("skipped_version", self.version_info.version)
        self.close()


class UpdateDownloadThread(QThread):
    """Thread for downloading updates"""

    progress_updated = Signal(int)
    download_completed = Signal(str)
    download_failed = Signal(str)

    def __init__(self, version_info: VersionInfo):
        super().__init__()
        self.version_info = version_info
        self.update_checker = UpdateChecker()

    def run(self):
        """Download the update"""
        filepath = self.update_checker.download_update(
            self.version_info,
            progress_callback=self.progress_updated.emit
        )

        if filepath:
            self.download_completed.emit(filepath)
        else:
            self.download_failed.emit("Download failed")


class UpdateCheckThread(QThread):
    """Thread for checking updates without blocking UI"""

    update_found = Signal(VersionInfo)
    no_update = Signal()
    check_failed = Signal(str)

    def __init__(self, update_checker: UpdateChecker):
        super().__init__()
        self.update_checker = update_checker

    def run(self):
        """Check for updates"""
        try:
            version_info = self.update_checker.check_for_updates()
            if version_info:
                self.update_found.emit(version_info)
            else:
                self.no_update.emit()
        except Exception as e:
            self.check_failed.emit(str(e))


# ================================================================================================
# MAIN APPLICATION ENTRY POINT
# ================================================================================================

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support

    # Create and show the main window
    window = TennisScraperGUI()
    window.show()

    # Check for updates on startup (optional)
    if window.settings.value("check_updates_on_startup", True, bool):
        QTimer.singleShot(3000, window.check_for_updates)  # Check after 3 seconds

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# ================================================================================================
# REQUIREMENTS.TXT
# ================================================================================================
"""
Required packages (save as requirements.txt):

PySide6>=6.5.0
requests>=2.28.0
beautifulsoup4>=4.11.0
selenium>=4.8.0
pandas>=1.5.0
lxml>=4.9.0

Install with: pip install -r requirements.txt

Additional setup:
- Install ChromeDriver for Selenium
- Ensure Chrome browser is installed
"""

# ================================================================================================
# UPDATE DEPLOYMENT GUIDE
# ================================================================================================
"""
🚀 DEPLOYMENT & UPDATE SYSTEM SETUP GUIDE
==========================================

## Option 1: GitHub Releases (Recommended)
1. Create a GitHub repository for your app
2. Update UpdateChecker.UPDATE_URL with your repo info:
   UPDATE_URL = "https://api.github.com/repos/USERNAME/REPO_NAME/releases/latest"

3. To push updates:
   a. Build your executable: `pyinstaller --onefile --windowed tennis_scraper.py`
   b. Create a new release on GitHub
   c. Upload the .exe file as an asset
   d. Tag it with version number (e.g., v1.0.1)

## Option 2: Your Own Server
1. Create a simple JSON endpoint that returns:
   {
     "tag_name": "v1.0.1",
     "published_at": "2025-05-24T10:00:00Z",
     "body": "Bug fixes and improvements",
     "assets": [{"browser_download_url": "https://yourserver.com/updates/app_v1.0.1.exe"}]
   }

2. Update UpdateChecker.UPDATE_URL to point to your endpoint

## Building Executable
Create a build script (build.py):

```python
import PyInstaller.__main__
import os
from datetime import datetime

# Build command
PyInstaller.__main__.run([
    '--onefile',
    '--windowed',
    '--icon=app_icon.ico',  # Optional
    '--name=TennisScraperPro',
    '--distpath=dist',
    '--workpath=build',
    '--specpath=build',
    'tennis_scraper.py'
])

print(f"Build completed: dist/TennisScraperPro.exe")
```

## Auto-updater Features:
✅ Automatic update checking on startup
✅ Manual update checking
✅ Progress bars for downloads
✅ Critical update enforcement
✅ Version skipping
✅ Changelog display
✅ Settings persistence

## Security Notes:
- Use HTTPS for all update URLs
- Consider code signing your executables
- Implement checksum verification for downloads
- Test updates thoroughly before release

## Quick Start for Client Updates:
1. Modify tennis_scraper.py
2. Increment version in UpdateChecker.CURRENT_VERSION
3. Run: `python build.py`
4. Upload to GitHub releases or your server
5. Client apps will automatically detect and offer the update!

## Example release workflow:
```bash
# 1. Update version in code
# 2. Build executable
python build.py

# 3. Create release (if using GitHub)
git tag v1.0.1
git push origin v1.0.1

# 4. Upload exe to GitHub release assets
# Your clients will automatically be notified!
```
"""