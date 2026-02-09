"""
Tests for Manifest Schema Migration (M2.1)
Tests conversion between extended and canonical UAPK manifest formats.
"""
import json
import pytest
from pathlib import Path
from uapk.manifest_migrations import (
    migrate_extended_to_canonical,
    migrate_canonical_to_extended,
    validate_canonical_manifest,
    extract_capabilities_from_extended
)


def load_opspilotos_manifest():
    """Load the OpsPilotOS extended manifest for testing"""
    manifest_path = Path("manifests/opspilotos.uapk.jsonld")
    if not manifest_path.exists():
        pytest.skip("OpsPilotOS manifest not found")
    with open(manifest_path, 'r') as f:
        return json.load(f)


class TestSchemaConvergence:
    """Test M2.1: Schema Convergence"""

    def test_extract_capabilities_from_extended(self):
        """Test capability extraction from extended manifest"""
        extended = load_opspilotos_manifest()
        capabilities = extract_capabilities_from_extended(extended)

        # Should extract capabilities from tool permissions
        assert len(capabilities) > 0
        assert "intakeagent:read_deliverable_requests" in capabilities
        assert "fullfillmentagent:generate_content" in capabilities or "fulfillmentagent:generate_content" in capabilities

        # Should extract from live action gates
        assert "mint_nft" in capabilities
        assert "send_invoice_email" in capabilities

    def test_migrate_extended_to_canonical_structure(self):
        """Test migration produces valid canonical structure"""
        extended = load_opspilotos_manifest()
        canonical = migrate_extended_to_canonical(extended)

        # Check top-level fields
        assert "version" in canonical
        assert canonical["version"] == "1.0"
        assert "agent" in canonical
        assert "capabilities" in canonical
        assert "constraints" in canonical
        assert "metadata" in canonical
        assert "policy" in canonical
        assert "extensions" in canonical

    def test_migrate_extended_to_canonical_agent(self):
        """Test agent section is correctly migrated"""
        extended = load_opspilotos_manifest()
        canonical = migrate_extended_to_canonical(extended)

        agent = canonical["agent"]
        assert "id" in agent
        assert "name" in agent
        assert "version" in agent
        assert "description" in agent
        assert "organization" in agent

        # Check values
        assert agent["name"] == "OpsPilotOS"
        assert agent["version"] == "0.1"
        assert agent["organization"] == "default"

    def test_migrate_extended_to_canonical_capabilities(self):
        """Test capabilities section is correctly migrated"""
        extended = load_opspilotos_manifest()
        canonical = migrate_extended_to_canonical(extended)

        capabilities = canonical["capabilities"]
        assert "requested" in capabilities
        assert isinstance(capabilities["requested"], list)
        assert len(capabilities["requested"]) > 0

        # Check some expected capabilities
        requested = capabilities["requested"]
        assert "mint_nft" in requested
        assert any("billingagent" in cap for cap in requested)

    def test_migrate_extended_to_canonical_constraints(self):
        """Test constraints section is correctly migrated"""
        extended = load_opspilotos_manifest()
        canonical = migrate_extended_to_canonical(extended)

        constraints = canonical["constraints"]
        assert "max_actions_per_hour" in constraints
        assert "require_human_approval" in constraints

        # Check approval gates are preserved
        assert "mint_nft" in constraints["require_human_approval"]
        assert "send_invoice_email" in constraints["require_human_approval"]

    def test_migrate_extended_to_canonical_policy(self):
        """Test policy section is correctly migrated"""
        extended = load_opspilotos_manifest()
        canonical = migrate_extended_to_canonical(extended)

        policy = canonical["policy"]
        assert "budgets" in policy
        assert "approval_thresholds" in policy

        # Check approval thresholds
        thresholds = policy["approval_thresholds"]
        assert "action_types" in thresholds
        assert "mint_nft" in thresholds["action_types"]

    def test_migrate_preserves_extended_in_extensions(self):
        """Test original extended manifest is preserved in extensions"""
        extended = load_opspilotos_manifest()
        canonical = migrate_extended_to_canonical(extended)

        # Check extensions object exists and contains original
        assert "extensions" in canonical
        assert "opspilotos" in canonical["extensions"]

        # Original should be preserved
        original = canonical["extensions"]["opspilotos"]
        assert original["@id"] == extended["@id"]
        assert original["name"] == extended["name"]
        assert "corporateModules" in original
        assert "aiOsModules" in original

    def test_validate_canonical_manifest_success(self):
        """Test validation passes for valid canonical manifest"""
        extended = load_opspilotos_manifest()
        canonical = migrate_extended_to_canonical(extended)

        valid, errors = validate_canonical_manifest(canonical)
        assert valid is True
        assert len(errors) == 0

    def test_validate_canonical_manifest_missing_version(self):
        """Test validation fails for missing version"""
        canonical = {"agent": {}, "capabilities": {}}
        valid, errors = validate_canonical_manifest(canonical)

        assert valid is False
        assert any("version" in error.lower() for error in errors)

    def test_validate_canonical_manifest_invalid_version(self):
        """Test validation fails for invalid version"""
        canonical = {
            "version": "2.0",
            "agent": {"id": "test", "name": "Test", "version": "0.1"},
            "capabilities": {"requested": ["test"]}
        }
        valid, errors = validate_canonical_manifest(canonical)

        assert valid is False
        assert any("version" in error.lower() for error in errors)

    def test_validate_canonical_manifest_missing_agent_fields(self):
        """Test validation fails for missing required agent fields"""
        canonical = {
            "version": "1.0",
            "agent": {"id": "test"},  # Missing name and version
            "capabilities": {"requested": ["test"]}
        }
        valid, errors = validate_canonical_manifest(canonical)

        assert valid is False
        assert any("name" in error.lower() for error in errors)
        assert any("version" in error.lower() for error in errors)

    def test_validate_canonical_manifest_empty_capabilities(self):
        """Test validation fails for empty capabilities list"""
        canonical = {
            "version": "1.0",
            "agent": {"id": "test", "name": "Test", "version": "0.1"},
            "capabilities": {"requested": []}
        }
        valid, errors = validate_canonical_manifest(canonical)

        assert valid is False
        assert any("empty" in error.lower() for error in errors)

    def test_roundtrip_migration(self):
        """Test extended → canonical → extended preserves data"""
        extended = load_opspilotos_manifest()

        # Migrate to canonical
        canonical = migrate_extended_to_canonical(extended)

        # Migrate back to extended
        roundtrip = migrate_canonical_to_extended(canonical)

        # Should get original back (from extensions)
        assert roundtrip["@id"] == extended["@id"]
        assert roundtrip["name"] == extended["name"]
        assert "corporateModules" in roundtrip
        assert "aiOsModules" in roundtrip


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
