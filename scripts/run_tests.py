"""
Test runner script with enhanced features.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_path="tests/", verbose=True, coverage=False, html_report=False):
    """Run test suite with various options."""
    cmd = [sys.executable, "-m", "pytest"]

    # Add test path
    cmd.append(test_path)

    # Verbosity
    if verbose:
        cmd.append("-v")

    # Coverage
    if coverage:
        cmd.extend(["--cov=tennis_scraper", "--cov-report=term-missing"])

        if html_report:
            cmd.append("--cov-report=html")

    # Additional options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])

    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main():
    parser = argparse.ArgumentParser(description="Run tennis scraper tests")
    parser.add_argument("--path", default="tests/", help="Test path")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Run with coverage")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")

    args = parser.parse_args()

    if not Path(args.path).exists():
        print(f"Test path does not exist: {args.path}")
        return 1

    return run_tests(
        test_path=args.path,
        verbose=not args.quiet,
        coverage=args.coverage,
        html_report=args.html
    )


if __name__ == "__main__":
    sys.exit(main())