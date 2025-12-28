# UAPK Gateway Codebase Gap Map
## File-by-File Analysis: Delete, Unify, Implement

**Purpose:** Map what exists vs. what UAPK spec requires
**Status:** Post-P0 fixes, pre-pilot hardening
**Date:** December 16, 2025

---

## Executive Summary

### What Works Well ✅
- Core gateway evaluate/execute flow
- Approval + override token system
- Interaction record audit chain (tamper-evident)
- Basic connectors with SSRF protection
- Database models are solid

### What Needs Work ⚠️
- **Two parallel permission systems** (must unify)
- **Two parallel policy systems** (must unify)
- **Incomplete enforcement** (schema promises more than engine delivers)
- **Missing operator surfaces** (secrets, retention, exports)
- **Security hardening** (UI RBAC, CSRF, logging PII)

---

## Part 1: DELETE or DEPRECATE

### 🗑️ Duplicate/Obsolete Token System

**DELETE THESE:**

| File | Reason | Action |
|------|--------|--------|
| `backend/app/api/v1/capability_tokens.py` | Duplicate token system, not used by Gateway | Delete or return 410 Gone |
| `backend/app/services/capability_token.py` | Issues HS256 tokens that Gateway doesn't accept | Delete |
| `backend/app/services/policy.py` (PolicyEvaluator) | Validates old tokens, not used by Gateway | Delete or refactor into PolicyEngine |

**Why:** Having two token systems creates operator confusion and false security. Gateway uses EdDSA issuer tokens from `/capabilities/issue`, not HS256 tokens from `/tokens`.

**Migration Path:**
1. Add deprecation warning to `/tokens` endpoint (return 410)
2. Document migration: "Use `/capabilities/issue` instead"
3. After 2 weeks, remove endpoints entirely
4. Remove PolicyEvaluator class if only used for old tokens

---

### 🗑️ Broken/Incomplete Features

**DELETE OR FIX:**

| File | Issue | Action |
|------|-------|--------|
| `backend/app/api/v1/metrics.py` | Broken (wrong field), unauthenticated | Fix or delete |
| `backend/scripts/demo.py` | If unused/outdated | Delete |
| `backend/app/core/audit.py` | If empty or superseded by interaction_record.py | Delete or merge |

---

## Part 2: UNIFY (Resolve Inconsistencies)

### 🔀 Policy Configuration (Two Systems)

**Current State:**
- **Manifest policy** (`manifest.policy.*`): Used by PolicyEngine at runtime
- **Policies table** (`backend/app/models/policy.py`): Separate policy storage, not used by Gateway

**Problem:** Operators can create policies via `/policies` API that the Gateway never checks.

**Unification Required:**

| File | Current Role | Target State |
|------|-------------|--------------|
| `backend/app/models/policy.py` | Stores policies in DB | DELETE or refactor to store manifest policy overrides |
| `backend/app/api/v1/policies.py` | CRUD for policies table | DELETE or repurpose for manifest policy templates |
| `backend/app/services/policy.py` | PolicyEvaluator for old tokens | DELETE or merge into PolicyEngine |
| `backend/app/gateway/policy_engine.py` | Reads manifest.policy | KEEP - this is the runtime enforcer |

**Recommended Unification:**
1. **Option A (Simple):** Delete policies table entirely, only use manifest.policy
2. **Option B (Flexible):** Keep policies table as **policy templates** that can be merged into manifests
3. **Option C (Override):** Policies table becomes **org-level overrides** that can tighten (but not loosen) manifest rules

**Action Required:** Choose unification strategy and implement.

---

### 🔀 Token/Permission Model (Two Systems)

**Current State:**
- **EdDSA Issuer Tokens** (`/capabilities/issue`): Used by Gateway PolicyEngine
- **HS256 DB Tokens** (`/tokens`): Not used by Gateway, validated by PolicyEvaluator

**Unification Required:**

| Component | Current | Target |
|-----------|---------|--------|
| Token issuance | Two endpoints | One: `/capabilities/issue` |
| Token format | Two formats (EdDSA + HS256) | One: EdDSA with issuer registry |
| Token validation | Two validators (PolicyEngine + PolicyEvaluator) | One: PolicyEngine |
| Token storage | `CapabilityToken` table + `CapabilityIssuer` table | Only `CapabilityIssuer` |

**Files to Unify:**

```
DELETE:
  backend/app/api/v1/capability_tokens.py
  backend/app/services/capability_token.py
  backend/app/models/capability_token.py (if separate)

KEEP:
  backend/app/api/v1/capabilities.py
  backend/app/services/capability_issuer.py
  backend/app/models/capability_issuer.py
  backend/app/core/capability_jwt.py
```

---

## Part 3: IMPLEMENT (Missing Spec Features)

### 🏗️ High Priority (Spec-Required)

#### 1. Manifest: One ACTIVE Per UAPK (Database Constraint)

**Status:** ✅ Query logic fixed (P0-1), ❌ DB constraint missing

**Implement:**
```sql
-- Add partial unique index
CREATE UNIQUE INDEX idx_one_active_manifest_per_uapk
ON uapk_manifests (org_id, uapk_id)
WHERE status = 'ACTIVE';
```

**Files:**
- `backend/alembic/versions/NNNN_one_active_manifest.py` (new migration)
- `backend/app/services/manifest.py` - Update `activate_manifest()` to auto-demote previous

---

#### 2. PolicyEngine: Missing Enforcement

**Status:** Schema declares, engine ignores

**Implement in `backend/app/gateway/policy_engine.py`:**

| Feature | Schema Field | Current Status | Implementation |
|---------|--------------|----------------|----------------|
| Hourly caps | `constraints.max_actions_per_hour` | ❌ Not enforced | Add hourly counter (similar to daily) |
| Time windows | `constraints.allowed_hours` | ❌ Not enforced | Check current time against window |
| Per-action budgets | `policy.budgets` | ❌ Not enforced | Replace global cap with per-action-type counters |

**Files to Modify:**
- `backend/app/gateway/policy_engine.py:_check_budget()` - Extend for hourly + per-action
- `backend/app/gateway/policy_engine.py:evaluate()` - Add time window check
- `backend/app/models/action_counter.py` - Add hourly_count field
- `backend/alembic/versions/NNNN_hourly_counters.py` (new migration)

---

#### 3. Secrets Management UI/API

**Status:** Runtime resolution exists, no operator surface

**Implement:**
```
NEW FILES:
  backend/app/api/v1/secrets.py
    - POST /orgs/{org_id}/secrets (create)
    - GET /orgs/{org_id}/secrets (list names only)
    - PUT /orgs/{org_id}/secrets/{name}/rotate (rotate)
    - DELETE /orgs/{org_id}/secrets/{name} (delete)
    - GET /orgs/{org_id}/secrets/{name}/audit (usage log)

  backend/app/services/secret.py
    - SecretService class
    - Rotation logic
    - Audit trail
```

**Files to Modify:**
- `backend/app/models/secret.py` - Add `last_rotated_at`, `rotated_by_user_id`, `usage_count`
- `backend/app/main.py` - Include secrets router

---

#### 4. Tool Existence Validation

**Status:** PolicyEngine doesn't check if tool exists in manifest.tools

**Implement in `backend/app/gateway/policy_engine.py:evaluate()`:**
```python
# After normalization, before action type check:
if context.action.tool not in (manifest_json.get("tools", {}) or {}):
    result.decision = GatewayDecision.DENY
    result.add_reason(
        ReasonCode.TOOL_NOT_CONFIGURED,
        f"Tool '{context.action.tool}' not configured in manifest"
    )
    return result
```

**Files:**
- `backend/app/gateway/policy_engine.py:evaluate()` (line ~196, after normalization)
- `backend/app/schemas/gateway.py` - Add `TOOL_NOT_CONFIGURED` reason code

---

### 🏗️ Medium Priority (Compliance/Safety)

#### 5. Logging Policy Modes

**Status:** Interaction records store raw params (may contain PII/secrets)

**Implement:**
```
NEW FILES:
  backend/app/core/logging_policy.py
    - LoggingMode enum (FULL, REDACTED, HASH_ONLY)
    - redact_params(params, mode)
    - redact_context(context, mode)

MODIFY:
  backend/app/services/interaction_record.py
    - Check manifest.logging_mode before storing
    - Apply redaction based on mode
    - Store hash of original for audit

  backend/app/schemas/manifest.py
    - Add logging_mode field to ManifestContent
    - logging_mode: Literal["full", "redacted", "hash_only"] = "redacted"
```

---

#### 6. Webhook Global Allowlist

**Status:** Setting exists but not enforced

**Implement in `backend/app/gateway/connectors/webhook.py`:**
```python
def __init__(self, config, secrets):
    # ...
    self.allowed_domains = config.extra.get(
        "allowed_domains",
        get_settings().gateway_allowed_webhook_domains  # Apply global default
    )
    if not self.allowed_domains:
        raise ValueError("WebhookConnector requires allowed_domains (per-tool or global)")
```

**Files:**
- `backend/app/gateway/connectors/webhook.py:__init__()` - Apply global allowlist
- Enforce deny-by-default unless explicit allowlist

---

#### 7. UI Security Hardening

**Status:** No CSRF, insecure cookies, no role checks

**Implement:**

```
NEW FILES:
  backend/app/ui/middleware.py
    - CSRF token generation/validation
    - Security headers middleware

MODIFY:
  backend/app/ui/routes.py
    - Add RequireOrgOperator to approve/deny routes
    - Add CSRF validation to POST handlers

  backend/app/core/security.py
    - create_session_cookie() - Add Secure, HttpOnly, SameSite flags

  backend/app/main.py
    - Add SecurityHeadersMiddleware
    - Add CSRFMiddleware
```

---

### 🏗️ Lower Priority (Operational Excellence)

#### 8. Export Packaging

**Status:** Basic CSV export exists, no structured packaging

**Implement:**
```
NEW FILES:
  backend/app/services/export.py
    - create_export_package(org_id, uapk_id, start_date, end_date)
      Returns: {
        manifest_snapshot.json,
        interaction_records.jsonl,
        verification_script.py,
        metadata.json
      }

  backend/scripts/verify_export_package.py
    - Standalone verifier for exported packages
```

---

#### 9. Retention Policy

**Status:** No automated cleanup

**Implement:**
```
NEW FILES:
  backend/app/services/retention.py
    - RetentionPolicy model/service
    - apply_retention(org_id) - Archive/delete old records
    - Configurable per org: retain_days, archive_after_days

  backend/scripts/apply_retention.py
    - Scheduled task (run daily)
    - Archive to S3/cold storage before delete
```

---

## Part 4: Component Health Matrix

### Core Gateway Components

| Component | File | Health | Actions Needed |
|-----------|------|--------|----------------|
| Gateway Service | `backend/app/gateway/service.py` | 🟢 Good | Add tool validation |
| Policy Engine | `backend/app/gateway/policy_engine.py` | 🟡 Mostly good | Implement missing checks (hourly, time window, per-action budgets) |
| Approvals | `backend/app/services/approval.py` | 🟢 Good | None (strong!) |
| Interaction Records | `backend/app/services/interaction_record.py` | 🟢 Good | Add logging modes |
| Manifests | `backend/app/services/manifest.py` | 🟡 Fixed | Add one-ACTIVE constraint |
| Connectors | `backend/app/gateway/connectors/*.py` | 🟡 Good | Apply global webhook allowlist |

### Permission/Auth Components

| Component | File | Health | Actions Needed |
|-----------|------|--------|----------------|
| EdDSA Capabilities | `backend/app/services/capability_issuer.py` | 🟢 Good | None (keep this!) |
| HS256 Tokens | `backend/app/services/capability_token.py` | 🔴 Duplicate | DELETE |
| PolicyEvaluator | `backend/app/services/policy.py` | 🔴 Not used | DELETE or merge |
| Policies Table | `backend/app/models/policy.py` | 🔴 Orphaned | DELETE or repurpose |

### API Endpoints

| Endpoint | File | Health | Actions Needed |
|----------|------|--------|----------------|
| `/gateway/evaluate` | `backend/app/api/v1/gateway.py` | 🟢 Good | None |
| `/gateway/execute` | `backend/app/api/v1/gateway.py` | 🟢 Good | None |
| `/approvals` | `backend/app/api/v1/approvals.py` | 🟢 Good | None |
| `/capabilities/issue` | `backend/app/api/v1/capabilities.py` | 🟢 Good | None (keep this!) |
| `/tokens` | `backend/app/api/v1/capability_tokens.py` | 🔴 Duplicate | DELETE or deprecate |
| `/policies` | `backend/app/api/v1/policies.py` | 🔴 Not used | DELETE or repurpose |
| `/metrics` | `backend/app/api/v1/metrics.py` | 🔴 Broken | Fix or delete |
| `/secrets` | ❌ Missing | 🔴 Missing | IMPLEMENT |

### UI Components

| Component | File | Health | Actions Needed |
|-----------|------|--------|----------------|
| Approval UI | `backend/app/ui/routes.py` | 🔴 No RBAC | Add RequireOrgOperator |
| Templates | `backend/app/ui/templates/*.html` | 🟡 Basic | Add CSRF tokens |
| Middleware | ❌ Missing | 🔴 Missing | Add CSRF + security headers |

---

## Part 5: Migration Sequence

### Phase 0: P0 Fixes (BEFORE PILOT)
**Timeline:** 1-2 days

1. ✅ P0-1: Manifest resolution (DONE)
2. ❌ P0-2: Deprecate `/tokens` endpoint
3. ❌ P0-3: Add UI RBAC
4. ❌ P0-4: Fix metrics endpoint
5. ❌ P0-5: Document unenforced schema fields

**Blockers Lifted:** Can run controlled pilot

---

### Phase 1: Unification (WEEK 1)
**Timeline:** 3-5 days

1. Remove `/tokens` and `capability_token.py`
2. Remove `policies` table or repurpose as templates
3. Merge PolicyEvaluator into PolicyEngine (if needed)
4. Add one-ACTIVE manifest constraint
5. Implement tool existence validation

**Outcome:** Single coherent permission model

---

### Phase 2: Complete Enforcement (WEEK 2)
**Timeline:** 5-7 days

1. Implement hourly caps
2. Implement time window enforcement
3. Implement per-action budgets
4. Add logging policy modes
5. Apply webhook global allowlist

**Outcome:** Schema matches reality

---

### Phase 3: Operator Surfaces (WEEK 3-4)
**Timeline:** 7-10 days

1. Secrets management API/UI
2. Export packaging improvements
3. Retention policy tooling
4. UI security hardening
5. Monitoring/alerting hooks

**Outcome:** Production-ready ops experience

---

## Summary: Key Metrics

### Code Cleanup

| Category | Files to Delete | Files to Unify | Files to Create |
|----------|----------------|----------------|-----------------|
| Auth/Tokens | 3 | 2 | 0 |
| Policy | 2 | 1 | 0 |
| API Endpoints | 2 | 0 | 1 (secrets) |
| Services | 2 | 1 | 3 (secrets, export, retention) |
| UI/Security | 0 | 0 | 2 (middleware, CSRF) |
| **Total** | **9** | **4** | **6** |

### Enforcement Gaps

| Feature | Schema | Engine | Gap |
|---------|--------|--------|-----|
| Daily caps | ✅ | ✅ | None |
| Hourly caps | ✅ | ❌ | Must implement |
| Time windows | ✅ | ❌ | Must implement |
| Per-action budgets | ✅ | ❌ | Must implement |
| Tool allowlist | ✅ | ✅ | None |
| Tool denylist | ✅ | ✅ | None |
| Amount caps | ✅ | ✅ | None (now safe) |
| Counterparty rules | ✅ | ✅ | None |
| Jurisdiction rules | ✅ | ✅ | None |
| **Total Gaps** | | | **3** |

---

## Quick Reference: What to Touch First

### Today (P0 Blockers)
1. `backend/app/api/v1/capability_tokens.py` - Deprecate
2. `backend/app/ui/routes.py` - Add RBAC
3. `backend/app/api/v1/metrics.py` - Fix or delete
4. `schemas/manifest.v1.schema.json` - Document gaps

### This Week (Unification)
1. `backend/app/services/capability_token.py` - Delete
2. `backend/app/services/policy.py` - Delete or merge
3. `backend/app/models/policy.py` - Delete or repurpose
4. `backend/alembic/versions/NNNN_one_active.py` - New migration

### Next Week (Complete Enforcement)
1. `backend/app/gateway/policy_engine.py` - Add hourly/time/per-action
2. `backend/app/gateway/connectors/webhook.py` - Global allowlist
3. `backend/app/services/interaction_record.py` - Logging modes

---

**This gap map provides a complete picture of what exists vs. what's needed. Use it as your engineering roadmap for the next 3-4 weeks.**
