# hook-playwright.py - Place this in your project root directory

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all playwright modules
hiddenimports = collect_submodules('playwright')

# Add specific modules that might be missed
hiddenimports += [
    'playwright.async_api',
    'playwright.sync_api',
    'playwright._impl._driver',
    'playwright._impl._connection',
    'playwright._impl._browser_type',
    'playwright._impl._page',
    'playwright._impl._frame',
    'playwright._impl._element_handle',
    'playwright._impl._locator'
]

# Collect playwright data files
datas = collect_data_files('playwright')

# Try to find and include browser binaries
try:
    import playwright

    playwright_path = Path(playwright.__file__).parent

    # Look for browser installations
    possible_browser_paths = [
        playwright_path / "driver",
        Path.home() / ".cache" / "ms-playwright",
        Path.home() / "AppData" / "Local" / "ms-playwright",  # Windows
        Path.home() / "Library" / "Caches" / "ms-playwright",  # macOS
    ]

    for browser_path in possible_browser_paths:
        if browser_path.exists():
            print(f"Found playwright browsers at: {browser_path}")
            # Add the entire browser directory
            datas.append((str(browser_path), "playwright_browsers"))
            break
    else:
        print("Warning: Playwright browsers not found - they may need to be installed at runtime")

except Exception as e:
    print(f"Warning: Could not locate playwright browsers: {e}")

# Include the playwright driver executable
try:
    from playwright._impl._driver import compute_driver_executable

    driver_path = compute_driver_executable()
    if driver_path and os.path.exists(driver_path):
        datas.append((driver_path, "playwright_driver"))
        print(f"Found playwright driver at: {driver_path}")
except Exception as e:
    print(f"Warning: Could not locate playwright driver: {e}")