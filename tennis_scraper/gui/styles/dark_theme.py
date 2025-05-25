"""
Dark theme implementation.
"""

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

from .themes import Theme


class DarkTheme(Theme):
    """Professional dark theme."""

    def get_name(self) -> str:
        return "Dark"

    def get_palette(self) -> QPalette:
        """Create dark theme palette."""
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))

        # Base colors (for input fields, etc.)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))

        # Text colors
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))

        # Button colors
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

        # Selection colors
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))

        # Link colors
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.LinkVisited, QColor(165, 42, 218))

        # Tooltip colors
        palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))

        return palette

    def get_stylesheet(self) -> str:
        """Get dark theme stylesheet."""
        return """
        /* Main Application Style */
        QMainWindow {
            background-color: #353535;
            color: #ffffff;
        }

        /* Menu Bar */
        QMenuBar {
            background-color: #2b2b2b;
            color: #ffffff;
            border-bottom: 1px solid #404040;
        }

        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
        }

        QMenuBar::item:selected {
            background-color: #404040;
        }

        QMenu {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #404040;
        }

        QMenu::item {
            padding: 6px 25px;
        }

        QMenu::item:selected {
            background-color: #404040;
        }

        /* Status Bar */
        QStatusBar {
            background-color: #2b2b2b;
            color: #ffffff;
            border-top: 1px solid #404040;
        }

        /* Buttons */
        QPushButton {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 6px 12px;
            border-radius: 3px;
            min-width: 80px;
        }

        QPushButton:hover {
            background-color: #4a4a4a;
            border-color: #666666;
        }

        QPushButton:pressed {
            background-color: #2a2a2a;
        }

        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #666666;
            border-color: #333333;
        }

        /* Input Fields */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #191919;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 4px;
            border-radius: 3px;
        }

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #2a82da;
        }

        /* Combo Boxes */
        QComboBox {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px 8px;
            border-radius: 3px;
        }

        QComboBox:hover {
            border-color: #666666;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #555555;
        }

        QComboBox::down-arrow {
            image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAGCAYAAAD68A/GAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAABYSURBVBiVpY4xDgAgCAPh/3+aGzU6mHQwJqGlBQoAXnvOOXLOiYhExBhjjKGqaq211lprrbXWWmuttdZaa6211lprrbXWWmuttdZaa6211lprrbXWWmuttdZaa6211h8vKwYGE1p8PAAAAABJRU5ErkJggg==);
        }

        QComboBox QAbstractItemView {
            background-color: #2b2b2b;
            color: #ffffff;
            selection-background-color: #404040;
            border: 1px solid #404040;
        }

        /* Spin Boxes */
        QSpinBox {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px;
            border-radius: 3px;
        }

        QSpinBox:hover {
            border-color: #666666;
        }

        /* Check Boxes */
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }

        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }

        QCheckBox::indicator:unchecked {
            background-color: #404040;
            border: 1px solid #555555;
            border-radius: 2px;
        }

        QCheckBox::indicator:checked {
            background-color: #2a82da;
            border: 1px solid #2a82da;
            border-radius: 2px;
        }

        /* Group Boxes */
        QGroupBox {
            color: #ffffff;
            border: 1px solid #404040;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }

        /* Tables */
        QTableWidget {
            background-color: #191919;
            alternate-background-color: #2a2a2a;
            color: #ffffff;
            gridline-color: #404040;
            selection-background-color: #2a82da;
            border: 1px solid #404040;
        }

        QTableWidget::item {
            padding: 4px;
        }

        QTableWidget::item:selected {
            background-color: #2a82da;
        }

        QHeaderView::section {
            background-color: #404040;
            color: #ffffff;
            padding: 6px;
            border: 1px solid #555555;
            font-weight: bold;
        }

        QHeaderView::section:hover {
            background-color: #4a4a4a;
        }

        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #404040;
            background-color: #353535;
        }

        QTabBar::tab {
            background-color: #2b2b2b;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }

        QTabBar::tab:selected {
            background-color: #353535;
            border-bottom: 2px solid #2a82da;
        }

        QTabBar::tab:hover:!selected {
            background-color: #404040;
        }

        /* Scroll Bars */
        QScrollBar:vertical {
            background-color: #2b2b2b;
            width: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background-color: #404040;
            min-height: 20px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #4a4a4a;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        QScrollBar:horizontal {
            background-color: #2b2b2b;
            height: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:horizontal {
            background-color: #404040;
            min-width: 20px;
            border-radius: 6px;
        }

        QScrollBar::handle:horizontal:hover {
            background-color: #4a4a4a;
        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        /* Progress Bar */
        QProgressBar {
            background-color: #2b2b2b;
            border: 1px solid #404040;
            border-radius: 3px;
            text-align: center;
            color: #ffffff;
        }

        QProgressBar::chunk {
            background-color: #2a82da;
            border-radius: 2px;
        }

        /* Splitter */
        QSplitter::handle {
            background-color: #404040;
        }

        QSplitter::handle:hover {
            background-color: #4a4a4a;
        }

        /* Tool Tips */
        QToolTip {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 4px;
            border-radius: 3px;
        }

        /* Live Match Highlighting */
        .live-match {
            background-color: rgba(255, 0, 0, 0.1);
            border-left: 3px solid #ff4444;
        }

        /* Important Matches */
        .important-match {
            background-color: rgba(255, 215, 0, 0.1);
            border-left: 3px solid #ffd700;
        }
        """

    def get_colors(self) -> dict:
        """Get theme color dictionary."""
        return {
            'primary': '#2a82da',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336',
            'background': '#353535',
            'surface': '#404040',
            'text': '#ffffff',
            'text_secondary': '#b0b0b0'
        }