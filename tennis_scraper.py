#!/usr/bin/env python3
"""
ITF Tennis Scraper - Professional Application Entry Point
=========================================================

This is the main entry point for the ITF Tennis Scraper application.
It initializes the application with proper configuration and error handling.
"""

import sys
import logging
from pathlib import Path

CURRENT_VERSION = "1.0.2"



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


def main():
    """Main application entry point."""
    try:
        # Initialize logging
        setup_logging()
        logger = logging.getLogger(__name__)

        logger.info("Starting ITF Tennis Scraper...")

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