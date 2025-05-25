from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QLineEdit, QFileDialog,
    QGroupBox, QTextEdit, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread
from typing import List
from pathlib import Path

from ...core.models import TennisMatch
from ...utils.export import ExportManager
from ...utils.logging import get_logger


class ExportWorker(QThread):
    """Worker thread for exporting data."""

    progress_updated = Signal(int)
    export_completed = Signal(str)
    export_failed = Signal(str)

    def __init__(self, matches: List[TennisMatch], output_path: str,
                 format_name: str, options: dict):
        super().__init__()
        self.matches = matches
        self.output_path = output_path
        self.format_name = format_name
        self.options = options
        self.export_manager = ExportManager()

    def run(self):
        """Run export in background."""
        try:
            self.progress_updated.emit(0)

            # Simulate progress for user feedback
            import asyncio
            import time

            # Create event loop for async export
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.progress_updated.emit(25)
            time.sleep(0.1)

            success = loop.run_until_complete(
                self.export_manager.export_matches(
                    self.matches, self.output_path, self.format_name, **self.options
                )
            )

            self.progress_updated.emit(75)
            time.sleep(0.1)

            if success:
                self.progress_updated.emit(100)
                self.export_completed.emit(self.output_path)
            else:
                self.export_failed.emit("Export operation failed")

        except Exception as e:
            self.export_failed.emit(str(e))
        finally:
            if 'loop' in locals():
                loop.close()


class ExportDialog(QDialog):
    """Dialog for configuring and exporting match data."""

    def __init__(self, matches: List[TennisMatch], parent=None):
        super().__init__(parent)
        self.matches = matches
        self.logger = get_logger(__name__)
        self.export_worker = None

        self._init_ui()
        self._connect_signals()
        self._populate_preview()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Export Tennis Matches")
        self.setFixedSize(600, 500)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)

        # Export settings
        settings_group = QGroupBox("Export Settings")
        settings_layout = QFormLayout(settings_group)

        # Format selection
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "JSON", "Excel"])
        settings_layout.addRow("Format:", self.format_combo)

        # File path
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Choose export location...")
        self.browse_btn = QPushButton("Browse...")
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addRow("Save to:", path_layout)

        # Options
        self.include_metadata_cb = QCheckBox("Include metadata")
        self.include_metadata_cb.setChecked(True)
        settings_layout.addRow(self.include_metadata_cb)

        self.timestamp_format_edit = QLineEdit()
        self.timestamp_format_edit.setText("%Y-%m-%d %H:%M:%S")
        settings_layout.addRow("Timestamp format:", self.timestamp_format_edit)

        layout.addWidget(settings_group)

        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10px;")
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel(f"Ready to export {len(self.matches)} matches")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancel")
        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)

        # Set default export path
        default_filename = f"tennis_matches_{self._get_timestamp()}"
        default_path = Path.home() / "Downloads" / default_filename
        self.path_edit.setText(str(default_path))

    def _connect_signals(self):
        """Connect signals and slots."""
        self.browse_btn.clicked.connect(self._browse_file)
        self.export_btn.clicked.connect(self._start_export)
        self.cancel_btn.clicked.connect(self.close)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        self.format_combo.currentTextChanged.connect(self._update_preview)
        self.include_metadata_cb.toggled.connect(self._update_preview)

    def _browse_file(self):
        """Browse for export file location."""
        format_name = self.format_combo.currentText().lower()

        filters = {
            'csv': "CSV Files (*.csv)",
            'json': "JSON Files (*.json)",
            'excel': "Excel Files (*.xlsx)"
        }

        file_filter = filters.get(format_name, "All Files (*.*)")

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Tennis Matches",
            self.path_edit.text(),
            file_filter
        )

        if filename:
            self.path_edit.setText(filename)

    def _on_format_changed(self):
        """Handle format change."""
        format_name = self.format_combo.currentText().lower()
        current_path = Path(self.path_edit.text())

        # Update file extension
        extensions = {'csv': '.csv', 'json': '.json', 'excel': '.xlsx'}
        new_extension = extensions.get(format_name, '.txt')

        new_path = current_path.with_suffix(new_extension)
        self.path_edit.setText(str(new_path))

    def _populate_preview(self):
        """Populate the preview with sample data."""
        if not self.matches:
            self.preview_text.setPlainText("No matches to preview")
            return

        self._update_preview()

    def _update_preview(self):
        """Update preview based on current settings."""
        if not self.matches:
            return

        format_name = self.format_combo.currentText().lower()
        include_metadata = self.include_metadata_cb.isChecked()

        # Show preview of first few matches
        preview_matches = self.matches[:3]

        if format_name == 'csv':
            preview = self._generate_csv_preview(preview_matches, include_metadata)
        elif format_name == 'json':
            preview = self._generate_json_preview(preview_matches, include_metadata)
        else:  # excel
            preview = self._generate_csv_preview(preview_matches, include_metadata)
            preview = "Excel format preview:\n" + preview

        if len(self.matches) > 3:
            preview += f"\n... and {len(self.matches) - 3} more matches"

        self.preview_text.setPlainText(preview)

    def _generate_csv_preview(self, matches: List[TennisMatch], include_metadata: bool) -> str:
        """Generate CSV preview."""
        lines = []

        # Headers
        headers = ['Home Player', 'Away Player', 'Score', 'Status', 'Tournament', 'Round', 'Source', 'Updated']
        if include_metadata:
            headers.extend(['Tournament Level', 'Surface', 'URL'])

        lines.append(','.join(headers))

        # Data rows
        for match in matches:
            row = [
                match.home_player.name,
                match.away_player.name,
                match.display_score,
                match.status.display_name,
                match.tournament,
                match.round_info,
                match.source,
                match.last_updated.strftime('%Y-%m-%d %H:%M:%S')
            ]

            if include_metadata:
                row.extend([
                    match.tournament_level.value,
                    match.surface.value,
                    match.source_url
                ])

            lines.append(','.join(f'"{item}"' for item in row))

        return '\n'.join(lines)

    def _generate_json_preview(self, matches: List[TennisMatch], include_metadata: bool) -> str:
        """Generate JSON preview."""
        import json

        data = []
        for match in matches:
            match_data = {
                'home_player': match.home_player.name,
                'away_player': match.away_player.name,
                'score': match.display_score,
                'status': match.status.display_name,
                'tournament': match.tournament,
                'round': match.round_info,
                'source': match.source,
                'updated': match.last_updated.isoformat()
            }

            if include_metadata:
                match_data.update({
                    'tournament_level': match.tournament_level.value,
                    'surface': match.surface.value,
                    'url': match.source_url
                })

            data.append(match_data)

        return json.dumps(data, indent=2)

    def _start_export(self):
        """Start the export process."""
        output_path = self.path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Export Error", "Please select an output file")
            return

        format_name = self.format_combo.currentText().lower()

        # Prepare export options
        options = {
            'include_metadata': self.include_metadata_cb.isChecked(),
            'timestamp_format': self.timestamp_format_edit.text()
        }

        # Disable UI during export
        self.export_btn.setEnabled(False)
        self.export_btn.setText("Exporting...")
        self.progress_bar.setVisible(True)
        self.status_label.setText("Exporting matches...")

        # Start export worker
        self.export_worker = ExportWorker(self.matches, output_path, format_name, options)
        self.export_worker.progress_updated.connect(self.progress_bar.setValue)
        self.export_worker.export_completed.connect(self._on_export_complete)
        self.export_worker.export_failed.connect(self._on_export_failed)
        self.export_worker.start()

    def _on_export_complete(self, file_path: str):
        """Handle successful export."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Export completed successfully!")

        QMessageBox.information(
            self, "Export Complete",
            f"Matches exported successfully!\n\nFile saved to:\n{file_path}"
        )

        self.close()

    def _on_export_failed(self, error: str):
        """Handle export failure."""
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        self.export_btn.setText("Export")
        self.status_label.setText("Export failed")

        QMessageBox.critical(
            self, "Export Error",
            f"Failed to export matches:\n\n{error}"
        )

    def _get_timestamp(self) -> str:
        """Get timestamp string for filename."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.export_worker and self.export_worker.isRunning():
            reply = QMessageBox.question(
                self, "Export in Progress",
                "Export is still in progress. Do you want to cancel it?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.export_worker.terminate()
                self.export_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()