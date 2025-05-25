#!/usr/bin/env python3
"""
GitHub API Test Script
======================

This script tests your GitHub token and repository access to help diagnose upload issues.
"""

import os
import json
import requests
from pathlib import Path


def test_github_setup():
    """Test GitHub API setup and permissions"""
    print("🔍 GitHub API Setup Test")
    print("=" * 40)

    # Check environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    github_repo = os.getenv('GITHUB_REPO', 'carpsesdema/itf-tennis-scraper')

    print(f"📋 Environment Check:")
    print(f"   GITHUB_TOKEN: {'✅ SET' if github_token else '❌ NOT SET'}")
    if github_token:
        print(f"   Token length: {len(github_token)} characters")
        print(f"   Token start: {github_token[:8]}..." if len(github_token) > 8 else "   Token too short!")
    print(f"   GITHUB_REPO: {github_repo}")
    print()

    if not github_token:
        print("❌ GITHUB_TOKEN not set!")
        print("📋 To fix this:")
        print("   1. Go to GitHub Settings → Developer settings → Personal access tokens")
        print("   2. Create a token with 'repo' permissions")
        print("   3. Run: set GITHUB_TOKEN=your_token_here (Windows)")
        print("   4. Or: export GITHUB_TOKEN=your_token_here (Linux/Mac)")
        return False

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ITF-Tennis-Scraper-Test"
    }

    try:
        # Test 1: Basic API access
        print("🧪 Test 1: Basic API Access")
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ Authenticated as: {user_data.get('login', 'Unknown')}")
            print(f"   📧 Email: {user_data.get('email', 'Not public')}")
            print(f"   🔒 Scopes: {response.headers.get('X-OAuth-Scopes', 'Not visible')}")
        else:
            print(f"   ❌ Failed: {response.text}")
            return False
        print()

        # Test 2: Repository access
        print("🧪 Test 2: Repository Access")
        repo_url = f"https://api.github.com/repos/{github_repo}"
        response = requests.get(repo_url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            repo_data = response.json()
            print(f"   ✅ Repository: {repo_data['full_name']}")
            print(f"   🔒 Private: {repo_data['private']}")
            permissions = repo_data.get('permissions', {})
            print(f"   📋 Permissions:")
            print(f"      Admin: {permissions.get('admin', False)}")
            print(f"      Push: {permissions.get('push', False)}")
            print(f"      Pull: {permissions.get('pull', False)}")

            if not permissions.get('push', False):
                print("   ⚠️  Warning: No push permissions - uploads may fail")
        else:
            print(f"   ❌ Failed: {response.text}")
            if response.status_code == 404:
                print("   💡 This usually means:")
                print("      - Repository doesn't exist")
                print("      - Repository is private and token lacks access")
                print("      - Repository name is incorrect")
            return False
        print()

        # Test 3: Releases access
        print("🧪 Test 3: Releases Access")
        releases_url = f"https://api.github.com/repos/{github_repo}/releases"
        response = requests.get(releases_url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            releases = response.json()
            print(f"   ✅ Can access releases")
            print(f"   📦 Existing releases: {len(releases)}")
            if releases:
                latest = releases[0]
                print(f"   🏷️  Latest: {latest['tag_name']} ({latest['published_at'][:10]})")
        else:
            print(f"   ❌ Cannot access releases: {response.text}")
            return False
        print()

        # Test 4: Create test release (draft)
        print("🧪 Test 4: Create Test Release")
        test_release_data = {
            "tag_name": "test-upload-permissions",
            "name": "Test Release - Delete Me",
            "body": "This is a test release to verify upload permissions. Safe to delete.",
            "draft": True,  # Draft so it doesn't notify users
            "prerelease": True
        }

        response = requests.post(
            f"https://api.github.com/repos/{github_repo}/releases",
            headers=headers,
            json=test_release_data,
            timeout=30
        )

        print(f"   Status: {response.status_code}")

        if response.status_code == 201:
            release_info = response.json()
            print(f"   ✅ Can create releases")
            print(f"   🆔 Release ID: {release_info['id']}")
            print(f"   🔗 Upload URL: {release_info['upload_url']}")

            # Clean up - delete the test release
            delete_response = requests.delete(
                f"https://api.github.com/repos/{github_repo}/releases/{release_info['id']}",
                headers=headers,
                timeout=30
            )
            if delete_response.status_code == 204:
                print("   🧹 Test release cleaned up")
            else:
                print("   ⚠️  Could not delete test release - please delete manually")
                print(f"      Release ID: {release_info['id']}")

        else:
            print(f"   ❌ Cannot create releases: {response.text}")
            if response.status_code == 403:
                print("   💡 This usually means:")
                print("      - Token lacks 'repo' scope")
                print("      - Repository settings block releases")
                print("      - Organization policies prevent releases")
            return False
        print()

        print("🎉 All tests passed! GitHub setup is working correctly.")
        print("📋 If uploads still fail, the issue is likely:")
        print("   - File size too large (GitHub has limits)")
        print("   - Network timeout during upload")
        print("   - Temporary GitHub API issues")
        return True

    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check your internet connection")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timeout - try again later")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def check_file_for_upload():
    """Check if there's a file ready to upload"""
    print("\n📁 File Check")
    print("=" * 20)

    releases_dir = Path("releases")
    if not releases_dir.exists():
        print("   ❌ No releases directory found")
        return None

    exe_files = list(releases_dir.glob("*.exe"))
    if not exe_files:
        print("   ❌ No .exe files found in releases directory")
        return None

    latest_exe = max(exe_files, key=lambda p: p.stat().st_mtime)
    file_size_mb = latest_exe.stat().st_size / (1024 * 1024)

    print(f"   📦 Latest executable: {latest_exe.name}")
    print(f"   📏 Size: {file_size_mb:.1f} MB")

    if file_size_mb > 100:
        print("   ⚠️  Warning: File is quite large - uploads may take time or timeout")

    return latest_exe


def main():
    print("GitHub Upload Troubleshooter")
    print("=" * 50)

    # Test GitHub setup
    github_ok = test_github_setup()

    # Check for files
    exe_file = check_file_for_upload()

    print("\n📋 Summary:")
    print(f"   GitHub API: {'✅ Working' if github_ok else '❌ Issues found'}")
    print(f"   Executable: {'✅ Ready' if exe_file else '❌ Not found'}")

    if github_ok and exe_file:
        print("\n🎯 Everything looks good! Try running the build script again:")
        print("   python build_and_deploy.py --version X.Y.Z --changelog 'Your changes'")
    elif github_ok and not exe_file:
        print("\n🎯 GitHub is working, but no executable found. Run:")
        print("   python build_and_deploy.py --version X.Y.Z --changelog 'Your changes' --no-github")
        print("   Then: python upload_helper.py X.Y.Z 'Your changes'")
    else:
        print("\n🎯 Fix the GitHub issues above first, then try again.")

    print(f"\n🔍 If problems persist, try the debug version:")
    print("   Save the debug script as 'debug_build.py' and run it instead")


if __name__ == "__main__":
    main()