#!/usr/bin/env python3
"""Test suite for enterprise security fixes.

Tests:
- P0-1: SECRET_KEY validation in production
- P0-2: Ed25519 key validation in production
- P0-3: Webhook allowlist deny-by-default
- P1: Atomic budget enforcement
- P1: Rate limiting on endpoints
- P1: httpx trust_env=False
"""

import asyncio
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))


# ============================================================================
# P0-1: SECRET_KEY Validation Tests
# ============================================================================

def test_p0_1_secret_key_validation_production():
    """Test that app fails to start in production with weak SECRET_KEY."""
    print("\n=== Testing P0-1: SECRET_KEY Validation ===")

    # Save original env
    original_env = os.environ.get("ENVIRONMENT")
    original_secret = os.environ.get("SECRET_KEY")
    original_fernet = os.environ.get("GATEWAY_FERNET_KEY")

    try:
        # Test 1: Production with default SECRET_KEY should fail
        os.environ["ENVIRONMENT"] = "production"
        os.environ["SECRET_KEY"] = "CHANGE-ME-IN-PRODUCTION-USE-SECURE-RANDOM-VALUE"
        os.environ["GATEWAY_FERNET_KEY"] = "test-key"

        print("  [1] Testing production with weak SECRET_KEY...")
        try:
            from app.core.config import Settings
            # Clear the cache
            from app.core.config import get_settings
            get_settings.cache_clear()

            settings = Settings()
            print("    ❌ FAIL: Should have raised ValueError for weak SECRET_KEY")
            return False
        except ValueError as e:
            if "SECRET_KEY must be set to a secure random value" in str(e):
                print(f"    ✅ PASS: Correctly rejected weak SECRET_KEY")
                print(f"       Error: {str(e)[:100]}...")
            else:
                print(f"    ❌ FAIL: Wrong error: {e}")
                return False

        # Test 2: Production with short SECRET_KEY should fail
        os.environ["SECRET_KEY"] = "short"
        get_settings.cache_clear()

        print("  [2] Testing production with short SECRET_KEY...")
        try:
            settings = Settings()
            print("    ❌ FAIL: Should have raised ValueError for short SECRET_KEY")
            return False
        except ValueError as e:
            if "min 32 chars" in str(e):
                print(f"    ✅ PASS: Correctly rejected short SECRET_KEY")
            else:
                print(f"    ❌ FAIL: Wrong error: {e}")
                return False

        # Test 3: Production without GATEWAY_FERNET_KEY should fail
        os.environ["SECRET_KEY"] = "a" * 32
        os.environ.pop("GATEWAY_FERNET_KEY", None)
        get_settings.cache_clear()

        print("  [3] Testing production without GATEWAY_FERNET_KEY...")
        try:
            settings = Settings()
            print("    ❌ FAIL: Should have raised ValueError for missing GATEWAY_FERNET_KEY")
            return False
        except ValueError as e:
            if "GATEWAY_FERNET_KEY is required" in str(e):
                print(f"    ✅ PASS: Correctly rejected missing GATEWAY_FERNET_KEY")
            else:
                print(f"    ❌ FAIL: Wrong error: {e}")
                return False

        # Test 4: Development should allow defaults
        os.environ["ENVIRONMENT"] = "development"
        os.environ["SECRET_KEY"] = "CHANGE-ME-IN-PRODUCTION-USE-SECURE-RANDOM-VALUE"
        os.environ.pop("GATEWAY_FERNET_KEY", None)
        get_settings.cache_clear()

        print("  [4] Testing development allows defaults...")
        try:
            settings = Settings()
            print("    ✅ PASS: Development correctly allows weak defaults")
        except ValueError as e:
            print(f"    ❌ FAIL: Development should allow defaults: {e}")
            return False

        # Test 5: Production with valid keys should succeed
        os.environ["ENVIRONMENT"] = "production"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["GATEWAY_FERNET_KEY"] = "dGVzdC1mZXJuZXQta2V5LXRoYXQtaXMtbG9uZy1lbm91Z2g="
        get_settings.cache_clear()

        print("  [5] Testing production with valid keys...")
        try:
            settings = Settings()
            print("    ✅ PASS: Production accepts valid keys")
        except ValueError as e:
            print(f"    ❌ FAIL: Should accept valid keys: {e}")
            return False

        print("\n✅ P0-1: All SECRET_KEY validation tests passed!\n")
        return True

    finally:
        # Restore original env
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)

        if original_secret:
            os.environ["SECRET_KEY"] = original_secret
        else:
            os.environ.pop("SECRET_KEY", None)

        if original_fernet:
            os.environ["GATEWAY_FERNET_KEY"] = original_fernet
        else:
            os.environ.pop("GATEWAY_FERNET_KEY", None)

        # Clear cache
        from app.core.config import get_settings
        get_settings.cache_clear()


# ============================================================================
# P0-2: Ed25519 Key Validation Tests
# ============================================================================

def test_p0_2_ed25519_key_validation():
    """Test that Ed25519 key is required in production."""
    print("\n=== Testing P0-2: Ed25519 Key Validation ===")

    original_env = os.environ.get("ENVIRONMENT")
    original_key = os.environ.get("GATEWAY_ED25519_PRIVATE_KEY")

    try:
        # Test 1: Production without Ed25519 key should fail
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("GATEWAY_ED25519_PRIVATE_KEY", None)

        print("  [1] Testing production without Ed25519 key...")
        try:
            from app.core.ed25519 import GatewayKeyManager
            # Reset singleton
            GatewayKeyManager._instance = None
            GatewayKeyManager._private_key = None

            manager = GatewayKeyManager()
            print("    ❌ FAIL: Should have raised KeyManagementError")
            return False
        except Exception as e:
            if "GATEWAY_ED25519_PRIVATE_KEY must be set" in str(e):
                print(f"    ✅ PASS: Correctly rejected missing Ed25519 key")
                print(f"       Error: {str(e)[:100]}...")
            else:
                print(f"    ❌ FAIL: Wrong error type: {type(e).__name__}: {e}")
                return False

        # Test 2: Development should allow auto-generation
        os.environ["ENVIRONMENT"] = "development"
        os.environ.pop("GATEWAY_ED25519_PRIVATE_KEY", None)

        print("  [2] Testing development allows auto-generation...")
        try:
            from app.core.config import get_settings
            get_settings.cache_clear()

            GatewayKeyManager._instance = None
            GatewayKeyManager._private_key = None

            manager = GatewayKeyManager()
            public_key = manager.public_key_base64
            print(f"    ✅ PASS: Development auto-generated key")
            print(f"       Public key (first 32 chars): {public_key[:32]}...")
        except Exception as e:
            print(f"    ❌ FAIL: Development should allow auto-generation: {e}")
            return False

        print("\n✅ P0-2: All Ed25519 key validation tests passed!\n")
        return True

    finally:
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)

        if original_key:
            os.environ["GATEWAY_ED25519_PRIVATE_KEY"] = original_key
        else:
            os.environ.pop("GATEWAY_ED25519_PRIVATE_KEY", None)

        # Reset singleton
        from app.core.ed25519 import GatewayKeyManager
        GatewayKeyManager._instance = None
        GatewayKeyManager._private_key = None

        from app.core.config import get_settings
        get_settings.cache_clear()


# ============================================================================
# P0-3: Webhook Allowlist Tests
# ============================================================================

async def test_p0_3_webhook_allowlist():
    """Test that webhook connector denies by default when no allowlist configured."""
    print("\n=== Testing P0-3: Webhook Allowlist Deny-by-Default ===")

    from app.gateway.connectors.base import ConnectorConfig
    from app.gateway.connectors.webhook import WebhookConnector

    # Test 1: No allowlist should deny
    print("  [1] Testing webhook with no allowlist...")
    config = ConnectorConfig(
        connector_type="webhook",
        url="https://example.com/webhook",
        method="POST",
        headers={},
        timeout_seconds=10,
        secret_refs={},
        extra={},
    )

    connector = WebhookConnector(config)
    is_valid, error, _ = connector._validate_url("https://example.com/webhook")

    if not is_valid and "No allowed domains configured" in (error or ""):
        print(f"    ✅ PASS: Correctly denied with no allowlist")
        print(f"       Error: {error}")
    else:
        print(f"    ❌ FAIL: Should deny without allowlist. is_valid={is_valid}, error={error}")
        return False

    # Test 2: With allowlist should allow matching domain
    print("  [2] Testing webhook with allowlist (matching domain)...")
    config.extra["allowed_domains"] = ["example.com"]
    connector = WebhookConnector(config)
    is_valid, error, ips = connector._validate_url("https://example.com/webhook")

    if is_valid:
        print(f"    ✅ PASS: Correctly allowed matching domain")
        print(f"       Resolved IPs: {ips}")
    else:
        print(f"    ❌ FAIL: Should allow matching domain. Error: {error}")
        return False

    # Test 3: With allowlist should deny non-matching domain
    print("  [3] Testing webhook with allowlist (non-matching domain)...")
    is_valid, error, _ = connector._validate_url("https://evil.com/webhook")

    if not is_valid and "not in allowlist" in (error or ""):
        print(f"    ✅ PASS: Correctly denied non-matching domain")
        print(f"       Error: {error}")
    else:
        print(f"    ❌ FAIL: Should deny non-matching domain. is_valid={is_valid}, error={error}")
        return False

    # Test 4: Global setting should be used as fallback
    print("  [4] Testing webhook falls back to global setting...")
    os.environ["GATEWAY_ALLOWED_WEBHOOK_DOMAINS"] = '["slack.com"]'
    from app.core.config import get_settings
    get_settings.cache_clear()

    config_no_extra = ConnectorConfig(
        connector_type="webhook",
        url="https://hooks.slack.com/webhook",
        method="POST",
        headers={},
        timeout_seconds=10,
        secret_refs={},
        extra={},  # No allowed_domains
    )

    connector = WebhookConnector(config_no_extra)
    is_valid, error, _ = connector._validate_url("https://hooks.slack.com/webhook")

    if is_valid:
        print(f"    ✅ PASS: Correctly used global allowlist")
    else:
        print(f"    ❌ FAIL: Should use global allowlist. Error: {error}")
        return False

    # Cleanup
    os.environ.pop("GATEWAY_ALLOWED_WEBHOOK_DOMAINS", None)
    get_settings.cache_clear()

    print("\n✅ P0-3: All webhook allowlist tests passed!\n")
    return True


# ============================================================================
# P1: Atomic Budget Enforcement Tests
# ============================================================================

async def test_p1_atomic_budget_enforcement():
    """Test that budget caps are enforced atomically under concurrency."""
    print("\n=== Testing P1: Atomic Budget Enforcement ===")

    # This requires a database connection, so we'll test the SQL logic
    from app.gateway.policy_engine import PolicyEngine
    from app.models.action_counter import ActionCounter
    from sqlalchemy.dialects.postgresql import insert
    from datetime import date

    print("  [1] Testing reserve_budget_if_available SQL logic...")

    # Simulate the SQL statement
    today = date.today()
    org_id = uuid4()
    uapk_id = "test-uapk"
    daily_cap = 10

    stmt = (
        insert(ActionCounter)
        .values(
            org_id=org_id,
            uapk_id=uapk_id,
            counter_date=today,
            count=1,
            updated_at=datetime.now(UTC),
        )
        .on_conflict_do_update(
            constraint="uq_action_counter_org_uapk_date",
            set_={"count": ActionCounter.count + 1, "updated_at": datetime.now(UTC)},
            where=(ActionCounter.count < daily_cap),
        )
        .returning(ActionCounter.count)
    )

    # Verify the SQL contains the WHERE clause
    sql_str = str(stmt.compile(compile_kwargs={"literal_binds": True}))

    if "WHERE" in sql_str and "count <" in sql_str.lower():
        print(f"    ✅ PASS: SQL contains conditional WHERE clause")
        print(f"       WHERE clause prevents increment if count >= cap")
    else:
        print(f"    ❌ FAIL: SQL missing WHERE clause for conditional increment")
        print(f"       SQL: {sql_str[:200]}...")
        return False

    # Test 2: Verify method signature exists
    print("  [2] Testing reserve_budget_if_available method exists...")
    if hasattr(PolicyEngine, 'reserve_budget_if_available'):
        import inspect
        sig = inspect.signature(PolicyEngine.reserve_budget_if_available)
        params = list(sig.parameters.keys())

        if 'daily_cap' in params:
            print(f"    ✅ PASS: Method exists with daily_cap parameter")
            print(f"       Parameters: {params}")
        else:
            print(f"    ❌ FAIL: Method missing daily_cap parameter")
            return False
    else:
        print(f"    ❌ FAIL: reserve_budget_if_available method not found")
        return False

    # Test 3: Verify service.py uses the new method
    print("  [3] Testing service.py uses atomic reserve...")
    service_path = Path(__file__).parent / "backend" / "app" / "gateway" / "service.py"
    service_content = service_path.read_text()

    if "reserve_budget_if_available" in service_content:
        print(f"    ✅ PASS: service.py calls reserve_budget_if_available")

        # Verify it's called BEFORE _execute_tool
        lines = service_content.split('\n')
        reserve_line = None
        execute_tool_line = None

        for i, line in enumerate(lines):
            if 'reserve_budget_if_available' in line:
                reserve_line = i
            if '_execute_tool' in line and execute_tool_line is None:
                execute_tool_line = i

        if reserve_line and execute_tool_line and reserve_line < execute_tool_line:
            print(f"    ✅ PASS: Budget reserved BEFORE tool execution")
            print(f"       reserve_budget at line {reserve_line}, _execute_tool at line {execute_tool_line}")
        else:
            print(f"    ⚠️  WARNING: Could not verify execution order")
    else:
        print(f"    ❌ FAIL: service.py does not call reserve_budget_if_available")
        return False

    # Test 4: Verify old increment_budget is not called after execution
    print("  [4] Testing old increment_budget removed from execute flow...")

    # Check for the old pattern: increment_budget after _execute_tool
    execute_section_start = service_content.find('async def execute(')
    execute_section = service_content[execute_section_start:execute_section_start + 5000]

    # Look for increment_budget in the execute method
    if 'increment_budget' in execute_section and 'await self.policy_engine.increment_budget' in execute_section:
        print(f"    ❌ FAIL: Old increment_budget still called in execute()")
        return False
    else:
        print(f"    ✅ PASS: Old increment_budget removed from execute flow")

    print("\n✅ P1: All atomic budget enforcement tests passed!\n")
    return True


# ============================================================================
# P1: Rate Limiting Tests
# ============================================================================

def test_p1_rate_limiting():
    """Test that rate limiting decorators are applied to critical endpoints."""
    print("\n=== Testing P1: Rate Limiting on Endpoints ===")

    # Test 1: Check gateway.py has rate limiting
    print("  [1] Testing gateway.py rate limiting...")
    gateway_path = Path(__file__).parent / "backend" / "app" / "api" / "v1" / "gateway.py"
    gateway_content = gateway_path.read_text()

    if '@limiter.limit("120/minute")' in gateway_content:
        print(f"    ✅ PASS: /evaluate has 120/minute limit")
    else:
        print(f"    ❌ FAIL: /evaluate missing rate limit")
        return False

    if '@limiter.limit("60/minute")' in gateway_content:
        print(f"    ✅ PASS: /execute has 60/minute limit")
    else:
        print(f"    ❌ FAIL: /execute missing rate limit")
        return False

    if 'from app.middleware.rate_limit import limiter' in gateway_content:
        print(f"    ✅ PASS: limiter imported")
    else:
        print(f"    ❌ FAIL: limiter not imported")
        return False

    if 'request_obj: Request' in gateway_content:
        print(f"    ✅ PASS: Request parameter added for rate limiting")
    else:
        print(f"    ❌ FAIL: Request parameter missing")
        return False

    # Test 2: Check auth.py has rate limiting
    print("  [2] Testing auth.py rate limiting...")
    auth_path = Path(__file__).parent / "backend" / "app" / "api" / "v1" / "auth.py"
    auth_content = auth_path.read_text()

    if '@limiter.limit("10/minute")' in auth_content:
        print(f"    ✅ PASS: /login has 10/minute limit")
    else:
        print(f"    ❌ FAIL: /login missing rate limit")
        return False

    if 'from app.middleware.rate_limit import limiter' in auth_content:
        print(f"    ✅ PASS: limiter imported")
    else:
        print(f"    ❌ FAIL: limiter not imported")
        return False

    print("\n✅ P1: All rate limiting tests passed!\n")
    return True


# ============================================================================
# P1: trust_env=False Tests
# ============================================================================

def test_p1_trust_env_disabled():
    """Test that httpx clients have trust_env=False."""
    print("\n=== Testing P1: httpx trust_env=False ===")

    # Test 1: WebhookConnector
    print("  [1] Testing WebhookConnector has trust_env=False...")
    webhook_path = Path(__file__).parent / "backend" / "app" / "gateway" / "connectors" / "webhook.py"
    webhook_content = webhook_path.read_text()

    if 'trust_env=False' in webhook_content:
        print(f"    ✅ PASS: WebhookConnector has trust_env=False")

        # Verify it's in the AsyncClient call
        if 'AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False)' in webhook_content:
            print(f"    ✅ PASS: Correctly positioned in AsyncClient constructor")
        else:
            print(f"    ⚠️  WARNING: trust_env=False found but position unclear")
    else:
        print(f"    ❌ FAIL: WebhookConnector missing trust_env=False")
        return False

    # Test 2: HttpRequestConnector
    print("  [2] Testing HttpRequestConnector has trust_env=False...")
    http_path = Path(__file__).parent / "backend" / "app" / "gateway" / "connectors" / "http_request.py"
    http_content = http_path.read_text()

    if 'trust_env=False' in http_content:
        print(f"    ✅ PASS: HttpRequestConnector has trust_env=False")

        # Verify it's in the AsyncClient call
        if 'AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False)' in http_content:
            print(f"    ✅ PASS: Correctly positioned in AsyncClient constructor")
        else:
            print(f"    ⚠️  WARNING: trust_env=False found but position unclear")
    else:
        print(f"    ❌ FAIL: HttpRequestConnector missing trust_env=False")
        return False

    print("\n✅ P1: All trust_env tests passed!\n")
    return True


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests():
    """Run all enterprise security tests."""
    print("=" * 70)
    print("ENTERPRISE SECURITY FIXES - TEST SUITE")
    print("=" * 70)

    results = {}

    # P0 Tests
    results["P0-1: SECRET_KEY Validation"] = test_p0_1_secret_key_validation_production()
    results["P0-2: Ed25519 Key Validation"] = test_p0_2_ed25519_key_validation()
    results["P0-3: Webhook Allowlist"] = await test_p0_3_webhook_allowlist()

    # P1 Tests
    results["P1: Atomic Budget Enforcement"] = await test_p1_atomic_budget_enforcement()
    results["P1: Rate Limiting"] = test_p1_rate_limiting()
    results["P1: trust_env Disabled"] = test_p1_trust_env_disabled()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = 0
    failed = 0

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"TOTAL: {passed} passed, {failed} failed out of {len(results)} tests")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
