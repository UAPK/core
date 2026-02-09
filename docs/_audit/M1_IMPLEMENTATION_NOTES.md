# Milestone 1 Implementation Notes

**Created**: 2026-02-08
**Scope**: Gateway Hardening Baseline (M1.1-M1.5)
**Status**: In Progress

---

## Current State Reconnaissance

### PolicyEngine (uapk/policy.py)
- **Location**: `uapk/policy.py:30-216`
- **Current evaluation steps**: 5 steps
  1. Tool permissions check (agent → tool mapping)
  2. Deny rules check
  3. Rate limiting (sliding window, in-memory)
  4. Live action gates (escalate in dry_run mode)
  5. Execution mode constraints
- **Decision types**: ALLOW, DENY, ESCALATE
- **Missing**: Capability tokens, override tokens, amount caps, jurisdiction constraints
- **Interface**: `evaluate(agent_id, action, tool, user_id, params) -> PolicyResult`

### HITL Endpoints (uapk/api/hitl.py)
- **Location**: `uapk/api/hitl.py:1-81`
- **Endpoints**:
  - `POST /hitl/requests` - Create approval request
  - `GET /hitl/requests` - List requests
  - `POST /hitl/requests/{id}/approve` - Approve (returns basic status)
  - `POST /hitl/requests/{id}/reject` - Reject
- **HITLRequest model** (uapk/db/models.py:217-231):
  - Fields: id, org_id, action, agent_id, reason, params, status, approved_by, approved_at
  - **Missing**: consumed_at, override_token_hash
- **Gap**: Approval endpoint doesn't generate override token

### Audit System (uapk/audit.py)
- **Location**: `uapk/audit.py:1-210`
- **Features**:
  - Append-only JSONL file (runtime/audit.jsonl)
  - SHA-256 hash chaining (previousHash → eventHash)
  - Hash chain verification (verify_chain method)
  - Merkle root computation (calls cas.compute_merkle_root)
- **Event structure**: eventId, timestamp, eventType, agentId, userId, action, params, result, decision, previousHash, eventHash
- **Missing**: eventSignature field, Ed25519 signatures
- **Database**: AuditEventDB model exists but not used (lines 234-251 in models.py)

### Auth/JWT (uapk/api/auth.py)
- **Location**: `uapk/api/auth.py:1-125`
- **JWT creation**: `create_access_token(data: dict)` (line 49-53)
  - Current payload: `{sub: user.id, exp: <60min>}`
  - **Missing**: role claim
- **Hardcoded secret**: `SECRET_KEY = "dev-secret-key-change-in-production"` (line 20)
- **Algorithm**: HS256
- **Token validation**: `get_current_user` dependency (lines 56-73)

### Roles/Membership (uapk/db/models.py)
- **Membership model** (lines 34-43):
  - Fields: user_id, org_id, role (str)
  - Roles defined in manifest: Owner, Admin, Operator, Viewer
- **No RBAC enforcement**: No decorators or middleware checking roles on endpoints

### Connectors
- **Not implemented**: No uapk/connectors/ directory
- **Agents use hardcoded methods**: e.g., FulfillmentAgent.generate_content() (lines 29-49 in fulfillment.py)
- **Example hardcoded tool**: `generate_content()` doesn't call external APIs, just does template.format()

### Secrets
- **Hardcoded**: SECRET_KEY in auth.py (line 20)
- **No env var loading**: Secrets not loaded from environment
- **No Secret model**: No encrypted storage for connector secrets
- **Gap**: Manifest would need connector auth but no mechanism to load from env vars

### Runtime/Keys
- **No runtime/keys/ directory**: Will need to create for Ed25519 keypairs
- **No key management**: No code for generating or loading Ed25519 keys

---

## M1 Implementation Plan

### M1.1: Override Tokens
**New files**:
- `uapk/core/ed25519_keys.py` - Key generation and loading
- `uapk/core/ed25519_token.py` - Token signing/verification
- `tests/test_override_tokens.py`
- `docs/api/override_tokens.md`

**Modified files**:
- `uapk/db/models.py` - Add consumed_at, override_token_hash to HITLRequest
- `uapk/api/hitl.py` - Generate override token on approve
- `uapk/policy.py` - Add override_token parameter, validate in evaluate()

**Database migration needed**: Yes (alembic or manual ALTER TABLE)

### M1.2: Audit Signatures
**Modified files**:
- `uapk/audit.py` - Sign events with Ed25519, add verify_signatures()
- `uapk/cli.py` - Add verify-audit command
- `tests/test_opspilotos.py` - Add signature verification tests

**New files**:
- `docs/audit/signature_verification.md`

**Shared dependency**: Uses uapk/core/ed25519_keys.py from M1.1

### M1.3: ToolConnector Framework
**New files**:
- `uapk/connectors/__init__.py`
- `uapk/connectors/base.py` - Abstract ToolConnector class
- `uapk/connectors/webhook.py` - WebhookConnector
- `uapk/connectors/http.py` - HTTPConnector
- `uapk/connectors/mock.py` - MockConnector (for testing)
- `uapk/connectors/ssrf.py` - SSRF protection utilities
- `tests/test_connectors.py`
- `docs/connectors/README.md`

**Modified files**:
- `uapk/agents/fulfillment.py` - Refactor generate_content to use HTTPConnector
- `manifests/opspilotos.uapk.jsonld` - Add connector definitions

**SSRF requirements**:
- Deny private IPs: 10/8, 172.16/12, 192.168/16, 127/8, 169.254/16
- DNS resolution check
- Redirect handling with re-validation
- TLS verification enforced

### M1.4: RBAC Enforcement
**New files**:
- `uapk/api/rbac.py` - Decorators (@require_role)
- `tests/test_api_rbac.py`

**Modified files**:
- `uapk/api/auth.py` - Add role claim to JWT
- `uapk/api/*.py` - Apply @require_role decorators to endpoints

**Role mapping**:
- Owner: Full control, delete org
- Admin: Manage users, approve HITL, view audit
- Operator: Create projects/deliverables, view invoices
- Viewer: Read-only

### M1.5: Secrets to Env Vars
**New files**:
- `uapk/core/secrets.py` - Load secrets from env vars
- `.env.example` - Template with UAPK_FERNET_KEY, etc.
- `docs/deployment/secrets.md`

**Modified files**:
- `uapk/api/auth.py` - Remove hardcoded SECRET_KEY, load from env
- `manifests/opspilotos.uapk.jsonld` - Use secretName instead of secretValue

**Env vars pattern**:
- `UAPK_JWT_SECRET_KEY` - JWT signing secret
- `UAPK_FERNET_KEY` - For encrypting stored secrets
- `UAPK_ED25519_PRIVATE_KEY` - Gateway signing key
- `UAPK_SECRET_<NAME>` - Connector secrets (e.g., UAPK_SECRET_OPENAI_API_KEY)

---

## Constraints & Decisions

1. **No database migrations in this M1 implementation** - Will document schema changes but implement as code-first (SQLModel auto-create)

2. **Ed25519 library choice**: Use `cryptography` package (already available in Python ecosystem)

3. **Override token format**: JWT-style with Ed25519 signature (not HS256)
   - Header: `{"alg": "EdDSA", "typ": "JWT"}`
   - Payload: `{"approval_id": int, "action_hash": str, "iat": int, "exp": int}`
   - Signature: Ed25519

4. **Action hash binding**: `action_hash = sha256(canonical_json({action, params}))`

5. **SSRF protection**: Implement in pure Python, no external dependencies beyond `ipaddress` stdlib

6. **Connector refactoring**: Only refactor FulfillmentAgent.generate_content as example; other agents remain unchanged in M1

7. **Test strategy**: Unit tests for core logic, integration tests for end-to-end flows

---

## Known Limitations (Scoped to M1)

- **Not implementing capability tokens** (A1 gap, deferred beyond M1)
- **Not implementing database storage for audit log** (using JSONL only)
- **Not implementing S3 Object Lock exports** (deferred to M2)
- **Not implementing all UAPK Gateway connectors** (only Webhook, HTTP, Mock)
- **Not migrating all agents** (only FulfillmentAgent as example)
- **Not implementing secrets rotation API** (just env var loading)
- **Not implementing fine-grained RBAC** (org-level only, no project-level ACLs)

---

## File Structure After M1

```
uapk/
├── core/                      # NEW - Core utilities
│   ├── __init__.py
│   ├── ed25519_keys.py        # Key generation/loading
│   ├── ed25519_token.py       # Override token signing/verification
│   └── secrets.py             # Env var secret loading
├── connectors/                # NEW - Connector framework
│   ├── __init__.py
│   ├── base.py
│   ├── http.py
│   ├── webhook.py
│   ├── mock.py
│   └── ssrf.py
├── api/
│   ├── rbac.py                # NEW - RBAC decorators
│   ├── auth.py                # MOD - Add role claim
│   ├── hitl.py                # MOD - Generate override token
│   └── ... (apply RBAC decorators)
├── policy.py                  # MOD - Validate override tokens
├── audit.py                   # MOD - Sign events with Ed25519
├── cli.py                     # MOD - Add verify-audit command
├── db/models.py               # MOD - Add HITLRequest fields
└── agents/
    └── fulfillment.py         # MOD - Use HTTPConnector

tests/
├── test_override_tokens.py    # NEW
├── test_connectors.py         # NEW
├── test_api_rbac.py           # NEW
└── test_opspilotos.py         # MOD - Add signature tests

docs/
├── api/override_tokens.md     # NEW
├── audit/signature_verification.md  # NEW
├── connectors/README.md       # NEW
└── deployment/secrets.md      # NEW

.env.example                   # NEW
scripts/verify_m1.sh           # NEW - M1 verification script
```

---

**Next**: Begin implementation with M1.1 (Override Tokens)
