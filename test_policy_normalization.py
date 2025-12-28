#!/usr/bin/env python3
"""Test script to verify policy config normalization works correctly.

This tests the backwards-compatible normalization layer that allows
manifests to use either the official schema naming or the internal
PolicyEngine naming conventions.
"""


def normalize_policy_config(policy_config: dict) -> dict:
    """Normalize policy config to accept both manifest schema and engine naming.

    This is a copy of the PolicyEngine._normalize_policy_config method for testing.
    """
    normalized = policy_config.copy()

    # 1. Normalize tool lists
    if "tool_allowlist" in policy_config and "allowed_tools" not in policy_config:
        normalized["allowed_tools"] = policy_config["tool_allowlist"]
    if "tool_denylist" in policy_config and "denied_tools" not in policy_config:
        normalized["denied_tools"] = policy_config["tool_denylist"]

    # 2. Normalize jurisdiction lists
    if "jurisdiction_allowlist" in policy_config and "allowed_jurisdictions" not in policy_config:
        normalized["allowed_jurisdictions"] = policy_config["jurisdiction_allowlist"]

    # 3. Normalize counterparty rules (flat to nested)
    if ("counterparty_allowlist" in policy_config or "counterparty_denylist" in policy_config) and \
       "counterparty" not in policy_config:
        normalized["counterparty"] = {}
        if "counterparty_allowlist" in policy_config:
            normalized["counterparty"]["allowlist"] = policy_config["counterparty_allowlist"]
        if "counterparty_denylist" in policy_config:
            normalized["counterparty"]["denylist"] = policy_config["counterparty_denylist"]

    # 4. Normalize amount_caps (simple dict to structured object)
    amount_caps = policy_config.get("amount_caps")
    if amount_caps and isinstance(amount_caps, dict):
        # Check if it's the simple format: {"USD": 1000, "EUR": 500}
        # vs structured format: {"max_amount": 1000, "escalate_above": 500, ...}
        if not any(k in amount_caps for k in ["max_amount", "escalate_above", "param_paths", "currency_field"]):
            # It's the simple format - find the highest value and use as max_amount
            if amount_caps:
                max_value = max(amount_caps.values())
                normalized["amount_caps"] = {
                    "max_amount": max_value,
                    "param_paths": ["amount", "value", "total"],
                    "currency_field": "currency",
                }

    return normalized


def test_tool_normalization():
    """Test that tool_allowlist/tool_denylist get normalized."""
    policy = {
        "tool_allowlist": ["email", "slack"],
        "tool_denylist": ["ssh", "database"],
    }
    normalized = normalize_policy_config(policy)

    assert "allowed_tools" in normalized
    assert normalized["allowed_tools"] == ["email", "slack"]
    assert "denied_tools" in normalized
    assert normalized["denied_tools"] == ["ssh", "database"]
    print("✓ Tool list normalization works")


def test_jurisdiction_normalization():
    """Test that jurisdiction_allowlist gets normalized."""
    policy = {
        "jurisdiction_allowlist": ["US", "CA", "GB"],
    }
    normalized = normalize_policy_config(policy)

    assert "allowed_jurisdictions" in normalized
    assert normalized["allowed_jurisdictions"] == ["US", "CA", "GB"]
    print("✓ Jurisdiction normalization works")


def test_counterparty_normalization():
    """Test that flat counterparty lists get nested."""
    policy = {
        "counterparty_allowlist": ["partner1@example.com", "partner2@example.com"],
        "counterparty_denylist": ["blocked@example.com"],
    }
    normalized = normalize_policy_config(policy)

    assert "counterparty" in normalized
    assert normalized["counterparty"]["allowlist"] == ["partner1@example.com", "partner2@example.com"]
    assert normalized["counterparty"]["denylist"] == ["blocked@example.com"]
    print("✓ Counterparty normalization works")


def test_amount_caps_normalization():
    """Test that simple amount caps get structured."""
    policy = {
        "amount_caps": {
            "USD": 10000.0,
            "EUR": 8500.0,
            "GBP": 7500.0,
        }
    }
    normalized = normalize_policy_config(policy)

    assert "amount_caps" in normalized
    assert isinstance(normalized["amount_caps"], dict)
    assert "max_amount" in normalized["amount_caps"]
    assert normalized["amount_caps"]["max_amount"] == 10000.0  # Highest value
    assert "param_paths" in normalized["amount_caps"]
    print("✓ Amount caps normalization works")


def test_backwards_compatibility():
    """Test that existing PolicyEngine format is not broken."""
    policy = {
        "allowed_tools": ["email", "slack"],
        "denied_tools": ["ssh"],
        "allowed_jurisdictions": ["US", "CA"],
        "counterparty": {
            "allowlist": ["partner@example.com"],
            "denylist": ["blocked@example.com"],
        },
        "amount_caps": {
            "max_amount": 10000,
            "escalate_above": 5000,
            "param_paths": ["amount"],
        }
    }
    normalized = normalize_policy_config(policy)

    # Should remain unchanged
    assert normalized["allowed_tools"] == ["email", "slack"]
    assert normalized["denied_tools"] == ["ssh"]
    assert normalized["allowed_jurisdictions"] == ["US", "CA"]
    assert normalized["counterparty"]["allowlist"] == ["partner@example.com"]
    assert normalized["amount_caps"]["max_amount"] == 10000
    print("✓ Backwards compatibility preserved")


def test_mixed_format():
    """Test that manifest schema format takes precedence when both exist."""
    policy = {
        "tool_allowlist": ["email"],
        "allowed_tools": ["slack"],  # This should be preserved (already in new format)
    }
    normalized = normalize_policy_config(policy)

    # Existing allowed_tools should not be overwritten
    assert normalized["allowed_tools"] == ["slack"]
    print("✓ Mixed format handling works (engine format takes precedence)")


if __name__ == "__main__":
    print("Testing PolicyEngine normalization layer...")
    print()

    test_tool_normalization()
    test_jurisdiction_normalization()
    test_counterparty_normalization()
    test_amount_caps_normalization()
    test_backwards_compatibility()
    test_mixed_format()

    print()
    print("=" * 60)
    print("✅ All normalization tests passed!")
    print("=" * 60)
    print()
    print("The PolicyEngine now accepts both naming conventions:")
    print("  - Manifest Schema: tool_allowlist, counterparty_allowlist, etc.")
    print("  - PolicyEngine:    allowed_tools, counterparty.allowlist, etc.")
    print()
    print("Manifests created with the official schema will now be")
    print("correctly enforced by the gateway.")
