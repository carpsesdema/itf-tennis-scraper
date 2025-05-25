import re  # Import re for a more robust search
from pathlib import Path

from setuptools import find_packages, setup

# Read the contents of your README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")


# Read the contents of your requirements file
def load_requirements(filename="requirements.txt"):
    requirements_path = this_directory / filename
    if not requirements_path.exists():
        print(f"Warning: {filename} not found. Proceeding without it.")
        return []
    with open(requirements_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


# Get version from the package __init__.py
def get_version(package_init_file_path: Path) -> str:
    """
    Reads the __version__ string from the given package's __init__.py file.
    """
    if not package_init_file_path.exists():
        raise RuntimeError(
            f"Package __init__.py not found at: {package_init_file_path}"
        )

    print(f"Attempting to read version from: {package_init_file_path}")
    init_py_content = package_init_file_path.read_text(encoding="utf-8")

    # Use regex to find __version__ = "version_string" or 'version_string'
    match = re.search(
        r"^__version__\s*=\s*['\"]([^'\"]*)['\"]", init_py_content, re.MULTILINE
    )

    if match:
        version = match.group(1)
        print(f"Found version: {version}")
        return version
    else:
        print(f"Could not find __version__ string in {package_init_file_path}")
        print("--- File Content ---")
        print(init_py_content)
        print("--- End File Content ---")
        raise RuntimeError(
            f"Unable to find __version__ string in {package_init_file_path}"
        )


# Construct the path to the main package's __init__.py
# __file__ is setup.py, its parent is the project root.
# Then navigate into 'tennis_scraper' directory to find its '__init__.py'.
package_init_path = this_directory / "tennis_scraper" / "__init__.py"
VERSION = get_version(package_init_path)

setup(
    name="itf-tennis-scraper-pro",  # Distribution name on PyPI
    version=VERSION,
    author="Your Name / Tennis Scraper Team",  # Replace with your name/team
    author_email="your.email@example.com",  # Replace with your email
    description="A professional application for scraping and monitoring ITF tennis matches.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/carpsesdema/itf-tennis-scraper",  # Replace with your repo URL
    license="MIT",  # Or your chosen license
    packages=find_packages(
        exclude=["tests*", "build*", "dist*", "*.egg-info*", "scripts*"]
    ),
    include_package_data=True,  # To include non-code files specified in MANIFEST.in (if you create one)
    install_requires=load_requirements(),
    python_requires=">=3.8",  # Specify your minimum Python version
    entry_points={
        "console_scripts": [
            "tennis-scraper-pro=main:main",  # Creates a command-line entry point
        ],
        "gui_scripts": [
            "tennis-scraper-pro-gui=main:main",  # For GUI applications, often the same as console
        ],
    },
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.org/classifiers/
        "Development Status :: 4 - Beta",  # Or "3 - Alpha", "5 - Production/Stable"
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",  # Adjust if you use a different license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",  # Or specify OS like "Operating System :: Microsoft :: Windows"
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Games/Entertainment",  # If applicable
        "Environment :: X11 Applications :: Qt",  # If using Qt directly for GUI
        "Framework :: PySide",  # Specifically for PySide6
    ],
    keywords="tennis scraper sports data itf live scores PySide6 selenium aiohttp",
    project_urls={  # Optional
        "Bug Reports": "https://github.com/carpsesdema/itf-tennis-scraper/issues",
        "Source": "https://github.com/carpsesdema/itf-tennis-scraper/",
        # 'Documentation': 'https://your-documentation-url.com/',
    },
)
