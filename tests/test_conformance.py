"""
Conformance Test Suite (M2.3)
Tests UAPK manifest validation against canonical schema.
"""
import json
import pytest
from pathlib import Path
from uapk.manifest_migrations import validate_canonical_manifest


class TestConformanceSuite:
    """M2.3: Conformance Test Suite"""

    def get_valid_manifests(self):
        """Load all valid test manifests"""
        valid_dir = Path("tests/conformance/valid")
        manifests = []
        for manifest_file in sorted(valid_dir.glob("*.json")):
            with open(manifest_file, 'r') as f:
                manifests.append((manifest_file.name, json.load(f)))
        return manifests

    def get_invalid_manifests(self):
        """Load all invalid test manifests"""
        invalid_dir = Path("tests/conformance/invalid")
        manifests = []
        for manifest_file in sorted(invalid_dir.glob("*.json")):
            with open(manifest_file, 'r') as f:
                manifests.append((manifest_file.name, json.load(f)))
        return manifests

    @pytest.mark.parametrize("name,manifest", get_valid_manifests(None))
    def test_valid_manifests_accepted(self, name, manifest):
        """Test that all valid manifests pass validation"""
        valid, errors = validate_canonical_manifest(manifest)

        assert valid is True, f"Valid manifest {name} was rejected: {errors}"
        assert len(errors) == 0, f"Valid manifest {name} had errors: {errors}"

    @pytest.mark.parametrize("name,manifest", get_invalid_manifests(None))
    def test_invalid_manifests_rejected(self, name, manifest):
        """Test that all invalid manifests fail validation"""
        valid, errors = validate_canonical_manifest(manifest)

        assert valid is False, f"Invalid manifest {name} was accepted"
        assert len(errors) > 0, f"Invalid manifest {name} had no error messages"

    def test_conformance_suite_completeness(self):
        """Test that conformance suite has sufficient coverage"""
        valid_manifests = list(Path("tests/conformance/valid").glob("*.json"))
        invalid_manifests = list(Path("tests/conformance/invalid").glob("*.json"))

        # Should have at least 3 valid and 4 invalid test cases
        assert len(valid_manifests) >= 3, f"Only {len(valid_manifests)} valid test cases"
        assert len(invalid_manifests) >= 4, f"Only {len(invalid_manifests)} invalid test cases"

    def test_minimal_manifest_valid(self):
        """Test minimal valid manifest"""
        minimal = {
            "version": "1.0",
            "agent": {
                "id": "test",
                "name": "Test",
                "version": "1.0.0"
            },
            "capabilities": {
                "requested": ["action"]
            }
        }

        valid, errors = validate_canonical_manifest(minimal)
        assert valid is True

    def test_missing_capabilities_invalid(self):
        """Test manifest without capabilities is invalid"""
        no_caps = {
            "version": "1.0",
            "agent": {
                "id": "test",
                "name": "Test",
                "version": "1.0.0"
            }
        }

        valid, errors = validate_canonical_manifest(no_caps)
        assert valid is False
        assert any("capabilities" in err.lower() for err in errors)


def run_conformance_suite():
    """
    Run full conformance test suite and generate report.
    Returns dict with results.
    """
    valid_dir = Path("tests/conformance/valid")
    invalid_dir = Path("tests/conformance/invalid")

    results = {
        "valid_manifests": {"passed": 0, "failed": 0, "total": 0},
        "invalid_manifests": {"passed": 0, "failed": 0, "total": 0},
        "failures": []
    }

    # Test valid manifests
    for manifest_file in sorted(valid_dir.glob("*.json")):
        results["valid_manifests"]["total"] += 1
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        valid, errors = validate_canonical_manifest(manifest)
        if valid:
            results["valid_manifests"]["passed"] += 1
        else:
            results["valid_manifests"]["failed"] += 1
            results["failures"].append({
                "file": str(manifest_file),
                "type": "valid_rejected",
                "errors": errors
            })

    # Test invalid manifests (should be rejected)
    for manifest_file in sorted(invalid_dir.glob("*.json")):
        results["invalid_manifests"]["total"] += 1
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        valid, errors = validate_canonical_manifest(manifest)
        if not valid:  # Should be invalid
            results["invalid_manifests"]["passed"] += 1
        else:
            results["invalid_manifests"]["failed"] += 1
            results["failures"].append({
                "file": str(manifest_file),
                "type": "invalid_accepted",
                "errors": []
            })

    return results


if __name__ == "__main__":
    # Run conformance suite and print report
    results = run_conformance_suite()

    print("=" * 60)
    print("UAPK Conformance Test Suite Results")
    print("=" * 60)

    print(f"\nValid Manifests: {results['valid_manifests']['passed']}/{results['valid_manifests']['total']} PASSED")
    print(f"Invalid Manifests: {results['invalid_manifests']['passed']}/{results['invalid_manifests']['total']} REJECTED (as expected)")

    if results['failures']:
        print(f"\n⚠️  {len(results['failures'])} FAILURES:")
        for failure in results['failures']:
            print(f"  - {failure['file']}: {failure['type']}")
            if failure['errors']:
                for error in failure['errors']:
                    print(f"      {error}")
        exit(1)
    else:
        print("\n✅ All tests PASSED")
        exit(0)
