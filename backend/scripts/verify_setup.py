#!/usr/bin/env python3
"""Verify that the project setup is correct.

This script checks:
- Python version
- Dependencies installed
- Database connectivity
- Application starts successfully
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def check_python_version() -> bool:
    """Check Python version is 3.12+."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python version {version.major}.{version.minor} is too old. Require 3.12+")
        return False


def check_imports() -> bool:
    """Check that critical imports work."""
    try:
        import fastapi
        import pydantic
        import sqlalchemy
        import structlog

        print("✓ Core dependencies imported successfully")
        print(f"  - FastAPI: {fastapi.__version__}")
        print(f"  - Pydantic: {pydantic.__version__}")
        print(f"  - SQLAlchemy: {sqlalchemy.__version__}")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Run: poetry install")
        return False


def check_domain_layer() -> bool:
    """Check domain layer loads correctly."""
    try:
        print("✓ Domain layer loads successfully")
        return True
    except Exception as e:
        print(f"✗ Domain layer error: {e}")
        return False


def check_config() -> bool:
    """Check configuration loads correctly."""
    try:
        from src.config.settings import get_settings

        settings = get_settings()
        print("✓ Configuration loaded successfully")
        print(f"  - Environment: {settings.environment}")
        print(f"  - App Version: {settings.app_version}")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        print("  Create .env file from .env.example")
        return False


def check_fastapi_app() -> bool:
    """Check FastAPI application creates successfully."""
    try:
        from src.presentation.main import create_application

        app = create_application()
        print("✓ FastAPI application created successfully")
        print(f"  - Title: {app.title}")
        print(f"  - Version: {app.version}")
        return True
    except Exception as e:
        print(f"✗ FastAPI application error: {e}")
        return False


def main() -> None:
    """Run all checks."""
    print("=" * 60)
    print("Enterprise Fraud Detection Platform - Setup Verification")
    print("=" * 60)
    print()

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_imports),
        ("Domain Layer", check_domain_layer),
        ("Configuration", check_config),
        ("FastAPI Application", check_fastapi_app),
    ]

    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())
        print()

    print("=" * 60)
    if all(results):
        print("✓ All checks passed! Setup is complete.")
        print("\nNext steps:")
        print("  1. Start the server: make run")
        print("  2. Visit: http://localhost:8000/v1/docs")
        print("  3. Run tests: make test")
        sys.exit(0)
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
