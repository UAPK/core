"""
Tests for Audit Export (M2.5)
"""
import json
import pytest
import tarfile
from pathlib import Path
from uapk.audit_export import create_audit_bundle, extract_and_verify_bundle


class TestAuditExport:
    """Test M2.5: Evidence-Grade Audit Exports"""

    def test_create_audit_bundle(self):
        """Test creating audit export bundle"""
        # Create bundle (will use existing audit log if available)
        bundle_path = create_audit_bundle(
            audit_log_path="runtime/audit.jsonl",
            output_dir="/tmp"
        )

        assert bundle_path.exists()
        assert bundle_path.suffix == ".gz"
        assert "audit_bundle" in bundle_path.name

        # Clean up
        bundle_path.unlink()

    def test_bundle_contains_required_files(self):
        """Test bundle contains all required files"""
        bundle_path = create_audit_bundle(output_dir="/tmp")

        # Extract and check contents
        with tarfile.open(bundle_path, "r:gz") as tar:
            names = tar.getnames()

            assert "audit.jsonl" in names
            assert "manifest.json" in names
            assert "verification_proof.json" in names

        # Clean up
        bundle_path.unlink()

    def test_verification_proof_structure(self):
        """Test verification proof has correct structure"""
        bundle_path = create_audit_bundle(output_dir="/tmp")

        # Extract and check verification proof
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall("/tmp/audit_test")

        with open("/tmp/audit_test/verification_proof.json", 'r') as f:
            proof = json.load(f)

        # Check required fields
        assert "bundle_created_at" in proof
        assert "audit_log_range" in proof
        assert "hash_chain" in proof
        assert "signatures" in proof
        assert "manifest" in proof

        # Check hash_chain fields
        hash_chain = proof["hash_chain"]
        assert "merkle_root" in hash_chain
        assert "chain_valid" in hash_chain

        # Check signatures fields
        signatures = proof["signatures"]
        assert "algorithm" in signatures
        assert signatures["algorithm"] == "Ed25519"
        assert "verified_count" in signatures

        # Clean up
        bundle_path.unlink()
        import shutil
        shutil.rmtree("/tmp/audit_test")

    def test_extract_and_verify_bundle(self):
        """Test extracting and verifying bundle"""
        bundle_path = create_audit_bundle(output_dir="/tmp")

        results = extract_and_verify_bundle(bundle_path)

        assert "valid" in results
        assert "extracted_files" in results
        assert "verification" in results

        # Should have extracted 3 files
        assert len(results["extracted_files"]) == 3

        # Clean up
        bundle_path.unlink()

    def test_date_filtering(self):
        """Test date range filtering (basic test)"""
        # Create bundle with date filter
        bundle_path = create_audit_bundle(
            start_date="2026-01-01",
            end_date="2026-12-31",
            output_dir="/tmp"
        )

        assert bundle_path.exists()

        # Clean up
        bundle_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
