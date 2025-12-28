# P0 Blockers Fix Guide
## Critical Issues That Must Be Fixed Before Production Pilot

**Status:** P0-1 FIXED, P0-2 through P0-5 require immediate attention

---

## ✅ P0-1: FIXED - Active Manifest Selection

### Problem
Gateway was selecting the **most recently created manifest** regardless of status. This meant uploading a PENDING manifest for staging would cause the gateway to stop using the previously ACTIVE manifest and deny all actions.

### Files Fixed
- ✅ `backend/app/gateway/policy_engine.py:331-347` - Added `status == ACTIVE` filter
- ✅ `backend/app/services/manifest.py:57-85` - Added `include_inactive` parameter, defaults to ACTIVE only

### What Changed
```python
# Before (DANGEROUS):
select(UapkManifest).where(
    UapkManifest.org_id == org_id,
    UapkManifest.uapk_id == uapk_id,
).order_by(created_at.desc())

# After (SAFE):
select(UapkManifest).where(
    UapkManifest.org_id == org_id,
    UapkManifest.uapk_id == uapk_id,
    UapkManifest.status == ManifestStatus.ACTIVE,  # Only ACTIVE!
).order_by(created_at.desc())
```

### Still Needs
- **Add DB constraint:** Only one ACTIVE manifest per `(org_id, uapk_id)`
- **Auto-demote:** When activating a manifest, automatically set previous ACTIVE to INACTIVE

---

## ❌ P0-2: NOT FIXED - Two Capability Token Systems

### Problem
There are **two different capability token systems** in the codebase:

1. **EdDSA Issuer Tokens** (good, used by Gateway):
   - API: `/api/v1/orgs/{org_id}/capabilities/issue`
   - Uses Ed25519 signing
   - PolicyEngine validates these

2. **HS256 DB Tokens** (bad, NOT used by Gateway):
   - API: `/api/v1/orgs/{org_id}/tokens`
   - Issues HS256 JWTs
   - PolicyEvaluator validates (not used by Gateway)

**Impact:** Operators can create tokens via `/tokens` that appear valid but the gateway **will not accept them**. This is a dangerous footgun that creates false sense of security.

### Files Involved
- `backend/app/api/v1/capability_tokens.py` - Old token endpoint
- `backend/app/services/capability_token.py` - Old token service
- `backend/app/api/v1/capabilities.py` - New EdDSA endpoint
- `backend/app/services/capability_issuer.py` - New issuer service

### Recommended Fix (Choose One)

**Option A (Recommended):** Remove the old system entirely
```python
# In backend/app/main.py, remove or comment out:
# app.include_router(capability_tokens.router)

# Add deprecation warning to endpoint:
@router.post("/orgs/{org_id}/tokens")
async def create_capability_token(...):
    raise HTTPException(
        status_code=410,  # Gone
        detail="This endpoint is deprecated. Use /capabilities/issue instead."
    )
```

**Option B:** Make old endpoint issue EdDSA tokens
- Refactor `/tokens` to call `capability_issuer.issue_capability_token()`
- Update response format to match
- Update tests

### Action Required
**Developer must choose Option A or B and implement before pilot.**

---

## ❌ P0-3: NOT FIXED - UI Approval Routes Have No RBAC

### Problem
UI endpoints for approving/denying escalated actions only check if user is logged in, not their role. Any user with ANY membership (even VIEWER) can approve critical actions.

### Files Needing Fix
- `backend/app/ui/routes.py:ui_approve_action`
- `backend/app/ui/routes.py:ui_deny_action`

### Current (INSECURE):
```python
@router.post("/ui/approve/{approval_id}")
async def ui_approve_action(
    approval_id: str,
    user: CurrentUser,  # Only checks authentication
    db: DbSession,
):
    # No role check!
```

### Required Fix:
```python
from app.api.deps import RequireOrgOperator

@router.post("/ui/approve/{approval_id}")
async def ui_approve_action(
    approval_id: str,
    _: Annotated[None, RequireOrgOperator],  # Add RBAC check
    user: CurrentUser,
    db: DbSession,
):
    # Now requires OPERATOR+ role
```

### Action Required
**Add `RequireOrgOperator` dependency to both UI approval endpoints.**

---

## ❌ P0-4: NOT FIXED - Metrics Endpoint Broken & Unauthenticated

### Problem
`/api/v1/metrics` endpoint will crash and has no authentication.

### File
- `backend/app/api/v1/metrics.py`

### Issues
1. **References wrong field:** Uses `InteractionRecord.timestamp` but model has `created_at`
2. **No authentication:** Anyone can query metrics
3. **UTC boundaries incorrect:** Date filtering may be wrong

### Required Fix:
```python
# Fix 1: Use correct field
# Before:
InteractionRecord.timestamp >= start_of_day

# After:
InteractionRecord.created_at >= start_of_day

# Fix 2: Add authentication
@router.get("/metrics", dependencies=[Depends(get_api_key_auth)])
async def get_metrics(...):
    # Now requires API key

# Fix 3: Fix UTC boundaries
from datetime import UTC
start_of_day = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=UTC)
```

### Action Required
**Fix field reference, add authentication, fix timezone handling.**

---

## ❌ P0-5: NOT FIXED - Schema Fields Not Enforced

### Problem
The manifest schema (`schemas/manifest.v1.schema.json`) declares fields that the PolicyEngine **does not enforce**. This creates false expectations for customers.

### Unenforced Fields

| Field | Schema Location | PolicyEngine Status |
|-------|----------------|---------------------|
| `constraints.max_actions_per_hour` | Line 75 | ❌ Not enforced |
| `constraints.allowed_hours` | Lines 92-107 | ❌ Not enforced |
| `policy.budgets` (per action type) | Lines 132-156 | ❌ Not enforced (only global daily cap works) |

### Required Fix (Choose One)

**Option A:** Implement the missing enforcement
```python
# In PolicyEngine.evaluate():
# 1. Check hourly cap (similar to daily cap)
# 2. Check allowed_hours time window
# 3. Check per-action-type budgets
```

**Option B:** Remove from schema until implemented
```json
// Mark as not enforced in schema:
"max_actions_per_hour": {
  "type": "integer",
  "description": "NOT YET ENFORCED - Maximum actions per hour"
}
```

**Option C:** Add validation warning
```python
# In manifest registration:
if "max_actions_per_hour" in manifest.constraints:
    logger.warning("max_actions_per_hour declared but not enforced")
```

### Action Required
**Choose an option and implement before claiming these features work.**

---

## Additional Recommendations (Medium Priority)

### Webhook Allowlist Not Applied
- `settings.gateway_allowed_webhook_domains` exists but `WebhookConnector` doesn't use it
- Webhook can call any public host (only blocks private IPs)
- **Fix:** Apply global allowlist or require per-tool allowlist

### Tool Existence Not Validated
- PolicyEngine doesn't check if tool exists in `manifest.tools`
- Fails later with `TOOL_NOT_CONFIGURED`
- **Fix:** Add tool registry check during evaluation

### Logging Stores Sensitive Data
- `InteractionRecord.action.params` may contain secrets/PII
- No redaction or encryption at rest
- **Fix:** Add logging policy modes (full/redacted/hash-only)

### UI Security Hardening
- Cookies not marked `Secure`
- No CSRF protection on approval forms
- **Fix:** Add CSRF tokens, secure cookie flags, security headers

---

## Testing Checklist After Fixes

### P0-1: Manifest Resolution
```bash
# Upload PENDING manifest
curl -X POST /api/v1/orgs/$ORG/manifests \
  -d '{"manifest": {...}, "status": "PENDING"}'

# Gateway should still use old ACTIVE manifest
curl -X POST /api/v1/gateway/evaluate \
  -d '{"uapk_id": "test-agent", ...}'
# Should NOT return MANIFEST_NOT_FOUND
```

### P0-2: Token System
```bash
# Try to use old /tokens endpoint
curl -X POST /api/v1/orgs/$ORG/tokens -d '{...}'
# Should return 410 Gone or redirect to /capabilities/issue
```

### P0-3: UI RBAC
```bash
# Log in as VIEWER
# Try to approve action
# Should get 403 Forbidden
```

### P0-4: Metrics
```bash
# Call metrics without auth
curl /api/v1/metrics
# Should require authentication

# With auth, should not crash
curl -H "X-API-Key: $KEY" /api/v1/metrics
# Should return valid metrics
```

### P0-5: Schema Enforcement
```bash
# Create manifest with max_actions_per_hour
# Make >N requests per hour
# Should enforce limit (or doc should say "not enforced")
```

---

## Summary

| Issue | Status | Priority | Effort |
|-------|--------|----------|--------|
| P0-1: Manifest resolution | ✅ FIXED | Critical | Done |
| P0-2: Token system confusion | ❌ NOT FIXED | Critical | 2-4 hours |
| P0-3: UI RBAC | ❌ NOT FIXED | Critical | 30 min |
| P0-4: Metrics endpoint | ❌ NOT FIXED | Critical | 1 hour |
| P0-5: Schema enforcement | ❌ NOT FIXED | Critical | 4-8 hours (implement) or 1 hour (document) |

**Before running a pilot, you MUST fix P0-2, P0-3, and P0-4. P0-5 can be fixed by documentation if time is short.**

---

## Next Steps

1. **Immediate (before pilot):**
   - Fix P0-2: Choose token system strategy and implement
   - Fix P0-3: Add RBAC to UI approvals (30 min)
   - Fix P0-4: Fix metrics endpoint (1 hour)
   - Fix P0-5: At minimum, document unenforced fields

2. **Phase 0.1 (first week of pilot):**
   - Add DB constraint for one ACTIVE manifest per uapk_id
   - Implement or document webhook allowlist behavior
   - Add tool existence validation

3. **Phase 0.2 (compliance hardening):**
   - Implement logging modes (redacted/hash-only)
   - Add secret management UI
   - UI security hardening (CSRF, secure cookies)

---

**For detailed codebase gap map and architectural unification plan, see CODEBASE_GAP_MAP.md**
