"""
Update checking functionality.
"""

import asyncio
import aiohttp
from dataclasses import dataclass, asdict  # Added asdict
from typing import Optional, Dict, Any
from datetime import datetime

from ..core.interfaces import UpdateChecker as CoreUpdateCheckerInterface  # Aliased to avoid name clash
from ..utils.logging import get_logger
from .. import __version__ as app_current_version  # Get current version from package


@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: str
    build_date: Optional[str] = None  # Made optional, API might not always provide it consistently
    download_url: Optional[str] = None  # Made optional
    changelog: Optional[str] = None  # Made optional
    critical: bool = False
    min_version: Optional[str] = None  # Made optional
    file_size: int = 0  # In bytes
    # Optional: add a field for the local path if downloaded
    local_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts the UpdateInfo object to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UpdateInfo':
        """Creates an UpdateInfo object from a dictionary."""
        return cls(**data)


class GitHubUpdateChecker(CoreUpdateCheckerInterface):  # Inherit from the core interface
    """Update checker using GitHub releases API."""

    def __init__(self, config: Dict[str, Any]):
        # config here is expected to be the 'updates' part of the main Config
        self.config = config
        self.logger = get_logger(__name__)
        self.github_repo = config.get('github_repo', 'carpsesdema/itf-tennis-scraper')
        # Ensure update_url is correctly formed if not explicitly provided
        self.update_url = config.get('update_url') or f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        self.current_version = app_current_version  # Use the package's version

    async def check_for_updates(self) -> Optional[UpdateInfo]:
        """Check if updates are available."""
        try:
            self.logger.info(
                f"Checking for updates from {self.update_url} (current version: {self.current_version})...")

            async with aiohttp.ClientSession() as session:
                async with session.get(self.update_url, timeout=10) as response:
                    if response.status != 200:
                        self.logger.error(
                            f"GitHub API request failed with status {response.status}: {await response.text()}")
                        # Consider raising an exception or returning specific error info
                        return None  # Or raise an exception to be handled by the caller

                    data = await response.json()
                    latest_version_tag = data.get("tag_name")
                    if not latest_version_tag:
                        self.logger.warning("No tag_name found in GitHub release data.")
                        return None

                    latest_version = latest_version_tag.lstrip('v')

                    if self._compare_versions(latest_version, self.current_version) > 0:
                        self.logger.info(f"New version found: {latest_version}")
                        download_url = None
                        file_size = 0
                        primary_asset_name_suffix = ".exe"  # Or .dmg for macOS, .zip for general

                        for asset in data.get("assets", []):
                            asset_name = asset.get("name", "").lower()
                            # Prioritize .exe, then .zip, then first asset
                            if asset_name.endswith(primary_asset_name_suffix):
                                download_url = asset.get("browser_download_url")
                                file_size = asset.get("size", 0)
                                break

                        if not download_url and data.get("assets"):  # Fallback to first asset if specific not found
                            first_asset = data["assets"][0]
                            download_url = first_asset.get("browser_download_url")
                            file_size = first_asset.get("size", 0)
                            self.logger.warning(
                                f"Primary asset type '{primary_asset_name_suffix}' not found, using first asset: {first_asset.get('name')}")

                        return UpdateInfo(
                            version=latest_version,
                            build_date=data.get("published_at"),
                            download_url=download_url,
                            changelog=data.get("body"),
                            critical=self._is_critical_update(data.get("body", "")),
                            file_size=file_size
                        )
                    else:
                        self.logger.info(
                            f"Current version {self.current_version} is up to date (latest: {latest_version}).")
                        return None

        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during update check: {e}")
            return None  # Or raise
        except asyncio.TimeoutError:
            self.logger.error("Timeout during update check.")
            return None  # Or raise
        except Exception as e:
            self.logger.error(f"Update check failed: {e}", exc_info=True)
            return None  # Or raise

    async def download_update(self, update_info: UpdateInfo, progress_callback=None) -> Optional[str]:
        """Download an update."""
        # This method is now part of the UpdateDownloader for separation of concerns.
        # This class (Checker) should ideally only check.
        # However, if it's kept here for simplicity of the interface:
        try:
            from .downloader import UpdateDownloader  # Local import to avoid circular dependency if any
            downloader = UpdateDownloader()
            downloaded_path = await downloader.download(update_info, progress_callback)
            if downloaded_path:
                update_info.local_file_path = downloaded_path  # Store the path in the UpdateInfo object
            return downloaded_path
        except Exception as e:
            self.logger.error(f"Update download initiation failed from checker: {e}")
            return None

    def _is_critical_update(self, changelog: str) -> bool:
        """Determine if update is critical based on changelog."""
        if not changelog: return False
        critical_keywords = ["critical", "security", "urgent", "hotfix", "vulnerability"]
        return any(keyword in changelog.lower() for keyword in critical_keywords)

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings (e.g., "1.0.1", "1.2.0")."""

        def version_to_tuple(v):
            try:
                return tuple(map(int, v.split('.')))
            except ValueError:  # Handle cases like "1.0.0-beta" if necessary, or ensure clean tags
                self.logger.warning(f"Could not parse version string '{v}' for comparison. Assuming older.")
                return (0, 0, 0)

        v1_tuple = version_to_tuple(version1)
        v2_tuple = version_to_tuple(version2)

        if v1_tuple > v2_tuple:
            return 1
        elif v1_tuple < v2_tuple:
            return -1
        else:
            return 0