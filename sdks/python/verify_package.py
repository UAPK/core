#!/usr/bin/env python3
"""Verify package is ready for PyPI distribution."""

import re
import sys
from pathlib import Path


def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a required file exists."""
    if file_path.exists():
        print(f"✅ {description}: {file_path.name}")
        return True
    else:
        print(f"❌ {description}: MISSING - {file_path.name}")
        return False


def check_pyproject_toml(file_path: Path) -> bool:
    """Verify pyproject.toml has required fields."""
    print("\n📋 Checking pyproject.toml...")

    if not file_path.exists():
        print("❌ pyproject.toml not found")
        return False

    with open(file_path) as f:
        content = f.read()

    required_fields = [
        (r'\[project\]', "project section"),
        (r'name\s*=\s*"uapk-gateway"', "package name"),
        (r'version\s*=\s*"[\d\.]+"', "version number"),
        (r'description\s*=', "description"),
        (r'readme\s*=\s*"README.md"', "README reference"),
        (r'requires-python\s*=', "Python version requirement"),
        (r'dependencies\s*=', "dependencies list"),
        (r'\[build-system\]', "build-system section"),
    ]

    all_valid = True
    for pattern, desc in required_fields:
        if re.search(pattern, content):
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ Missing: {desc}")
            all_valid = False

    return all_valid


def check_readme(file_path: Path) -> bool:
    """Verify README.md has required sections."""
    print("\n📖 Checking README.md...")

    if not file_path.exists():
        print("❌ README.md not found")
        return False

    with open(file_path) as f:
        content = f.read()

    required_sections = [
        "# UAPK Gateway Python SDK",
        "## Features",
        "## Installation",
        "## Quick Start",
        "## Usage",
        "## API Reference",
    ]

    all_valid = True
    for section in required_sections:
        if section in content:
            print(f"  ✅ Has section: {section}")
        else:
            print(f"  ⚠️  Missing section: {section}")
            all_valid = False

    # Check length
    words = len(content.split())
    print(f"  📊 Word count: {words}")
    if words < 500:
        print("  ⚠️  README might be too short (< 500 words)")

    return all_valid


def check_package_structure(root: Path) -> bool:
    """Verify package directory structure."""
    print("\n📦 Checking package structure...")

    required_files = [
        ("uapk_gateway/__init__.py", "Package __init__"),
        ("uapk_gateway/client.py", "Sync client"),
        ("uapk_gateway/async_client.py", "Async client"),
        ("uapk_gateway/models.py", "Models"),
        ("uapk_gateway/exceptions.py", "Exceptions"),
        ("uapk_gateway/integrations/__init__.py", "Integrations __init__"),
        ("uapk_gateway/integrations/langchain.py", "LangChain integration"),
    ]

    all_valid = True
    for file_path, desc in required_files:
        full_path = root / file_path
        if full_path.exists():
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ Missing: {desc}")
            all_valid = False

    return all_valid


def check_version_consistency(root: Path) -> bool:
    """Check version is consistent across files."""
    print("\n🔢 Checking version consistency...")

    # Get version from pyproject.toml
    pyproject = root / "pyproject.toml"
    with open(pyproject) as f:
        content = f.read()
        match = re.search(r'version\s*=\s*"([\d\.]+)"', content)
        if match:
            pyproject_version = match.group(1)
            print(f"  pyproject.toml: {pyproject_version}")
        else:
            print("  ❌ No version in pyproject.toml")
            return False

    # Get version from __init__.py
    init_file = root / "uapk_gateway/__init__.py"
    with open(init_file) as f:
        content = f.read()
        match = re.search(r'__version__\s*=\s*"([\d\.]+)"', content)
        if match:
            init_version = match.group(1)
            print(f"  __init__.py: {init_version}")
        else:
            print("  ❌ No __version__ in __init__.py")
            return False

    # Check CHANGELOG
    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        with open(changelog) as f:
            first_lines = f.read(500)
            if pyproject_version in first_lines:
                print(f"  ✅ CHANGELOG.md mentions {pyproject_version}")
            else:
                print(f"  ⚠️  CHANGELOG.md might not mention {pyproject_version}")

    if pyproject_version == init_version:
        print(f"  ✅ Versions match: {pyproject_version}")
        return True
    else:
        print(f"  ❌ Version mismatch!")
        return False


def check_dependencies(root: Path) -> bool:
    """Check dependencies are properly specified."""
    print("\n📚 Checking dependencies...")

    pyproject = root / "pyproject.toml"
    with open(pyproject) as f:
        content = f.read()

    # Check core dependencies
    if 'httpx' in content:
        print("  ✅ httpx (HTTP client)")
    else:
        print("  ❌ Missing httpx")

    if 'pydantic' in content:
        print("  ✅ pydantic (validation)")
    else:
        print("  ❌ Missing pydantic")

    # Check optional dependencies
    if 'langchain' in content:
        print("  ✅ langchain (optional integration)")

    # Check dev dependencies
    if 'pytest' in content:
        print("  ✅ pytest (dev)")

    return True


def check_classifiers(root: Path) -> bool:
    """Check PyPI classifiers are set."""
    print("\n🏷️  Checking PyPI classifiers...")

    pyproject = root / "pyproject.toml"
    with open(pyproject) as f:
        content = f.read()

    required_classifiers = [
        "Development Status",
        "Intended Audience",
        "License",
        "Programming Language :: Python",
    ]

    all_valid = True
    for classifier in required_classifiers:
        if classifier in content:
            print(f"  ✅ {classifier}")
        else:
            print(f"  ❌ Missing: {classifier}")
            all_valid = False

    return all_valid


def estimate_package_size(root: Path) -> None:
    """Estimate package size."""
    print("\n💾 Estimating package size...")

    total_size = 0
    file_count = 0

    for pattern in ["**/*.py", "**/*.md", "**/*.txt"]:
        for file in root.glob(pattern):
            if "test" not in str(file) and ".egg" not in str(file):
                total_size += file.stat().st_size
                file_count += 1

    print(f"  📊 Estimated size: ~{total_size / 1024:.1f} KB")
    print(f"  📄 Files included: ~{file_count}")

    if total_size > 1024 * 1024:
        print("  ⚠️  Package is larger than 1MB")


def main():
    """Main verification function."""
    root = Path("/home/dsanker/uapk-gateway/sdks/python")

    print("=" * 70)
    print("UAPK Gateway SDK - PyPI Package Verification")
    print("=" * 70)

    checks = []

    # Check required files
    print("\n📁 Required Files:")
    checks.append(check_file_exists(root / "pyproject.toml", "Build config"))
    checks.append(check_file_exists(root / "README.md", "README"))
    checks.append(check_file_exists(root / "LICENSE", "License"))
    checks.append(check_file_exists(root / "CHANGELOG.md", "Changelog"))
    checks.append(check_file_exists(root / "MANIFEST.in", "Manifest"))
    check_file_exists(root / "setup.py", "Setup script (optional)")

    # Detailed checks
    checks.append(check_pyproject_toml(root / "pyproject.toml"))
    checks.append(check_readme(root / "README.md"))
    checks.append(check_package_structure(root))
    checks.append(check_version_consistency(root))
    checks.append(check_dependencies(root))
    checks.append(check_classifiers(root))

    # Estimate size
    estimate_package_size(root)

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    if all(checks):
        print("✅ All checks passed!")
        print("\n📦 Package is ready for PyPI distribution")
        print("\n💡 Next steps:")
        print("   1. Build: python -m build")
        print("   2. Check: twine check dist/*")
        print("   3. Test upload: twine upload --repository testpypi dist/*")
        print("   4. Production upload: twine upload dist/*")
        return 0
    else:
        print("❌ Some checks failed")
        print("\n⚠️  Fix the issues above before publishing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
