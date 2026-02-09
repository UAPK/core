"""
Tests for Ed25519 Override Token Flow (M1.1)
"""
import pytest
import time
from datetime import datetime, timedelta
from uapk.core.ed25519_token import (
    create_override_token,
    verify_override_token,
    compute_action_hash,
    hash_override_token
)
from uapk.core.ed25519_keys import generate_ed25519_keypair
import json

# Skip database tests if SQLModel not available (lightweight testing)
try:
    from sqlmodel import Session, create_engine, SQLModel
    from uapk.policy import PolicyEngine
    from uapk.manifest_schema import UAPKManifest
    from uapk.db.models import HITLRequest
    SQLMODEL_AVAILABLE = True
except ImportError:
    SQLMODEL_AVAILABLE = False


class TestOverrideTokenCreation:
    """Test override token creation and signing"""

    def test_create_override_token_format(self):
        """Test override token has correct format (header.payload.signature)"""
        token = create_override_token(
            approval_id=123,
            action="mint_nft",
            params={"force": True},
            expiry_minutes=5
        )

        # Token should have 3 parts separated by dots
        parts = token.split('.')
        assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}"

        # Parts should be base64-encoded (no padding required in URL-safe base64)
        header, payload, signature = parts
        assert len(header) > 0
        assert len(payload) > 0
        assert len(signature) > 0

    def test_override_token_payload(self):
        """Test override token payload contains required fields"""
        import base64

        token = create_override_token(
            approval_id=456,
            action="send_invoice",
            params={"invoice_id": 789},
            expiry_minutes=5
        )

        # Decode payload (second part)
        payload_b64 = token.split('.')[1]
        # Add padding if needed
        payload_json = base64.urlsafe_b64decode(payload_b64 + '==')
        payload = json.loads(payload_json)

        # Verify payload structure
        assert "approval_id" in payload
        assert payload["approval_id"] == 456
        assert "action_hash" in payload
        assert "iat" in payload
        assert "exp" in payload

        # Verify expiry is ~5 minutes from now
        now = datetime.utcnow()
        exp = datetime.fromtimestamp(payload['exp'])
        delta = (exp - now).total_seconds()
        assert 290 <= delta <= 310, f"Expected ~300s expiry, got {delta}s"

    def test_action_hash_deterministic(self):
        """Test action hash is deterministic (same action+params → same hash)"""
        action = "test_action"
        params = {"key": "value", "number": 123}

        hash1 = compute_action_hash(action, params)
        hash2 = compute_action_hash(action, params)

        assert hash1 == hash2, "Action hash should be deterministic"

        # Different params → different hash
        hash3 = compute_action_hash(action, {"key": "different"})
        assert hash1 != hash3, "Different params should produce different hash"


class TestOverrideTokenVerification:
    """Test override token verification logic"""

    def test_verify_valid_token(self):
        """Test verification succeeds for valid token"""
        action = "mint_nft"
        params = {"force": True}

        token = create_override_token(
            approval_id=1,
            action=action,
            params=params,
            expiry_minutes=5
        )

        valid, reason, payload = verify_override_token(token, action, params)

        assert valid is True, f"Token should be valid, got: {reason}"
        assert payload is not None
        assert payload['approval_id'] == 1

    def test_verify_expired_token(self):
        """Test verification fails for expired token"""
        action = "test_action"
        params = {}

        # Create token with 0 minute expiry (will be expired immediately)
        token = create_override_token(
            approval_id=2,
            action=action,
            params=params,
            expiry_minutes=0
        )

        # Wait a moment to ensure expiry
        time.sleep(0.1)

        valid, reason, payload = verify_override_token(token, action, params)

        assert valid is False, "Expired token should be rejected"
        assert "expired" in reason.lower()

    def test_verify_wrong_action(self):
        """Test verification fails when action doesn't match"""
        action1 = "action_one"
        action2 = "action_two"
        params = {}

        token = create_override_token(
            approval_id=3,
            action=action1,
            params=params,
            expiry_minutes=5
        )

        # Try to use token for different action
        valid, reason, payload = verify_override_token(token, action2, params)

        assert valid is False, "Token should not work for different action"
        assert "action_hash mismatch" in reason.lower()

    def test_verify_wrong_params(self):
        """Test verification fails when params don't match"""
        action = "test_action"
        params1 = {"key": "value1"}
        params2 = {"key": "value2"}

        token = create_override_token(
            approval_id=4,
            action=action,
            params=params1,
            expiry_minutes=5
        )

        # Try to use token with different params
        valid, reason, payload = verify_override_token(token, action, params2)

        assert valid is False, "Token should not work for different params"
        assert "action_hash mismatch" in reason.lower()

    def test_verify_tampered_token(self):
        """Test verification fails for tampered token"""
        action = "test_action"
        params = {}

        token = create_override_token(
            approval_id=5,
            action=action,
            params=params,
            expiry_minutes=5
        )

        # Tamper with payload (change a character)
        parts = token.split('.')
        tampered_payload = parts[1][:-1] + ('x' if parts[1][-1] != 'x' else 'y')
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        valid, reason, payload = verify_override_token(tampered_token, action, params)

        assert valid is False, "Tampered token should be rejected"
        # Will fail on signature or JSON decode

    def test_verify_invalid_signature(self):
        """Test verification fails with invalid signature"""
        action = "test_action"
        params = {}

        token = create_override_token(
            approval_id=6,
            action=action,
            params=params,
            expiry_minutes=5
        )

        # Replace signature with garbage
        parts = token.split('.')
        fake_token = f"{parts[0]}.{parts[1]}.invalidSignature"

        valid, reason, payload = verify_override_token(fake_token, action, params)

        assert valid is False, "Invalid signature should be rejected"


@pytest.mark.skipif(not SQLMODEL_AVAILABLE, reason="SQLModel not installed")
class TestPolicyEngineOverrideTokens:
    """Test PolicyEngine integration with override tokens (requires SQLModel)"""

    @pytest.fixture
    def manifest(self):
        """Create test manifest"""
        manifest_json = {
            "@context": "https://uapk.ai/context/v0.1",
            "@id": "urn:uapk:test:v1",
            "uapkVersion": "0.1",
            "name": "TestManifest",
            "description": "Test",
            "executionMode": "dry_run",
            "cryptoHeader": {},
            "corporateModules": {
                "governance": {"roles": [], "approvalWorkflow": {}},
                "policyGuardrails": {
                    "toolPermissions": {},
                    "denyRules": [],
                    "rateLimits": {"actionsPerMinute": 100},
                    "liveActionGates": ["mint_nft", "send_invoice"]
                }
            },
            "aiOsModules": {"agentProfiles": [], "modelRegistry": {}, "promptTemplates": {}},
            "saasModules": {"subscriptionPlans": [], "connectors": {}},
            "workflows": []
        }
        return UAPKManifest(**manifest_json)

    @pytest.fixture
    def session(self):
        """Create in-memory database session for testing"""
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    def test_override_token_allows_gated_action(self, manifest, session):
        """Test override token allows gated action that would otherwise require approval"""
        engine = PolicyEngine(manifest)

        action = "mint_nft"
        params = {"force": True}

        # Create HITL request in database
        hitl = HITLRequest(
            org_id=1,
            action=action,
            params=params,
            reason="Test approval",
            status="approved",
            approved_by=1,
            approved_at=datetime.utcnow()
        )
        session.add(hitl)
        session.commit()
        session.refresh(hitl)

        # Generate override token
        token = create_override_token(
            approval_id=hitl.id,
            action=action,
            params=params,
            expiry_minutes=5
        )

        # Update HITLRequest with token hash
        hitl.override_token_hash = hash_override_token(token)
        session.add(hitl)
        session.commit()

        # Evaluate with override token (should ALLOW, not ESCALATE)
        result = engine.evaluate(
            agent_id=None,
            action=action,
            params=params,
            override_token=token,
            session=session
        )

        assert result.decision == "ALLOW", f"Expected ALLOW with override token, got {result.decision}"
        assert any("Override token valid" in r for r in result.reasons)

    def test_consumed_override_token_rejected(self, manifest, session):
        """Test override token can only be used once"""
        engine = PolicyEngine(manifest)

        action = "mint_nft"
        params = {}

        # Create and approve HITL request
        hitl = HITLRequest(
            org_id=1,
            action=action,
            params=params,
            reason="Test",
            status="approved"
        )
        session.add(hitl)
        session.commit()
        session.refresh(hitl)

        token = create_override_token(hitl.id, action, params, expiry_minutes=5)
        hitl.override_token_hash = hash_override_token(token)
        session.add(hitl)
        session.commit()

        # First use: should succeed
        result1 = engine.evaluate(
            agent_id=None,
            action=action,
            params=params,
            override_token=token,
            session=session
        )
        assert result1.decision == "ALLOW"

        # Second use: should fail (already consumed)
        result2 = engine.evaluate(
            agent_id=None,
            action=action,
            params=params,
            override_token=token,
            session=session
        )
        assert result2.decision == "DENY"
        assert any("already consumed" in r.lower() for r in result2.reasons)

    def test_gated_action_without_override_token_escalates(self, manifest):
        """Test that gated action without override token still requires approval"""
        engine = PolicyEngine(manifest)

        action = "mint_nft"
        params = {}

        # No override token provided
        result = engine.evaluate(
            agent_id=None,
            action=action,
            params=params,
            override_token=None
        )

        assert result.decision == "ESCALATE", f"Expected ESCALATE for gated action, got {result.decision}"
        assert result.requires_approval is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
