#!/bin/bash
# Enterprise Security Fixes - Verification Script
# Verifies all P0/P1 fixes are present in the codebase

echo "======================================================================"
echo "ENTERPRISE SECURITY FIXES - VERIFICATION"
echo "======================================================================"

PASS=0
FAIL=0

function test_pass() {
    echo "    ✅ PASS: $1"
    ((PASS++))
}

function test_fail() {
    echo "    ❌ FAIL: $1"
    ((FAIL++))
}

# ============================================================================
# P0-1: SECRET_KEY Validation
# ============================================================================

echo ""
echo "=== Testing P0-1: SECRET_KEY Validation ==="

echo "  [1] Checking config.py has model_validator import..."
if grep -q "from pydantic import.*model_validator" backend/app/core/config.py; then
    test_pass "model_validator imported"
else
    test_fail "model_validator not imported"
fi

echo "  [2] Checking config.py has validate_production_security method..."
if grep -q "@model_validator" backend/app/core/config.py && \
   grep -q "def validate_production_security" backend/app/core/config.py; then
    test_pass "validate_production_security method exists"
else
    test_fail "validate_production_security method missing"
fi

echo "  [3] Checking SECRET_KEY validation logic..."
if grep -q "SECRET_KEY must be set to a secure random value" backend/app/core/config.py && \
   grep -q "min 32 chars" backend/app/core/config.py; then
    test_pass "SECRET_KEY validation implemented"
else
    test_fail "SECRET_KEY validation missing"
fi

echo "  [4] Checking GATEWAY_FERNET_KEY validation..."
if grep -q "GATEWAY_FERNET_KEY is required" backend/app/core/config.py; then
    test_pass "GATEWAY_FERNET_KEY validation implemented"
else
    test_fail "GATEWAY_FERNET_KEY validation missing"
fi

echo "  [5] Checking environment check (staging/production)..."
if grep -q 'if self.environment in ("staging", "production")' backend/app/core/config.py; then
    test_pass "Environment-specific validation implemented"
else
    test_fail "Environment-specific validation missing"
fi

echo "  [6] Checking main.py uses settings for max_request_bytes..."
if grep -q "settings.gateway_max_request_bytes" backend/app/main.py; then
    test_pass "main.py uses settings.gateway_max_request_bytes"
else
    test_fail "main.py not using settings"
fi

# ============================================================================
# P0-2: Ed25519 Key Validation
# ============================================================================

echo ""
echo "=== Testing P0-2: Ed25519 Key Validation ==="

echo "  [1] Checking Ed25519 production validation..."
if grep -q "GATEWAY_ED25519_PRIVATE_KEY must be set in staging/production" backend/app/core/ed25519.py; then
    test_pass "Ed25519 production validation implemented"
else
    test_fail "Ed25519 production validation missing"
fi

echo "  [2] Checking environment check in _load_or_generate_keys..."
if grep -q 'if settings.environment in ("staging", "production") and not env_private_key' backend/app/core/ed25519.py; then
    test_pass "Environment check before key generation"
else
    test_fail "Environment check missing"
fi

echo "  [3] Checking KeyManagementError is raised..."
if grep -B3 "GATEWAY_ED25519_PRIVATE_KEY must be set" backend/app/core/ed25519.py | grep -q "raise KeyManagementError"; then
    test_pass "KeyManagementError raised in production"
else
    test_fail "KeyManagementError not raised properly"
fi

# ============================================================================
# P0-3: Webhook Allowlist
# ============================================================================

echo ""
echo "=== Testing P0-3: Webhook Allowlist Deny-by-Default ==="

echo "  [1] Checking webhook.py has _get_allowed_domains method..."
if grep -q "def _get_allowed_domains" backend/app/gateway/connectors/webhook.py; then
    test_pass "_get_allowed_domains method exists"
else
    test_fail "_get_allowed_domains method missing"
fi

echo "  [2] Checking webhook connector denies without allowlist..."
if grep -q "No allowed domains configured" backend/app/gateway/connectors/webhook.py; then
    test_pass "Deny-by-default error message present"
else
    test_fail "Deny-by-default not implemented"
fi

echo "  [3] Checking webhook uses _get_allowed_domains in validation..."
if grep -q "allowed_domains = self._get_allowed_domains()" backend/app/gateway/connectors/webhook.py; then
    test_pass "Webhook uses _get_allowed_domains helper"
else
    test_fail "Webhook not using helper method"
fi

echo "  [4] Checking webhook validates allowlist before resolving IP..."
if grep -A10 "allowed_domains = self._get_allowed_domains()" backend/app/gateway/connectors/webhook.py | \
   grep -q "if not allowed_domains:"; then
    test_pass "Webhook checks allowlist before IP resolution"
else
    test_fail "Webhook allowlist check missing"
fi

echo "  [5] Checking http_request connector also denies by default..."
if grep -q "No allowed domains configured" backend/app/gateway/connectors/http_request.py; then
    test_pass "HttpRequestConnector also denies by default"
else
    test_fail "HttpRequestConnector deny-by-default missing"
fi

# ============================================================================
# P1: Atomic Budget Enforcement
# ============================================================================

echo ""
echo "=== Testing P1: Atomic Budget Enforcement ==="

echo "  [1] Checking policy_engine.py has reserve_budget_if_available..."
if grep -q "async def reserve_budget_if_available" backend/app/gateway/policy_engine.py; then
    test_pass "reserve_budget_if_available method exists"
else
    test_fail "reserve_budget_if_available method missing"
fi

echo "  [2] Checking reserve method has daily_cap parameter..."
if grep -A5 "async def reserve_budget_if_available" backend/app/gateway/policy_engine.py | \
   grep -q "daily_cap:"; then
    test_pass "daily_cap parameter present"
else
    test_fail "daily_cap parameter missing"
fi

echo "  [3] Checking atomic WHERE clause in reserve logic..."
if grep -A30 "async def reserve_budget_if_available" backend/app/gateway/policy_engine.py | \
   grep -q "where="; then
    test_pass "Atomic WHERE clause present (count < daily_cap)"
else
    test_fail "Atomic WHERE clause missing"
fi

echo "  [4] Checking service.py calls reserve_budget_if_available..."
if grep -q "reserve_budget_if_available" backend/app/gateway/service.py; then
    test_pass "service.py calls reserve_budget_if_available"
else
    test_fail "service.py not calling reserve method"
fi

echo "  [5] Checking budget reserved BEFORE tool execution..."
# Check that reserve_budget_if_available appears before _execute_tool in the file
RESERVE_LINE=$(grep -n "reserve_budget_if_available" backend/app/gateway/service.py | head -1 | cut -d: -f1)
EXECUTE_LINE=$(grep -n "_execute_tool" backend/app/gateway/service.py | grep -v "async def _execute_tool" | head -1 | cut -d: -f1)

if [ ! -z "$RESERVE_LINE" ] && [ ! -z "$EXECUTE_LINE" ] && [ "$RESERVE_LINE" -lt "$EXECUTE_LINE" ]; then
    test_pass "Budget reserved BEFORE tool execution (line $RESERVE_LINE < $EXECUTE_LINE)"
else
    test_fail "Budget not reserved before execution"
fi

echo "  [6] Checking old increment_budget removed from execute flow..."
# Check that increment_budget is NOT called after _execute_tool in the execute() method
if grep -A100 "async def execute(" backend/app/gateway/service.py | \
   grep -A50 "_execute_tool" | \
   grep -q "increment_budget"; then
    test_fail "Old increment_budget still called after execution"
else
    test_pass "Old increment_budget removed from execute flow"
fi

# ============================================================================
# P1: Rate Limiting
# ============================================================================

echo ""
echo "=== Testing P1: Rate Limiting on Endpoints ==="

echo "  [1] Checking gateway.py imports limiter..."
if grep -q "from app.middleware.rate_limit import limiter" backend/app/api/v1/gateway.py; then
    test_pass "gateway.py imports limiter"
else
    test_fail "gateway.py missing limiter import"
fi

echo "  [2] Checking /evaluate has rate limit (120/minute)..."
if grep -B2 "async def evaluate_action" backend/app/api/v1/gateway.py | \
   grep -q '@limiter.limit("120/minute")'; then
    test_pass "/evaluate has 120/minute rate limit"
else
    test_fail "/evaluate missing rate limit"
fi

echo "  [3] Checking /execute has rate limit (60/minute)..."
if grep -B2 "async def execute_action" backend/app/api/v1/gateway.py | \
   grep -q '@limiter.limit("60/minute")'; then
    test_pass "/execute has 60/minute rate limit"
else
    test_fail "/execute missing rate limit"
fi

echo "  [4] Checking gateway.py has Request parameter..."
if grep -q "request_obj: Request" backend/app/api/v1/gateway.py; then
    test_pass "gateway.py has Request parameter for rate limiting"
else
    test_fail "gateway.py missing Request parameter"
fi

echo "  [5] Checking auth.py imports limiter..."
if grep -q "from app.middleware.rate_limit import limiter" backend/app/api/v1/auth.py; then
    test_pass "auth.py imports limiter"
else
    test_fail "auth.py missing limiter import"
fi

echo "  [6] Checking /login has rate limit (10/minute)..."
if grep -B2 "async def login" backend/app/api/v1/auth.py | \
   grep -q '@limiter.limit("10/minute")'; then
    test_pass "/login has 10/minute rate limit"
else
    test_fail "/login missing rate limit"
fi

# ============================================================================
# P1: trust_env=False
# ============================================================================

echo ""
echo "=== Testing P1: httpx trust_env=False ==="

echo "  [1] Checking WebhookConnector has trust_env=False..."
if grep -q "trust_env=False" backend/app/gateway/connectors/webhook.py; then
    test_pass "WebhookConnector has trust_env=False"
else
    test_fail "WebhookConnector missing trust_env=False"
fi

echo "  [2] Checking WebhookConnector AsyncClient constructor..."
if grep -q "AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False)" backend/app/gateway/connectors/webhook.py; then
    test_pass "WebhookConnector AsyncClient properly configured"
else
    test_fail "WebhookConnector AsyncClient not properly configured"
fi

echo "  [3] Checking HttpRequestConnector has trust_env=False..."
if grep -q "trust_env=False" backend/app/gateway/connectors/http_request.py; then
    test_pass "HttpRequestConnector has trust_env=False"
else
    test_fail "HttpRequestConnector missing trust_env=False"
fi

echo "  [4] Checking HttpRequestConnector AsyncClient constructor..."
if grep -q "AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False)" backend/app/gateway/connectors/http_request.py; then
    test_pass "HttpRequestConnector AsyncClient properly configured"
else
    test_fail "HttpRequestConnector AsyncClient not properly configured"
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "======================================================================"
echo "TEST SUMMARY"
echo "======================================================================"

TOTAL=$((PASS + FAIL))

echo "✅ PASSED: $PASS"
echo "❌ FAILED: $FAIL"
echo "TOTAL: $TOTAL tests"
echo "======================================================================"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "🎉 All enterprise security fixes verified successfully!"
    echo ""
    exit 0
else
    echo ""
    echo "⚠️  Some fixes are missing or incomplete"
    echo ""
    exit 1
fi
