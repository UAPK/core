#!/bin/bash
# P0 Fixes Validation Script
# Validates that all critical P0 security fixes are present in the codebase

set -e

echo "========================================="
echo "P0 Security Fixes Validation Script"
echo "========================================="
echo ""

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file_exists() {
    local file="$1"
    local description="$2"

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file NOT FOUND"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

check_file_contains() {
    local file="$1"
    local pattern="$2"
    local description="$3"

    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} $description: File $file not found"
        ERRORS=$((ERRORS + 1))
        return 1
    fi

    if grep -q "$pattern" "$file"; then
        echo -e "${GREEN}✓${NC} $description"
        return 0
    else
        echo -e "${RED}✗${NC} $description: Pattern not found in $file"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

check_python_syntax() {
    local file="$1"
    local description="$2"

    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description: Valid Python syntax"
        return 0
    else
        echo -e "${RED}✗${NC} $description: Syntax error in $file"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo "Checking core files..."
echo "----------------------"

# P0-1: action_hash module
check_file_exists "backend/app/core/action_hash.py" "action_hash module"
check_file_contains "backend/app/core/action_hash.py" "compute_action_hash" "compute_action_hash function"
check_python_syntax "backend/app/core/action_hash.py" "action_hash.py"

echo ""
echo "Checking User model..."
echo "----------------------"

# P0-2: User.default_org_id property
check_file_contains "backend/app/models/user.py" "def default_org_id" "User.default_org_id property"
check_file_contains "backend/app/models/user.py" "memberships\[0\]\.org_id" "default_org_id returns first membership"
check_python_syntax "backend/app/models/user.py" "user.py"

echo ""
echo "Checking Approval model..."
echo "---------------------------"

# P0-3: Approval consumption fields
check_file_contains "backend/app/models/approval.py" "consumed_at" "Approval.consumed_at field"
check_file_contains "backend/app/models/approval.py" "consumed_interaction_id" "Approval.consumed_interaction_id field"
check_python_syntax "backend/app/models/approval.py" "approval.py"

echo ""
echo "Checking Policy Engine..."
echo "--------------------------"

# P0-4: Override token validation
check_file_contains "backend/app/gateway/policy_engine.py" "_validate_override_token" "Override token validation method"
check_file_contains "backend/app/gateway/policy_engine.py" "from app.core.action_hash import compute_action_hash" "action_hash import"
check_file_contains "backend/app/gateway/policy_engine.py" "from app.models.approval import Approval" "Approval model import"
check_file_contains "backend/app/gateway/policy_engine.py" "token_claims.*CapabilityTokenClaims" "PolicyResult.token_claims field"
check_file_contains "backend/app/gateway/policy_engine.py" "OVERRIDE_TOKEN_ACCEPTED" "Override token accepted reason code"
check_python_syntax "backend/app/gateway/policy_engine.py" "policy_engine.py"

echo ""
echo "Checking Gateway Service..."
echo "----------------------------"

# P0-5: Override token consumption
check_file_contains "backend/app/gateway/service.py" "_consume_override_approval" "Override approval consumption method"
check_file_contains "backend/app/gateway/service.py" "from sqlalchemy import.*update" "SQLAlchemy update import"
check_file_contains "backend/app/gateway/service.py" "consumed_at.*consumed_interaction_id" "Consumption tracking"
check_python_syntax "backend/app/gateway/service.py" "service.py"

echo ""
echo "Checking Auth Service..."
echo "-------------------------"

# P0-6: Eager loading of memberships
check_file_contains "backend/app/services/auth.py" "selectinload.*User\.memberships" "Eager loading memberships"
check_python_syntax "backend/app/services/auth.py" "auth.py"

echo ""
echo "Checking Approval Service..."
echo "-----------------------------"

# P0-7: Centralized action hash
check_file_contains "backend/app/services/approval.py" "from app.core.action_hash import compute_action_hash" "Centralized action_hash import"
check_file_contains "backend/app/services/approval.py" "compute_action_hash.*approval\.action" "Using centralized compute_action_hash"
if grep -q "def _compute_action_hash" "backend/app/services/approval.py"; then
    echo -e "${RED}✗${NC} Local _compute_action_hash should be removed"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} Local _compute_action_hash removed (using centralized)"
fi
check_python_syntax "backend/app/services/approval.py" "approval.py"

echo ""
echo "Checking Gateway Schema..."
echo "---------------------------"

# P0-8: Override token reason codes
check_file_contains "backend/app/schemas/gateway.py" "OVERRIDE_TOKEN_ACCEPTED" "OVERRIDE_TOKEN_ACCEPTED reason code"
check_file_contains "backend/app/schemas/gateway.py" "OVERRIDE_TOKEN_INVALID" "OVERRIDE_TOKEN_INVALID reason code"
check_file_contains "backend/app/schemas/gateway.py" "OVERRIDE_TOKEN_ALREADY_USED" "OVERRIDE_TOKEN_ALREADY_USED reason code"
check_python_syntax "backend/app/schemas/gateway.py" "gateway.py"

echo ""
echo "Checking WebhookConnector..."
echo "-----------------------------"

# P0-9: SSRF protection
check_file_contains "backend/app/gateway/connectors/webhook.py" "_validate_url" "URL validation method"
check_file_contains "backend/app/gateway/connectors/webhook.py" "BLOCKED_IP_RANGES\|blocked_range" "IP blocking"

echo ""
echo "Checking Database Migration..."
echo "-------------------------------"

# P0-10: Migration for consumption fields
check_file_exists "backend/alembic/versions/20251216_000000_0008_approval_consumption_tracking.py" "Migration 0008"
check_file_contains "backend/alembic/versions/20251216_000000_0008_approval_consumption_tracking.py" "consumed_at" "Migration adds consumed_at"
check_file_contains "backend/alembic/versions/20251216_000000_0008_approval_consumption_tracking.py" "consumed_interaction_id" "Migration adds consumed_interaction_id"
check_python_syntax "backend/alembic/versions/20251216_000000_0008_approval_consumption_tracking.py" "migration 0008"

echo ""
echo "Checking Test Suite..."
echo "-----------------------"

# P0-11: Integration tests
check_file_exists "backend/tests/test_p0_fixes_integration.py" "P0 integration tests"
check_file_contains "backend/tests/test_p0_fixes_integration.py" "test_p0_fix_override_token_validation" "Override token validation test"
check_file_contains "backend/tests/test_p0_fixes_integration.py" "test_p0_fix_override_token_consumption" "Override token consumption test"
check_python_syntax "backend/tests/test_p0_fixes_integration.py" "P0 integration tests"

echo ""
echo "Checking Documentation..."
echo "--------------------------"

# P0-12: Deployment documentation
check_file_exists "P0_FIXES_DEPLOYMENT.md" "Deployment guide"

echo ""
echo "========================================="
echo "Validation Summary"
echo "========================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo "All P0 security fixes are present and validated."
    echo ""
    echo "Next steps:"
    echo "1. Run database migration: docker-compose run --rm migrate"
    echo "2. Run integration tests: pytest backend/tests/test_p0_fixes_integration.py -v"
    echo "3. Restart services: docker-compose up -d"
    echo "4. Review deployment guide: P0_FIXES_DEPLOYMENT.md"
    echo ""
    exit 0
else
    echo -e "${RED}✗ VALIDATION FAILED: $ERRORS error(s) found${NC}"
    echo ""
    echo "Please review the errors above and ensure all P0 fixes are properly applied."
    echo "Refer to the technical review document for details on each fix."
    echo ""
    exit 1
fi
