"""
MatchesTable component for displaying tennis match data.
"""

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor

from typing import List, Optional
from datetime import datetime, timezone  # For consistent timezone handling

from ...core.models import TennisMatch, MatchStatus  # Adjusted import path
from ...utils.logging import get_logger


class MatchesTable(QTableWidget):
    """
    A QTableWidget specialized for displaying TennisMatch data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._matches_data: List[TennisMatch] = []
        self._setup_ui()

    def _setup_ui(self):
        """Initialize table properties and headers."""
        self.setColumnCount(8)  # Status, Home, Away, Score, Tournament, Round, Source, Last Updated
        self.setHorizontalHeaderLabels([
            "Status", "Home Player", "Away Player", "Score",
            "Tournament", "Round", "Source", "Last Updated"
        ])

        # Table behaviors
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)  # Hide default row numbers

        # Column sizing
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Home Player
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Away Player
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Score
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Tournament
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Round
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Source
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Last Updated

        # Further styling can be applied via the theme system
        # self.setStyleSheet("QTableWidget { gridline-color: #404040; }") # Example

    def update_matches(self, matches: List[TennisMatch]):
        """
        Clears and repopulates the table with new match data.
        """
        self.setSortingEnabled(False)  # Disable sorting during update for performance
        self.clearContents()
        self.setRowCount(len(matches))
        self._matches_data = sorted(matches, key=lambda m: (m.status != MatchStatus.LIVE,
                                                            m.scheduled_time or datetime.max.replace(
                                                                tzinfo=timezone.utc)))  # Show live first, then by time

        for row_idx, match in enumerate(self._matches_data):
            self._populate_row(row_idx, match)

        self.setSortingEnabled(True)
        self.logger.info(f"Matches table updated with {len(matches)} matches.")

    def _populate_row(self, row_idx: int, match: TennisMatch):
        """Populates a single row in the table with match data."""

        status_item = QTableWidgetItem(match.status.display_name)
        home_player_item = QTableWidgetItem(match.home_player.display_name)
        away_player_item = QTableWidgetItem(match.away_player.display_name)
        score_item = QTableWidgetItem(match.display_score)
        tournament_item = QTableWidgetItem(match.tournament)
        round_item = QTableWidgetItem(match.round_info)
        source_item = QTableWidgetItem(match.source)

        # Format last_updated timestamp (assuming it's UTC)
        last_updated_str = match.last_updated.astimezone().strftime('%H:%M:%S %Z') if match.last_updated else "N/A"
        last_updated_item = QTableWidgetItem(last_updated_str)

        # Set items in table
        self.setItem(row_idx, 0, status_item)
        self.setItem(row_idx, 1, home_player_item)
        self.setItem(row_idx, 2, away_player_item)
        self.setItem(row_idx, 3, score_item)
        self.setItem(row_idx, 4, tournament_item)
        self.setItem(row_idx, 5, round_item)
        self.setItem(row_idx, 6, source_item)
        self.setItem(row_idx, 7, last_updated_item)

        # Apply styling for live matches
        if match.status == MatchStatus.LIVE:
            live_color = QColor(Qt.GlobalColor.red).lighter(180)  # A light red/pinkish
            for col_idx in range(self.columnCount()):
                item = self.item(row_idx, col_idx)
                if item:
                    item.setBackground(live_color)
                    # item.setForeground(QColor(Qt.GlobalColor.white)) # If needed for contrast
        elif match.status == MatchStatus.FINISHED:
            finished_color = QColor(Qt.GlobalColor.gray).lighter(130)
            for col_idx in range(self.columnCount()):
                item = self.item(row_idx, col_idx)
                if item:
                    item.setBackground(finished_color)

    def get_selected_match(self) -> Optional[TennisMatch]:
        """Returns the TennisMatch object for the currently selected row."""
        current_row = self.currentRow()
        if 0 <= current_row < len(self._matches_data):
            return self._matches_data[current_row]
        return None

    def get_matches(self) -> List[TennisMatch]:
        """Returns all matches currently displayed in the table."""
        return self._matches_data

    def get_match_count(self) -> int:
        """Returns the number of matches currently displayed."""
        return len(self._matches_data)

    def save_settings(self, settings: QSettings):
        """Save table settings (e.g., column widths, sort order)."""
        settings.setValue("matchesTable/columnStates", self.horizontalHeader().saveState())
        self.logger.debug("MatchesTable settings saved.")

    def load_settings(self, settings: QSettings):
        """Load table settings."""
        column_states = settings.value("matchesTable/columnStates")
        if column_states:
            self.horizontalHeader().restoreState(column_states)
            self.logger.debug("MatchesTable settings loaded.")
        else:
            # Apply default resize mode if no saved state
            self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)