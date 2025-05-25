from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

from ... import get_info


class AboutDialog(QDialog):
    """About dialog showing application information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_info = get_info()
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("About ITF Tennis Scraper")
        self.setFixedSize(500, 400)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)

        # Header with icon and title
        header_layout = QHBoxLayout()

        # App icon (you could add an actual icon here)
        icon_label = QLabel("🎾")
        icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)

        # Title and version
        title_layout = QVBoxLayout()
        title_label = QLabel(self.app_info["name"])
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        version_label = QLabel(f"Version {self.app_info['version']}")
        version_label.setStyleSheet("font-size: 14px; color: #666;")

        title_layout.addWidget(title_label)
        title_layout.addWidget(version_label)
        title_layout.addStretch()

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(self.app_info["description"])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin: 10px 0px;")
        layout.addWidget(desc_label)

        # Tabs for different information
        tab_widget = QTabWidget()

        # About tab
        about_tab = self._create_about_tab()
        tab_widget.addTab(about_tab, "About")

        # Credits tab
        credits_tab = self._create_credits_tab()
        tab_widget.addTab(credits_tab, "Credits")

        # License tab
        license_tab = self._create_license_tab()
        tab_widget.addTab(license_tab, "License")

        layout.addWidget(tab_widget)

        # Close button
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def _create_about_tab(self) -> QWidget:
        """Create the about tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        about_text = f"""
<h3>Professional ITF Tennis Match Scraper</h3>

<p><strong>Version:</strong> {self.app_info['version']}</p>
<p><strong>Author:</strong> {self.app_info['author']}</p>
<p><strong>Contact:</strong> {self.app_info['email']}</p>

<h4>Features:</h4>
<ul>
<li>Real-time tennis match scraping from multiple sources</li>
<li>Advanced filtering and search capabilities</li>
<li>Professional GUI with dark theme support</li>
<li>Export to CSV, JSON, and Excel formats</li>
<li>Automatic updates and error recovery</li>
<li>Comprehensive logging and monitoring</li>
</ul>

<h4>Data Sources:</h4>
<ul>
<li>Flashscore - Live scores and comprehensive coverage</li>
<li>SofaScore - Detailed statistics and match data</li>
<li>ITF Official - Official tournament information</li>
</ul>

<h4>System Information:</h4>
<p><strong>Platform:</strong> Cross-platform (Windows, macOS, Linux)</p>
<p><strong>GUI Framework:</strong> PySide6/Qt</p>
<p><strong>Python Version:</strong> 3.8+</p>
        """

        about_label = QLabel(about_text)
        about_label.setWordWrap(True)
        about_label.setTextFormat(Qt.RichText)
        about_label.setOpenExternalLinks(True)
        layout.addWidget(about_label)
        layout.addStretch()

        return widget

    def _create_credits_tab(self) -> QWidget:
        """Create the credits tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        credits_text = """
<h3>Credits and Acknowledgments</h3>

<h4>Development Team:</h4>
<ul>
<li><strong>Lead Developer:</strong> Tennis Scraper Team</li>
<li><strong>UI/UX Design:</strong> Modern Qt Interface</li>
<li><strong>Testing:</strong> Community Contributors</li>
</ul>

<h4>Third-Party Libraries:</h4>
<ul>
<li><strong>PySide6:</strong> Cross-platform GUI framework</li>
<li><strong>Selenium:</strong> Web browser automation</li>
<li><strong>BeautifulSoup:</strong> HTML parsing and extraction</li>
<li><strong>aiohttp:</strong> Asynchronous HTTP client</li>
<li><strong>pandas:</strong> Data analysis and manipulation</li>
<li><strong>requests:</strong> HTTP library for Python</li>
</ul>

<h4>Special Thanks:</h4>
<ul>
<li>Qt Project for the excellent GUI framework</li>
<li>Python Software Foundation</li>
<li>All open-source contributors</li>
<li>Tennis data providers</li>
<li>Community testers and feedback providers</li>
</ul>

<h4>Icon Credits:</h4>
<p>Tennis ball emoji and icons from system emoji sets</p>
        """

        credits_label = QLabel(credits_text)
        credits_label.setWordWrap(True)
        credits_label.setTextFormat(Qt.RichText)
        layout.addWidget(credits_label)
        layout.addStretch()

        return widget

    def _create_license_tab(self) -> QWidget:
        """Create the license tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        license_text = """
MIT License

Copyright (c) 2025 Tennis Scraper Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

IMPORTANT LEGAL NOTICE:

This software is designed for educational and personal use. Users are 
responsible for ensuring compliance with:

1. Website Terms of Service
2. Data scraping best practices
3. Local laws and regulations
4. Respectful use of web resources

The developers are not responsible for misuse of this software or any 
legal consequences arising from its use.
        """

        license_text_edit = QTextEdit()
        license_text_edit.setPlainText(license_text)
        license_text_edit.setReadOnly(True)
        license_text_edit.setFont(QFont("Courier New", 9))
        layout.addWidget(license_text_edit)

        return widget