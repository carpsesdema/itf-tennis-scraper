"""
Settings configuration panel for the tennis scraper application.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QSpinBox, QCheckBox, QComboBox, QLineEdit,
    QTabWidget, QMessageBox, QFileDialog, QSlider, QLabel,
    QTextEdit, QScrollArea
)
from PySide6.QtCore import Signal, QSettings, Qt
from PySide6.QtGui import QFont

from ...config import Config
from ...utils.logging import get_logger


class SettingsPanel(QScrollArea):
    """Comprehensive settings panel with multiple categories."""

    # Signals
    settings_changed = Signal()
    scrapers_changed = Signal()
    ui_changed = Signal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.logger = get_logger(__name__)

        # Make scrollable
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._init_ui()
        self._load_settings()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface."""
        # Create main widget for scroll area
        main_widget = QWidget()
        self.setWidget(main_widget)

        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Create tabs for different setting categories
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create setting tabs
        self._create_scraping_tab()
        self._create_ui_tab()
        self._create_sources_tab()
        self._create_filters_tab()
        self._create_export_tab()
        self._create_updates_tab()
        self._create_advanced_tab()

        # Action buttons
        self._create_action_buttons(layout)

    def _create_scraping_tab(self):
        """Create scraping settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Request settings
        request_group = QGroupBox("Request Settings")
        request_layout = QFormLayout(request_group)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 30)
        self.delay_spin.setValue(self.config.scraping.delay_between_requests)
        self.delay_spin.setSuffix(" seconds")
        self.delay_spin.setToolTip("Delay between requests to avoid rate limiting")
        request_layout.addRow("Delay between requests:", self.delay_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(self.config.scraping.request_timeout)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setToolTip("Timeout for HTTP requests")
        request_layout.addRow("Request timeout:", self.timeout_spin)

        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(1, 10)
        self.retries_spin.setValue(self.config.scraping.max_retries)
        self.retries_spin.setToolTip("Maximum number of retry attempts")
        request_layout.addRow("Max retries:", self.retries_spin)

        # Browser settings
        browser_group = QGroupBox("Browser Settings")
        browser_layout = QFormLayout(browser_group)

        self.headless_cb = QCheckBox("Run browsers in headless mode")
        self.headless_cb.setChecked(self.config.scraping.headless_browser)
        self.headless_cb.setToolTip("Hide browser windows during scraping")
        browser_layout.addRow(self.headless_cb)

        self.user_agent_edit = QLineEdit()
        self.user_agent_edit.setText(self.config.scraping.user_agent)
        self.user_agent_edit.setToolTip("User agent string for HTTP requests")
        browser_layout.addRow("User Agent:", self.user_agent_edit)

        layout.addWidget(request_group)
        layout.addWidget(browser_group)
        layout.addStretch()

        self.tab_widget.addTab(widget, "Scraping")

    def _create_ui_tab(self):
        """Create UI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Appearance settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.theme_combo.setCurrentText(self.config.ui.theme.title())
        appearance_layout.addRow("Theme:", self.theme_combo)

        # Window settings
        window_group = QGroupBox("Window Settings")
        window_layout = QFormLayout(window_group)

        self.window_width_spin = QSpinBox()
        self.window_width_spin.setRange(800, 3000)
        self.window_width_spin.setValue(self.config.ui.window_width)
        window_layout.addRow("Default width:", self.window_width_spin)

        self.window_height_spin = QSpinBox()
        self.window_height_spin.setRange(600, 2000)
        self.window_height_spin.setValue(self.config.ui.window_height)
        window_layout.addRow("Default height:", self.window_height_spin)

        # Refresh settings
        refresh_group = QGroupBox("Refresh Settings")
        refresh_layout = QFormLayout(refresh_group)

        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(30, 3600)
        self.refresh_interval_spin.setValue(self.config.ui.auto_refresh_interval)
        self.refresh_interval_spin.setSuffix(" seconds")
        refresh_layout.addRow("Auto-refresh interval:", self.refresh_interval_spin)

        self.show_live_only_cb = QCheckBox("Show live matches only by default")
        self.show_live_only_cb.setChecked(self.config.ui.show_live_only)
        refresh_layout.addRow(self.show_live_only_cb)

        layout.addWidget(appearance_group)
        layout.addWidget(window_group)
        layout.addWidget(refresh_group)
        layout.addStretch()

        self.tab_widget.addTab(widget, "Interface")

    def _create_sources_tab(self):
        """Create data sources settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        sources_group = QGroupBox("Data Sources")
        sources_layout = QVBoxLayout(sources_group)

        # Source checkboxes - ONLY FLASHSCORE NOW
        self.source_checkboxes = {}

        for source_name, enabled in self.config.scraping.sources_enabled.items():
            cb = QCheckBox(f"Enable {source_name.title()}")
            cb.setChecked(enabled)

            # Add descriptions - ONLY FLASHSCORE
            descriptions = {
                'flashscore': 'Fast updates, comprehensive coverage, bet365 indicators',
                # Removed sofascore and itf_official descriptions
            }

            if source_name in descriptions:
                cb.setToolTip(descriptions[source_name])

            self.source_checkboxes[source_name] = cb
            sources_layout.addWidget(cb)

        # Add note about bet365 requirement
        bet365_note = QLabel("Note: Flashscore is required for bet365 betting indicator detection")
        bet365_note.setStyleSheet("color: #888; font-style: italic; margin-top: 10px;")
        sources_layout.addWidget(bet365_note)

        layout.addWidget(sources_group)
        layout.addStretch()

        self.tab_widget.addTab(widget, "Sources")

    def _create_filters_tab(self):
        """Create filters settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Default filters
        default_group = QGroupBox("Default Filters")
        default_layout = QFormLayout(default_group)

        self.default_live_only_cb = QCheckBox("Live matches only")
        self.default_live_only_cb.setChecked(True)
        default_layout.addRow(self.default_live_only_cb)

        self.default_ranking_cb = QCheckBox("Top ranked players only")
        default_layout.addRow(self.default_ranking_cb)

        self.max_ranking_spin = QSpinBox()
        self.max_ranking_spin.setRange(1, 1000)
        self.max_ranking_spin.setValue(200)
        self.max_ranking_spin.setEnabled(self.default_ranking_cb.isChecked())
        default_layout.addRow("Max ranking:", self.max_ranking_spin)

        # Connect ranking checkbox to enable/disable spinner
        self.default_ranking_cb.toggled.connect(self.max_ranking_spin.setEnabled)

        # Advanced filters
        advanced_group = QGroupBox("Advanced Filtering")
        advanced_layout = QFormLayout(advanced_group)

        self.regex_enabled_cb = QCheckBox("Enable regex filtering")
        advanced_layout.addRow(self.regex_enabled_cb)

        self.case_sensitive_cb = QCheckBox("Case sensitive filtering")
        advanced_layout.addRow(self.case_sensitive_cb)

        layout.addWidget(default_group)
        layout.addWidget(advanced_group)
        layout.addStretch()

        self.tab_widget.addTab(widget, "Filters")

    def _create_export_tab(self):
        """Create export settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Export format
        format_group = QGroupBox("Export Format")
        format_layout = QFormLayout(format_group)

        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["CSV", "JSON", "Excel"])
        self.export_format_combo.setCurrentText(self.config.export.default_format.upper())
        format_layout.addRow("Default format:", self.export_format_combo)

        self.include_metadata_cb = QCheckBox("Include metadata in exports")
        self.include_metadata_cb.setChecked(self.config.export.include_metadata)
        format_layout.addRow(self.include_metadata_cb)

        # Date format
        self.timestamp_format_edit = QLineEdit()
        self.timestamp_format_edit.setText(self.config.export.timestamp_format)
        self.timestamp_format_edit.setToolTip("Python datetime format string")
        format_layout.addRow("Timestamp format:", self.timestamp_format_edit)

        # Export location
        location_group = QGroupBox("Export Location")
        location_layout = QFormLayout(location_group)

        self.export_path_edit = QLineEdit()
        self.export_path_edit.setText("./exports/")
        location_layout.addRow("Default path:", self.export_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_export_path)
        location_layout.addRow("", browse_btn)

        layout.addWidget(format_group)
        layout.addWidget(location_group)
        layout.addStretch()

        self.tab_widget.addTab(widget, "Export")

    def _create_updates_tab(self):
        """Create updates settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Update checking
        check_group = QGroupBox("Update Checking")
        check_layout = QFormLayout(check_group)

        self.check_on_startup_cb = QCheckBox("Check for updates on startup")
        self.check_on_startup_cb.setChecked(self.config.updates.check_on_startup)
        check_layout.addRow(self.check_on_startup_cb)

        self.update_frequency_combo = QComboBox()
        self.update_frequency_combo.addItems(["Never", "Daily", "Weekly", "Monthly"])
        self.update_frequency_combo.setCurrentText(self.config.updates.frequency.title())
        check_layout.addRow("Check frequency:", self.update_frequency_combo)

        self.auto_download_cb = QCheckBox("Automatically download updates")
        self.auto_download_cb.setChecked(self.config.updates.auto_download)
        check_layout.addRow(self.auto_download_cb)

        # Update source
        source_group = QGroupBox("Update Source")
        source_layout = QFormLayout(source_group)

        self.github_repo_edit = QLineEdit()
        self.github_repo_edit.setText(self.config.updates.github_repo)
        self.github_repo_edit.setToolTip("GitHub repository for updates")
        source_layout.addRow("GitHub repository:", self.github_repo_edit)

        layout.addWidget(check_group)
        layout.addWidget(source_group)
        layout.addStretch()

        self.tab_widget.addTab(widget, "Updates")

    def _create_advanced_tab(self):
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Logging settings
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText(self.config.logging.level)
        logging_layout.addRow("Log level:", self.log_level_combo)

        self.log_file_edit = QLineEdit()
        self.log_file_edit.setText(self.config.logging.file_path)
        logging_layout.addRow("Log file:", self.log_file_edit)

        self.max_log_size_spin = QSpinBox()
        self.max_log_size_spin.setRange(1, 100)
        self.max_log_size_spin.setValue(self.config.logging.max_file_size // (1024 * 1024))
        self.max_log_size_spin.setSuffix(" MB")
        logging_layout.addRow("Max log file size:", self.max_log_size_spin)

        # Performance settings
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout(performance_group)

        self.concurrent_scrapers_spin = QSpinBox()
        self.concurrent_scrapers_spin.setRange(1, 10)
        self.concurrent_scrapers_spin.setValue(3)
        self.concurrent_scrapers_spin.setToolTip("Number of concurrent scraping operations")
        performance_layout.addRow("Concurrent scrapers:", self.concurrent_scrapers_spin)

        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(10, 1000)
        self.cache_size_spin.setValue(100)
        self.cache_size_spin.setToolTip("Maximum number of cached matches")
        performance_layout.addRow("Cache size:", self.cache_size_spin)

        layout.addWidget(logging_group)
        layout.addWidget(performance_group)
        layout.addStretch()

        self.tab_widget.addTab(widget, "Advanced")

    def _create_action_buttons(self, layout: QVBoxLayout):
        """Create action buttons at the bottom."""
        button_layout = QHBoxLayout()

        # Save button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # Reset button
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        # Apply button
        self.apply_btn = QPushButton("Apply")

        button_layout.addStretch()
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect widget signals."""
        # Action buttons
        self.save_btn.clicked.connect(self._save_settings)
        self.reset_btn.clicked.connect(self._reset_settings)
        self.apply_btn.clicked.connect(self._apply_settings)

        # Settings change signals (connect to apply button enabling)
        widgets_to_watch = [
            self.delay_spin, self.timeout_spin, self.retries_spin,
            self.headless_cb, self.user_agent_edit, self.theme_combo,
            self.refresh_interval_spin, self.show_live_only_cb,
            self.check_on_startup_cb, self.update_frequency_combo,
            self.log_level_combo, self.export_format_combo
        ]

        for widget in widgets_to_watch:
            if hasattr(widget, 'valueChanged'):
                widget.valueChanged.connect(self._on_setting_changed)
            elif hasattr(widget, 'toggled'):
                widget.toggled.connect(self._on_setting_changed)
            elif hasattr(widget, 'currentTextChanged'):
                widget.currentTextChanged.connect(self._on_setting_changed)
            elif hasattr(widget, 'textChanged'):
                widget.textChanged.connect(self._on_setting_changed)

        # Source checkboxes
        for cb in self.source_checkboxes.values():
            cb.toggled.connect(self._on_setting_changed)

    def _load_settings(self):
        """Load settings into the UI."""
        # Settings are already loaded in _init_ui methods
        pass

    def _on_setting_changed(self):
        """Handle setting changes."""
        # Enable apply button when settings change
        self.apply_btn.setEnabled(True)

    def _apply_settings(self):
        """Apply settings without saving to file."""
        self._update_config_from_ui()
        self.settings_changed.emit()
        self.apply_btn.setEnabled(False)

        QMessageBox.information(self, "Settings", "Settings applied successfully!")

    def _save_settings(self):
        """Save settings to file."""
        self._update_config_from_ui()

        try:
            self.config.save_to_file()
            self.settings_changed.emit()
            self.apply_btn.setEnabled(False)

            QMessageBox.information(self, "Settings", "Settings saved successfully!")
            self.logger.info("Settings saved from settings panel")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")
            self.logger.error(f"Failed to save settings: {e}")

    def _reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Create new default config
            from ...config import Config
            default_config = Config()

            # Update UI with defaults
            self._load_config_to_ui(default_config)
            self._on_setting_changed()  # Enable apply button

    def _update_config_from_ui(self):
        """Update configuration object from UI values."""
        # Scraping settings
        self.config.scraping.delay_between_requests = self.delay_spin.value()
        self.config.scraping.request_timeout = self.timeout_spin.value()
        self.config.scraping.max_retries = self.retries_spin.value()
        self.config.scraping.headless_browser = self.headless_cb.isChecked()
        self.config.scraping.user_agent = self.user_agent_edit.text()

        # UI settings
        self.config.ui.theme = self.theme_combo.currentText().lower()
        self.config.ui.window_width = self.window_width_spin.value()
        self.config.ui.window_height = self.window_height_spin.value()
        self.config.ui.auto_refresh_interval = self.refresh_interval_spin.value()
        self.config.ui.show_live_only = self.show_live_only_cb.isChecked()

        # Source settings
        for source_name, cb in self.source_checkboxes.items():
            self.config.scraping.sources_enabled[source_name] = cb.isChecked()

        # Update settings
        self.config.updates.check_on_startup = self.check_on_startup_cb.isChecked()
        self.config.updates.frequency = self.update_frequency_combo.currentText().lower()
        self.config.updates.auto_download = self.auto_download_cb.isChecked()
        self.config.updates.github_repo = self.github_repo_edit.text()

        # Export settings
        self.config.export.default_format = self.export_format_combo.currentText().lower()
        self.config.export.include_metadata = self.include_metadata_cb.isChecked()
        self.config.export.timestamp_format = self.timestamp_format_edit.text()

        # Logging settings
        self.config.logging.level = self.log_level_combo.currentText()
        self.config.logging.file_path = self.log_file_edit.text()
        self.config.logging.max_file_size = self.max_log_size_spin.value() * 1024 * 1024

    def _load_config_to_ui(self, config: Config):
        """Load configuration values into UI."""
        # Block signals during loading
        self.blockSignals(True)

        # Scraping settings
        self.delay_spin.setValue(config.scraping.delay_between_requests)
        self.timeout_spin.setValue(config.scraping.request_timeout)
        self.retries_spin.setValue(config.scraping.max_retries)
        self.headless_cb.setChecked(config.scraping.headless_browser)
        self.user_agent_edit.setText(config.scraping.user_agent)

        # UI settings
        self.theme_combo.setCurrentText(config.ui.theme.title())
        self.window_width_spin.setValue(config.ui.window_width)
        self.window_height_spin.setValue(config.ui.window_height)
        self.refresh_interval_spin.setValue(config.ui.auto_refresh_interval)
        self.show_live_only_cb.setChecked(config.ui.show_live_only)

        # Source settings
        for source_name, enabled in config.scraping.sources_enabled.items():
            if source_name in self.source_checkboxes:
                self.source_checkboxes[source_name].setChecked(enabled)

        # Update settings
        self.check_on_startup_cb.setChecked(config.updates.check_on_startup)
        self.update_frequency_combo.setCurrentText(config.updates.frequency.title())
        self.auto_download_cb.setChecked(config.updates.auto_download)
        self.github_repo_edit.setText(config.updates.github_repo)

        # Export settings
        self.export_format_combo.setCurrentText(config.export.default_format.upper())
        self.include_metadata_cb.setChecked(config.export.include_metadata)
        self.timestamp_format_edit.setText(config.export.timestamp_format)

        # Logging settings
        self.log_level_combo.setCurrentText(config.logging.level)
        self.log_file_edit.setText(config.logging.file_path)
        self.max_log_size_spin.setValue(config.logging.max_file_size // (1024 * 1024))

        self.blockSignals(False)

    def _browse_export_path(self):
        """Browse for export path."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", self.export_path_edit.text()
        )
        if path:
            self.export_path_edit.setText(path)
            self._on_setting_changed()

    def get_current_settings(self) -> Config:
        """Get current settings as Config object."""
        self._update_config_from_ui()
        return self.config