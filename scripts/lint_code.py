"""
Code quality and linting script.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_black(check_only=False):
    """Run Black code formatter."""
    cmd = [sys.executable, "-m", "black"]

    if check_only:
        cmd.append("--check")

    cmd.extend(["tennis_scraper/", "tests/", "scripts/", "build/"])

    print("🔧 Running Black formatter...")
    return subprocess.run(cmd).returncode == 0


def run_isort(check_only=False):
    """Run isort import sorter."""
    cmd = [sys.executable, "-m", "isort"]

    if check_only:
        cmd.append("--check-only")

    cmd.extend(["tennis_scraper/", "tests/", "scripts/", "build/"])

    print("📦 Running isort...")
    return subprocess.run(cmd).returncode == 0


def run_flake8():
    """Run flake8 linter."""
    cmd = [sys.executable, "-m", "flake8", "tennis_scraper/", "tests/"]

    print("🔍 Running flake8...")
    return subprocess.run(cmd).returncode == 0


def run_mypy():
    """Run mypy type checker."""
    cmd = [sys.executable, "-m", "mypy", "tennis_scraper/"]

    print("🔬 Running mypy...")
    return subprocess.run(cmd).returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run code quality checks")
    parser.add_argument("--check", action="store_true", help="Check only (don't fix)")
    parser.add_argument("--skip-format", action="store_true", help="Skip formatting")
    parser.add_argument("--skip-lint", action="store_true", help="Skip linting")
    parser.add_argument("--skip-types", action="store_true", help="Skip type checking")

    args = parser.parse_args()

    all_passed = True

    # Formatting
    if not args.skip_format:
        if not run_black(args.check):
            all_passed = False

        if not run_isort(args.check):
            all_passed = False

    # Linting
    if not args.skip_lint:
        if not run_flake8():
            all_passed = False

    # Type checking
    if not args.skip_types:
        if not run_mypy():
            all_passed = False

    if all_passed:
        print("✅ All code quality checks passed!")
        return 0
    else:
        print("❌ Some code quality checks failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())