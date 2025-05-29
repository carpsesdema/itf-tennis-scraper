#!/usr/bin/env python3
"""
ITF Tennis Scraper - Professional Application Entry Point
=========================================================

This is the main entry point for the ITF Tennis Scraper application.
It initializes the application with proper configuration and error handling.
"""

import sys
import logging
import os
import subprocess
from pathlib import Path

CURRENT_VERSION = "1.0.3"

# Add the project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from tennis_scraper.app import TennisScraperApp
    from tennis_scraper.config import Config
    from tennis_scraper.utils.logging import setup_logging
except ImportError as e:
    print(f"Error importing tennis_scraper modules: {e}")
    print("Please ensure you're running from the project root directory")
    print("and that all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def setup_playwright_for_packaged_app():
    """Setup Playwright browsers for packaged application."""
    if not getattr(sys, 'frozen', False):
        # Not a packaged app, return early
        return True

    print("🎭 Setting up Playwright for packaged application...")

    try:
        # Set environment variables for Playwright
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller temp directory
            bundle_dir = Path(sys._MEIPASS)

            # Look for included browsers
            browser_dirs = [
                bundle_dir / "playwright_browsers",
                bundle_dir / "_internal" / "playwright_browsers"
            ]

            for browser_dir in browser_dirs:
                if browser_dir.exists():
                    print(f"✅ Found packaged browsers at: {browser_dir}")
                    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_dir)
                    return True

        # If browsers not found in package, try to install them
        print("🔄 Browsers not found in package, attempting installation...")

        # Try to install to user directory
        user_browser_dir = Path.home() / ".cache" / "ms-playwright"
        if sys.platform == "win32":
            user_browser_dir = Path.home() / "AppData" / "Local" / "ms-playwright"

        # Create directory if it doesn't exist
        user_browser_dir.mkdir(parents=True, exist_ok=True)

        # Try to install browsers
        try:
            # Method 1: Use playwright install command
            install_cmd = [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"]

            print("🔄 Installing Chromium browser...")
            result = subprocess.run(install_cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=300,  # 5 minute timeout
                                    cwd=str(user_browser_dir.parent))

            if result.returncode == 0:
                print("✅ Browser installation completed successfully")
                return True
            else:
                print(f"⚠️ Browser installation had issues: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("⚠️ Browser installation timed out")
        except FileNotFoundError:
            print("⚠️ Playwright command not found in packaged app")
        except Exception as e:
            print(f"⚠️ Browser installation failed: {e}")

        # Method 2: Try programmatic installation
        try:
            print("🔄 Trying programmatic browser installation...")
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("✅ Browser test successful")
                return True

        except Exception as e:
            print(f"⚠️ Programmatic browser test failed: {e}")

        # Method 3: Check if system Chrome/Chromium exists
        try:
            print("🔄 Looking for system Chrome/Chromium...")
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ]

            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    print(f"✅ Found system Chrome at: {chrome_path}")
                    os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = chrome_path
                    return True

        except Exception as e:
            print(f"⚠️ System Chrome detection failed: {e}")

        print("❌ Could not setup browsers - scraping may fail")
        return False

    except Exception as e:
        print(f"❌ Critical error in browser setup: {e}")
        return False


def main():
    """Main application entry point."""
    try:
        # Initialize logging
        setup_logging()
        logger = logging.getLogger(__name__)

        logger.info("Starting ITF Tennis Scraper...")

        # Setup Playwright browsers for packaged app
        if not setup_playwright_for_packaged_app():
            logger.warning("Playwright browser setup had issues - scraping may not work properly")

        # Load configuration
        config = Config.load_from_file()

        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            return 1

        # Create and run application
        app = TennisScraperApp(config)
        exit_code = app.run()

        logger.info("Application shutting down")
        return exit_code

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        logging.exception("Fatal error occurred")
        return 1


if __name__ == "__main__":
    sys.exit(main())