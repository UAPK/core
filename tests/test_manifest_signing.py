"""
Tests for Manifest Signing (M2.4)
"""
import json
import pytest
from pathlib import Path
import tempfile
from uapk.manifest_signing import (
    compute_manifest_hash,
    sign_manifest,
    verify_manifest_signature,
    keygen
)


class TestManifestSigning:
    """Test M2.4: Manifest Signing and Verification"""

    @pytest.fixture
    def temp_keys(self):
        """Generate temporary keypair for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            private_path, public_path = keygen(temp_dir)
            yield private_path, public_path

    @pytest.fixture
    def sample_manifest(self):
        """Sample manifest for testing"""
        return {
            "version": "1.0",
            "agent": {
                "id": "test-agent",
                "name": "Test Agent",
                "version": "1.0.0"
            },
            "capabilities": {
                "requested": ["test_action"]
            }
        }

    def test_keygen_creates_keypair(self):
        """Test keypair generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            private_path, public_path = keygen(output_dir)

            assert private_path.exists()
            assert public_path.exists()
            assert private_path.stat().st_mode & 0o777 == 0o600  # Private key has restrictive permissions

    def test_compute_manifest_hash_deterministic(self, sample_manifest):
        """Test manifest hash is deterministic"""
        hash1 = compute_manifest_hash(sample_manifest)
        hash2 = compute_manifest_hash(sample_manifest)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_compute_manifest_hash_ignores_signature(self, sample_manifest):
        """Test hash computation excludes signature fields"""
        manifest_unsigned = sample_manifest.copy()
        manifest_signed = sample_manifest.copy()
        manifest_signed["cryptoHeader"] = {
            "signature": "fake-signature",
            "signedBy": "fake-key",
            "signedAt": "2026-01-01T00:00:00Z"
        }

        hash_unsigned = compute_manifest_hash(manifest_unsigned)
        hash_signed = compute_manifest_hash(manifest_signed)

        # Hashes should be the same (signature excluded)
        assert hash_unsigned == hash_signed

    def test_sign_manifest_adds_signature(self, sample_manifest, temp_keys):
        """Test signing adds cryptoHeader with signature"""
        private_path, _ = temp_keys

        signed = sign_manifest(sample_manifest, private_path)

        assert "cryptoHeader" in signed
        assert "signature" in signed["cryptoHeader"]
        assert "signedBy" in signed["cryptoHeader"]
        assert "signedAt" in signed["cryptoHeader"]

        # Signature should be base64
        signature = signed["cryptoHeader"]["signature"]
        assert len(signature) > 0
        assert signed["cryptoHeader"]["hashAlg"] == "sha256"

    def test_verify_valid_signature(self, sample_manifest, temp_keys):
        """Test verification succeeds for valid signature"""
        private_path, public_path = temp_keys

        # Sign manifest
        signed = sign_manifest(sample_manifest, private_path)

        # Verify signature
        valid, message = verify_manifest_signature(signed, public_path)

        assert valid is True
        assert "valid" in message.lower()

    def test_verify_rejects_tampered_manifest(self, sample_manifest, temp_keys):
        """Test verification fails if manifest is tampered"""
        private_path, public_path = temp_keys

        # Sign manifest
        signed = sign_manifest(sample_manifest, private_path)

        # Tamper with manifest
        signed["agent"]["name"] = "Tampered Agent"

        # Verify signature
        valid, message = verify_manifest_signature(signed, public_path)

        assert valid is False
        assert "invalid" in message.lower()

    def test_verify_rejects_missing_signature(self, sample_manifest, temp_keys):
        """Test verification fails if no signature present"""
        _, public_path = temp_keys

        valid, message = verify_manifest_signature(sample_manifest, public_path)

        assert valid is False
        assert "signature" in message.lower()

    def test_sign_and_verify_roundtrip(self, sample_manifest, temp_keys):
        """Test sign → verify roundtrip"""
        private_path, public_path = temp_keys

        # Sign
        signed = sign_manifest(sample_manifest, private_path)

        # Verify
        valid, _ = verify_manifest_signature(signed, public_path)
        assert valid is True

    def test_verify_with_wrong_key_fails(self, sample_manifest):
        """Test verification fails with wrong public key"""
        with tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:

            # Generate two different keypairs
            dir1 = Path(tmpdir1)
            dir2 = Path(tmpdir2)

            private1, _ = keygen(dir1)
            _, public2 = keygen(dir2)

            # Sign with key1
            signed = sign_manifest(sample_manifest, private1)

            # Try to verify with key2 (wrong key)
            valid, message = verify_manifest_signature(signed, public2)

            assert valid is False
            assert "invalid" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
