"""
ControlPanel component for managing scraping operations.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QLabel,
                               QSpinBox, QCheckBox, QGroupBox, QVBoxLayout)
from PySide6.QtCore import Signal, QSettings

from ...config import Config  # Adjusted import
from ...utils.logging import get_logger


class ControlPanel(QGroupBox):
    """
    A QGroupBox providing controls for starting, stopping, and configuring scraping.
    """
    start_scraping = Signal()
    stop_scraping = Signal()
    refresh_requested = Signal()
    settings_changed = Signal()  # Emitted when settings controlled here are changed

    def __init__(self, config: Config, parent=None):
        super().__init__("Controls", parent)
        self.config = config  # Store a reference to the main Config object
        self.logger = get_logger(__name__)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the UI elements of the control panel."""
        layout = QHBoxLayout(self)

        # Start/Stop buttons
        self.start_button = QPushButton("▶ Start Scraping")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.stop_button = QPushButton("■ Stop Scraping")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.stop_button.setEnabled(False)

        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh Now")

        # Auto-refresh controls
        refresh_group_layout = QHBoxLayout()
        self.auto_refresh_checkbox = QCheckBox("Auto-refresh every:")
        self.auto_refresh_checkbox.setChecked(True)  # Default to on

        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(30, 3600)  # 30 seconds to 1 hour
        self.interval_spinbox.setValue(self.config.ui.auto_refresh_interval)
        self.interval_spinbox.setSuffix(" s")
        self.interval_spinbox.setToolTip("Interval for automatic match refreshing.")

        self.auto_refresh_checkbox.toggled.connect(self.interval_spinbox.setEnabled)

        refresh_group_layout.addWidget(self.auto_refresh_checkbox)
        refresh_group_layout.addWidget(self.interval_spinbox)

        # Add widgets to main layout
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.refresh_button)
        layout.addStretch(1)  # Pushes auto-refresh to the right
        layout.addLayout(refresh_group_layout)

    def _connect_signals(self):
        """Connect internal signals to slots or emit external signals."""
        self.start_button.clicked.connect(self.start_scraping.emit)
        self.stop_button.clicked.connect(self.stop_scraping.emit)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        # Connect interval changes to settings_changed signal
        self.interval_spinbox.valueChanged.connect(self._on_interval_changed)
        self.auto_refresh_checkbox.toggled.connect(self._on_auto_refresh_toggled)

    def _on_interval_changed(self, value: int):
        """Handle interval spinbox value change."""
        self.config.ui.auto_refresh_interval = value
        self.settings_changed.emit()
        self.logger.debug(f"Auto-refresh interval changed to {value}s")

    def _on_auto_refresh_toggled(self, checked: bool):
        """Handle auto-refresh checkbox toggle."""
        # This state could be managed by MainWindow based on this signal
        self.settings_changed.emit()  # MainWindow can read checkbox state
        self.logger.debug(f"Auto-refresh toggled: {'Enabled' if checked else 'Disabled'}")

    def set_scraping_state(self, is_scraping: bool):
        """Update button states based on scraping status."""
        self.start_button.setEnabled(not is_scraping)
        self.stop_button.setEnabled(is_scraping)
        self.refresh_button.setEnabled(not is_scraping)  # Can't refresh while continuous scraping
        self.logger.info(f"ControlPanel scraping state set to: {'Active' if is_scraping else 'Inactive'}")

    def get_auto_refresh_interval(self) -> int:
        """Returns the current auto-refresh interval in seconds."""
        return self.interval_spinbox.value()

    def is_auto_refresh_enabled(self) -> bool:
        """Returns whether auto-refresh is currently checked."""
        return self.auto_refresh_checkbox.isChecked()

    def save_settings(self, settings: QSettings):
        """Save control panel specific settings."""
        settings.setValue("controlPanel/autoRefreshEnabled", self.auto_refresh_checkbox.isChecked())
        settings.setValue("controlPanel/autoRefreshInterval", self.interval_spinbox.value())
        self.logger.debug("ControlPanel settings saved.")

    def load_settings(self, settings: QSettings):
        """Load control panel specific settings."""
        auto_refresh_enabled = settings.value("controlPanel/autoRefreshEnabled", True, bool)
        auto_refresh_interval = settings.value("controlPanel/autoRefreshInterval",
                                               self.config.ui.auto_refresh_interval, int)

        self.auto_refresh_checkbox.setChecked(auto_refresh_enabled)
        self.interval_spinbox.setValue(auto_refresh_interval)
        self.interval_spinbox.setEnabled(auto_refresh_enabled)
        self.logger.debug("ControlPanel settings loaded.")