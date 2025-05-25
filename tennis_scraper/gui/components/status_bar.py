"""
Custom status bar component with enhanced features.
"""

from PySide6.QtWidgets import (
    QStatusBar, QLabel, QProgressBar, QPushButton, QHBoxLayout, QWidget, QSizePolicy
)
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSizePolicy
from ...utils.logging import get_logger


class CustomStatusBar(QStatusBar):
    """Enhanced status bar with additional features."""

    # Signals
    settings_clicked = Signal()
    logs_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # Status tracking
        self.current_status = ""
        self.live_match_count = 0
        self.total_match_count = 0

        # Auto-clear timer
        self.clear_timer = QTimer()
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self._auto_clear_status)

        self._init_widgets()

    def _init_widgets(self):
        """Initialize status bar widgets."""
        # Main status label (left side)
        self.status_label = QLabel("Ready")
        self.addWidget(self.status_label)

        # Spacer to push right-side widgets to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        # Live matches indicator
        self.live_matches_label = QLabel("Live: 0")
        self.live_matches_label.setStyleSheet("""
            QLabel {
                color: #ff4444;
                font-weight: bold;
                padding: 2px 8px;
                border: 1px solid #ff4444;
                border-radius: 3px;
                background-color: rgba(255, 68, 68, 0.1);
            }
        """)
        self.live_matches_label.setVisible(False)
        self.addWidget(self.live_matches_label)

        # Total matches indicator
        self.total_matches_label = QLabel("Total: 0")
        self.total_matches_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-weight: bold;
                padding: 2px 8px;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                background-color: rgba(76, 175, 80, 0.1);
            }
        """)
        self.addWidget(self.total_matches_label)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setTextVisible(True)
        self.addWidget(self.progress_bar)

        # Connection status indicator
        self.connection_label = QLabel("●")
        self.connection_label.setToolTip("Connection Status")
        self.set_connection_status(True)  # Default to connected
        self.addWidget(self.connection_label)

        # Quick access buttons
        self.logs_btn = QPushButton("Logs")
        self.logs_btn.setMaximumWidth(50)
        self.logs_btn.setFlat(True)
        self.logs_btn.clicked.connect(self.logs_clicked.emit)
        self.addWidget(self.logs_btn)

        # Memory usage (if available)
        self.memory_label = QLabel()
        self.memory_label.setVisible(False)
        self.addWidget(self.memory_label)

        # Setup memory monitoring
        self.memory_timer = QTimer()
        self.memory_timer.timeout.connect(self._update_memory_usage)
        self.memory_timer.start(5000)  # Update every 5 seconds

    def set_status(self, message: str, timeout: int = 5000):
        """Set status message with optional auto-clear timeout."""
        self.current_status = message
        self.status_label.setText(message)

        if timeout > 0:
            self.clear_timer.start(timeout)

        self.logger.debug(f"Status: {message}")

    def set_permanent_status(self, message: str):
        """Set permanent status message (won't auto-clear)."""
        self.current_status = message
        self.status_label.setText(message)
        self.clear_timer.stop()

    def clear_status(self):
        """Clear the status message."""
        self.status_label.setText("Ready")
        self.current_status = ""
        self.clear_timer.stop()

    def _auto_clear_status(self):
        """Auto-clear status after timeout."""
        if self.current_status:
            self.clear_status()

    def show_progress(self, text: str = "", value: int = -1):
        """Show progress bar with optional text and value."""
        self.progress_bar.setVisible(True)

        if text:
            self.progress_bar.setFormat(text)

        if value >= 0:
            self.progress_bar.setValue(value)
        else:
            # Indeterminate progress
            self.progress_bar.setRange(0, 0)

    def update_progress(self, value: int, text: str = ""):
        """Update progress bar value and text."""
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(value)
            if text:
                self.progress_bar.setFormat(text)

    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def set_live_count(self, count: int):
        """Set live matches count."""
        self.live_match_count = count
        self.live_matches_label.setText(f"Live: {count}")
        self.live_matches_label.setVisible(count > 0)

        # Animate live indicator
        if count > 0:
            self._animate_live_indicator()

    def set_total_count(self, count: int):
        """Set total matches count."""
        self.total_match_count = count
        self.total_matches_label.setText(f"Total: {count}")

    def _animate_live_indicator(self):
        """Animate the live matches indicator."""
        # Simple color animation for live indicator
        current_style = self.live_matches_label.styleSheet()
        if "background-color: rgba(255, 68, 68, 0.3)" in current_style:
            # Reset to normal
            self.live_matches_label.setStyleSheet("""
                QLabel {
                    color: #ff4444;
                    font-weight: bold;
                    padding: 2px 8px;
                    border: 1px solid #ff4444;
                    border-radius: 3px;
                    background-color: rgba(255, 68, 68, 0.1);
                }
            """)
        else:
            # Highlight
            self.live_matches_label.setStyleSheet("""
                QLabel {
                    color: #ff4444;
                    font-weight: bold;
                    padding: 2px 8px;
                    border: 1px solid #ff4444;
                    border-radius: 3px;
                    background-color: rgba(255, 68, 68, 0.3);
                }
            """)

        # Schedule reset after short delay
        QTimer.singleShot(500, lambda: self.live_matches_label.setStyleSheet("""
            QLabel {
                color: #ff4444;
                font-weight: bold;
                padding: 2px 8px;
                border: 1px solid #ff4444;
                border-radius: 3px;
                background-color: rgba(255, 68, 68, 0.1);
            }
        """))

    def set_connection_status(self, connected: bool):
        """Set connection status indicator."""
        if connected:
            self.connection_label.setText("●")
            self.connection_label.setStyleSheet("color: #4CAF50; font-size: 16px;")
            self.connection_label.setToolTip("Connected")
        else:
            self.connection_label.setText("●")
            self.connection_label.setStyleSheet("color: #f44336; font-size: 16px;")
            self.connection_label.setToolTip("Disconnected")

    def _update_memory_usage(self):
        """Update memory usage display."""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024

            self.memory_label.setText(f"RAM: {memory_mb:.1f}MB")
            self.memory_label.setVisible(True)

            # Color code based on usage
            if memory_mb > 500:  # > 500MB
                self.memory_label.setStyleSheet("color: #ff4444;")
            elif memory_mb > 200:  # > 200MB
                self.memory_label.setStyleSheet("color: #ffaa00;")
            else:
                self.memory_label.setStyleSheet("color: #4CAF50;")

        except ImportError:
            # psutil not available
            self.memory_label.setVisible(False)
        except Exception:
            # Other error
            self.memory_label.setVisible(False)

    def add_custom_widget(self, widget, permanent: bool = False):
        """Add a custom widget to the status bar."""
        if permanent:
            self.addPermanentWidget(widget)
        else:
            self.addWidget(widget)

    def show_notification(self, message: str, duration: int = 3000):
        """Show a temporary notification."""
        # Save current status
        previous_status = self.current_status

        # Show notification
        self.set_status(f"💬 {message}", duration)

        # Restore previous status after notification
        QTimer.singleShot(duration + 100, lambda: self.set_status(previous_status, 0))