#!/usr/bin/env python3
"""
Minimal tests that run without external dependencies.
Tests basic logic and file structure.
"""
import json
import hashlib
from pathlib import Path


def test_manifest_file_exists():
    """Test that manifest file exists and is valid JSON"""
    manifest_path = Path("manifests/opspilotos.uapk.jsonld")
    assert manifest_path.exists(), "Manifest file not found"

    with open(manifest_path) as f:
        data = json.load(f)

    assert data["name"] == "OpsPilotOS"
    assert data["executionMode"] == "dry_run"
    assert "@context" in data
    print("✓ Manifest file is valid JSON-LD")


def test_manifest_structure():
    """Test manifest has required sections"""
    manifest_path = Path("manifests/opspilotos.uapk.jsonld")
    with open(manifest_path) as f:
        data = json.load(f)

    required_sections = [
        "corporateModules",
        "aiOsModules",
        "saasModules",
        "connectors"
    ]

    for section in required_sections:
        assert section in data, f"Missing section: {section}"

    print("✓ Manifest has all required sections")


def test_manifest_agents_defined():
    """Test that agents are defined in manifest"""
    manifest_path = Path("manifests/opspilotos.uapk.jsonld")
    with open(manifest_path) as f:
        data = json.load(f)

    agents = data["aiOsModules"]["agentProfiles"]
    assert len(agents) >= 7, f"Expected at least 7 agents, found {len(agents)}"

    agent_ids = [agent["agentId"] for agent in agents]
    expected_agents = ["intake-agent", "fulfillment-agent", "billing-agent", "tax-agent"]

    for expected in expected_agents:
        assert expected in agent_ids, f"Missing agent: {expected}"

    print(f"✓ Found {len(agents)} agents defined")


def test_manifest_workflows_defined():
    """Test that workflows are defined"""
    manifest_path = Path("manifests/opspilotos.uapk.jsonld")
    with open(manifest_path) as f:
        data = json.load(f)

    workflows = data["aiOsModules"]["workflows"]
    assert len(workflows) >= 4, f"Expected at least 4 workflows, found {len(workflows)}"

    workflow_ids = [wf["workflowId"] for wf in workflows]
    expected_workflows = ["deliverable_fulfillment_pipeline", "subscription_renewal_pipeline"]

    for expected in expected_workflows:
        assert expected in workflow_ids, f"Missing workflow: {expected}"

    print(f"✓ Found {len(workflows)} workflows defined")


def test_vat_rates_configured():
    """Test that VAT rates are configured"""
    manifest_path = Path("manifests/opspilotos.uapk.jsonld")
    with open(manifest_path) as f:
        data = json.load(f)

    vat_rules = data["corporateModules"]["taxOps"]["vatRules"]
    vat_rates = vat_rules["vat_rates"]

    # Check some key countries
    assert "DE" in vat_rates, "Germany VAT rate missing"
    assert "FR" in vat_rates, "France VAT rate missing"
    assert "US" in vat_rates, "US rate missing"

    assert vat_rates["DE"] == 0.19, "Germany VAT should be 19%"
    assert vat_rates["FR"] == 0.20, "France VAT should be 20%"
    assert vat_rates["US"] == 0.0, "US should have 0% VAT"

    print("✓ VAT rates configured correctly")


def test_hash_computation():
    """Test SHA-256 hash computation works"""
    test_data = b"Hello, World!"
    hash1 = hashlib.sha256(test_data).hexdigest()
    hash2 = hashlib.sha256(test_data).hexdigest()

    assert hash1 == hash2, "Hash should be deterministic"
    assert len(hash1) == 64, "SHA-256 hash should be 64 hex characters"

    print("✓ Hash computation works")


def test_source_files_exist():
    """Test that core source files exist"""
    required_files = [
        "uapk/cli.py",
        "uapk/manifest_schema.py",
        "uapk/interpreter.py",
        "uapk/policy.py",
        "uapk/audit.py",
        "uapk/tax.py",
        "uapk/cas.py",
        "uapk/api/main.py",
        "uapk/db/models.py",
        "uapk/agents/base.py",
        "uapk/agents/fulfillment.py",
        "uapk/agents/billing.py",
        "uapk/workflows/engine.py",
        "uapk/nft/minter.py",
    ]

    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)

    assert len(missing) == 0, f"Missing files: {missing}"
    print(f"✓ All {len(required_files)} core source files exist")


def test_fixtures_exist():
    """Test that fixture files exist"""
    required_fixtures = [
        "fixtures/kb/cloud_architecture_best_practices.md",
        "fixtures/kb/saas_pricing_strategies.md",
        "fixtures/deliverable_requests/sample_request.json",
    ]

    for fixture in required_fixtures:
        assert Path(fixture).exists(), f"Missing fixture: {fixture}"

    print(f"✓ All {len(required_fixtures)} fixtures exist")


def test_scripts_exist_and_executable():
    """Test that scripts exist"""
    scripts = [
        "scripts/bootstrap_demo.sh",
        "scripts/run_e2e_demo.sh",
    ]

    for script in scripts:
        path = Path(script)
        assert path.exists(), f"Missing script: {script}"
        assert path.stat().st_mode & 0o111, f"Script not executable: {script}"

    print(f"✓ All {len(scripts)} scripts exist and are executable")


def test_documentation_exists():
    """Test that documentation exists"""
    docs = [
        "README_OPSPILOTOS.md",
        "OPSPILOTOS_QUICKSTART.md",
    ]

    for doc in docs:
        assert Path(doc).exists(), f"Missing documentation: {doc}"

    print(f"✓ All {len(docs)} documentation files exist")


def run_all_tests():
    """Run all tests"""
    tests = [
        test_manifest_file_exists,
        test_manifest_structure,
        test_manifest_agents_defined,
        test_manifest_workflows_defined,
        test_vat_rates_configured,
        test_hash_computation,
        test_source_files_exist,
        test_fixtures_exist,
        test_scripts_exist_and_executable,
        test_documentation_exists,
    ]

    passed = 0
    failed = 0

    print("=" * 70)
    print("OpsPilotOS Minimal Test Suite")
    print("=" * 70)
    print()

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
