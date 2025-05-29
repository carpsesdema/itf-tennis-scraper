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
    """Setup Playwright browsers for packaged application with detailed logging."""
    is_packaged = getattr(sys, 'frozen', False)

    if not is_packaged:
        print("🔧 Running in development mode - Playwright should work normally")
        return True

    print("🎭 PACKAGED APP DETECTED - Setting up Playwright browsers...")
    print(f"📁 Executable path: {sys.executable}")
    print(f"📁 Current working directory: {os.getcwd()}")

    try:
        # First, let's test if Playwright can be imported
        try:
            import playwright
            print(f"✅ Playwright imported successfully from: {playwright.__file__}")
        except ImportError as e:
            print(f"❌ CRITICAL: Cannot import playwright: {e}")
            return False

        # Check if we're in PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            bundle_dir = Path(sys._MEIPASS)
            print(f"📦 PyInstaller bundle directory: {bundle_dir}")

            # List contents to see what's included
            print("📂 Bundle contents:")
            try:
                for item in bundle_dir.iterdir():
                    if item.is_dir():
                        print(f"  📁 {item.name}/")
                    else:
                        print(f"  📄 {item.name}")
            except Exception as e:
                print(f"⚠️ Cannot list bundle contents: {e}")

        # Check for system Chrome/Chromium first (most reliable for packaged apps)
        print("🔍 Checking for system Chrome/Chromium...")
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]

        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                print(f"✅ Found system Chrome: {chrome_path}")
                os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = chrome_path

                # Test if Chrome works
                try:
                    result = subprocess.run([chrome_path, "--version"],
                                            capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"✅ Chrome version: {result.stdout.strip()}")
                        return True
                except Exception as e:
                    print(f"⚠️ Chrome test failed: {e}")

        print("❌ No system Chrome found")

        # Try to find Playwright browsers
        print("🔍 Looking for Playwright browsers...")

        # Common Playwright browser locations
        possible_paths = []

        # Windows locations
        if sys.platform == "win32":
            possible_paths.extend([
                Path.home() / "AppData" / "Local" / "ms-playwright",
                Path.cwd() / "ms-playwright",
                Path(sys.executable).parent / "ms-playwright"
            ])
        # Linux/Mac locations
        else:
            possible_paths.extend([
                Path.home() / ".cache" / "ms-playwright",
                Path("/usr/share/ms-playwright"),
                Path.cwd() / "ms-playwright"
            ])

        for browser_path in possible_paths:
            print(f"  Checking: {browser_path}")
            if browser_path.exists():
                print(f"✅ Found Playwright browsers at: {browser_path}")
                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_path)

                # Look for Chromium executable
                chromium_paths = [
                    browser_path / "chromium-*/chrome-win" / "chrome.exe",
                    browser_path / "chromium-*/chrome-linux" / "chrome",
                    browser_path / "chromium-*/chrome-mac" / "Chromium.app/Contents/MacOS/Chromium"
                ]

                for pattern in chromium_paths:
                    import glob
                    matches = glob.glob(str(pattern))
                    if matches:
                        chromium_exe = matches[0]
                        print(f"✅ Found Chromium executable: {chromium_exe}")
                        os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = chromium_exe
                        return True

        print("❌ No Playwright browsers found")

        # Try to install browsers to user directory
        print("🔄 Attempting to install Playwright browsers...")

        user_dir = Path.home() / "AppData" / "Local" / "ms-playwright" if sys.platform == "win32" else Path.home() / ".cache" / "ms-playwright"
        user_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Try using the current Python executable
            install_cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
            print(f"🔄 Running: {' '.join(install_cmd)}")

            result = subprocess.run(install_cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=180,  # 3 minute timeout
                                    cwd=str(user_dir.parent))

            print(f"📋 Install stdout: {result.stdout}")
            print(f"📋 Install stderr: {result.stderr}")
            print(f"📋 Install return code: {result.returncode}")

            if result.returncode == 0:
                print("✅ Browser installation completed")
                return True
            else:
                print(f"❌ Browser installation failed with code {result.returncode}")

        except subprocess.TimeoutExpired:
            print("❌ Browser installation timed out")
        except Exception as e:
            print(f"❌ Browser installation error: {e}")

        # Final attempt - try to test Playwright directly
        print("🔄 Testing Playwright directly...")
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                print("✅ Playwright context created successfully")

                # Try to get browser executable path
                try:
                    browser_path = p.chromium.executable_path
                    print(f"✅ Chromium executable path: {browser_path}")
                    if browser_path and os.path.exists(browser_path):
                        print("✅ Chromium executable exists")
                        return True
                    else:
                        print("❌ Chromium executable not found")
                except Exception as e:
                    print(f"❌ Error getting Chromium path: {e}")

        except Exception as e:
            print(f"❌ Playwright test failed: {e}")

        print("❌ All browser setup methods failed")
        return False

    except Exception as e:
        print(f"❌ Critical error in browser setup: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main application entry point."""
    try:
        # Initialize logging
        setup_logging()
        logger = logging.getLogger(__name__)

        logger.info("Starting ITF Tennis Scraper...")

        # Setup Playwright browsers for packaged app with detailed logging
        browser_setup_success = setup_playwright_for_packaged_app()

        if not browser_setup_success:
            logger.error("❌ CRITICAL: Playwright browser setup failed!")
            if getattr(sys, 'frozen', False):
                # Show error message for packaged app
                try:
                    from PySide6.QtWidgets import QApplication, QMessageBox
                    app = QApplication(sys.argv)
                    QMessageBox.critical(None, "Browser Setup Failed",
                                         "Could not setup browsers for web scraping.\n\n"
                                         "Please install Google Chrome or try running as administrator.\n\n"
                                         "Check the console output for detailed error information.")
                    return 1
                except:
                    print("❌ Could not show error dialog")
                    return 1
        else:
            logger.info("✅ Playwright browser setup completed successfully")

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