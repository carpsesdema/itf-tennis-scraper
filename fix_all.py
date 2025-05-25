#!/usr/bin/env python3
"""
Automatic fix script for ITF Tennis Scraper issues.
"""

from pathlib import Path


def fix_file(file_path, changes):
    """Apply changes to a file."""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        for old, new in changes:
            if old in content:
                content = content.replace(old, new)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"⚠️  No changes needed: {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False


def create_missing_files():
    """Create missing __init__.py files."""
    init_files = [
        "tennis_scraper/gui/workers/__init__.py",
        "tennis_scraper/gui/dialogs/__init__.py"
    ]

    for init_file in init_files:
        init_path = Path(init_file)
        if not init_path.exists():
            init_path.parent.mkdir(parents=True, exist_ok=True)
            init_path.write_text('"""Module initialization."""\n')
            print(f"✅ Created: {init_file}")


def main():
    print("🔧 ITF Tennis Scraper - Auto Fix Script")
    print("=" * 50)

    # Create missing files first
    print("\n📁 Creating missing files...")
    create_missing_files()

    # Apply all fixes
    print("\n🔧 Applying fixes...")

    fixes = {
        "tennis_scraper/utils/export.py": [
            ("from typing import List, Dict, Any", "from typing import List, Dict, Any, Optional")
        ],

        "tennis_scraper/gui/components/status_bar.py": [
            ("from PySide6.QtWidgets import (\n    QStatusBar, QLabel, QProgressBar, QPushButton, QHBoxLayout, QWidget\n)",
             "from PySide6.QtWidgets import (\n    QStatusBar, QLabel, QProgressBar, QPushButton, QHBoxLayout, QWidget, QSizePolicy\n)"),
            ("spacer.setSizePolicy(spacer.sizePolicy().Expanding, spacer.sizePolicy().Preferred)",
             "spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)")
        ],

        "tennis_scraper/gui/components/matches_table.py": [
            ("from datetime import timezone", "from datetime import datetime, timezone")
        ],

        "tennis_scraper/scrapers/base.py": [
            ("source=asyncio.run(self.get_source_name()),", "source=\"\",  # Will be set by caller")
        ],

        "tennis_scraper/scrapers/flashscore.py": [
            ("source=asyncio.run(self.get_source_name()),", "source=\"flashscore\",")
        ],

        "tennis_scraper/scrapers/sofascore.py": [
            ("source=asyncio.run(self.get_source_name()),", "source=\"sofascore\",")
        ],

        "tennis_scraper/gui/dialogs/update_dialog.py": [
            ("from PySide6.QtWidgets import (", "from typing import Optional\nfrom PySide6.QtWidgets import (")
        ],

        "tennis_scraper/gui/workers/update_worker.py": [
            ("from PySide6.QtCore import QThread, Signal",
             "from typing import Optional\nfrom PySide6.QtCore import QThread, Signal")
        ]
    }

    fixed_count = 0
    for file_path, changes in fixes.items():
        if fix_file(file_path, changes):
            fixed_count += 1

    print(f"\n🎉 Fixed {fixed_count} files!")
    print("\nNow try: python main.py")


if __name__ == "__main__":
    main()