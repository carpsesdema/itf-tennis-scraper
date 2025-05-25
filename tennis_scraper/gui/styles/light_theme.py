"""
Light theme implementation.
"""

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

from .themes import Theme


class LightTheme(Theme):
    """Professional light theme."""

    def get_name(self) -> str:
        return "Light"

    def get_palette(self) -> QPalette:
        """Create light theme palette."""
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))

        # Base colors
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))

        # Text colors
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.BrightText, QColor(255, 255, 255))

        # Button colors
        palette.setColor(QPalette.Button, QColor(225, 225, 225))
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))

        # Selection colors
        palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        # Link colors
        palette.setColor(QPalette.Link, QColor(0, 120, 215))
        palette.setColor(QPalette.LinkVisited, QColor(120, 0, 215))

        return palette

    def get_stylesheet(self) -> str:
        """Get light theme stylesheet."""
        return """
        /* Main Application Style */
        QMainWindow {
            background-color: #f0f0f0;
            color: #000000;
        }

        /* Buttons */
        QPushButton {
            background-color: #e1e1e1;
            color: #000000;
            border: 1px solid #adadad;
            padding: 6px 12px;
            border-radius: 3px;
            min-width: 80px;
        }

        QPushButton:hover {
            background-color: #e6e6e6;
            border-color: #999999;
        }

        QPushButton:pressed {
            background-color: #d4d4d4;
        }

        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #888888;
            border-color: #cccccc;
        }

        /* Input Fields */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 4px;
            border-radius: 3px;
        }

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #0078d4;
        }

        /* Tables */
        QTableWidget {
            background-color: #ffffff;
            alternate-background-color: #f9f9f9;
            color: #000000;
            gridline-color: #dddddd;
            selection-background-color: #0078d4;
            selection-color: #ffffff;
            border: 1px solid #cccccc;
        }

        QHeaderView::section {
            background-color: #e1e1e1;
            color: #000000;
            padding: 6px;
            border: 1px solid #adadad;
            font-weight: bold;
        }

        /* Group Boxes */
        QGroupBox {
            color: #000000;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }

        /* Live Match Highlighting */
        .live-match {
            background-color: rgba(255, 0, 0, 0.1);
            border-left: 3px solid #ff4444;
        }
        """

    def get_colors(self) -> dict:
        """Get theme color dictionary."""
        return {
            'primary': '#0078d4',
            'success': '#107c10',
            'warning': '#ff8c00',
            'error': '#d13438',
            'background': '#f0f0f0',
            'surface': '#ffffff',
            'text': '#000000',
            'text_secondary': '#666666'
        }