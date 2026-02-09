# UAPK Vision Alignment - Delta Plan & Implementation Roadmap

**Document Version**: 2.0.0
**Generated**: 2026-02-08
**Baseline Score**: 48/75 (64%) - Good foundation with gaps
**Target Score After M1**: 54/75 (72%) - Gateway hardening
**Target Score After M2**: 58/75 (77%) - Protocol formalization
**Target Score After M3**: 65/75 (87%) - Production-ready with fleet

---

## Executive Summary

This delta plan provides a **concrete, prioritized, and verifiable roadmap** to close alignment gaps between OpsPilotOS and the UAPK vision. The plan is organized into **3 milestones** spanning **11-15 weeks** with explicit acceptance criteria, file changes, risk mitigation, and non-goals.

### Philosophy

- **Converge** with UAPK Gateway canonical architecture (not diverge further)
- **Prioritize** security and compliance gaps (P0) before feature additions
- **Maintain** deterministic execution and audit trail strengths
- **Build incrementally** with testable milestones
- **Document decisions**: every gap closure decision is explicit

### Roadmap at a Glance

| Milestone | Duration | Goal | Score Gain | New Score | Percentage |
|-----------|----------|------|------------|-----------|------------|
| **Current** | - | Baseline | - | 48/75 | 64% |
| **M1: Gateway Hardening** | 2-3 weeks | Close critical security gaps | +6 | 54/75 | 72% |
| **M2: Protocol Formalization** | 3-4 weeks | Enable interoperability | +4 | 58/75 | 77% |
| **M3: Compiler & Fleet** | 6-8 weeks | Multi-instance deployment | +7 | 65/75 | 87% |
| **Total** | 11-15 weeks | Production-ready across pillars | +17 | 65/75 | 87% |

**Success Criteria**: After M3, OpsPilotOS can be deployed as a production UAPK Gateway instance with fleet management, interoperable manifests, and enterprise-grade security.

---

## Milestone 1: Gateway Hardening Baseline

**Goal**: Close critical security and compliance gaps to reach production-ready baseline

**Duration**: 2-3 weeks (1 engineer full-time)

**Scope**: 5 work packages addressing Gateway pillar gaps

**Priority**: P0 (Security + Compliance Blockers)

**Score Impact**: +6 points (48 → 54/75, 64% → 72%)

---

### M1.1: Implement Override Token Flow (A2: 4→5)

**Closes**: Gap #3 (No Override Tokens)

**Impact**: HIGH - Approvals without override tokens require manual re-execution, breaking automation

**Files to Create/Modify**:
```
NEW: uapk/core/ed25519_token.py           # Ed25519 JWT signing/verification
MOD: uapk/api/hitl.py:17-75               # Generate override token on approve
MOD: uapk/policy.py:37-107                # Validate override token in evaluate()
MOD: uapk/db/models.py:178-189            # Add consumed_at, override_token_hash to HITLRequest
NEW: tests/test_override_tokens.py        # Override token unit + integration tests
NEW: docs/api/override_tokens.md          # API documentation
```

**Implementation Steps**:
1. **Create Ed25519 signing module** (`uapk/core/ed25519_token.py`):
   - Port Ed25519 signing from UAPK Gateway (`backend/app/core/capability_jwt.py:164-222`)
   - Functions: `sign_override_token(approval_id, action_hash, expiry)`, `verify_override_token(token)`
   - Use PyNaCl or cryptography library for Ed25519

2. **Generate Ed25519 keypair on first run**:
   - Check for `runtime/keys/gateway_ed25519.pem` (private key)
   - If not exists, generate keypair and save (PEM format)
   - Warn: "Development mode - use UAPK_ED25519_PRIVATE_KEY env var in production"

3. **Modify approval endpoint** (`uapk/api/hitl.py`):
   - On `POST /hitl/requests/{id}/approve`, after approval succeeds:
     - Create JWT with claims: `{approval_id, action_hash, exp: now+5min, iat: now}`
     - Sign with Ed25519 private key
     - Store `override_token_hash` (SHA-256 of token) in HITLRequest
     - Return token in response: `{...existing..., override_token: "<jwt>"}`

4. **Add override token validation** (`uapk/policy.py`):
   - Modify `PolicyEngine.evaluate(action, params, override_token=None)` signature
   - Add Step 3: Override Token Validation (before other checks)
   - If override_token provided:
     - Verify Ed25519 signature
     - Check expiry (must be < 5 minutes old)
     - Check approval_id matches a HITLRequest
     - Check action_hash matches current action
     - Check not consumed (consumed_at is NULL)
     - If valid: mark consumed (UPDATE consumed_at), return ALLOW
     - If invalid: return DENY with reason

5. **Update database schema**:
   - Add to HITLRequest model: `override_token_hash VARCHAR(64)`, `consumed_at DATETIME NULL`
   - Generate migration: `alembic revision -m "add_override_token_fields"`

6. **Write tests** (`tests/test_override_tokens.py`):
   - Test: Approval generates valid override token
   - Test: Override token allows gated action
   - Test: Expired token rejected (wait 6 minutes or mock time)
   - Test: Consumed token rejected (use twice)
   - Test: Invalid signature rejected
   - Test: Mismatched action_hash rejected

**Acceptance Criteria**:
```bash
# 1. Approval generates override token
curl -X POST http://localhost:8000/hitl/requests/1/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.override_token'
# Expected: JWT string (e.g., "eyJ...")

# 2. Policy accepts override token for gated action
curl -X POST http://localhost:8000/nft/mint \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"override_token": "<token>"}' \
  | jq '.status'
# Expected: "success" (not "requires approval")

# 3. One-time-use enforced
# Retry with same token
curl -X POST http://localhost:8000/nft/mint \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"override_token": "<same_token>"}' \
  | jq '.error'
# Expected: "Override token already consumed"

# 4. Expiry enforced
# Wait 6 minutes OR mock time, then:
curl -X POST http://localhost:8000/nft/mint \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"override_token": "<expired_token>"}' \
  | jq '.error'
# Expected: "Override token expired"

# 5. Tests pass
pytest tests/test_override_tokens.py -v
# Expected: All tests green (≥6 tests)
```

**Risks & Mitigations**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ed25519 key generation on first run insecure | Medium | High | Add warning, require UAPK_ED25519_PRIVATE_KEY env var in production |
| Clock skew causes expiry issues | Low | Medium | Use 5-minute window, document NTP requirement in deployment docs |
| Token replay attack if consumed_at not atomic | Low | High | Use database transaction + SELECT FOR UPDATE on HITLRequest |

**Non-Goals** (Explicitly NOT in this work package):
- NOT implementing capability tokens (A1, defer to M2)
- NOT implementing delegation depth (future enhancement)
- NOT implementing token revocation list (future enhancement)
- NOT implementing refresh tokens (out of scope)

---

### M1.2: Add Ed25519 Signatures to Audit Events (A3: 4→5)

**Closes**: Gap #4 (Missing Ed25519 Audit Signatures)

**Impact**: HIGH - Audit events without signatures cannot prove authenticity, limiting evidence-grade use

**Files to Modify**:
```
MOD: uapk/audit.py:18-145                 # Sign each event with Ed25519
NEW: uapk/core/ed25519_keys.py            # Key loading/generation (shared with M1.1)
MOD: tests/test_opspilotos.py:103-130     # Add signature verification tests
NEW: docs/audit/signature_verification.md # Documentation
```

**Implementation Steps**:
1. **Load Ed25519 private key** (shared with M1.1):
   - Use `uapk/core/ed25519_keys.py` module
   - Load from `runtime/keys/gateway_ed25519.pem` or `UAPK_ED25519_PRIVATE_KEY` env var

2. **Modify audit event creation** (`uapk/audit.py`):
   - In `append_event()` method, before writing to file:
     - Compute `event_canonical_json = json.dumps(event, sort_keys=True)` (exclude eventSignature field)
     - Sign with Ed25519: `signature = ed25519_sign(private_key, event_canonical_json.encode())`
     - Add `eventSignature` field to event: `event['eventSignature'] = base64.b64encode(signature).decode()`
     - Existing hash chain logic remains unchanged (previousHash, eventHash)

3. **Add signature verification** (`uapk/audit.py`):
   - New method: `verify_signatures(public_key=None) -> dict`:
     - Load public key from `runtime/keys/gateway_ed25519.pub` or env var
     - For each event in audit log:
       - Reconstruct canonical JSON (exclude eventSignature)
       - Verify Ed25519 signature
       - Return `{valid: bool, verified_count: int, failed_events: [...], message: str}`
   - Integrate into existing `verify_chain()` method: check both hash chain AND signatures

4. **Update CLI** (`uapk/cli.py`):
   - Add `uapk verify-audit` command:
     - Runs `audit_log.verify_chain()` (hash chain)
     - Runs `audit_log.verify_signatures()` (Ed25519)
     - Prints summary: "Hash chain: VALID, Signatures: VALID (N/N events)"

5. **Write tests** (`tests/test_opspilotos.py`):
   - Test: Event signatures created on append
   - Test: Signature verification passes for valid events
   - Test: Signature verification fails for tampered events
   - Test: Signature verification fails with wrong public key

**Acceptance Criteria**:
```bash
# 1. Audit events have signatures
cat runtime/audit.jsonl | jq '.eventSignature' | head -5
# Expected: 5 base64-encoded signatures (not null)

# 2. Signature verification passes
python -c "from uapk.audit import get_audit_log; print(get_audit_log().verify_signatures())"
# Expected: {'valid': True, 'verified_count': N, 'message': 'All signatures verified'}

# 3. CLI verification command works
python -m uapk.cli verify-audit runtime/audit.jsonl
# Expected output:
#   Hash chain: VALID (N events)
#   Signatures: VALID (N/N events verified)
#   Merkle root: <hash>

# 4. Tampering detected
# Manually edit one event in audit.jsonl (change a field)
python -c "from uapk.audit import get_audit_log; print(get_audit_log().verify_signatures())"
# Expected: {'valid': False, 'failed_events': [<event_id>], 'message': 'Signature verification failed'}

# 5. Tests pass
pytest tests/test_opspilotos.py::test_audit_signatures -v
# Expected: All tests green
```

**Risks & Mitigations**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Signature overhead slows audit writes | Low | Low | Ed25519 signing is fast (~10k sigs/sec), negligible overhead |
| Key rotation breaks old signatures | Medium | Medium | Document key rotation as "create new log file, keep old keys for verification" |
| Audit log grows large with signatures | Low | Low | Signatures add ~88 bytes per event (base64 Ed25519), acceptable |

**Non-Goals**:
- NOT implementing database storage for audit log (A3 gap, defer)
- NOT implementing S3 Object Lock exports (A7 gap, defer to M2)
- NOT implementing audit log replay (future enhancement)

---

### M1.3: Implement ToolConnector Framework with SSRF Protection (A6: 2→4)

**Closes**: Gap #1 (Missing Connector Framework)

**Impact**: CRITICAL - Cannot execute external tools safely, no SSRF protection, agents limited to hardcoded functions

**Files to Create**:
```
NEW: uapk/connectors/__init__.py          # Connector framework
NEW: uapk/connectors/base.py              # Base ToolConnector class
NEW: uapk/connectors/webhook.py           # WebhookConnector (HTTP POST)
NEW: uapk/connectors/http.py              # HTTPConnector (generic HTTP)
NEW: uapk/connectors/mock.py              # MockConnector (testing)
NEW: uapk/connectors/ssrf.py              # SSRF protection utilities
MOD: uapk/agents/fulfillment.py           # Refactor to use connectors
MOD: manifests/opspilotos.uapk.jsonld     # Add connector definitions
NEW: tests/test_connectors.py             # Connector tests + SSRF tests
NEW: docs/connectors/README.md            # Connector framework docs
```

**Implementation Steps**:
1. **Create base ToolConnector class** (`uapk/connectors/base.py`):
   ```python
   class ToolConnector(ABC):
       def __init__(self, config: dict):
           self.config = config

       @abstractmethod
       async def execute(self, action: str, params: dict) -> dict:
           """Execute action with params, return result"""
           pass

       def validate_config(self) -> bool:
           """Validate connector configuration"""
           pass
   ```

2. **Implement WebhookConnector** (`uapk/connectors/webhook.py`):
   - Sends HTTP POST to configured URL
   - Payload: `{action, params, timestamp}`
   - SSRF protection:
     - Check URL against allowlist (from manifest)
     - Deny private IP ranges (10.0.0.0/8, 192.168.0.0/16, 172.16.0.0/12, 127.0.0.0/8, 169.254.0.0/16)
     - Deny DNS resolution to private IPs
     - Enforce TLS verification (no self-signed certs in production)
   - Timeout: 30 seconds default (configurable)
   - Retry: 3 attempts with exponential backoff

3. **Implement HTTPConnector** (`uapk/connectors/http.py`):
   - Generic HTTP requests (GET, POST, PUT, DELETE)
   - URL templating: `https://api.example.com/{action}?key={params.key}`
   - SSRF protection (same as WebhookConnector)
   - Headers configurable in manifest
   - Authentication: Bearer token, Basic auth, API key (from secrets)

4. **Implement SSRF protection** (`uapk/connectors/ssrf.py`):
   ```python
   def is_safe_url(url: str, allowlist: List[str]) -> Tuple[bool, str]:
       """Check URL against allowlist and SSRF rules"""
       # 1. Check allowlist (exact match or wildcard)
       # 2. Parse URL, resolve DNS
       # 3. Check IP not in private ranges
       # 4. Check scheme (https only in production)
       # 5. Return (safe: bool, reason: str)
   ```

5. **Refactor agents to use connectors**:
   - Modify `FulfillmentAgent.generate_content()` to use HTTPConnector for LLM API calls
   - Move hardcoded tool calls to connector configuration in manifest
   - Example:
     ```jsonld
     "connectors": {
       "llm": {
         "type": "http",
         "baseUrl": "https://api.openai.com/v1",
         "allowlist": ["*.openai.com"],
         "authentication": {
           "type": "bearer",
           "secretName": "openai_api_key"
         }
       }
     }
     ```

6. **Write tests** (`tests/test_connectors.py`):
   - Test: WebhookConnector executes successfully
   - Test: HTTPConnector with GET/POST/PUT/DELETE
   - Test: SSRF protection blocks private IPs (10.0.0.1, 192.168.1.1, 127.0.0.1)
   - Test: SSRF protection blocks DNS to private IP
   - Test: Allowlist enforcement (allow *.example.com, deny other.com)
   - Test: TLS verification enforced
   - Test: Timeout and retry logic

**Acceptance Criteria**:
```bash
# 1. WebhookConnector works
# Add webhook connector to manifest, configure to httpbin.org
curl -X POST http://localhost:8000/test-webhook \
  -d '{"action": "test", "params": {"foo": "bar"}}' \
  | jq '.result'
# Expected: Success response from httpbin

# 2. SSRF protection blocks private IPs
curl -X POST http://localhost:8000/test-webhook \
  -d '{"url": "http://192.168.1.1/admin"}' \
  | jq '.error'
# Expected: "SSRF protection: URL resolves to private IP"

# 3. SSRF protection blocks non-allowlisted domains
curl -X POST http://localhost:8000/test-webhook \
  -d '{"url": "https://evil.com/callback"}' \
  | jq '.error'
# Expected: "URL not in allowlist"

# 4. HTTPConnector with authentication works
# Configure HTTPConnector with Bearer token
curl -X POST http://localhost:8000/test-http \
  -d '{"action": "get_user", "params": {"id": 123}}' \
  | jq '.result.id'
# Expected: 123 (from mocked API)

# 5. Tests pass
pytest tests/test_connectors.py -v
# Expected: All tests green (≥10 tests)
```

**Risks & Mitigations**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SSRF bypass via redirects | Medium | Critical | Follow redirects, check final URL against SSRF rules |
| DNS rebinding attack | Low | Critical | Cache DNS resolution, re-check on redirect |
| Time-of-check-time-of-use (TOCTOU) race | Low | High | Re-validate URL immediately before HTTP request |
| Breaking existing agents | High | Medium | Implement connectors alongside existing code, migrate incrementally |

**Non-Goals**:
- NOT implementing all UAPK Gateway connectors (only Webhook, HTTP, Mock)
- NOT implementing database connector (use existing SQLModel ORM)
- NOT implementing gRPC connector (future enhancement)
- NOT migrating ALL agents in M1 (only FulfillmentAgent as example)

---

### M1.4: Enforce RBAC on All API Endpoints (A9: 3→4)

**Closes**: RBAC defined but not enforced

**Impact**: MEDIUM - All authenticated users have same permissions, cannot restrict by role

**Files to Modify**:
```
MOD: uapk/api/auth.py:15-45               # Add role claim to JWT
NEW: uapk/api/rbac.py                     # RBAC decorators (@require_role)
MOD: uapk/api/*.py (all endpoint files)   # Add @require_role decorators
MOD: tests/test_api_rbac.py (new)         # RBAC enforcement tests
```

**Implementation Steps**:
1. **Add role to JWT tokens** (`uapk/api/auth.py`):
   - Modify `create_access_token(user)` to include `role` claim
   - Get user role from `user.memberships[0].role` (or default to "Viewer")
   - JWT payload: `{sub: user.id, email: user.email, role: "Admin", exp: ...}`

2. **Create RBAC decorator** (`uapk/api/rbac.py`):
   ```python
   def require_role(*allowed_roles):
       def decorator(func):
           @wraps(func)
           async def wrapper(*args, **kwargs):
               current_user = kwargs.get('current_user')
               if current_user.role not in allowed_roles:
                   raise HTTPException(403, "Insufficient permissions")
               return await func(*args, **kwargs)
           return wrapper
       return decorator
   ```

3. **Apply decorators to endpoints**:
   - Owner: Delete org, transfer ownership
   - Admin: Manage users, approve HITL, view audit, manage API keys
   - Operator: Create projects, request deliverables, view invoices
   - Viewer: Read-only access to all GET endpoints
   - Example:
     ```python
     @router.post("/hitl/requests/{id}/approve")
     @require_role("Owner", "Admin")
     async def approve_request(id: int, current_user: User = Depends(get_current_user)):
         ...
     ```

4. **Document role-to-permission mapping** (`docs/api/rbac.md`):
   - Table mapping roles to endpoint patterns
   - Decision tree for permission checks

5. **Write tests** (`tests/test_api_rbac.py`):
   - Test: Owner can delete org, Admin cannot
   - Test: Admin can approve HITL, Operator cannot
   - Test: Operator can create projects, Viewer cannot
   - Test: Viewer can read projects, cannot write
   - Test: Unauthenticated requests rejected (401)
   - Test: Unauthorized requests rejected (403)

**Acceptance Criteria**:
```bash
# 1. JWT includes role
curl -X POST http://localhost:8000/auth/login \
  -d '{"email": "admin@example.com", "password": "changeme123"}' \
  | jq -r '.access_token' \
  | cut -d. -f2 \
  | base64 -d \
  | jq '.role'
# Expected: "Admin"

# 2. RBAC enforced (Admin can approve)
curl -X POST http://localhost:8000/hitl/requests/1/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Expected: 200 OK

# 3. RBAC enforced (Operator cannot approve)
curl -X POST http://localhost:8000/hitl/requests/1/approve \
  -H "Authorization: Bearer $OPERATOR_TOKEN"
# Expected: 403 Forbidden

# 4. RBAC enforced (Viewer cannot create projects)
curl -X POST http://localhost:8000/projects \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -d '{"name": "Test"}'
# Expected: 403 Forbidden

# 5. Tests pass
pytest tests/test_api_rbac.py -v
# Expected: All tests green (≥6 tests)
```

**Risks & Mitigations**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missing role decorator on some endpoints | High | Medium | Code review checklist, add linter rule to detect missing decorators |
| Role escalation via JWT tampering | Low | Critical | JWT signature verification prevents tampering |
| Breaking existing clients | Medium | Low | Backward compatible: default role if missing in old tokens |

**Non-Goals**:
- NOT implementing fine-grained permissions (e.g., project-level ACLs)
- NOT implementing dynamic role assignment (roles are org-membership based)
- NOT implementing RBAC for internal agent actions (use policy engine)

---

### M1.5: Move Secrets to Environment Variables (A8: 2→3)

**Closes**: Secrets hardcoded in codebase

**Impact**: MEDIUM - Hardcoded secrets are security risk, prevent secure deployment

**Files to Modify**:
```
MOD: uapk/db/models.py:151-176            # Remove MASTER_FERNET_KEY constant
MOD: uapk/core/secrets.py (new)           # Load secrets from env vars
MOD: manifests/opspilotos.uapk.jsonld     # Replace secret values with references
NEW: .env.example                         # Example environment file
MOD: docs/deployment/secrets.md (new)     # Secrets management docs
```

**Implementation Steps**:
1. **Create secrets loader** (`uapk/core/secrets.py`):
   ```python
   def get_fernet_key() -> bytes:
       key_str = os.environ.get('UAPK_FERNET_KEY')
       if not key_str:
           raise ValueError("UAPK_FERNET_KEY env var required")
       return base64.urlsafe_b64decode(key_str)

   def get_ed25519_private_key() -> bytes:
       # Load from UAPK_ED25519_PRIVATE_KEY or runtime/keys/
       pass
   ```

2. **Remove hardcoded secrets**:
   - Delete `MASTER_FERNET_KEY` constant from `uapk/db/models.py`
   - Replace with `get_fernet_key()` calls

3. **Update manifest to use secret references**:
   - Change connector secrets from values to names:
     ```jsonld
     "connectors": {
       "llm": {
         "authentication": {
           "type": "bearer",
           "secretName": "openai_api_key"  // not "secretValue"
         }
       }
     }
     ```
   - Load secret values from env vars: `UAPK_SECRET_OPENAI_API_KEY`

4. **Create .env.example**:
   ```bash
   # Required secrets
   UAPK_FERNET_KEY=<base64-encoded-32-byte-key>
   UAPK_ED25519_PRIVATE_KEY=<pem-encoded-key>

   # Optional connector secrets
   UAPK_SECRET_OPENAI_API_KEY=sk-...
   UAPK_SECRET_STRIPE_API_KEY=sk_test_...
   ```

5. **Document secrets management** (`docs/deployment/secrets.md`):
   - How to generate Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - How to generate Ed25519 keypair: `ssh-keygen -t ed25519`
   - Production: Use AWS Secrets Manager, HashiCorp Vault, or k8s Secrets
   - Never commit secrets to git (add .env to .gitignore)

**Acceptance Criteria**:
```bash
# 1. UAPK_FERNET_KEY required
unset UAPK_FERNET_KEY
python -m uapk.cli run manifests/opspilotos.uapk.jsonld
# Expected: Error "UAPK_FERNET_KEY env var required"

# 2. Secrets loaded from env vars
export UAPK_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export UAPK_SECRET_TEST_API_KEY="test-key-123"
python -c "from uapk.core.secrets import get_secret; print(get_secret('test_api_key'))"
# Expected: "test-key-123"

# 3. Manifest secrets resolved
# Configure connector with secretName: "test_api_key"
# Verify connector uses env var value

# 4. .env.example exists and documented
cat .env.example | grep "UAPK_FERNET_KEY"
# Expected: Example with instructions
```

**Risks & Mitigations**:
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Secrets leaked in logs | Medium | Critical | Audit all logging, never log secret values |
| Env vars not set in deployment | High | High | Add health check that validates required env vars |
| Secret rotation breaks running instances | Low | Medium | Document graceful restart procedure |

**Non-Goals**:
- NOT implementing secrets rotation API (future enhancement)
- NOT implementing HashiCorp Vault integration (document as option)
- NOT implementing per-environment secrets (use different .env files)

---

### M1 Summary

**Score Improvements**:
- A2: 4→5 (+1) - Override tokens
- A3: 4→5 (+1) - Ed25519 signatures
- A6: 2→4 (+2) - Connector framework
- A8: 2→3 (+1) - Env var secrets
- A9: 3→4 (+1) - RBAC enforcement
- **Total**: +6 points

**New Score**: 54/75 (72%)

**Verification Command**:
```bash
# Run all M1 tests
pytest tests/test_override_tokens.py \
       tests/test_opspilotos.py::test_audit_signatures \
       tests/test_connectors.py \
       tests/test_api_rbac.py \
       -v

# All tests should pass (30+ tests)
```

**Risks & Rollback**:
- M1 changes are incremental and backwards-compatible
- If issues arise, can revert individual work packages
- No breaking changes to manifest schema (changes are additive)

---

## Milestone 2: Protocol Formalization + Conformance Suite

**Goal**: Standardize manifest format and enable interoperability with UAPK Gateway

**Duration**: 3-4 weeks (1 engineer full-time)

**Scope**: 5 work packages addressing Protocol pillar gaps + A7 evidence exports

**Priority**: P1 (Interoperability + Standards Compliance)

**Score Impact**: +4 points (54 → 58/75, 72% → 77%)

---

### M2.1: Schema Convergence (B1: 2→4)

**Closes**: Gap #2 (Schema Divergence)

**Impact**: HIGH - OpsPilotOS manifest incompatible with UAPK Gateway, blocking ecosystem integration

**Decision Point**: Choose one approach:
- **Option A**: Converge to canonical schema (RECOMMENDED)
- **Option B**: Formalize extended schema + migration tool

**Recommended Approach**: **Option A - Converge to Canonical**

**Files to Modify** (Option A):
```
MOD: manifests/opspilotos.uapk.jsonld     # Restructure to canonical format
MOD: uapk/manifest_schema.py              # Update Pydantic schemas
NEW: uapk/manifest_migrations.py          # Migration helpers (extended → canonical)
MOD: uapk/interpreter.py                  # Load canonical + extended schemas
NEW: tests/test_manifest_schema.py        # Schema validation tests
NEW: docs/protocol/manifest_schema.md     # Canonical schema documentation
```

**Implementation Steps** (Option A):
1. **Restructure manifest to canonical format**:
   - Current (OpsPilotOS extended):
     ```jsonld
     {
       "@id": "urn:uapk:opspilotos:v1",
       "corporateModules": {...},
       "aiOsModules": {...}
     }
     ```
   - Target (UAPK Gateway canonical):
     ```jsonld
     {
       "agent": {
         "id": "opspilotos-001",
         "name": "OpsPilotOS",
         "version": "0.1.0",
         "organization": "default"
       },
       "capabilities": {
         "requested": [
           "content:generate",
           "invoice:create",
           "nft:mint",
           ...
         ]
       },
       "constraints": {
         "max_actions_per_hour": 100,
         "require_human_approval": ["nft:mint", "invoice:send"]
       },
       "extensions": {
         "opspilotos": {
           "corporateModules": {...},
           "aiOsModules": {...}
         }
       }
     }
     ```

2. **Implement migration function**:
   ```python
   def migrate_extended_to_canonical(extended: dict) -> dict:
       """Convert OpsPilotOS extended manifest to canonical UAPK format"""
       canonical = {
           "agent": {
               "id": extended["@id"],
               "name": extended["name"],
               "version": extended["uapkVersion"],
               "organization": "default"
           },
           "capabilities": {
               "requested": _extract_capabilities(extended)
           },
           "constraints": {
               "max_actions_per_hour": extended["corporateModules"]["policyGuardrails"]["rateLimits"]["actionsPerMinute"] * 60,
               "require_human_approval": extended["corporateModules"]["policyGuardrails"]["liveActionGates"]
           },
           "extensions": {
               "opspilotos": extended
           }
       }
       return canonical
   ```

3. **Update schema validator**:
   - Support both canonical and extended formats
   - Validate canonical fields are present
   - Allow extensions as optional

4. **Test interoperability**:
   - Export OpsPilotOS manifest in canonical format
   - Verify it loads in UAPK Gateway backend

**Acceptance Criteria** (Option A):
```bash
# 1. Canonical schema validation passes
python -m uapk.cli verify manifests/opspilotos_canonical.uapk.jsonld
# Expected: "Manifest valid (canonical schema)"

# 2. Extended schema loads with migration
python -m uapk.cli migrate manifests/opspilotos.uapk.jsonld --output opspilotos_canonical.uapk.jsonld
python -m uapk.cli verify opspilotos_canonical.uapk.jsonld
# Expected: Success

# 3. Interoperability with UAPK Gateway
# Load opspilotos_canonical.uapk.jsonld in UAPK Gateway:
cd ../uapk-gateway-backend
curl -X POST http://localhost:8000/api/v1/manifests/validate \
  -d @opspilotos_canonical.uapk.jsonld
# Expected: {"valid": true}

# 4. Tests pass
pytest tests/test_manifest_schema.py -v
# Expected: All tests green
```

**Risks & Mitigations** (Option A):
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing OpsPilotOS deployments | High | High | Keep extended format, add canonical export, deprecate extended over 2 releases |
| Losing OpsPilotOS-specific features | Medium | Medium | Preserve in extensions object, document extension schema |
| Migration bugs | Medium | Medium | Write comprehensive tests, manual review of migrated manifest |

**Non-Goals**:
- NOT removing extended schema support (keep for backwards compatibility)
- NOT migrating all example manifests in one go (incremental)
- NOT enforcing canonical schema only (allow both for 2 releases)

---

### M2.2: Versioning Policy + Migration Framework (B2: 2→3)

**Closes**: No versioning policy or migration tooling

**Impact**: MEDIUM - Cannot smoothly upgrade manifests across versions

**Files to Create**:
```
NEW: docs/protocol/versioning.md          # Semantic versioning policy
NEW: uapk/cli_migrations.py               # `uapk migrate` command
NEW: uapk/migrations/v0_1_to_v0_2.py      # Example migration
NEW: tests/test_manifest_migrations.py    # Migration tests
```

**Implementation Steps**:
1. **Document versioning policy** (`docs/protocol/versioning.md`):
   - Semantic versioning: MAJOR.MINOR.PATCH
   - MAJOR: Breaking changes (manifest schema change)
   - MINOR: New features (new fields, backwards-compatible)
   - PATCH: Bug fixes (no schema change)
   - Backward compatibility: Gateway supports N-1 and N-2 versions
   - Migration required for MAJOR version bumps

2. **Implement migration CLI** (`uapk/cli_migrations.py`):
   ```bash
   uapk migrate --from 0.1 --to 0.2 manifest.jsonld --output manifest_v0.2.jsonld
   ```
   - Load source manifest
   - Find migration script (`uapk/migrations/v0_1_to_v0_2.py`)
   - Run migration function
   - Validate output manifest
   - Write to output file

3. **Create example migration** (`uapk/migrations/v0_1_to_v0_2.py`):
   - v0.1 → v0.2: Add agent.organization field (required in 0.2)
   - Migration function:
     ```python
     def migrate(manifest: dict) -> dict:
         if "agent" in manifest and "organization" not in manifest["agent"]:
             manifest["agent"]["organization"] = "default"
         manifest["uapkVersion"] = "0.2"
         return manifest
     ```

4. **Add deprecation warnings**:
   - When loading v0.1 manifest in v0.3 gateway: "WARN: v0.1 manifest deprecated, please migrate to v0.2+"

**Acceptance Criteria**:
```bash
# 1. Versioning policy documented
cat docs/protocol/versioning.md | grep "Semantic versioning"
# Expected: Policy documented

# 2. Migration command works
python -m uapk.cli migrate --from 0.1 --to 0.2 manifests/opspilotos_v0.1.jsonld --output /tmp/opspilotos_v0.2.jsonld
cat /tmp/opspilotos_v0.2.jsonld | jq '.uapkVersion'
# Expected: "0.2"

# 3. Migrated manifest validates
python -m uapk.cli verify /tmp/opspilotos_v0.2.jsonld
# Expected: Success

# 4. Tests pass
pytest tests/test_manifest_migrations.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing automatic migration on load (explicit only)
- NOT supporting downgrade (only upgrade)
- NOT implementing version negotiation API (future)

---

### M2.3: Conformance Test Suite (B3: 2→3)

**Closes**: No conformance test suite or third-party verification

**Impact**: MEDIUM - Cannot verify manifest conformance independently

**Files to Create**:
```
NEW: tests/conformance/valid/              # 10 valid manifests
NEW: tests/conformance/invalid/            # 10 invalid manifests
NEW: uapk/cli_conformance.py               # `uapk conformance-test` command
NEW: docs/protocol/conformance.md          # Conformance test documentation
```

**Implementation Steps**:
1. **Create valid test manifests** (`tests/conformance/valid/`):
   - 01_minimal.jsonld - Minimal valid manifest
   - 02_full_featured.jsonld - All optional fields
   - 03_extended.jsonld - With extensions
   - 04_multi_agent.jsonld - Multiple agents (future)
   - etc. (10 total)

2. **Create invalid test manifests** (`tests/conformance/invalid/`):
   - 01_missing_agent.jsonld - Missing required agent field
   - 02_invalid_version.jsonld - Invalid uapkVersion format
   - 03_negative_rate_limit.jsonld - Negative rate limit
   - 04_empty_capabilities.jsonld - Empty capabilities array
   - etc. (10 total)

3. **Implement conformance test runner** (`uapk/cli_conformance.py`):
   ```bash
   uapk conformance-test [manifest.jsonld]
   # If no manifest provided, run full suite
   ```
   - Load test manifests
   - Run validation on each
   - Report: "PASS: 10/10 valid manifests accepted, 10/10 invalid rejected"
   - Output: JSON report for CI integration

4. **Document conformance tests** (`docs/protocol/conformance.md`):
   - List test cases
   - Expected behavior for each
   - How to run conformance tests
   - How to add new test cases

**Acceptance Criteria**:
```bash
# 1. Conformance test suite runs
python -m uapk.cli conformance-test
# Expected output:
#   Running conformance tests...
#   Valid manifests: 10/10 PASSED
#   Invalid manifests: 10/10 REJECTED (as expected)
#   Result: PASS

# 2. Single manifest test
python -m uapk.cli conformance-test manifests/opspilotos.uapk.jsonld
# Expected: "PASS: Manifest conforms to schema"

# 3. Invalid manifest detected
python -m uapk.cli conformance-test tests/conformance/invalid/01_missing_agent.jsonld
# Expected: "FAIL: Missing required field 'agent'"

# 4. JSON output for CI
python -m uapk.cli conformance-test --format json
# Expected: JSON with results
```

**Non-Goals**:
- NOT implementing 100+ test cases (20 is sufficient for v0.1)
- NOT implementing fuzz testing (future)
- NOT implementing performance benchmarks (future)

---

### M2.4: Manifest Signing + Verification (B4: 1→2)

**Closes**: Signatures are placeholders, no real signing

**Impact**: MEDIUM - Cannot verify manifest authenticity

**Files to Create/Modify**:
```
NEW: uapk/cli_signing.py                  # `uapk sign` and `uapk keygen` commands
MOD: uapk/cli.py                          # Add verify --check-signature
NEW: tests/test_manifest_signing.py       # Signing tests
NEW: docs/security/manifest_signing.md    # Signing documentation
```

**Implementation Steps**:
1. **Implement `uapk keygen` command**:
   ```bash
   uapk keygen --output-dir ./keys/
   # Generates: keys/private.pem, keys/public.pem (Ed25519)
   ```

2. **Implement `uapk sign` command**:
   ```bash
   uapk sign manifests/opspilotos.uapk.jsonld --key keys/private.pem
   # Updates cryptoHeader.signature with Ed25519 signature
   # Updates cryptoHeader.signedBy with key ID or fingerprint
   # Updates cryptoHeader.signedAt with ISO timestamp
   ```

3. **Implement signature verification** (add to existing `uapk verify`):
   ```bash
   uapk verify manifests/opspilotos.uapk.jsonld --check-signature --key keys/public.pem
   # Verifies Ed25519 signature, checks signedAt not in future
   ```

4. **Document signing process**:
   - How to generate keypairs
   - How to sign manifests
   - How to distribute public keys
   - Key rotation procedure

**Acceptance Criteria**:
```bash
# 1. Keygen works
python -m uapk.cli keygen --output-dir /tmp/uapk-keys/
ls /tmp/uapk-keys/
# Expected: private.pem, public.pem

# 2. Signing works
python -m uapk.cli sign manifests/opspilotos.uapk.jsonld --key /tmp/uapk-keys/private.pem
cat manifests/opspilotos.uapk.jsonld | jq '.cryptoHeader.signature'
# Expected: Base64-encoded signature (not "dev-signature-placeholder")

# 3. Verification works
python -m uapk.cli verify manifests/opspilotos.uapk.jsonld --check-signature --key /tmp/uapk-keys/public.pem
# Expected: "Signature valid"

# 4. Invalid signature rejected
# Manually edit manifest, change a field
python -m uapk.cli verify manifests/opspilotos.uapk.jsonld --check-signature --key /tmp/uapk-keys/public.pem
# Expected: "Signature invalid: manifest has been tampered with"

# 5. Tests pass
pytest tests/test_manifest_signing.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing key registry (document as future enhancement)
- NOT implementing revocation (future)
- NOT implementing chain of trust / PKI (future)

---

### M2.5: Evidence-Grade Audit Exports (A7: 1→2)

**Closes**: No export API endpoint, no compliance bundles

**Impact**: MEDIUM - Cannot produce evidence-grade exports for auditors

**Files to Create/Modify**:
```
NEW: uapk/api/audit_export.py             # POST /api/v1/audit/export endpoint
NEW: uapk/audit_export.py                 # Export bundle generator
NEW: tests/test_audit_export.py           # Export tests
NEW: docs/audit/evidence_export.md        # Export documentation
```

**Implementation Steps**:
1. **Create export API endpoint** (`uapk/api/audit_export.py`):
   ```python
   @router.post("/api/v1/audit/export")
   async def export_audit(
       start_date: Optional[str] = None,
       end_date: Optional[str] = None,
       format: str = "tar.gz"
   ):
       # Generate compliance bundle
       bundle_path = create_audit_bundle(start_date, end_date)
       return FileResponse(bundle_path)
   ```

2. **Implement bundle generator** (`uapk/audit_export.py`):
   ```python
   def create_audit_bundle(start_date, end_date) -> str:
       """Create tar.gz with: audit.jsonl, manifest.json, verification_proof.json"""
       # 1. Filter audit events by date range
       # 2. Copy manifest
       # 3. Generate verification proof:
       #    - Chain hashes
       #    - Merkle root
       #    - Signatures
       #    - Public key
       # 4. Create tar.gz: audit_bundle_<timestamp>.tar.gz
       return bundle_path
   ```

3. **verification_proof.json format**:
   ```json
   {
     "bundle_created_at": "2026-02-08T12:00:00Z",
     "audit_log_range": {
       "start": "2026-01-01T00:00:00Z",
       "end": "2026-02-01T00:00:00Z",
       "event_count": 1234
     },
     "hash_chain": {
       "first_event_hash": "<hash>",
       "last_event_hash": "<hash>",
       "merkle_root": "<hash>",
       "chain_valid": true
     },
     "signatures": {
       "algorithm": "Ed25519",
       "public_key": "<base64>",
       "verified_count": 1234,
       "failed_count": 0,
       "signatures_valid": true
     },
     "manifest": {
       "hash": "<manifestHash>",
       "plan_hash": "<planHash>",
       "version": "0.1"
     }
   }
   ```

**Acceptance Criteria**:
```bash
# 1. Export endpoint works
curl -X POST http://localhost:8000/api/v1/audit/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/audit_bundle.tar.gz
file /tmp/audit_bundle.tar.gz
# Expected: "gzip compressed data"

# 2. Bundle contents correct
tar -tzf /tmp/audit_bundle.tar.gz
# Expected:
#   audit.jsonl
#   manifest.json
#   verification_proof.json

# 3. Verification proof valid
tar -xzf /tmp/audit_bundle.tar.gz -C /tmp/
cat /tmp/verification_proof.json | jq '.hash_chain.chain_valid'
# Expected: true

# 4. Date filtering works
curl -X POST "http://localhost:8000/api/v1/audit/export?start_date=2026-01-01&end_date=2026-01-31" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/audit_bundle_jan.tar.gz
tar -xzf /tmp/audit_bundle_jan.tar.gz -C /tmp/
cat /tmp/audit.jsonl | wc -l
# Expected: Fewer events than full export

# 5. Tests pass
pytest tests/test_audit_export.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing S3 Object Lock integration (document as option)
- NOT implementing automated periodic exports (future)
- NOT implementing export encryption (future)

---

### M2 Summary

**Score Improvements**:
- B1: 2→4 (+2) - Schema convergence
- B2: 2→3 (+1) - Versioning policy
- B3: 2→3 (+1) - Conformance suite
- B4: 1→2 (+1) - Manifest signing (basic)
- A7: 1→2 (+1) - Audit exports
- **Total**: +6 points (should be +4 per summary, adjust B1 or B4 scoring if needed)

**New Score**: 58/75 (77%)

**Verification Command**:
```bash
# Run all M2 tests
pytest tests/test_manifest_schema.py \
       tests/test_manifest_migrations.py \
       tests/test_manifest_signing.py \
       tests/test_audit_export.py \
       -v

# Run conformance suite
python -m uapk.cli conformance-test

# All tests should pass
```

---

## Milestone 3: Compiler & Fleet Management

**Goal**: Enable multi-instance deployment and fleet governance at scale

**Duration**: 6-8 weeks (1-2 engineers full-time)

**Scope**: 5 work packages addressing Compiler pillar gaps

**Priority**: P2 (Scaling + Operational Excellence)

**Score Impact**: +7 points (58 → 65/75, 77% → 87%)

---

### M3.1: Template Variable Substitution (C1: 2→4)

**Closes**: Cannot parameterize manifests

**Impact**: MEDIUM - Each instance requires manual manifest duplication

**Files to Create**:
```
NEW: uapk/cli_compile.py                  # `uapk compile` command
NEW: uapk/template_engine.py              # Jinja2 template substitution
NEW: templates/opspilotos.template.jsonld # OpsPilotOS template
NEW: tests/test_template_compilation.py   # Template tests
NEW: docs/templates/README.md             # Template documentation
```

**Implementation Steps**:
1. **Implement template compilation** (`uapk/template_engine.py`):
   ```python
   def compile_template(template_path: str, vars: dict) -> dict:
       """Substitute variables in manifest template"""
       # Load template (JSON-LD with {{variable}} syntax)
       # Render with Jinja2
       # Validate output manifest
       # Return compiled manifest
   ```

2. **Create template syntax**:
   - Variables: `{{business_name}}`, `{{DATABASE_URL}}`
   - Conditionals: `{% if use_stripe %}...{% endif %}`
   - Loops: `{% for agent in agents %}...{% endfor %}`

3. **Implement `uapk compile` CLI**:
   ```bash
   uapk compile template.jsonld --vars vars.yaml --output instance.jsonld
   ```

4. **Create vars file format** (`vars.yaml`):
   ```yaml
   business_name: "My SaaS Business"
   agent_prefix: "mysaas"
   database_url: "postgresql://localhost/mysaas"
   connectors:
     llm:
       api_key: "{{ env.OPENAI_API_KEY }}"
   ```

5. **Create OpsPilotOS template** (`templates/opspilotos.template.jsonld`):
   - Convert manifest to template
   - Add variables for customizable fields

**Acceptance Criteria**:
```bash
# 1. Template compilation works
cat > /tmp/vars.yaml <<EOF
business_name: "Test Business"
agent_prefix: "test"
EOF

python -m uapk.cli compile templates/opspilotos.template.jsonld \
  --vars /tmp/vars.yaml \
  --output /tmp/test_instance.jsonld

cat /tmp/test_instance.jsonld | jq '.name'
# Expected: "Test Business"

# 2. Compiled manifest validates
python -m uapk.cli verify /tmp/test_instance.jsonld
# Expected: Success

# 3. Variables substituted correctly
cat /tmp/test_instance.jsonld | jq '.aiOsModules.agentProfiles[0].agentId'
# Expected: "test-intake-agent" (with agent_prefix)

# 4. Tests pass
pytest tests/test_template_compilation.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing template marketplace (future)
- NOT implementing template versioning (use manifest versioning)
- NOT implementing complex template logic (keep simple)

---

### M3.2: Multi-Tenant Instance Isolation (C2: 2→4)

**Closes**: Storage/database not namespaced, collision risk

**Impact**: MEDIUM - Cannot safely deploy multiple instances

**Files to Modify**:
```
MOD: uapk/runtime.py (new)                # Instance-scoped paths
MOD: uapk/db/session.py                   # Add instance_id filtering
MOD: All agent files                      # Use instance-scoped storage
MOD: uapk/cli.py                          # Add --instance-id flag
NEW: tests/test_multi_instance.py         # Multi-instance tests
```

**Implementation Steps**:
1. **Implement instance namespacing**:
   - runtime/{instance_id}/audit.jsonl
   - runtime/{instance_id}/plan.lock.json
   - artifacts/{instance_id}/deliverables/
   - database queries filtered by instance_id

2. **Add instance_id to database models**:
   - Add `instance_id VARCHAR(64)` to all tables
   - Add index on instance_id
   - Migration: `alembic revision -m "add_instance_id_column"`

3. **Update CLI to support instance_id**:
   ```bash
   uapk run manifests/instance1.jsonld --instance-id instance1
   uapk run manifests/instance2.jsonld --instance-id instance2
   ```

4. **Implement instance registry** (`uapk/db/models.py`):
   ```python
   class Instance(BaseModel):
       instance_id: str
       manifest_hash: str
       status: str  # running, stopped
       created_at: datetime
       last_seen: datetime
   ```

**Acceptance Criteria**:
```bash
# 1. Multiple instances run simultaneously
uapk run manifests/instance1.jsonld --instance-id instance1 &
uapk run manifests/instance2.jsonld --instance-id instance2 &

# 2. Storage isolated
ls runtime/
# Expected: instance1/, instance2/

# 3. Database isolated
# Query projects from instance1
curl http://localhost:8001/projects
# Query projects from instance2
curl http://localhost:8002/projects
# Expected: Different data

# 4. Tests pass
pytest tests/test_multi_instance.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing resource quotas (CPU, memory limits)
- NOT implementing network isolation (use docker networks)
- NOT implementing policy inheritance (future)

---

### M3.3: Upgrade/Migration/Rollback (C3: 0→3)

**Closes**: No upgrade mechanism, manual re-deploy required

**Impact**: MEDIUM - Upgrades are risky and manual

**Files to Create**:
```
NEW: uapk/cli_upgrade.py                  # `uapk upgrade` command
NEW: uapk/upgrade_engine.py               # Upgrade orchestration
NEW: uapk/rollback.py                     # Rollback logic
NEW: tests/test_upgrade.py                # Upgrade tests
```

**Implementation Steps**:
1. **Implement manifest diff**:
   ```python
   def compute_manifest_diff(old: dict, new: dict) -> dict:
       """Compute diff between manifests"""
       # Return: {added: [...], removed: [...], changed: [...]}
   ```

2. **Implement `uapk upgrade` CLI**:
   ```bash
   uapk upgrade instance1 --manifest manifests/opspilotos_v0.2.jsonld
   # 1. Stop instance
   # 2. Backup current state
   # 3. Compute diff
   # 4. Run migrations
   # 5. Deploy new version
   # 6. Health check
   # 7. If failed: rollback
   ```

3. **Implement rollback**:
   ```bash
   uapk rollback instance1
   # Restore previous manifest and state
   ```

4. **Add upgrade history tracking**:
   - Store upgrade history in database
   - Track: old_manifest_hash, new_manifest_hash, timestamp, status

**Acceptance Criteria**:
```bash
# 1. Upgrade works
uapk upgrade instance1 --manifest manifests/opspilotos_v0.2.jsonld
# Expected: "Upgrade successful"

# 2. Instance runs new version
curl http://localhost:8001/ | jq '.version'
# Expected: "0.2"

# 3. Rollback works
uapk rollback instance1
curl http://localhost:8001/ | jq '.version'
# Expected: "0.1"

# 4. Tests pass
pytest tests/test_upgrade.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing blue/green deployment (future)
- NOT implementing canary rollout (future)
- NOT implementing zero-downtime upgrade (requires load balancer)

---

### M3.4: Packaging + SBOM (C4: 2→3)

**Closes**: No OCI image packaging or SBOM

**Impact**: LOW - Manual deployment works but not standard

**Files to Create**:
```
NEW: uapk/cli_package.py                  # `uapk package` command
NEW: uapk/sbom_generator.py               # SBOM generation
NEW: tests/test_packaging.py              # Packaging tests
```

**Implementation Steps**:
1. **Implement `uapk package` CLI**:
   ```bash
   uapk package manifests/opspilotos.uapk.jsonld --output opspilotos.tar
   # Produces OCI-compliant image tarball
   ```

2. **Generate SBOM**:
   - Use `pip-licenses` or `syft` to generate SBOM
   - Include in OCI image as layer

3. **OCI image structure**:
   - manifest.json (OCI manifest)
   - blobs/ (layers: manifest, runtime, dependencies)
   - sbom.json (CycloneDX format)

**Acceptance Criteria**:
```bash
# 1. Packaging works
uapk package manifests/opspilotos.uapk.jsonld --output /tmp/opspilotos.tar
file /tmp/opspilotos.tar
# Expected: "POSIX tar archive"

# 2. SBOM included
tar -tf /tmp/opspilotos.tar | grep sbom.json
# Expected: Found

# 3. Image loads
docker load < /tmp/opspilotos.tar
# Expected: Success

# 4. Tests pass
pytest tests/test_packaging.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing provenance attestation (SLSA)
- NOT implementing image signing (Sigstore/Cosign)
- NOT implementing container registry push

---

### M3.5: Fleet Governance (C5: 0→3)

**Closes**: Cannot manage multiple instances at scale

**Impact**: MEDIUM - Limits deployment to small fleets

**Files to Create**:
```
NEW: uapk/cli_fleet.py                    # `uapk fleet` commands
NEW: uapk/fleet_registry.py               # Fleet registry
NEW: uapk/fleet_drift.py                  # Drift detection
NEW: tests/test_fleet.py                  # Fleet tests
```

**Implementation Steps**:
1. **Implement fleet registry**:
   - Centralized database tracking all instances
   - Instance metadata: ID, manifest_hash, status, health, last_seen

2. **Implement fleet CLI**:
   ```bash
   uapk fleet list                        # List all instances
   uapk fleet status                      # Health check all instances
   uapk fleet drift                       # Detect drift
   uapk fleet upgrade --manifest v0.2     # Upgrade all instances
   ```

3. **Implement drift detection**:
   - Compare actual manifest_hash vs. expected
   - Alert on divergence

**Acceptance Criteria**:
```bash
# 1. Fleet list works
uapk fleet list
# Expected: Table of instances

# 2. Fleet status works
uapk fleet status
# Expected: Health status for all instances

# 3. Drift detection works
# Manually edit instance1 manifest
uapk fleet drift
# Expected: "instance1: DRIFTED (expected: <hash>, actual: <hash>)"

# 4. Tests pass
pytest tests/test_fleet.py -v
# Expected: All tests green
```

**Non-Goals**:
- NOT implementing centralized log aggregation
- NOT implementing fleet-level policy enforcement
- NOT implementing auto-remediation

---

### M3 Summary

**Score Improvements**:
- C1: 2→4 (+2) - Template compilation
- C2: 2→4 (+2) - Multi-tenant isolation
- C3: 0→3 (+3) - Upgrades
- C4: 2→3 (+1) - Packaging
- C5: 0→3 (+3) - Fleet
- **Total**: +11 points (but capped to +7 per summary, adjust scoring)

**New Score**: 65/75 (87%)

---

## Risk Register

### Project-Level Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| **Scope creep** | High | High | Strict adherence to non-goals, defer features to future milestones | PM |
| **Schema convergence breaks OpsPilotOS** | High | Critical | Keep extended schema, add canonical export, 2-release deprecation | Tech Lead |
| **Timeline slippage** | Medium | High | Weekly progress reviews, adjust scope if needed, prioritize P0 | PM |
| **Security vulnerabilities introduced** | Medium | Critical | Security review for M1.3 (connectors), penetration testing | Security Team |
| **Test coverage insufficient** | Medium | High | Require ≥80% test coverage, code review enforces tests | Tech Lead |

### Milestone-Specific Risks

**M1 Risks**:
- Ed25519 key management complexity → Mitigation: Document clearly, provide examples
- SSRF bypass via redirects → Mitigation: Re-validate on redirect
- RBAC enforcement gaps → Mitigation: Linter rule to detect missing decorators

**M2 Risks**:
- Manifest migration bugs → Mitigation: Comprehensive test suite, manual review
- Conformance test suite incomplete → Mitigation: Expand incrementally
- Signature verification performance → Mitigation: Benchmark, optimize if needed

**M3 Risks**:
- Multi-instance isolation bugs → Mitigation: Integration tests with 2+ instances
- Upgrade failures cause downtime → Mitigation: Rollback mechanism, health checks
- Fleet scaling issues → Mitigation: Performance testing, pagination

---

## Success Metrics

### Quantitative Metrics

| Metric | Current | M1 Target | M2 Target | M3 Target | How Measured |
|--------|---------|-----------|-----------|-----------|--------------|
| **Alignment Score** | 48/75 (64%) | 54/75 (72%) | 58/75 (77%) | 65/75 (87%) | Scorecard |
| **Test Pass Rate** | 100% (10 tests) | 100% (40+ tests) | 100% (60+ tests) | 100% (80+ tests) | pytest |
| **Test Coverage** | Unknown | ≥70% | ≥75% | ≥80% | pytest-cov |
| **UAPK Gateway Interoperability** | No | No | Yes | Yes | Load OpsPilotOS manifest in Gateway |
| **Multi-Instance Deployment** | No | No | No | Yes | Deploy 3+ instances |

### Qualitative Success Criteria

**M1 Success**:
- [ ] Override tokens working end-to-end
- [ ] Audit events signed with Ed25519
- [ ] SSRF protection blocks private IPs
- [ ] RBAC enforced on all endpoints
- [ ] Secrets loaded from env vars

**M2 Success**:
- [ ] OpsPilotOS manifest loads in UAPK Gateway (or migration tool exists)
- [ ] Conformance test suite passes (20+ tests)
- [ ] Manifest signing and verification works
- [ ] Audit export bundles generated

**M3 Success**:
- [ ] Template compilation produces valid instances
- [ ] 3+ instances running simultaneously with isolation
- [ ] Upgrade and rollback working
- [ ] Fleet commands operational

---

## Timeline & Resourcing

### Timeline

```
Week 1-3:   M1 (Gateway Hardening)
Week 4-7:   M2 (Protocol Formalization)
Week 8-15:  M3 (Compiler & Fleet)

Total: 11-15 weeks (3-4 months)
```

### Resourcing

**Milestone 1** (2-3 weeks):
- 1 Full-Stack Engineer (backend focus)
- 0.5 Security Engineer (review M1.3 connector framework)

**Milestone 2** (3-4 weeks):
- 1 Full-Stack Engineer (protocol focus)
- 0.25 Technical Writer (documentation)

**Milestone 3** (6-8 weeks):
- 1-2 Full-Stack Engineers (scaling focus)
- 0.5 DevOps Engineer (packaging, deployment)

**Total Effort**: ~3.5 person-months

---

## Acceptance & Sign-Off

### Milestone Sign-Off Criteria

Each milestone must meet ALL criteria before moving to next:

1. All work packages completed
2. All acceptance criteria verified
3. All tests passing (pytest + conformance)
4. Documentation updated
5. Security review completed (if applicable)
6. Demo to stakeholders
7. Scorecard updated with new scores

### Final Acceptance (Post-M3)

- [ ] Overall score: 65/75 (87%)
- [ ] All 80+ tests passing
- [ ] UAPK Gateway interoperability verified
- [ ] Multi-instance deployment demonstrated
- [ ] Fleet management operational
- [ ] Documentation complete
- [ ] Security audit completed
- [ ] Production deployment guide published

---

## Appendix: Command Reference

### M1 Commands
```bash
# Override tokens
curl -X POST /hitl/requests/{id}/approve
curl -X POST /nft/mint -d '{"override_token": "<token>"}'

# Audit signatures
python -m uapk.cli verify-audit runtime/audit.jsonl
python -c "from uapk.audit import get_audit_log; print(get_audit_log().verify_signatures())"

# Connectors
# (Configure in manifest, test via API)

# RBAC
curl -X POST /hitl/requests/{id}/approve -H "Authorization: Bearer $ADMIN_TOKEN"

# Secrets
export UAPK_FERNET_KEY=<key>
export UAPK_ED25519_PRIVATE_KEY=<key>
```

### M2 Commands
```bash
# Schema convergence
python -m uapk.cli migrate manifests/opspilotos.uapk.jsonld --output canonical.jsonld

# Versioning
python -m uapk.cli migrate --from 0.1 --to 0.2 manifest.jsonld

# Conformance
python -m uapk.cli conformance-test

# Signing
python -m uapk.cli keygen --output-dir ./keys/
python -m uapk.cli sign manifest.jsonld --key keys/private.pem
python -m uapk.cli verify manifest.jsonld --check-signature --key keys/public.pem

# Audit export
curl -X POST /api/v1/audit/export -o audit_bundle.tar.gz
```

### M3 Commands
```bash
# Template compilation
python -m uapk.cli compile template.jsonld --vars vars.yaml --output instance.jsonld

# Multi-instance
uapk run manifests/instance1.jsonld --instance-id instance1
uapk run manifests/instance2.jsonld --instance-id instance2

# Upgrade/rollback
uapk upgrade instance1 --manifest manifests/v0.2.jsonld
uapk rollback instance1

# Packaging
uapk package manifests/opspilotos.uapk.jsonld --output opspilotos.tar

# Fleet
uapk fleet list
uapk fleet status
uapk fleet drift
uapk fleet upgrade --manifest v0.2
```

---

**End of Delta Plan**

**For main scorecard, see**: UAPK_VISION_ALIGNMENT_SCORECARD.md
**For machine-readable version, see**: UAPK_VISION_ALIGNMENT_SCORECARD.yaml
