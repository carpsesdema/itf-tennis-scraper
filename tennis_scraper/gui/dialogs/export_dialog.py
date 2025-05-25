from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QLineEdit, QFileDialog,
    QGroupBox, QTextEdit, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread
from typing import List
from pathlib import Path
import asyncio  # For the worker

from ...core.models import TennisMatch
from ...utils.export import ExportManager
from ...utils.logging import get_logger


class ExportWorker(QThread):
    """Worker thread for exporting data."""
    progress_updated = Signal(int)  # Percentage 0-100
    export_completed = Signal(str)  # Filepath
    export_failed = Signal(str)  # Error message

    def __init__(self, matches: List[TennisMatch], output_path: str,
                 format_name: str, options: dict, parent=None):
        super().__init__(parent)
        self.matches = matches
        self.output_path = output_path
        self.format_name = format_name
        self.options = options
        self.export_manager = ExportManager()
        self.logger = get_logger(__name__)  # Add logger to worker

    def run(self):
        """Run export in background."""
        loop = None
        try:
            self.logger.info(f"ExportWorker started for {self.output_path} (format: {self.format_name})")
            self.progress_updated.emit(0)

            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Simulate some progress steps if actual progress is hard to get
            self.progress_updated.emit(10)

            # Perform the async export operation
            success = loop.run_until_complete(
                self.export_manager.export_matches(
                    self.matches, self.output_path, self.format_name, **self.options
                )
            )

            self.progress_updated.emit(90)  # Mark near completion

            if success:
                self.progress_updated.emit(100)
                self.export_completed.emit(self.output_path)
                self.logger.info(f"ExportWorker successfully exported to {self.output_path}")
            else:
                self.export_failed.emit(f"Export operation failed for {self.output_path}")
                self.logger.error(f"ExportWorker: ExportManager reported failure for {self.output_path}")

        except Exception as e:
            self.logger.error(f"ExportWorker error during export to {self.output_path}: {e}", exc_info=True)
            self.export_failed.emit(str(e))
        finally:
            if loop:
                loop.close()
            self.logger.info(f"ExportWorker finished for {self.output_path}")


class ExportDialog(QDialog):
    """Dialog for configuring and exporting match data."""

    def __init__(self, matches: List[TennisMatch], parent=None):
        super().__init__(parent)
        self.matches = matches
        self.logger = get_logger(__name__)
        self.export_manager = ExportManager()  # For getting formats
        self.export_worker = None

        self._init_ui()
        self._connect_signals()
        self._update_preview()  # Initial preview

    def _init_ui(self):
        self.setWindowTitle("Export Tennis Matches")
        self.setMinimumWidth(550)  # Adjusted size
        self.setModal(True)  # Ensure it's modal

        layout = QVBoxLayout(self)

        settings_group = QGroupBox("Export Settings")
        settings_layout = QFormLayout(settings_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(self.export_manager.get_supported_formats())  # Populate from manager
        settings_layout.addRow("Format:", self.format_combo)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Choose export location...")
        self.browse_btn = QPushButton("Browse...")
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addRow("Save to:", path_layout)

        self.include_metadata_cb = QCheckBox("Include all match metadata")
        self.include_metadata_cb.setChecked(True)
        settings_layout.addRow(self.include_metadata_cb)

        self.timestamp_format_edit = QLineEdit()
        self.timestamp_format_edit.setText("%Y-%m-%d %H:%M:%S %Z")  # Include timezone
        self.timestamp_format_edit.setToolTip("Python strftime format for timestamps")
        settings_layout.addRow("Timestamp format:", self.timestamp_format_edit)
        layout.addWidget(settings_group)

        preview_group = QGroupBox("Preview (first 3 matches)")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(100)  # Reduced height
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet("font-family: 'Courier New', monospace; font-size: 9pt;")
        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel(f"Ready to export {len(self.matches)} matches.")
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.export_btn = QPushButton("Export Matches")
        self.export_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.export_btn)
        layout.addLayout(button_layout)

        self._on_format_changed()  # Set initial path based on default format

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._browse_file)
        self.export_btn.clicked.connect(self._start_export)
        self.cancel_btn.clicked.connect(self.reject)  # Use reject for cancel
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        # Update preview on option changes
        self.include_metadata_cb.toggled.connect(self._update_preview)
        self.timestamp_format_edit.textChanged.connect(self._update_preview)

    def _get_default_filename(self) -> str:
        """Generates a default filename based on current format and timestamp."""
        format_name = self.format_combo.currentText().lower()
        exporter = self.export_manager.get_exporter(format_name)
        extension = exporter.get_default_extension() if exporter else f".{format_name}"

        from datetime import datetime  # Local import
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"tennis_matches_{timestamp_str}{extension}"

    def _browse_file(self):
        format_name = self.format_combo.currentText().lower()
        exporter = self.export_manager.get_exporter(format_name)

        default_file = self.path_edit.text() or str(Path.home() / "Downloads" / self._get_default_filename())

        if exporter:
            extension = exporter.get_default_extension().lstrip('.')
            file_filter = f"{format_name.upper()} Files (*.{extension});;All Files (*)"
        else:
            file_filter = "All Files (*)"

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Exported Matches", default_file, file_filter
        )
        if filename:
            self.path_edit.setText(filename)

    def _on_format_changed(self):
        """Update file extension in path_edit when format changes."""
        current_path_str = self.path_edit.text()
        format_name = self.format_combo.currentText().lower()
        exporter = self.export_manager.get_exporter(format_name)

        if not exporter: return

        new_extension = exporter.get_default_extension()

        if current_path_str:
            p = Path(current_path_str)
            # If path is a directory, append default filename, else change suffix
            if p.is_dir() or not p.suffix:
                base_name = self._get_default_filename().rsplit('.', 1)[0]  # name without extension
                new_path = p / f"{base_name}{new_extension}"
            else:
                new_path = p.with_suffix(new_extension)
            self.path_edit.setText(str(new_path))
        else:
            # Set a default path if empty
            default_dir = Path.home() / "Downloads"
            self.path_edit.setText(str(default_dir / self._get_default_filename()))

        self._update_preview()

    def _update_preview(self):
        if not self.matches:
            self.preview_text.setPlainText("No matches to preview.")
            return

        format_name = self.format_combo.currentText().lower()
        # Preview first 3 matches
        preview_matches = self.matches[:3]

        # For simplicity, JSON preview will always be a list of match dicts
        # CSV preview will be a few lines
        preview_content = f"--- Preview for {format_name.upper()} format ---\n"
        if format_name == 'json':
            import json  # Local import
            preview_data = [m.to_dict() for m in preview_matches]
            preview_content += json.dumps(preview_data, indent=2, default=str)[:500]  # Limit length
        elif format_name == 'csv' or format_name == 'excel' or format_name == 'xlsx':
            # Simplified CSV-like preview
            headers = list(preview_matches[0].to_dict().keys()) if preview_matches else []
            # Select a few key headers for brevity
            display_headers = ['match_id', 'home_player_name', 'away_player_name', 'status', 'tournament']
            actual_headers = [h for h in display_headers if h in headers]
            preview_content += ",".join(actual_headers) + "\n"
            for match in preview_matches:
                match_dict = match.to_dict()
                row_values = [str(match_dict.get(h, '')) for h in actual_headers]
                preview_content += ",".join(row_values) + "\n"
        else:
            preview_content += "Preview not available for this format."

        self.preview_text.setPlainText(preview_content.strip())

    def _start_export(self):
        output_path_str = self.path_edit.text().strip()
        if not output_path_str:
            QMessageBox.warning(self, "Export Error", "Please select an output file path.")
            return

        output_path = Path(output_path_str)
        if output_path.is_dir():
            QMessageBox.warning(self, "Export Error", "Output path is a directory. Please specify a file name.")
            return
        if not output_path.parent.exists():
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to create directory {output_path.parent}: {e}")
                return

        format_name = self.format_combo.currentText().lower()
        options = {
            'include_metadata': self.include_metadata_cb.isChecked(),
            'timestamp_format': self.timestamp_format_edit.text()
        }

        self.export_btn.setEnabled(False)
        self.export_btn.setText("Exporting...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Exporting {len(self.matches)} matches as {format_name.upper()}...")

        self.export_worker = ExportWorker(self.matches, str(output_path), format_name, options)
        self.export_worker.progress_updated.connect(self.progress_bar.setValue)
        self.export_worker.export_completed.connect(self._on_export_complete)
        self.export_worker.export_failed.connect(self._on_export_failed)
        self.export_worker.start()

    def _on_export_complete(self, file_path: str):
        self.progress_bar.setValue(100)  # Ensure it hits 100
        self.status_label.setText("Export completed successfully!")
        QMessageBox.information(
            self, "Export Complete",
            f"Matches exported successfully!\n\nFile saved to:\n{file_path}"
        )
        self.accept()  # Close dialog on success

    def _on_export_failed(self, error: str):
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        self.export_btn.setText("Export Matches")
        self.status_label.setText(f"Export failed: {error[:100]}")  # Show part of error
        QMessageBox.critical(
            self, "Export Error", f"Failed to export matches:\n\n{error}"
        )

    def closeEvent(self, event):
        if self.export_worker and self.export_worker.isRunning():
            reply = QMessageBox.question(
                self, "Export in Progress",
                "Export is still in progress. Are you sure you want to cancel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.export_worker.terminate()  # Attempt to stop
                self.export_worker.wait(1000)  # Wait a bit
                self.logger.info("Export cancelled by user.")
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()