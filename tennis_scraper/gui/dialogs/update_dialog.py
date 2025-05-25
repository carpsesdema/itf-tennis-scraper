from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPixmap

from ...updates.checker import UpdateInfo # Ensure UpdateInfo is imported
from ...utils.logging import get_logger
from ... import __version__ as APP_CURRENT_VERSION
from dataclasses import asdict


class UpdateDialog(QDialog):
    """Dialog for showing update information and handling downloads."""

    install_requested = Signal(str)

    def __init__(self, update_info_obj: UpdateInfo, parent=None): # EXPECT UpdateInfo OBJECT
        super().__init__(parent)
        self.update_info = update_info_obj # ASSIGN OBJECT DIRECTLY
        self.logger = get_logger(__name__)
        self.update_worker = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Update Available")
        self.setFixedSize(500, 420)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        icon_label = QLabel("🔄")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)

        # self.update_info is now an UpdateInfo object
        title_label = QLabel(f"Version {self.update_info.version} Available!")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        version_layout = QHBoxLayout()
        current_label = QLabel(f"Current: v{APP_CURRENT_VERSION}")
        new_label = QLabel(f"New: v{self.update_info.version}") # Access .version attribute
        new_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        version_layout.addWidget(current_label)
        version_layout.addStretch()
        version_layout.addWidget(new_label)
        layout.addLayout(version_layout)

        if self.update_info.critical:
            warning_label = QLabel("⚠️ This is a critical security update!")
            warning_label.setStyleSheet(
                "color: #FF5722; font-weight: bold; background: #FFF3E0; "
                "padding: 8px; border-radius: 4px; margin: 10px 0px;"
            )
            layout.addWidget(warning_label)

        changelog_label = QLabel("What's New:")
        changelog_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setPlainText(self.update_info.changelog or "No changelog details available.")
        self.changelog_text.setMaximumHeight(150)
        self.changelog_text.setReadOnly(True)
        layout.addWidget(self.changelog_text)

        if self.update_info.file_size > 0:
            size_mb = self.update_info.file_size / (1024 * 1024)
            size_label = QLabel(f"Download size: {size_mb:.1f} MB")
            size_label.setStyleSheet("color: #666; font-size: 12px;")
            layout.addWidget(size_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.auto_install_cb = QCheckBox("Automatically install after download")
        self.auto_install_cb.setChecked(True)
        layout.addWidget(self.auto_install_cb)

        button_layout = QHBoxLayout()
        self.skip_btn = QPushButton("Skip This Version")
        self.later_btn = QPushButton("Remind Me Later")
        self.download_btn = QPushButton("Download Update")
        self.download_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold;"
        )
        if self.update_info.critical:
            self.later_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.later_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.download_btn)
        layout.addLayout(button_layout)

    def _connect_signals(self):
        self.download_btn.clicked.connect(self._start_download)
        self.later_btn.clicked.connect(self.close)
        self.skip_btn.clicked.connect(self._skip_version)

    def _start_download(self):
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        main_window_config = getattr(self.parent(), 'config', None)
        update_cfg_dict = {}
        if main_window_config and hasattr(main_window_config, 'updates'):
             update_cfg_dict = asdict(main_window_config.updates)
        else:
            self.logger.warning("MainWindow config or updates attribute not found, using default for UpdateWorker.")
            update_cfg_dict = {"github_repo": "carpsesdema/itf-tennis-scraper"}

        from ...gui.workers.update_worker import UpdateWorker
        self.update_worker = UpdateWorker(update_cfg_dict)

        self.update_worker.download_progress.connect(self.progress_bar.setValue)
        self.update_worker.update_downloaded.connect(self._on_download_complete)
        self.update_worker.download_failed.connect(self._on_download_failed)

        self.update_worker.trigger_download(self.update_info) # Pass the UpdateInfo OBJECT

    def _on_download_complete(self, update_info_obj_with_path: UpdateInfo): # Expect UpdateInfo OBJECT
        self.progress_bar.setValue(100)
        self.download_btn.setText("Download Complete")
        file_path = update_info_obj_with_path.local_file_path

        if not file_path:
            self.logger.error("Download complete signal received, but no file path found in UpdateInfo object.")
            self._on_download_failed("Downloaded file path missing.")
            return

        self.logger.info(f"Update download complete: {file_path}")
        if self.auto_install_cb.isChecked():
            reply = QMessageBox.question(
                self, "Install Update",
                "Download completed successfully!\n\n"
                f"File saved to: {file_path}\n\n"
                "Would you like to install the update now?\n"
                "The application will close and the installer will run.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info(f"Emitting install_requested for: {file_path}")
                self.install_requested.emit(file_path)
                self.accept()
                return
        else:
            QMessageBox.information(
                self, "Download Complete",
                f"Update downloaded successfully!\n\n"
                f"File saved to: {file_path}\n\n"
                f"You can install it later by running the downloaded file."
            )
        self.accept()

    def _on_download_failed(self, error: str):
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Download Update")
        QMessageBox.critical(
            self, "Download Failed",
            f"Failed to download update:\n\n{error}\n\n"
            f"Please try again later or download manually."
        )
        self.logger.error(f"Download failed: {error}")

    def _skip_version(self):
        from PySide6.QtCore import QSettings
        settings = QSettings("TennisScraper", "ITFScraper")
        if self.update_info: # Check if update_info is not None
            settings.setValue("skipped_version", self.update_info.version)
            QMessageBox.information(
                self, "Version Skipped",
                f"Version {self.update_info.version} will be skipped.\n"
                f"You will not be notified about this version again unless it's critical."
            )
            self.logger.info(f"User skipped update version: {self.update_info.version}")
        self.accept()

    def closeEvent(self, event):
        if self.update_worker and self.update_worker.isRunning():
            self.logger.debug("UpdateDialog closeEvent while worker might be running.")
        super().closeEvent(event)