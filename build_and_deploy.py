#!/usr/bin/env python3
"""
Build and Deploy Script for ITF Tennis Scraper
==============================================

This script automates the building and deployment of updates for the tennis scraper.
Run this after making changes to push updates to your client.

Usage:
    python build_and_deploy.py --version 1.0.1 --changelog "Bug fixes and improvements"
"""

import os
import sys
import argparse
import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime
import requests


class TennisScraperBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.releases_dir = self.project_root / "releases"

        # Configuration - Update these for your setup
        self.app_name = "TennisScraperPro"
        self.main_script = "tennis_scraper.py"
        self.icon_file = "app_icon.ico"  # Optional

        # GitHub configuration (if using GitHub releases)
        self.github_repo = "YOUR_USERNAME/itf-tennis-scraper"  # Update this
        self.github_token = os.getenv("GITHUB_TOKEN")  # Set this as environment variable

    def clean_build_dirs(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning build directories...")
        for directory in [self.dist_dir, self.build_dir]:
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)

        self.releases_dir.mkdir(exist_ok=True)

    def update_version_in_code(self, version):
        """Update version number in the main script"""
        print(f"📝 Updating version to {version}...")

        script_path = self.project_root / self.main_script
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace the version string
        import re
        pattern = r'CURRENT_VERSION = "[^"]*"'
        replacement = f'CURRENT_VERSION = "{version}"'

        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Version updated to {version}")
        else:
            print("⚠️  Warning: Could not find version string to update")

    def build_executable(self, version):
        """Build the executable using PyInstaller"""
        print("🔨 Building executable...")

        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--onefile",
            "--windowed",
            f"--name={self.app_name}_v{version}",
            f"--distpath={self.dist_dir}",
            f"--workpath={self.build_dir}",
            f"--specpath={self.build_dir}",
            "--clean"
        ]

        # Add icon if it exists
        icon_path = self.project_root / self.icon_file
        if icon_path.exists():
            cmd.extend([f"--icon={icon_path}"])

        # Add hidden imports for common issues
        cmd.extend([
            "--hidden-import=selenium.webdriver.chrome.service",
            "--hidden-import=PySide6.QtCore",
            "--hidden-import=requests",
        ])

        cmd.append(str(self.project_root / self.main_script))

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Build completed successfully!")

            # Move to releases directory
            exe_name = f"{self.app_name}_v{version}.exe"
            src_path = self.dist_dir / exe_name
            dst_path = self.releases_dir / exe_name

            if src_path.exists():
                shutil.move(str(src_path), str(dst_path))
                print(f"📦 Executable saved: {dst_path}")
                return dst_path
            else:
                print("❌ Executable not found after build")
                return None

        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            print(f"Output: {e.stdout}")
            print(f"Error: {e.stderr}")
            return None

    def create_update_info(self, version, changelog, exe_path):
        """Create update information file"""
        update_info = {
            "version": version,
            "build_date": datetime.now().isoformat(),
            "changelog": changelog,
            "filename": exe_path.name,
            "file_size": exe_path.stat().st_size,
            "download_url": f"https://github.com/{self.github_repo}/releases/download/v{version}/{exe_path.name}"
        }

        info_file = self.releases_dir / f"update_info_v{version}.json"
        with open(info_file, 'w') as f:
            json.dump(update_info, f, indent=2)

        print(f"📄 Update info saved: {info_file}")
        return info_file

    def create_github_release(self, version, changelog, exe_path):
        """Create a GitHub release and upload the executable"""
        if not self.github_token:
            print("⚠️  GITHUB_TOKEN environment variable not set. Skipping GitHub release.")
            print(f"   Please manually create a release at: https://github.com/{self.github_repo}/releases")
            print(f"   Upload file: {exe_path}")
            return False

        print("🚀 Creating GitHub release...")

        # Create release
        release_data = {
            "tag_name": f"v{version}",
            "target_commitish": "main",
            "name": f"Tennis Scraper v{version}",
            "body": changelog,
            "draft": False,
            "prerelease": False
        }

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Create the release
        response = requests.post(
            f"https://api.github.com/repos/{self.github_repo}/releases",
            headers=headers,
            json=release_data
        )

        if response.status_code == 201:
            release_info = response.json()
            print(f"✅ GitHub release created: {release_info['html_url']}")

            # Upload the executable
            upload_url = release_info['upload_url'].replace('{?name,label}', '')

            with open(exe_path, 'rb') as f:
                upload_response = requests.post(
                    f"{upload_url}?name={exe_path.name}",
                    headers={
                        "Authorization": f"token {self.github_token}",
                        "Content-Type": "application/octet-stream"
                    },
                    data=f.read()
                )

            if upload_response.status_code == 201:
                print("✅ Executable uploaded to GitHub release!")
                return True
            else:
                print(f"❌ Failed to upload executable: {upload_response.text}")
                return False
        else:
            print(f"❌ Failed to create GitHub release: {response.text}")
            return False

    def build_and_deploy(self, version, changelog, deploy_to_github=True):
        """Complete build and deploy process"""
        print(f"🚀 Starting build and deploy process for version {version}")
        print("=" * 60)

        # Step 1: Clean build directories
        self.clean_build_dirs()

        # Step 2: Update version in code
        self.update_version_in_code(version)

        # Step 3: Build executable
        exe_path = self.build_executable(version)
        if not exe_path:
            print("❌ Build failed. Aborting deployment.")
            return False

        # Step 4: Create update info
        self.create_update_info(version, changelog, exe_path)

        # Step 5: Deploy to GitHub (optional)
        if deploy_to_github:
            success = self.create_github_release(version, changelog, exe_path)
            if success:
                print("🎉 Deployment completed successfully!")
                print(f"Your client will automatically be notified of version {version}")
                return True
            else:
                print("⚠️  GitHub deployment failed, but executable is ready for manual upload")
                return False
        else:
            print("📦 Build completed. Executable ready for manual deployment.")
            return True


def main():
    parser = argparse.ArgumentParser(description='Build and deploy tennis scraper updates')
    parser.add_argument('--version', required=True, help='Version number (e.g., 1.0.1)')
    parser.add_argument('--changelog', required=True, help='Changelog description')
    parser.add_argument('--no-github', action='store_true', help='Skip GitHub deployment')
    parser.add_argument('--config', help='Path to configuration file')

    args = parser.parse_args()

    # Validate version format
    import re
    if not re.match(r'^\d+\.\d+\.\d+$', args.version):
        print("❌ Version must be in format X.Y.Z (e.g., 1.0.1)")
        sys.exit(1)

    builder = TennisScraperBuilder()

    # Load custom configuration if provided
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)
        for key, value in config.items():
            if hasattr(builder, key):
                setattr(builder, key, value)

    success = builder.build_and_deploy(
        version=args.version,
        changelog=args.changelog,
        deploy_to_github=not args.no_github
    )

    if success:
        print("\n🎉 SUCCESS! Your client can now update to the new version.")
        sys.exit(0)
    else:
        print("\n❌ FAILED! Check the output above for errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()

# ================================================================================================
# SETUP INSTRUCTIONS
# ================================================================================================
"""
🔧 SETUP INSTRUCTIONS
====================

1. Install PyInstaller:
   pip install pyinstaller

2. Set up GitHub (optional but recommended):
   a. Create a GitHub repository for your app
   b. Get a GitHub token: Settings > Developer settings > Personal access tokens
   c. Set environment variable: export GITHUB_TOKEN=your_token_here
   d. Update self.github_repo in the script above

3. Usage examples:

   # Build and deploy to GitHub
   python build_and_deploy.py --version 1.0.1 --changelog "Fixed bug with match filtering"

   # Build only (no GitHub)
   python build_and_deploy.py --version 1.0.1 --changelog "Bug fixes" --no-github

   # Use custom config
   python build_and_deploy.py --version 1.0.1 --changelog "Updates" --config my_config.json

4. Configuration file example (config.json):
   {
     "app_name": "MyTennisApp",
     "github_repo": "myusername/my-tennis-repo",
     "icon_file": "my_icon.ico"
   }

5. Client Update Process:
   - Your client runs the tennis scraper
   - App automatically checks for updates on startup
   - If update found, shows professional update dialog
   - Client can download and install with one click
   - App handles the installation and restart

That's it! Your client will always have the latest version automatically. 🚀
"""