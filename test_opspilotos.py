"""
OpsPilotOS Test Suite
Tests core functionality: manifest verification, VAT calculation, audit log, policy enforcement.
"""
import pytest
import json
from pathlib import Path

from uapk.interpreter import verify_manifest, ManifestInterpreter
from uapk.tax import TaxCalculator
from uapk.manifest_schema import TaxOpsModule
from uapk.audit import AuditLog
from uapk.cas import ContentAddressedStore, compute_merkle_root
from uapk.policy import PolicyEngine
from uapk.manifest_schema import UAPKManifest


class TestManifestVerification:
    """Test manifest loading and verification"""

    def test_manifest_loads_successfully(self):
        """Test that the manifest can be loaded and validated"""
        result = verify_manifest("manifests/opspilotos.uapk.jsonld")
        assert result['valid'] == True
        assert 'manifestHash' in result
        assert 'planHash' in result
        assert result['executionMode'] == 'dry_run'

    def test_manifest_hash_deterministic(self):
        """Test that manifest hash is deterministic"""
        result1 = verify_manifest("manifests/opspilotos.uapk.jsonld")
        result2 = verify_manifest("manifests/opspilotos.uapk.jsonld")
        assert result1['manifestHash'] == result2['manifestHash']

    def test_plan_resolution_deterministic(self):
        """Test that plan resolution is deterministic"""
        result1 = verify_manifest("manifests/opspilotos.uapk.jsonld")
        result2 = verify_manifest("manifests/opspilotos.uapk.jsonld")
        assert result1['planHash'] == result2['planHash']

    def test_plan_lock_created(self):
        """Test that plan.lock.json is created"""
        verify_manifest("manifests/opspilotos.uapk.jsonld")
        lock_path = Path("runtime/plan.lock.json")
        assert lock_path.exists()

        # Check it's valid JSON
        plan = json.loads(lock_path.read_text())
        assert 'manifestHash' in plan
        assert 'planHash' in plan


class TestVATCalculation:
    """Test VAT calculation logic"""

    @pytest.fixture
    def tax_calculator(self):
        """Create tax calculator from manifest"""
        interpreter = ManifestInterpreter("manifests/opspilotos.uapk.jsonld")
        manifest = interpreter.load()
        return TaxCalculator(manifest.corporateModules.taxOps)

    def test_eu_b2b_reverse_charge(self, tax_calculator):
        """Test EU B2B with valid VAT ID applies reverse charge"""
        result = tax_calculator.calculate_vat(
            amount=100.0,
            customer_country="DE",
            customer_vat_id="DE123456789",
            is_business=True
        )

        assert result.subtotal == 100.0
        assert result.vat_rate == 0.0
        assert result.vat_amount == 0.0
        assert result.total == 100.0
        assert result.reverse_charge == True
        assert "reverse charge" in result.reason.lower()

    def test_eu_b2c_applies_vat(self, tax_calculator):
        """Test EU B2C applies VAT"""
        result = tax_calculator.calculate_vat(
            amount=100.0,
            customer_country="DE",
            customer_vat_id=None,
            is_business=False
        )

        assert result.subtotal == 100.0
        assert result.vat_rate == 0.19  # 19% for DE
        assert result.vat_amount == 19.0
        assert result.total == 119.0
        assert result.reverse_charge == False

    def test_non_eu_no_vat(self, tax_calculator):
        """Test non-EU customer has no VAT"""
        result = tax_calculator.calculate_vat(
            amount=100.0,
            customer_country="US",
            customer_vat_id=None,
            is_business=False
        )

        assert result.subtotal == 100.0
        assert result.vat_rate == 0.0
        assert result.vat_amount == 0.0
        assert result.total == 100.0
        assert result.reverse_charge == False

    def test_different_vat_rates(self, tax_calculator):
        """Test different EU countries have correct VAT rates"""
        countries_and_rates = [
            ("DE", 0.19),
            ("FR", 0.20),
            ("GB", 0.20),
            ("NL", 0.21),
        ]

        for country, expected_rate in countries_and_rates:
            result = tax_calculator.calculate_vat(
                amount=100.0,
                customer_country=country,
                is_business=False
            )
            assert result.vat_rate == expected_rate, f"Wrong VAT rate for {country}"


class TestAuditLog:
    """Test tamper-evident audit log"""

    def test_audit_log_hash_chain(self, tmp_path):
        """Test that audit log creates valid hash chain"""
        log_path = tmp_path / "test_audit.jsonl"
        audit = AuditLog(str(log_path))

        # Add events
        event1 = audit.append_event("test", "action1", params={"key": "value1"})
        event2 = audit.append_event("test", "action2", params={"key": "value2"})
        event3 = audit.append_event("test", "action3", params={"key": "value3"})

        # Verify chain
        assert event1['previousHash'] == ''
        assert event2['previousHash'] == event1['eventHash']
        assert event3['previousHash'] == event2['eventHash']

    def test_audit_log_verification(self, tmp_path):
        """Test audit log verification"""
        log_path = tmp_path / "test_audit.jsonl"
        audit = AuditLog(str(log_path))

        # Add events
        for i in range(10):
            audit.append_event("test", f"action{i}", params={"index": i})

        # Verify
        result = audit.verify_chain()
        assert result['valid'] == True
        assert result['eventCount'] == 10

    def test_merkle_root_computation(self, tmp_path):
        """Test merkle root computation"""
        log_path = tmp_path / "test_audit.jsonl"
        audit = AuditLog(str(log_path))

        # Add events
        audit.append_event("test", "action1")
        audit.append_event("test", "action2")

        # Compute merkle root
        merkle_root = audit.compute_merkle_root()
        assert merkle_root != ""
        assert len(merkle_root) == 64  # SHA-256 hex


class TestContentAddressedStorage:
    """Test content-addressed storage"""

    def test_cas_put_get(self, tmp_path):
        """Test basic CAS put and get"""
        cas = ContentAddressedStore(str(tmp_path / "cas"))

        content = b"Hello, World!"
        hash1 = cas.put(content)

        retrieved = cas.get(hash1)
        assert retrieved == content

    def test_cas_idempotent(self, tmp_path):
        """Test that CAS is idempotent"""
        cas = ContentAddressedStore(str(tmp_path / "cas"))

        content = b"Test content"
        hash1 = cas.put(content)
        hash2 = cas.put(content)

        assert hash1 == hash2

    def test_cas_json(self, tmp_path):
        """Test JSON storage in CAS"""
        cas = ContentAddressedStore(str(tmp_path / "cas"))

        data = {"key": "value", "number": 42}
        hash1 = cas.put_json(data)

        retrieved = cas.get_json(hash1)
        assert retrieved == data

    def test_merkle_root(self):
        """Test merkle root computation"""
        hashes = [
            "abc123",
            "def456",
            "ghi789"
        ]

        root1 = compute_merkle_root(hashes)
        root2 = compute_merkle_root(hashes)

        assert root1 == root2
        assert len(root1) == 64  # SHA-256 hex


class TestPolicyEngine:
    """Test policy enforcement"""

    @pytest.fixture
    def manifest(self):
        """Load manifest"""
        interpreter = ManifestInterpreter("manifests/opspilotos.uapk.jsonld")
        return interpreter.load()

    @pytest.fixture
    def policy_engine(self, manifest):
        """Create policy engine"""
        return PolicyEngine(manifest)

    def test_tool_permission_allowed(self, policy_engine):
        """Test that allowed tool passes policy check"""
        result = policy_engine.evaluate(
            agent_id="FulfillmentAgent",
            action="generate_content",
            tool="generate_content"
        )
        assert result.decision == "ALLOW"

    def test_tool_permission_denied(self, policy_engine):
        """Test that disallowed tool is denied"""
        result = policy_engine.evaluate(
            agent_id="FulfillmentAgent",
            action="delete_user",
            tool="delete_user"
        )
        assert result.decision == "DENY"

    def test_live_action_gate_dry_run(self, policy_engine):
        """Test that live action requires approval in dry_run"""
        result = policy_engine.evaluate(
            agent_id=None,
            action="mint_nft"
        )
        assert result.decision == "ESCALATE"
        assert result.requires_approval == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
