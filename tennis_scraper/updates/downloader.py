import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Callable

from .checker import UpdateInfo
from ..utils.logging import get_logger


class UpdateDownloader:
    """Handles downloading updates."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def download(self, update_info: UpdateInfo, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """
        Download update file.

        Args:
            update_info: Information about the update
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Create updates directory
            updates_dir = Path("updates")
            updates_dir.mkdir(exist_ok=True)

            filename = f"TennisScraperUpdate_v{update_info.version}.exe"
            filepath = updates_dir / filename

            self.logger.info(f"Downloading update to {filepath}")

            async with aiohttp.ClientSession() as session:
                async with session.get(update_info.download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Download failed with status {response.status}")

                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            if progress_callback and total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                progress_callback(progress)

            self.logger.info(f"Download completed: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None