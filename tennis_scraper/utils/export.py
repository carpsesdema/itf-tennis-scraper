import csv
import json
# import pandas as pd # Import pandas if ExcelExporter is re-enabled and uses it
from pathlib import Path
from typing import List, Dict, Any, Optional, Optional
from datetime import datetime, timezone

from ..core.interfaces import DataExporter
from ..core.models import TennisMatch, Player, Score, MatchStatus, TournamentLevel, \
    Surface  # Ensure all models are imported
from .logging import get_logger


class CSVExporter(DataExporter):
    """Export matches to CSV format."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def export_matches(self, matches: List[TennisMatch], output_path: str, **kwargs) -> bool:
        """Export matches to CSV file."""
        try:
            include_metadata = kwargs.get('include_metadata', True)
            timestamp_format = kwargs.get('timestamp_format', '%Y-%m-%d %H:%M:%S %Z')

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                columns = [
                    'match_id', 'home_player_name', 'home_player_country', 'home_player_ranking',
                    'away_player_name', 'away_player_country', 'away_player_ranking',
                    'score_sets', 'score_current_game', 'status', 'tournament_name',
                    'tournament_level', 'surface', 'round_info', 'scheduled_time_utc',
                    'source', 'source_url', 'last_updated_utc'
                ]
                if include_metadata:
                    # Add any other specific metadata keys you expect from match.metadata
                    # For dynamic metadata, you might need a different approach.
                    pass  # Example: columns.extend(list(matches[0].metadata.keys())) if matches and matches[0].metadata else None

                writer = csv.DictWriter(csvfile, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()

                for match in matches:
                    scheduled_time_str = match.scheduled_time.strftime(timestamp_format) if match.scheduled_time else ""
                    last_updated_str = match.last_updated.strftime(timestamp_format) if match.last_updated else ""

                    row = {
                        'match_id': match.match_id,
                        'home_player_name': match.home_player.name,
                        'home_player_country': match.home_player.country_code,
                        'home_player_ranking': match.home_player.ranking,
                        'away_player_name': match.away_player.name,
                        'away_player_country': match.away_player.country_code,
                        'away_player_ranking': match.away_player.ranking,
                        'score_sets': " ".join([f"{s[0]}-{s[1]}" for s in match.score.sets]),
                        'score_current_game': f"{match.score.current_game[0]}-{match.score.current_game[1]}" if match.score.current_game else "",
                        'status': match.status.value,
                        'tournament_name': match.tournament,
                        'tournament_level': match.tournament_level.value,
                        'surface': match.surface.value,
                        'round_info': match.round_info,
                        'scheduled_time_utc': scheduled_time_str,
                        'source': match.source,
                        'source_url': match.source_url,
                        'last_updated_utc': last_updated_str,
                    }
                    if include_metadata:
                        row.update(match.metadata)  # Add all metadata fields

                    writer.writerow(row)

            self.logger.info(f"Exported {len(matches)} matches to CSV: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"CSV export failed for {output_path}: {e}", exc_info=True)
            return False

    def get_supported_formats(self) -> List[str]:
        return ["csv"]

    def get_default_extension(self) -> str:
        return ".csv"


class JSONExporter(DataExporter):
    """Export matches to JSON format."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def export_matches(self, matches: List[TennisMatch], output_path: str, **kwargs) -> bool:
        try:
            indent = kwargs.get('indent', 2)

            export_data = {
                'export_timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'total_matches': len(matches),
                'matches': [match.to_dict() for match in matches]  # Use the model's to_dict
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=indent, ensure_ascii=False)

            self.logger.info(f"Exported {len(matches)} matches to JSON: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"JSON export failed for {output_path}: {e}", exc_info=True)
            return False

    def get_supported_formats(self) -> List[str]:
        return ["json"]

    def get_default_extension(self) -> str:
        return ".json"


class ExcelExporter(DataExporter):
    """Export matches to Excel format."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.pd = None  # Lazy load pandas

    async def _lazy_load_pandas(self):
        if self.pd is None:
            try:
                import pandas
                self.pd = pandas
            except ImportError:
                self.logger.error(
                    "Pandas library is not installed. Excel export unavailable. Run: pip install pandas openpyxl")
                raise RuntimeError("Pandas not installed, required for Excel export.")

    async def export_matches(self, matches: List[TennisMatch], output_path: str, **kwargs) -> bool:
        await self._lazy_load_pandas()
        if not self.pd: return False

        try:
            # Convert matches to list of dicts for DataFrame
            data_for_df = [match.to_dict() for match in matches]

            # Flatten nested player and score dicts for easier Excel viewing
            flat_data = []
            for record in data_for_df:
                flat_record = {}
                for key, value in record.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flat_record[f"{key}_{sub_key}"] = sub_value
                    else:
                        flat_record[key] = value
                flat_data.append(flat_record)

            df = self.pd.DataFrame(flat_data)

            # Clean up some column names if necessary, e.g. score_sets list to string
            if 'score_sets' in df.columns:
                df['score_sets'] = df['score_sets'].apply(
                    lambda x: " ".join([f"{s[0]}-{s[1]}" for s in x]) if isinstance(x, list) else x)
            if 'score_current_game' in df.columns:
                df['score_current_game'] = df['score_current_game'].apply(
                    lambda x: f"{x[0]}-{x[1]}" if isinstance(x, list) and len(x) == 2 else x)

            with self.pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Tennis Matches', index=False)
                # Auto-adjust column widths (basic implementation)
                worksheet = writer.sheets['Tennis Matches']
                for column_cells in worksheet.columns:
                    length = max(len(str(cell.value)) for cell in column_cells)
                    worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)

            self.logger.info(f"Exported {len(matches)} matches to Excel: {output_path}")
            return True

        except RuntimeError as r_err:  # Catch pandas not installed
            self.logger.error(str(r_err))
            return False
        except Exception as e:
            self.logger.error(f"Excel export failed for {output_path}: {e}", exc_info=True)
            return False

    def get_supported_formats(self) -> List[str]:
        return ["xlsx", "excel"]  # Support both common names

    def get_default_extension(self) -> str:
        return ".xlsx"


class ExportManager:
    """Manage different export formats."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.exporters: Dict[str, DataExporter] = {
            'csv': CSVExporter(),
            'json': JSONExporter(),
            'xlsx': ExcelExporter(),
            'excel': ExcelExporter()  # Alias
        }

    def get_exporter(self, format_name: str) -> Optional[DataExporter]:
        format_lower = format_name.lower()
        exporter = self.exporters.get(format_lower)
        if not exporter:
            self.logger.warning(f"No exporter found for format: {format_name}")
        return exporter

    async def export_matches(self, matches: List[TennisMatch], output_path: str,
                             format_name: Optional[str] = None, **kwargs) -> bool:
        try:
            if format_name is None:
                format_name = Path(output_path).suffix.lstrip('.')

            exporter = self.get_exporter(format_name)
            if not exporter:
                raise ValueError(f"Unsupported export format: {format_name}")

            return await exporter.export_matches(matches, output_path, **kwargs)

        except Exception as e:
            self.logger.error(f"ExportManager: Export failed for {output_path} (format: {format_name}): {e}",
                              exc_info=True)
            return False

    def get_supported_formats(self) -> List[str]:
        formats = set()
        for exporter in self.exporters.values():
            # Ensure get_supported_formats doesn't require await if it's simple
            supported_by_exporter = exporter.get_supported_formats()
            formats.update(supported_by_exporter)
        return sorted(list(formats))