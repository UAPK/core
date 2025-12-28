# Security Fixes v0.2.1

**Date**: December 16, 2025
**Priority**: CRITICAL - Deploy immediately

---

## Critical Security Fixes

### 🚨 CRITICAL #1: Leaked Secrets Removed
**Severity**: P0 - Stop-the-line issue
**Status**: ✅ FIXED

**Problem**:
- `.env` file with secrets was included in distribution archive
- `.claude/settings.local.json` with GitHub PAT token was included
- Any customer who unpacked the archive could extract these secrets

**Fix**:
- Removed both files from repository
- Added `.claude/` to `.gitignore`
- **ACTION REQUIRED**: If you previously distributed v0.2.0, you MUST:
  1. Revoke the GitHub token (`ghp_...`) immediately
  2. Rotate all secrets in `.env` (JWT secret, encryption keys, admin password)
  3. Notify anyone who downloaded v0.2.0 to delete it

**Files Changed**:
- Deleted: `.env`, `.claude/settings.local.json`
- Modified: `.gitignore` (added `.claude/` exclusion)

---

### 🚨 CRITICAL #2: Token Type Confusion Fixed
**Severity**: P0 - Security boundary violation
**Status**: ✅ FIXED

**Problem**:
Override tokens and capability tokens used the same JWT structure. An attacker could:
- Submit an override token in the `capability_token` field
- Bypass the "one action per approval" guarantee
- Create confusing audit trails

**Fix**:
Added explicit `token_type` claim to all tokens:
- **Capability tokens**: `token_type: "capability"`, must NOT have `action_hash`/`approval_id`
- **Override tokens**: `token_type: "override"`, MUST have `action_hash`/`approval_id`

Validation enforces:
- If token has `action_hash` → must be `token_type="override"`
- If `token_type="override"` → must have `action_hash` and `approval_id`
- Mismatched tokens are rejected with `CAPABILITY_TOKEN_INVALID`

**Files Changed**:
- `backend/app/core/capability_jwt.py`:
  - Added `token_type` field to `CapabilityTokenClaims`
  - Updated `create_override_token()` to set `token_type="override"`
  - Updated `to_dict()` and `from_dict()` to include `token_type`
- `backend/app/gateway/policy_engine.py`:
  - Added validation in `_validate_capability_token()` (lines 837-853)

**Backward Compatibility**:
- Old tokens without `token_type` default to `"capability"` during parsing
- New tokens always include `token_type` explicitly

---

## P0 Product Correctness Fixes

### ✅ P0-3: Tool Existence Validation
**Severity**: P0 - Demo stability + trust
**Status**: ✅ FIXED

**Problem**:
PolicyEngine could ALLOW actions for tools not configured in `manifest.tools`. Execution would fail later with a connector error, creating a confusing "gateway allowed it but didn't do it" experience.

**Fix**:
Added `_check_tool_configured()` method that validates tool exists in manifest before allowing action.

**Behavior**:
- If tool not in `manifest.tools` → DENY with reason `TOOL_NOT_ALLOWED`
- Error message includes list of configured tools for debugging

**Files Changed**:
- `backend/app/gateway/policy_engine.py`:
  - Added `_check_tool_configured()` method (lines 473-500)
  - Added check in `evaluate()` flow (step 5b, line 220-225)

**Testing**:
```python
# Tool "foobar" not in manifest.tools
result = gateway.evaluate(action={"tool": "foobar", ...})
assert result.decision == "deny"
assert "tool_not_configured" in result.reason_codes
```

---

## Migration Notes for v0.2.0 → v0.2.1

### Required Actions

1. **Rotate Secrets** (if you deployed v0.2.0):
   - Revoke GitHub PAT if it was in your `.env`
   - Generate new JWT secret: `openssl rand -hex 32`
   - Generate new encryption key: `openssl rand -hex 32`
   - Update environment variables before deploying v0.2.1

2. **Token Migration**:
   - Old tokens (without `token_type`) continue to work (defaulted to "capability")
   - New tokens issued after upgrade include explicit `token_type`
   - Override tokens are now cryptographically distinct from capability tokens

3. **Tool Configuration**:
   - Ensure all tools your agents use are defined in `manifest.tools`
   - Previously, unconfigured tools would fail at execution time
   - Now they fail at evaluation time with clear error message

### Testing Checklist

- [ ] Secrets rotated (if needed)
- [ ] Demo harness runs successfully: `python scripts/demo_harness.py`
- [ ] Approval workflow works end-to-end
- [ ] Tool validation rejects unconfigured tools
- [ ] Override token can't be used as capability token

---

## Still Pending (Future Releases)

These issues were identified but not fixed in v0.2.1:

### P1 Fixes (Before Production Scale)

1. **DB Constraint for One ACTIVE Manifest**
   - Add partial unique index: `(org_id, uapk_id) WHERE status='ACTIVE'`
   - Update `activate_manifest()` to demote previous ACTIVE manifests

2. **Budget Counter Concurrency Safety**
   - Handle `IntegrityError` on first counter creation
   - Use upsert pattern to avoid race conditions

3. **Global Webhook Allowlist Enforcement**
   - Apply `gateway_allowed_webhook_domains` by default in `WebhookConnector`
   - Deny-by-default unless explicit allowlist

### P2 Fixes (Production Hardening)

4. **CSRF Protection**
   - Add CSRF tokens to UI approval forms
   - Add CSRF middleware

5. **Secure Cookies**
   - Set `Secure`, `HttpOnly`, stricter `SameSite` on session cookies

6. **Audit Chain Concurrency**
   - Implement chain head table with row locks
   - Prevent audit chain "forks" under concurrent requests

7. **Logging Modes**
   - Implement redaction modes (full/redacted/hash-only)
   - Prevent PII/secrets from appearing in interaction records

---

## Files Modified in v0.2.1

### Security
- `.gitignore` - Added `.claude/` exclusion
- `backend/app/core/capability_jwt.py` - Added `token_type` field
- `backend/app/gateway/policy_engine.py` - Added token type validation

### Product
- `backend/app/gateway/policy_engine.py` - Added tool existence check

### Documentation
- `SECURITY_FIXES_v0.2.1.md` - This file
- `CHANGELOG.md` - Updated with v0.2.1 changes

---

## Verification Commands

### Verify secrets removed
```bash
tar -tzf uapk-gateway-v0.2.1.tar.gz | grep -E '\.env|settings.local.json'
# Should return nothing
```

### Verify token_type enforcement
```python
from app.core.capability_jwt import create_capability_token, CapabilityTokenClaims

# Create override token
claims = CapabilityTokenClaims(
    iss="gateway",
    sub="agent-001",
    org_id="org-123",
    uapk_id="test-agent",
    token_type="override",
    action_hash="abc123",
    approval_id="apr-456",
)
token = create_capability_token(claims)

# Verify it has token_type in payload
import base64, json
payload = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '==='))
assert payload['token_type'] == 'override'
```

### Verify tool validation
```bash
# Use demo harness with unconfigured tool
python scripts/demo_harness.py
# All tools are properly configured, so should pass

# Or manually test:
curl -X POST http://localhost:8000/api/v1/gateway/evaluate \
  -H "X-API-Key: $API_KEY" \
  -d '{"uapk_id":"test","agent_id":"a1","action":{"tool":"nonexistent",...}}'
# Should return decision=deny with reason tool_not_configured
```

---

## Contact for Security Issues

If you discover additional security issues, please:
1. **Do not** create a public GitHub issue
2. Email security@[your-domain].com with details
3. Include steps to reproduce and potential impact
4. We will respond within 24 hours

---

**Bottom Line**: v0.2.1 closes two critical security holes and one demo-breaking gap. Deploy immediately and rotate secrets if you shipped v0.2.0.
