from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPixmap

from ...updates.checker import UpdateInfo
from ...utils.logging import get_logger


class UpdateDialog(QDialog):
    """Dialog for showing update information and handling downloads."""

    download_requested = Signal(dict)
    install_requested = Signal(str)

    def __init__(self, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.logger = get_logger(__name__)
        self.download_thread = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Update Available")
        self.setFixedSize(500, 400)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        # Update icon (you could add an actual icon here)
        icon_label = QLabel("🔄")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)

        title_label = QLabel(f"Version {self.update_info.version} Available!")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Version comparison
        version_layout = QHBoxLayout()
        current_label = QLabel("Current: v2.0.0")  # Should come from config
        new_label = QLabel(f"New: v{self.update_info.version}")
        new_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

        version_layout.addWidget(current_label)
        version_layout.addStretch()
        version_layout.addWidget(new_label)
        layout.addLayout(version_layout)

        # Critical update warning
        if self.update_info.critical:
            warning_label = QLabel("⚠️ This is a critical security update!")
            warning_label.setStyleSheet(
                "color: #FF5722; font-weight: bold; background: #FFF3E0; "
                "padding: 8px; border-radius: 4px; margin: 10px 0px;"
            )
            layout.addWidget(warning_label)

        # Changelog
        changelog_label = QLabel("What's New:")
        changelog_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setPlainText(self.update_info.changelog)
        self.changelog_text.setMaximumHeight(150)
        self.changelog_text.setReadOnly(True)
        layout.addWidget(self.changelog_text)

        # File size info
        if self.update_info.file_size > 0:
            size_mb = self.update_info.file_size / (1024 * 1024)
            size_label = QLabel(f"Download size: {size_mb:.1f} MB")
            size_label.setStyleSheet("color: #666; font-size: 12px;")
            layout.addWidget(size_label)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Options
        self.auto_install_cb = QCheckBox("Automatically install after download")
        self.auto_install_cb.setChecked(True)
        layout.addWidget(self.auto_install_cb)

        # Buttons
        button_layout = QHBoxLayout()

        self.skip_btn = QPushButton("Skip This Version")
        self.later_btn = QPushButton("Remind Me Later")
        self.download_btn = QPushButton("Download & Install")

        self.download_btn.setStyleSheet("""
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

        # Disable options for critical updates
        if self.update_info.critical:
            self.later_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
            self.later_btn.setToolTip("Critical updates cannot be postponed")
            self.skip_btn.setToolTip("Critical updates cannot be skipped")

        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.later_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.download_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect signals and slots."""
        self.download_btn.clicked.connect(self._start_download)
        self.later_btn.clicked.connect(self.close)
        self.skip_btn.clicked.connect(self._skip_version)

    def _start_download(self):
        """Start downloading the update."""
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.progress_bar.setVisible(True)

        # Start download in thread
        from ...gui.workers.update_worker import UpdateWorker
        self.download_thread = UpdateWorker({"github_repo": "carpsesdema/itf-tennis-scraper"})
        self.download_thread.download_progress.connect(self.progress_bar.setValue)
        self.download_thread.update_available.connect(self._on_download_complete)
        self.download_thread.check_failed.connect(self._on_download_failed)

        # Start download
        self.download_thread.download_update(self.update_info.__dict__)

    def _on_download_complete(self, update_info: dict):
        """Handle successful download."""
        self.progress_bar.setValue(100)
        file_path = update_info.get('local_file', '')

        if self.auto_install_cb.isChecked():
            reply = QMessageBox.question(
                self, "Install Update",
                "Download completed successfully!\n\n"
                "Would you like to install the update now?\n"
                "The application will close and the installer will run.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.install_requested.emit(file_path)
                self.close()
                return

        QMessageBox.information(
            self, "Download Complete",
            f"Update downloaded successfully!\n\n"
            f"File saved to: {file_path}\n\n"
            f"You can install it later by running the downloaded file."
        )
        self.close()

    def _on_download_failed(self, error: str):
        """Handle download failure."""
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Download & Install")

        QMessageBox.critical(
            self, "Download Failed",
            f"Failed to download update:\n\n{error}\n\n"
            f"Please try again later or download manually from the website."
        )

    def _skip_version(self):
        """Skip this version."""
        from PySide6.QtCore import QSettings
        settings = QSettings("TennisScraper", "ITFScraper")
        settings.setValue("skipped_version", self.update_info.version)

        QMessageBox.information(
            self, "Version Skipped",
            f"Version {self.update_info.version} will be skipped.\n\n"
            f"You will not be notified about this version again."
        )
        self.close()