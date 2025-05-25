"""
Log viewer component for displaying application logs.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QCheckBox, QLineEdit, QSpinBox
)
from PySide6.QtCore import QTimer, Signal, Qt, QThread
from PySide6.QtGui import QFont, QTextCursor, QColor

from ...utils.logging import get_recent_logs, get_log_file_path
from ...utils.logging import get_logger


class LogMonitorWorker(QThread):
    """Worker thread for monitoring log file changes."""

    new_log_line = Signal(str)

    def __init__(self, log_file_path: str):
        super().__init__()
        self.log_file_path = log_file_path
        self.running = False
        self.last_position = 0

    def run(self):
        """Monitor log file for new entries."""
        import time
        from pathlib import Path

        self.running = True
        log_file = Path(self.log_file_path)

        # Get initial file size
        if log_file.exists():
            self.last_position = log_file.stat().st_size

        while self.running:
            try:
                if log_file.exists():
                    current_size = log_file.stat().st_size

                    if current_size > self.last_position:
                        # Read new content
                        with open(log_file, 'r', encoding='utf-8') as f:
                            f.seek(self.last_position)
                            new_content = f.read()

                            for line in new_content.splitlines():
                                if line.strip():
                                    self.new_log_line.emit(line)

                        self.last_position = current_size

                time.sleep(1)  # Check every second

            except Exception:
                # Ignore errors and continue monitoring
                time.sleep(1)

    def stop(self):
        """Stop monitoring."""
        self.running = False


class LogViewer(QWidget):
    """Log viewer component with filtering and monitoring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.monitor_worker = None
        self.max_lines = 1000
        self.auto_scroll = True

        self._init_ui()
        self._connect_signals()
        self._load_initial_logs()
        self._start_monitoring()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()

        # Log level filter
        controls_layout.addWidget(QLabel("Level:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_filter.setCurrentText("INFO")
        self.level_filter.setMaximumWidth(100)
        controls_layout.addWidget(self.level_filter)

        # Search filter
        controls_layout.addWidget(QLabel("Search:"))
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Filter logs...")
        self.search_filter.setMaximumWidth(200)
        controls_layout.addWidget(self.search_filter)

        # Max lines
        controls_layout.addWidget(QLabel("Max lines:"))
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(100, 10000)
        self.max_lines_spin.setValue(self.max_lines)
        self.max_lines_spin.setMaximumWidth(80)
        controls_layout.addWidget(self.max_lines_spin)

        # Auto-scroll checkbox
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(self.auto_scroll)
        controls_layout.addWidget(self.auto_scroll_cb)

        controls_layout.addStretch()

        # Action buttons
        self.clear_btn = QPushButton("Clear")
        self.refresh_btn = QPushButton("Refresh")
        self.save_btn = QPushButton("Save Logs")

        controls_layout.addWidget(self.clear_btn)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.save_btn)

        layout.addLayout(controls_layout)

        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        self.log_display.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.log_display)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _connect_signals(self):
        """Connect signals and slots."""
        self.level_filter.currentTextChanged.connect(self._apply_filters)
        self.search_filter.textChanged.connect(self._apply_filters)
        self.max_lines_spin.valueChanged.connect(self._on_max_lines_changed)
        self.auto_scroll_cb.toggled.connect(self._on_auto_scroll_toggled)

        self.clear_btn.clicked.connect(self._clear_logs)
        self.refresh_btn.clicked.connect(self._refresh_logs)
        self.save_btn.clicked.connect(self._save_logs)

    def _load_initial_logs(self):
        """Load initial log entries."""
        try:
            recent_logs = get_recent_logs(self.max_lines)
            if recent_logs:
                for log_line in recent_logs:
                    self._add_log_line(log_line.strip())
                self.status_label.setText(f"Loaded {len(recent_logs)} log entries")
            else:
                self.status_label.setText("No log entries found")
        except Exception as e:
            self.logger.error(f"Failed to load initial logs: {e}")
            self.status_label.setText("Failed to load logs")

    def _start_monitoring(self):
        """Start monitoring log file for new entries."""
        try:
            log_file_path = get_log_file_path()
            self.monitor_worker = LogMonitorWorker(log_file_path)
            self.monitor_worker.new_log_line.connect(self._add_log_line)
            self.monitor_worker.start()
            self.logger.info("Started log monitoring")
        except Exception as e:
            self.logger.error(f"Failed to start log monitoring: {e}")

    def _add_log_line(self, line: str):
        """Add a new log line to the display."""
        if not self._should_show_line(line):
            return

        # Color code based on log level
        colored_line = self._colorize_log_line(line)

        # Add to display
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(colored_line + "<br>")

        # Limit number of lines
        self._enforce_line_limit()

        # Auto-scroll if enabled
        if self.auto_scroll:
            scrollbar = self.log_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _should_show_line(self, line: str) -> bool:
        """Check if log line should be displayed based on filters."""
        # Level filter
        level_filter = self.level_filter.currentText()
        if level_filter != "ALL":
            if level_filter not in line:
                return False

        # Search filter
        search_text = self.search_filter.text().strip()
        if search_text and search_text.lower() not in line.lower():
            return False

        return True

    def _colorize_log_line(self, line: str) -> str:
        """Add color coding to log line based on level."""
        line_html = line.replace('<', '&lt;').replace('>', '&gt;')

        if " ERROR " in line:
            return f'<span style="color: #ff4444;">{line_html}</span>'
        elif " WARNING " in line:
            return f'<span style="color: #ffaa00;">{line_html}</span>'
        elif " INFO " in line:
            return f'<span style="color: #00aa00;">{line_html}</span>'
        elif " DEBUG " in line:
            return f'<span style="color: #888888;">{line_html}</span>'
        elif " CRITICAL " in line:
            return f'<span style="color: #ff0000; font-weight: bold;">{line_html}</span>'
        else:
            return line_html

    def _enforce_line_limit(self):
        """Ensure log display doesn't exceed maximum lines."""
        document = self.log_display.document()
        if document.blockCount() > self.max_lines:
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor,
                                document.blockCount() - self.max_lines)
            cursor.removeSelectedText()

    def _apply_filters(self):
        """Reapply filters to existing log content."""
        self._refresh_logs()

    def _on_max_lines_changed(self, value: int):
        """Handle max lines change."""
        self.max_lines = value
        self._enforce_line_limit()

    def _on_auto_scroll_toggled(self, enabled: bool):
        """Handle auto-scroll toggle."""
        self.auto_scroll = enabled

    def _clear_logs(self):
        """Clear the log display."""
        self.log_display.clear()
        self.status_label.setText("Logs cleared")

    def _refresh_logs(self):
        """Refresh log display."""
        self.log_display.clear()
        self._load_initial_logs()

    def _save_logs(self):
        """Save current log content to file."""
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Logs",
            f"tennis_scraper_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*.*)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_display.toPlainText())
                self.status_label.setText(f"Logs saved to {filename}")
            except Exception as e:
                self.status_label.setText(f"Failed to save logs: {e}")

    def closeEvent(self, event):
        """Handle widget close."""
        if self.monitor_worker and self.monitor_worker.isRunning():
            self.monitor_worker.stop()
            self.monitor_worker.wait(3000)
        event.accept()