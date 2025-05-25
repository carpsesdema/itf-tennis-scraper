"""
Development environment setup script.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, check=True, shell=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {cmd}")
        print(f"   Error: {e.stderr}")
        return False


def setup_virtual_environment():
    """Setup virtual environment."""
    venv_path = Path("tennis_scraper_env")

    if venv_path.exists():
        print(f"⚠️  Virtual environment already exists at {venv_path}")
        response = input("Do you want to recreate it? (y/N): ")
        if response.lower() != 'y':
            return True

        import shutil
        shutil.rmtree(venv_path)

    print("🔄 Creating virtual environment...")
    venv.create(venv_path, with_pip=True)
    print("✅ Virtual environment created")

    # Get activation script path
    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate.bat"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        activate_script = venv_path / "bin" / "activate"
        pip_path = venv_path / "bin" / "pip"

    print(f"📝 To activate the virtual environment, run:")
    print(f"   {activate_script}")

    return pip_path


def install_dependencies(pip_path):
    """Install project dependencies."""
    requirements_files = ["requirements.txt"]

    # Install development dependencies if available
    if Path("requirements-dev.txt").exists():
        requirements_files.append("requirements-dev.txt")

    for req_file in requirements_files:
        if Path(req_file).exists():
            cmd = f'"{pip_path}" install -r {req_file}'
            if not run_command(cmd, f"Installing {req_file}"):
                return False

    # Install project in editable mode
    cmd = f'"{pip_path}" install -e .'
    return run_command(cmd, "Installing project in editable mode")


def setup_pre_commit(pip_path):
    """Setup pre-commit hooks."""
    if Path(".pre-commit-config.yaml").exists():
        cmd = f'"{pip_path}" install pre-commit'
        if run_command(cmd, "Installing pre-commit"):
            # Activate pre-commit hooks
            venv_path = pip_path.parent
            if sys.platform == "win32":
                precommit_path = venv_path / "pre-commit.exe"
            else:
                precommit_path = venv_path / "pre-commit"

            cmd = f'"{precommit_path}" install'
            return run_command(cmd, "Setting up pre-commit hooks")
    else:
        print("⚠️  No .pre-commit-config.yaml found, skipping pre-commit setup")

    return True


def create_config_files():
    """Create default configuration files."""
    configs = {
        ".env": """# Environment variables for development
DEBUG=true
LOG_LEVEL=DEBUG
""",
        "pytest.ini": """[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
""",
        ".pre-commit-config.yaml": """repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
"""
    }

    for filename, content in configs.items():
        if not Path(filename).exists():
            print(f"📝 Creating {filename}...")
            with open(filename, 'w') as f:
                f.write(content)
            print(f"✅ Created {filename}")


def verify_installation(pip_path):
    """Verify the installation by importing key modules."""
    print("🔍 Verifying installation...")

    test_imports = [
        "tennis_scraper",
        "PySide6",
        "requests",
        "selenium",
        "pandas"
    ]

    venv_python = pip_path.parent / ("python.exe" if sys.platform == "win32" else "python")

    for module in test_imports:
        cmd = f'"{venv_python}" -c "import {module}; print(f\\"✅ {module}\\")"'
        try:
            subprocess.run(cmd, check=True, shell=True, capture_output=True)
            print(f"✅ {module}")
        except subprocess.CalledProcessError:
            print(f"❌ {module}")
            return False

    return True


def main():
    """Main setup function."""
    print("🎾 ITF Tennis Scraper - Development Environment Setup")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # Setup virtual environment
    pip_path = setup_virtual_environment()
    if not pip_path:
        print("❌ Failed to setup virtual environment")
        sys.exit(1)

    # Install dependencies
    if not install_dependencies(pip_path):
        print("❌ Failed to install dependencies")
        sys.exit(1)

    # Create config files
    create_config_files()

    # Setup pre-commit
    setup_pre_commit(pip_path)

    # Verify installation
    if not verify_installation(pip_path):
        print("❌ Installation verification failed")
        sys.exit(1)

    print("\n🎉 Development environment setup completed!")
    print("\n📋 Next steps:")
    print("1. Activate virtual environment:")
    if sys.platform == "win32":
        print("   tennis_scraper_env\\Scripts\\activate")
    else:
        print("   source tennis_scraper_env/bin/activate")
    print("2. Run the application:")
    print("   python main.py")
    print("3. Run tests:")
    print("   pytest")
    print("4. Build executable:")
    print("   python build/builder.py")


if __name__ == "__main__":
    main()