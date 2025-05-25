import csv
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..core.interfaces import DataExporter
from ..core.models import TennisMatch
from .logging import get_logger


class CSVExporter(DataExporter):
    """Export matches to CSV format."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def export_matches(self, matches: List[TennisMatch], output_path: str, **kwargs) -> bool:
        """Export matches to CSV file."""
        try:
            include_metadata = kwargs.get('include_metadata', True)
            timestamp_format = kwargs.get('timestamp_format', '%Y-%m-%d %H:%M:%S')

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                # Define columns
                columns = [
                    'home_player', 'away_player', 'score', 'status', 'tournament',
                    'round', 'source', 'last_updated'
                ]

                if include_metadata:
                    columns.extend(['tournament_level', 'surface', 'source_url'])

                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()

                for match in matches:
                    row = {
                        'home_player': match.home_player.name,
                        'away_player': match.away_player.name,
                        'score': match.display_score,
                        'status': match.status.display_name,
                        'tournament': match.tournament,
                        'round': match.round_info,
                        'source': match.source,
                        'last_updated': match.last_updated.strftime(timestamp_format)
                    }

                    if include_metadata:
                        row.update({
                            'tournament_level': match.tournament_level.value,
                            'surface': match.surface.value,
                            'source_url': match.source_url
                        })

                    writer.writerow(row)

            self.logger.info(f"Exported {len(matches)} matches to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            return False

    def get_supported_formats(self) -> List[str]:
        """Return supported formats."""
        return ["csv"]

    def get_default_extension(self) -> str:
        """Return default file extension."""
        return ".csv"


class JSONExporter(DataExporter):
    """Export matches to JSON format."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def export_matches(self, matches: List[TennisMatch], output_path: str, **kwargs) -> bool:
        """Export matches to JSON file."""
        try:
            include_metadata = kwargs.get('include_metadata', True)
            indent = kwargs.get('indent', 2)

            match_data = []
            for match in matches:
                match_dict = match.to_dict()

                if not include_metadata:
                    # Remove metadata fields
                    match_dict.pop('metadata', None)
                    match_dict.pop('source_url', None)

                match_data.append(match_dict)

            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_matches': len(matches),
                'matches': match_data
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=indent, ensure_ascii=False)

            self.logger.info(f"Exported {len(matches)} matches to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"JSON export failed: {e}")
            return False

    def get_supported_formats(self) -> List[str]:
        """Return supported formats."""
        return ["json"]

    def get_default_extension(self) -> str:
        """Return default file extension."""
        return ".json"


class ExcelExporter(DataExporter):
    """Export matches to Excel format."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def export_matches(self, matches: List[TennisMatch], output_path: str, **kwargs) -> bool:
        """Export matches to Excel file."""
        try:
            include_metadata = kwargs.get('include_metadata', True)
            timestamp_format = kwargs.get('timestamp_format', '%Y-%m-%d %H:%M:%S')

            # Convert matches to DataFrame
            data = []
            for match in matches:
                row = {
                    'Home Player': match.home_player.name,
                    'Away Player': match.away_player.name,
                    'Score': match.display_score,
                    'Status': match.status.display_name,
                    'Tournament': match.tournament,
                    'Round': match.round_info,
                    'Source': match.source,
                    'Last Updated': match.last_updated.strftime(timestamp_format)
                }

                if include_metadata:
                    row.update({
                        'Tournament Level': match.tournament_level.value,
                        'Surface': match.surface.value,
                        'Source URL': match.source_url,
                        'Home Country': match.home_player.country,
                        'Away Country': match.away_player.country,
                        'Home Ranking': match.home_player.ranking,
                        'Away Ranking': match.away_player.ranking
                    })

                data.append(row)

            df = pd.DataFrame(data)

            # Write to Excel with formatting
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Tennis Matches', index=False)

                # Get workbook and worksheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['Tennis Matches']

                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass

                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            self.logger.info(f"Exported {len(matches)} matches to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Excel export failed: {e}")
            return False

    def get_supported_formats(self) -> List[str]:
        """Return supported formats."""
        return ["xlsx", "xls"]

    def get_default_extension(self) -> str:
        """Return default file extension."""
        return ".xlsx"


class ExportManager:
    """Manage different export formats."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.exporters = {
            'csv': CSVExporter(),
            'json': JSONExporter(),
            'xlsx': ExcelExporter(),
            'excel': ExcelExporter()
        }

    def get_exporter(self, format_name: str) -> DataExporter:
        """Get exporter for format."""
        format_lower = format_name.lower()
        if format_lower not in self.exporters:
            raise ValueError(f"Unsupported export format: {format_name}")
        return self.exporters[format_lower]

    async def export_matches(self, matches: List[TennisMatch], output_path: str,
                             format_name: str = None, **kwargs) -> bool:
        """Export matches using appropriate exporter."""
        try:
            # Determine format from file extension if not specified
            if format_name is None:
                format_name = Path(output_path).suffix.lstrip('.')

            exporter = self.get_exporter(format_name)
            return await exporter.export_matches(matches, output_path, **kwargs)

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return False

    def get_supported_formats(self) -> List[str]:
        """Get all supported export formats."""
        formats = set()
        for exporter in self.exporters.values():
            formats.update(exporter.get_supported_formats())
        return sorted(list(formats))