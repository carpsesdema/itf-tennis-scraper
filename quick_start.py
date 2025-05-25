"""
Quick start script for ITF Tennis Scraper.
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Quick start the application."""
    print("🎾 ITF Tennis Scraper - Quick Start")
    print("=" * 40)

    # Check if virtual environment exists
    venv_path = Path("tennis_scraper_env")
    if not venv_path.exists():
        print("❌ Virtual environment not found!")
        print("Please run setup first:")
        print("   python scripts/setup_dev.py")
        return 1

    # Determine activation command
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        print("❌ Python executable not found in virtual environment!")
        return 1

    # Run the application
    print("🚀 Starting ITF Tennis Scraper...")
    try:
        subprocess.run([str(python_exe), "main.py"], check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Application failed to start: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        return 0


if __name__ == "__main__":
    sys.exit(main())