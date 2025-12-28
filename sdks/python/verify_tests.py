#!/usr/bin/env python3
"""Verify test suite structure and syntax without running tests."""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set


class TestAnalyzer(ast.NodeVisitor):
    """Analyze test files for structure and completeness."""

    def __init__(self):
        self.test_classes: List[str] = []
        self.test_functions: List[str] = []
        self.fixtures: Set[str] = []
        self.imports: Set[str] = []
        self.async_tests: int = 0

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions."""
        if node.name.startswith("Test"):
            self.test_classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        # Check for test functions
        if node.name.startswith("test_"):
            self.test_functions.append(node.name)

        # Check for fixtures
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "fixture":
                self.fixtures.add(node.name)
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr == "fixture":
                    self.fixtures.add(node.name)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definitions."""
        if node.name.startswith("test_"):
            self.test_functions.append(node.name)
            self.async_tests += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track imports."""
        if node.module:
            try:
                self.imports.add(node.module)
            except AttributeError:
                # Handle case where imports might be list
                if isinstance(self.imports, list):
                    self.imports.append(node.module)
        self.generic_visit(node)


def analyze_test_file(file_path: Path) -> Dict:
    """Analyze a test file and return statistics."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        analyzer = TestAnalyzer()
        analyzer.visit(tree)

        return {
            "file": file_path.name,
            "lines": len(content.splitlines()),
            "test_classes": len(analyzer.test_classes),
            "test_functions": len(analyzer.test_functions),
            "fixtures": len(analyzer.fixtures),
            "async_tests": analyzer.async_tests,
            "imports_uapk": any("uapk_gateway" in imp for imp in analyzer.imports),
            "syntax_valid": True,
            "error": None,
        }
    except SyntaxError as e:
        return {
            "file": file_path.name,
            "syntax_valid": False,
            "error": str(e),
        }
    except Exception as e:
        return {
            "file": file_path.name,
            "syntax_valid": False,
            "error": f"Error: {str(e)}",
        }


def verify_module_structure():
    """Verify the SDK module structure."""
    sdk_root = Path("/home/dsanker/uapk-gateway/sdks/python")

    required_files = [
        "uapk_gateway/__init__.py",
        "uapk_gateway/client.py",
        "uapk_gateway/async_client.py",
        "uapk_gateway/models.py",
        "uapk_gateway/exceptions.py",
        "uapk_gateway/integrations/langchain.py",
    ]

    print("📦 Verifying SDK Module Structure")
    print("=" * 60)

    all_exist = True
    for file_path in required_files:
        full_path = sdk_root / file_path
        exists = full_path.exists()
        status = "✅" if exists else "❌"
        print(f"{status} {file_path}")
        if not exists:
            all_exist = False

    print()
    return all_exist


def verify_test_structure():
    """Verify test file structure."""
    tests_dir = Path("/home/dsanker/uapk-gateway/sdks/python/tests")

    test_files = [
        "conftest.py",
        "test_client.py",
        "test_async_client.py",
        "test_models.py",
        "test_exceptions.py",
        "test_langchain_integration.py",
    ]

    print("\n🧪 Analyzing Test Files")
    print("=" * 60)

    total_stats = {
        "files": 0,
        "lines": 0,
        "test_classes": 0,
        "test_functions": 0,
        "fixtures": 0,
        "async_tests": 0,
    }

    all_valid = True

    for test_file in test_files:
        file_path = tests_dir / test_file

        if not file_path.exists():
            print(f"❌ Missing: {test_file}")
            all_valid = False
            continue

        stats = analyze_test_file(file_path)

        if not stats["syntax_valid"]:
            print(f"❌ {test_file}: SYNTAX ERROR")
            print(f"   {stats.get('error', 'Unknown error')}")
            all_valid = False
            continue

        print(f"\n✅ {stats['file']}")
        print(f"   Lines: {stats['lines']}")
        print(f"   Test classes: {stats['test_classes']}")
        print(f"   Test functions: {stats['test_functions']}")

        if stats.get("fixtures", 0) > 0:
            print(f"   Fixtures: {stats['fixtures']}")

        if stats.get("async_tests", 0) > 0:
            print(f"   Async tests: {stats['async_tests']}")

        # Update totals
        total_stats["files"] += 1
        total_stats["lines"] += stats.get("lines", 0)
        total_stats["test_classes"] += stats.get("test_classes", 0)
        total_stats["test_functions"] += stats.get("test_functions", 0)
        total_stats["fixtures"] += stats.get("fixtures", 0)
        total_stats["async_tests"] += stats.get("async_tests", 0)

    print("\n" + "=" * 60)
    print("📊 Test Suite Summary")
    print("=" * 60)
    print(f"Total test files: {total_stats['files']}")
    print(f"Total lines of test code: {total_stats['lines']:,}")
    print(f"Total test classes: {total_stats['test_classes']}")
    print(f"Total test functions: {total_stats['test_functions']}")
    print(f"Total fixtures: {total_stats['fixtures']}")
    print(f"Total async tests: {total_stats['async_tests']}")

    return all_valid, total_stats


def check_import_structure():
    """Check if modules can be imported (syntax check)."""
    print("\n\n🔍 Verifying Module Imports (Syntax Check)")
    print("=" * 60)

    sdk_root = Path("/home/dsanker/uapk-gateway/sdks/python")
    sys.path.insert(0, str(sdk_root))

    modules_to_check = [
        ("uapk_gateway/client.py", "Sync client"),
        ("uapk_gateway/async_client.py", "Async client"),
        ("uapk_gateway/models.py", "Pydantic models"),
        ("uapk_gateway/exceptions.py", "Exceptions"),
    ]

    all_valid = True

    for module_path, description in modules_to_check:
        file_path = sdk_root / module_path

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Parse to check syntax
            ast.parse(content, filename=str(file_path))
            print(f"✅ {description}: Syntax valid")

        except SyntaxError as e:
            print(f"❌ {description}: SYNTAX ERROR")
            print(f"   Line {e.lineno}: {e.msg}")
            all_valid = False

        except Exception as e:
            print(f"❌ {description}: ERROR - {e}")
            all_valid = False

    return all_valid


def verify_test_coverage_potential():
    """Estimate test coverage potential."""
    print("\n\n📈 Test Coverage Potential")
    print("=" * 60)

    sdk_root = Path("/home/dsanker/uapk-gateway/sdks/python")

    # Count source files
    source_files = {
        "client.py": sdk_root / "uapk_gateway/client.py",
        "async_client.py": sdk_root / "uapk_gateway/async_client.py",
        "models.py": sdk_root / "uapk_gateway/models.py",
        "exceptions.py": sdk_root / "uapk_gateway/exceptions.py",
        "langchain.py": sdk_root / "uapk_gateway/integrations/langchain.py",
    }

    source_lines = 0
    for name, path in source_files.items():
        if path.exists():
            with open(path) as f:
                lines = len([l for l in f.readlines() if l.strip() and not l.strip().startswith("#")])
                print(f"  {name}: ~{lines} lines")
                source_lines += lines

    print(f"\nTotal source code: ~{source_lines} lines")

    return True


def main():
    """Main verification function."""
    print("\n" + "=" * 60)
    print("UAPK Gateway SDK - Test Suite Verification")
    print("=" * 60)

    results = []

    # Verify module structure
    results.append(("Module structure", verify_module_structure()))

    # Verify test structure
    test_valid, test_stats = verify_test_structure()
    results.append(("Test structure", test_valid))

    # Check imports
    results.append(("Module syntax", check_import_structure()))

    # Coverage potential
    results.append(("Coverage analysis", verify_test_coverage_potential()))

    # Final summary
    print("\n\n" + "=" * 60)
    print("✨ Verification Summary")
    print("=" * 60)

    all_passed = True
    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All verification checks passed!")
        print(f"\n📊 Test suite ready with {test_stats['test_functions']} test cases")
        print("\n💡 To run tests when pytest is available:")
        print("   cd sdks/python")
        print("   pip install -e \".[dev,langchain]\"")
        print("   pytest --cov=uapk_gateway --cov-report=html")
        return 0
    else:
        print("\n⚠️  Some verification checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
