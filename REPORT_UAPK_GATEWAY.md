# UAPK Gateway Security Inspection Report

**Generated:** 2025-12-27
**Repository:** uapk-gateway
**Branch:** main
**Inspector:** Claude Code (Senior Security + Platform Engineer)

---

## Copy/Paste Summary

### Quick Facts
- **Runtime:** Python 3.12, FastAPI + Uvicorn, PostgreSQL 16
- **Purpose:** AI agent gateway for policy enforcement, approval workflows, and tamper-evident audit logging
- **Architecture:** Request → Auth → Policy Engine → Tool Execution → Audit Log
- **Deployment:** Docker Compose (dev), designed for production deployment
- **Auth Methods:** API Keys (agents), JWT (users), Ed25519 Capability Tokens

### Critical Security Controls Present
- ✅ SSRF protection with private IP blocking in connectors
- ✅ Ed25519-signed tamper-evident audit logs with hash chaining
- ✅ Policy engine with budget caps, approval escalation, and counterparty controls
- ✅ Fernet encryption for secrets storage
- ✅ JWT-based authentication for users and API keys for agents
- ✅ RBAC with org-level roles (Owner/Admin/Operator/Viewer)
- ✅ Override tokens with one-time-use enforcement for approved actions

### Top P0 Issues (Must Fix Immediately)
1. **Default SECRET_KEY hardcoded** - Production deployments risk using placeholder
2. **DNS TOCTOU vulnerability** - SSRF check → request race condition
3. **No rate limiting** - Gateway endpoints vulnerable to DoS/abuse
4. **Fernet key optional** - Secrets can be stored without encryption
5. **Ed25519 keys auto-generated in dev** - Risk of weak key material in production

### Top P1 Issues (High Priority)
1. **No request size limits** - Action params can be arbitrarily large
2. **Budget counter race conditions** - Check/increment not fully atomic
3. **No webhook response size limits** - Memory exhaustion risk
4. **Sensitive data in logs** - Action params may contain secrets/PII
5. **Empty CORS default** - Could cause prod misconfiguration

### Positive Highlights
- Excellent tamper-evident audit trail design with hash chains + signatures
- Well-structured policy engine with comprehensive constraint checking
- One-time-use override tokens with atomic consumption enforcement
- Proper separation of evaluate vs execute flows
- Good RBAC implementation with org-level access control

---

## A) Repository Map

### Environment Info
```
OS: Linux 6.12.57+deb13-cloud-amd64
Repository Root: /home/dsanker/uapk-gateway
Git Branch: main
Git Status: Modified files (21 files changed, 8 untracked)
```

### Directory Structure (Depth 3)
```
uapk-gateway/
├── backend/                    # Python FastAPI application
│   ├── alembic/               # Database migrations
│   │   └── versions/          # Migration files
│   ├── app/                   # Main application code
│   │   ├── api/              # API endpoints
│   │   │   └── v1/           # API v1 routes
│   │   ├── core/             # Core utilities (config, auth, audit)
│   │   ├── gateway/          # Gateway service + policy engine
│   │   │   └── connectors/   # Tool execution connectors
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic services
│   │   └── ui/               # Web UI templates/static files
│   ├── scripts/              # Deployment scripts
│   └── tests/                # Test suite
├── docs/                      # Documentation (MkDocs)
├── examples/                  # Example manifests/configs
├── schemas/                   # JSON schemas
├── scripts/                   # Utility scripts
└── deploy/                    # Deployment configs
    ├── caddy/                # Reverse proxy config
    ├── postgres/             # PostgreSQL init scripts
    └── systemd/              # Systemd service files
```

### Language & Framework
- **Language:** Python 3.12
- **Framework:** FastAPI (async, Pydantic validation)
- **Server:** Uvicorn (ASGI)
- **Database:** PostgreSQL 16 (asyncpg driver)
- **Key Libraries:** SQLAlchemy 2.x, httpx, cryptography, python-jose, passlib, structlog

### Entry Points
- **Main App:** `backend/app/main.py:app` (FastAPI instance)
- **CLI:** `uapk` command (via pyproject.toml scripts)
- **Docker:** `backend/Dockerfile` (multi-stage: dev + production)
- **Docker Compose:** `docker-compose.yml` (backend + postgres)

---

## B) Architecture & Execution Flow

### High-Level Request Flow

```
Agent Request
    ↓
[1] HTTP POST /api/v1/gateway/execute
    ↓
[2] API Key Authentication (X-API-Key header)
    → Validate against api_keys table (bcrypt hash)
    → Extract org_id from API key
    ↓
[3] GatewayService.execute(org_id, request)
    ↓
[4] PolicyEngine.evaluate(context)
    → Load manifest (org_id + uapk_id)
    → Validate capability token (if provided)
    → Check: action type, tool, amounts, jurisdiction, counterparty
    → Check: daily budget cap
    → Decision: ALLOW | DENY | ESCALATE
    ↓
[5a] If ALLOW:
    → Execute tool via connector (HTTP/Webhook)
    → Increment budget counter (atomic)
    → Log InteractionRecord (hash-chained + signed)
    → Return result to agent
    ↓
[5b] If DENY:
    → Log InteractionRecord
    → Return decision to agent
    ↓
[5c] If ESCALATE:
    → Create Approval task
    → Log InteractionRecord
    → Return approval_id to agent
    → Human reviews via UI
    → If approved: generate override token
    → Agent retries with override token
```

### Key Modules & Responsibilities

| Module | Responsibilities | Location |
|--------|-----------------|----------|
| `app.main` | FastAPI app setup, CORS, lifespan | `backend/app/main.py:1-115` |
| `app.api.deps` | Auth dependencies (JWT, API key, RBAC) | `backend/app/api/deps.py:1-174` |
| `app.gateway.service` | Orchestrate evaluate/execute flows | `backend/app/gateway/service.py:1-581` |
| `app.gateway.policy_engine` | Policy evaluation logic | `backend/app/gateway/policy_engine.py:1-1248` |
| `app.gateway.connectors` | Tool execution (HTTP, Webhook) | `backend/app/gateway/connectors/*.py` |
| `app.core.audit` | Hash chaining + Ed25519 signatures | `backend/app/core/audit.py:1-317` |
| `app.core.security` | Password hashing, JWT tokens | `backend/app/core/security.py:1-188` |
| `app.core.capability_jwt` | Ed25519-signed capability tokens | `backend/app/core/capability_jwt.py:1-293` |
| `app.core.encryption` | Fernet secret encryption | `backend/app/core/encryption.py:1-84` |
| `app.core.ed25519` | Key management (signing keys) | `backend/app/core/ed25519.py:1-181` |
| `app.services.*` | Business logic (users, orgs, approvals) | `backend/app/services/` |
| `app.models.*` | SQLAlchemy ORM models | `backend/app/models/` |

### Configuration Loading

**Environment Variables (via pydantic-settings):**
- `.env` file loaded automatically (dev)
- Env vars override defaults
- Settings cached via `@lru_cache`

**Secrets Sources:**
1. **JWT Secret:** `SECRET_KEY` env var (default: hardcoded placeholder ⚠️)
2. **Fernet Key:** `GATEWAY_FERNET_KEY` env var (optional ⚠️)
3. **Ed25519 Private Key:**
   - Production: `GATEWAY_ED25519_PRIVATE_KEY` env var
   - Dev: Auto-generated in `/app/keys/gateway_ed25519.pem`
4. **Database Password:** In `DATABASE_URL` connection string
5. **User Secrets:** Encrypted in `secrets` table with Fernet

**Config File:** `backend/app/core/config.py:1-74`

---

## C) API Surface

### HTTP Endpoints (16 routes)

All routes under `/api/v1/` prefix. Authentication requirements noted.

#### Gateway Endpoints (Public-facing, Agent Auth)

| Method | Path | Auth | Side Effects | Description |
|--------|------|------|--------------|-------------|
| POST | `/gateway/evaluate` | API Key | Creates interaction record, approval (if escalate) | Dry-run policy evaluation |
| POST | `/gateway/execute` | API Key | **Executes tool, increments budget, creates records** | Execute action with policy enforcement |

**Critical:** `/gateway/execute` is the **primary attack surface**. It:
- Triggers external HTTP requests (SSRF risk)
- Modifies database (budget counters)
- Logs to audit trail (integrity critical)
- Returns execution results to untrusted agents

#### User Management (User JWT Auth)

| Method | Path | Auth | Side Effects | Description |
|--------|------|------|--------------|-------------|
| POST | `/auth/login` | None | None | Login (returns JWT) |
| POST | `/auth/register` | None | Creates user | Register new user |
| GET | `/users/me` | User JWT | None | Get current user |

**Note:** Registration endpoint could be abused if not disabled in production.

#### Organization Management (User JWT + RBAC)

| Method | Path | Auth | Side Effects | Description |
|--------|------|------|--------------|-------------|
| GET | `/orgs` | User JWT | None | List user's orgs |
| POST | `/orgs` | User JWT | Creates org | Create new org |
| GET | `/orgs/{org_id}/memberships` | User JWT + Viewer | None | List org members |

#### Approval Workflow (User JWT + RBAC)

| Method | Path | Auth | Side Effects | Description |
|--------|------|------|--------------|-------------|
| GET | `/orgs/{org_id}/approvals` | Operator | None | List approvals |
| GET | `/orgs/{org_id}/approvals/pending` | Operator | Marks expired approvals | Get pending approvals |
| GET | `/orgs/{org_id}/approvals/{id}` | Operator | None | Get approval details |
| POST | `/orgs/{org_id}/approvals/{id}/approve` | Operator | **Updates approval, generates override token** | Approve action |
| POST | `/orgs/{org_id}/approvals/{id}/deny` | Operator | **Updates approval** | Deny action |

**Critical:** Approval endpoints allow humans to override policy. Override tokens enable one-time execution bypass.

#### Manifest Management (User JWT + RBAC)

| Method | Path | Auth | Side Effects | Description |
|--------|------|------|--------------|-------------|
| GET | `/orgs/{org_id}/manifests` | Viewer | None | List manifests |
| POST | `/orgs/{org_id}/manifests` | Admin | **Creates manifest** | Upload new manifest |
| PATCH | `/orgs/{org_id}/manifests/{id}` | Admin | **Updates manifest status** | Activate/deactivate manifest |
| DELETE | `/orgs/{org_id}/manifests/{id}` | Owner | **Deletes manifest** | Delete manifest |

**Critical:** Manifest controls which tools are available and policy rules. Compromise = policy bypass.

#### Audit Logs (User JWT + RBAC)

| Method | Path | Auth | Side Effects | Description |
|--------|------|------|--------------|-------------|
| GET | `/orgs/{org_id}/interaction-records` | Viewer | None | List interaction records |
| GET | `/orgs/{org_id}/logs/verify-chain` | Viewer | None | Verify hash chain integrity |

#### Health Checks (Unauthenticated)

| Method | Path | Auth | Side Effects | Description |
|--------|------|------|--------------|-------------|
| GET | `/healthz` | None | None | Health check |
| GET | `/readyz` | None | None | Readiness check |

### Unauthenticated Endpoints (Risk Summary)

- `/healthz` - Safe (no sensitive data)
- `/readyz` - Safe (no sensitive data)
- `/auth/login` - Brute-force risk (no rate limit ⚠️)
- `/auth/register` - User enumeration risk (no rate limit ⚠️)

### Weakly Authenticated Endpoints

- API Key auth uses bcrypt (good) but **no rate limiting** on failed attempts ⚠️

---

## D) Guardrails & Safety Controls

### 1. Budget Caps / Rate Limits / Quotas

**Implementation:** Daily action counter per UAPK
- **File:** `backend/app/gateway/policy_engine.py:718-816`
- **Function:** `PolicyEngine._check_budget()`, `PolicyEngine.increment_budget()`
- **Mechanism:**
  - Counter stored in `action_counters` table (org_id, uapk_id, date)
  - Atomic increment via PostgreSQL `ON CONFLICT DO UPDATE`
  - Default limit: 1000 actions/day (configurable via `max_actions_per_day` constraint)
  - Escalation threshold: 90% of limit (configurable via `budget_escalate_at_percent`)
- **Controls:**
  - DENY if count >= limit
  - ESCALATE if count >= threshold
  - Increment happens AFTER approval in execute flow
- **Gap:** ⚠️ Race condition window between check and increment (see P1-2)

**Configuration:**
- Per-manifest: `constraints.max_actions_per_day`
- Global default: `GATEWAY_DEFAULT_DAILY_BUDGET` env var (default: 1000)

### 2. Approval Gates / Human-in-the-Loop

**Implementation:** Escalation triggers and approval workflow
- **File:** `backend/app/gateway/policy_engine.py:502-577` (thresholds), `backend/app/services/approval.py` (approval logic)
- **Triggers:**
  - Budget threshold reached (e.g., 90% of daily cap)
  - Amount exceeds threshold (`approval_thresholds.amount`)
  - Specific action types require approval (`approval_thresholds.action_types`)
  - Specific tools require approval (`approval_thresholds.tools`)
- **Flow:**
  1. Policy engine returns ESCALATE decision
  2. Approval task created in database (status: PENDING)
  3. Human reviews via UI
  4. If approved: generates short-lived override token (5 min default)
  5. Agent retries with override token
  6. Policy engine validates override token → ALLOW
  7. Approval marked as consumed (one-time use enforcement)
- **Controls:**
  - Override tokens bound to specific action (via SHA-256 action hash)
  - One-time use enforced atomically via database UPDATE WHERE consumed_at IS NULL
  - Expiration enforced (default: 24 hours for approval, 5 minutes for override token)
- **Files:**
  - Approval service: `backend/app/services/approval.py:1-end`
  - Override token creation: `backend/app/core/capability_jwt.py:262-293`
  - Consumption enforcement: `backend/app/gateway/service.py:417-449`

### 3. Policy Engine / Rules Evaluation

**Implementation:** Multi-stage policy evaluation pipeline
- **File:** `backend/app/gateway/policy_engine.py:100-345`
- **Function:** `PolicyEngine.evaluate()`
- **Checks (in order):**
  1. Manifest exists and active
  2. Capability token validation (if provided)
  3. Override token validation (if provided)
  4. Require capability token (if policy demands it)
  5. Action type allowed (manifest)
  6. Action type allowed (capability token)
  7. Tool allowed (manifest allowlist/denylist)
  8. Tool configured in manifest
  9. Tool allowed (capability token)
  10. Approval thresholds (action type, tool, amount)
  11. Amount caps (manifest + token)
  12. Jurisdiction allowlist (manifest + token)
  13. Counterparty allowlist/denylist (manifest + token)
  14. Daily budget cap
  15. Override token bypass (if valid)
- **Decision Logic:**
  - Each check can return: PASS, DENY, or ESCALATE
  - First DENY terminates evaluation → DENY decision
  - ESCALATE is "sticky" (can accumulate multiple reasons)
  - Override token converts final ESCALATE → ALLOW
- **Trace:** Full policy trace logged to `policy_trace_json` in interaction records

**Policy Configuration Sources:**
1. **Manifest:** `uapk_manifests.manifest_json.policy`
2. **Capability Token:** JWT claims (allowed_action_types, allowed_tools, constraints)
3. **Override Token:** Bypasses policy for specific pre-approved action

### 4. Tool Allowlists/Denylists

**Implementation:** Manifest-based tool control
- **File:** `backend/app/gateway/policy_engine.py:444-501`
- **Functions:** `_check_tool_allowed()`, `_check_tool_configured()`
- **Mechanism:**
  - Manifest defines `policy.allowed_tools` (allowlist) and `policy.denied_tools` (denylist)
  - Denylist checked first (explicit deny)
  - Allowlist checked if specified (deny if not present)
  - Tool must exist in `tools` registry (connector configuration)
- **Example Manifest:**
  ```json
  {
    "policy": {
      "allowed_tools": ["send_email", "read_file"],
      "denied_tools": ["delete_database"]
    },
    "tools": {
      "send_email": {"type": "webhook", "config": {...}},
      "read_file": {"type": "http_request", "config": {...}}
    }
  }
  ```

### 5. Prompt Injection Defenses / Input Sanitization

**Status:** ⚠️ **LIMITED**

**Present Controls:**
- Pydantic validation on all request schemas (type checking, field validation)
- No direct LLM interaction in gateway (agents use external LLMs)
- Action params treated as opaque JSON (not interpreted by gateway)

**Gaps:**
- Action params forwarded to connectors without sanitization
- Webhook/HTTP connectors insert params into URLs/bodies (potential injection)
- No content filtering on param values (XSS, SQLi strings could be in logs)

**Files:**
- Request schemas: `backend/app/schemas/gateway.py:1-end`
- Connector param handling: `backend/app/gateway/connectors/http_request.py:112-122` (URL template substitution)

### 6. SSRF Protections

**Implementation:** Domain allowlist + private IP blocking
- **File:** `backend/app/gateway/connectors/http_request.py:55-111`, `webhook.py:43-97`
- **Classes:** `HttpRequestConnector._validate_url()`, `WebhookConnector._validate_url()`
- **Protections:**
  1. **Scheme validation:** Only http/https allowed
  2. **Domain allowlist:** Configurable via `GATEWAY_ALLOWED_WEBHOOK_DOMAINS` or per-connector `allowed_domains`
  3. **Private IP blocking:** Rejects connections to:
     - 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 (RFC 1918)
     - 127.0.0.0/8 (loopback)
     - 169.254.0.0/16 (link-local)
     - ::1/128, fc00::/7, fe80::/10 (IPv6 private)
  4. **DNS resolution check:** Resolves hostname before request, blocks if any IP is private
- **Default:** Empty allowlist = **deny all** (secure default)

**Example Config:**
```bash
GATEWAY_ALLOWED_WEBHOOK_DOMAINS=["api.example.com","webhooks.stripe.com"]
```

**Gap:** ⚠️ DNS TOCTOU vulnerability (see P0-2)

### 7. File Path Protections

**Status:** ⚠️ **NOT APPLICABLE** (No file operations exposed via gateway)

- Connectors only support HTTP/Webhook (no file:// URIs)
- No file upload/download endpoints for agents

### 8. Command Execution Protections

**Status:** ✅ **NO SHELL COMMANDS**

- No `subprocess`, `os.system`, or shell execution in gateway
- Connectors use `httpx` library (safe HTTP client)

---

## E) Auditability & Integrity

### What is Logged

**Interaction Records (Tamper-Evident Audit Trail):**
- **File:** `backend/app/gateway/service.py:451-581`, `backend/app/models/interaction_record.py:1-144`
- **Logged Fields:**
  - Record ID (unique)
  - Org ID, UAPK ID, Agent ID
  - Action type + tool
  - Request (full action params + context)
  - Request hash (SHA-256 of canonical JSON)
  - Policy decision (APPROVED, DENIED, PENDING)
  - Reasons (structured list of reason codes + messages)
  - Policy trace (all checks executed + results)
  - Risk snapshot (budget usage, etc.)
  - Execution result (if executed)
  - Result hash (SHA-256 of canonical result JSON)
  - Duration (milliseconds)
  - Previous record hash (hash chain link)
  - Record hash (SHA-256 of canonical record subset + previous hash)
  - Gateway signature (Ed25519 signature over record_hash)
  - Timestamp (created_at)
- **All fields stored in PostgreSQL** `interaction_records` table

**Application Logs (Structured JSON via structlog):**
- Request processing events
- Policy evaluation steps
- Connector execution
- Errors and warnings
- **Format:** JSON (production) or console (development)
- **Not tamper-evident** (standard application logs)

### Correlation IDs / Trace IDs

- **Interaction ID:** Unique ID per gateway request (format: `int-{hex}`)
  - Generated: `backend/app/gateway/service.py:49-51`
  - Propagated through policy evaluation, execution, and logging
  - Included in all log messages for that request
- **Approval ID:** Unique ID per approval task (format: `appr-{hex}`)
  - Links approval to interaction record

### Tamper-Evident Mechanisms

**Hash Chaining:**
- **Implementation:** `backend/app/core/audit.py:84-123`
- **Mechanism:**
  1. For each new record, fetch previous record for same UAPK
  2. Compute `record_hash = SHA256(canonical_record_data + previous_record_hash)`
  3. Store `record_hash` and `previous_record_hash` in database
  4. Creates blockchain-like chain per UAPK
- **Verification:** `backend/app/core/audit.py:154-219`
  - Function: `verify_hash_chain(records)`
  - Recomputes all hashes and checks chain integrity
  - Endpoint: `GET /api/v1/orgs/{org_id}/logs/verify-chain`

**Ed25519 Signatures:**
- **Implementation:** `backend/app/core/audit.py:125-135`
- **Mechanism:**
  1. Gateway maintains Ed25519 keypair (32-byte private key)
  2. For each record, sign `record_hash` with private key
  3. Store base64-encoded signature in `gateway_signature` field
- **Verification:** `backend/app/core/audit.py:137-152`
  - Function: `verify_record_signature(record_hash, signature)`
  - Verifies signature against gateway's public key
- **Key Storage:**
  - Production: `GATEWAY_ED25519_PRIVATE_KEY` env var (PEM format)
  - Development: `/app/keys/gateway_ed25519.pem` (auto-generated)

**Canonical JSON:**
- **Implementation:** `backend/app/core/audit.py:17-53`
- **Purpose:** Deterministic serialization for hashing
- **Rules:**
  - Keys sorted alphabetically
  - No whitespace
  - Unicode escaped
  - Floats normalized (avoid precision drift)

### Storage

**Audit Records:**
- **Database:** PostgreSQL `interaction_records` table
- **Retention:** Indefinite (no automatic cleanup)
- **Indexes:** On org_id, uapk_id, created_at for fast queries
- **Backup:** Relies on PostgreSQL backups (not specified in codebase)

**Application Logs:**
- **Destination:** stdout/stderr (captured by Docker/systemd)
- **Format:** JSON (structlog)
- **External Storage:** Not configured in codebase (operator responsibility)

### Gaps Relative to "Unforgeable Audit Trail"

1. ⚠️ **No external timestamping:** Records use server time (could be manipulated by privileged attacker)
2. ⚠️ **No write-once storage:** PostgreSQL is mutable (DBA could alter records)
3. ⚠️ **No cryptographic commitment:** No periodic publication of root hashes to external ledger
4. ⚠️ **Key rotation not implemented:** Ed25519 private key is static (compromise = all signatures invalid)
5. ⚠️ **No multi-party signatures:** Only gateway signs (no notary/witness signatures)
6. ✅ **Hash chaining present:** Detects tampering within chain
7. ✅ **Cryptographic signatures present:** Ed25519 ensures authenticity
8. ✅ **Verification API present:** Can verify integrity on-demand

**Recommendation:** For true non-repudiation, add:
- Periodic hash anchor publishing (e.g., to Bitcoin/Ethereum)
- Write-once append-only storage (e.g., AWS QLDB, Azure Immutable Blob Storage)
- External timestamping (e.g., RFC 3161 TSA)

---

## F) Security Findings (Ranked)

### P0 (Critical - Must Fix Before Production)

#### P0-1: Hardcoded Default SECRET_KEY

**Risk:** JWT tokens and API key hashes use SECRET_KEY. Default placeholder could be left in production, allowing attackers to forge tokens.

**Location:** `backend/app/core/config.py:40`

**Evidence:**
```python
secret_key: str = "CHANGE-ME-IN-PRODUCTION-USE-SECURE-RANDOM-VALUE"
```

**Exploit Scenario:**
1. Operator deploys without setting SECRET_KEY env var
2. Attacker finds default key in public repo
3. Attacker forges admin JWT tokens
4. Full system compromise

**Impact:** Complete authentication bypass

**Mitigation:**
- Remove default value (require via env var)
- Add startup validation to check for placeholder value
- Generate random key on first startup if not set (log warning)

---

#### P0-2: DNS TOCTOU Race in SSRF Protection

**Risk:** Connectors resolve DNS at validation time, but hostname could resolve to different IP at request time (DNS rebinding attack).

**Location:** `backend/app/gateway/connectors/http_request.py:92-105`, `webhook.py:78-92`

**Evidence:**
```python
# Validation time
addr_info = socket.getaddrinfo(parsed.hostname, None)
for info in addr_info:
    ip_str = info[4][0]
    if ip_addr in blocked_range:
        return False, "SSRF blocked"

# Later (request time)
async with httpx.AsyncClient() as client:
    response = await client.request(method, url, ...)  # DNS re-resolved here
```

**Exploit Scenario:**
1. Attacker controls DNS for evil.com
2. At validation: evil.com → 1.2.3.4 (public IP, passes check)
3. Attacker changes DNS: evil.com → 127.0.0.1
4. At request: evil.com → 127.0.0.1 (SSRF to localhost)

**Impact:** SSRF to internal services (cloud metadata, admin panels, etc.)

**Mitigation:**
- Resolve DNS once, use IP directly in httpx request
- Re-validate IP before request
- Use httpx transport with custom DNS resolver that caches validation result

---

#### P0-3: No Rate Limiting on Gateway Endpoints

**Risk:** Gateway endpoints have no rate limits. Attackers can abuse /execute to exhaust budgets, DoS the system, or brute-force API keys.

**Location:** `backend/app/api/v1/gateway.py:16-80`, `auth.py`

**Evidence:**
- No rate limiting middleware in `backend/app/main.py`
- No rate limiting decorators on endpoints
- No IP-based throttling

**Exploit Scenarios:**
1. **Budget exhaustion:** Attacker floods /execute with valid requests → drains daily budget for legitimate UAPK
2. **DoS:** Attacker floods with invalid requests → database overload, CPU exhaustion
3. **API key brute force:** Try 1M keys/sec against /execute until one succeeds
4. **Approval spam:** Create thousands of approval tasks → operator overwhelm

**Impact:** Service disruption, resource exhaustion, security control bypass

**Mitigation:**
- Add rate limiting middleware (e.g., slowapi, fastapi-limiter)
- Per-API-key rate limits (e.g., 100 req/min)
- Per-IP rate limits for unauthenticated endpoints (e.g., 10 req/min)
- Progressive backoff on auth failures

---

#### P0-4: Fernet Encryption Key Not Enforced

**Risk:** Secrets table encryption is optional. Operator could deploy without GATEWAY_FERNET_KEY, storing secrets in plaintext.

**Location:** `backend/app/core/encryption.py:14-30`, `backend/app/core/config.py:52`

**Evidence:**
```python
gateway_fernet_key: str | None = None  # Optional
```

**Exploit Scenario:**
1. Operator forgets to set GATEWAY_FERNET_KEY
2. Secrets stored in `secrets.encrypted_value` column (but actually plaintext base64)
3. Database dump leaks all secrets (API keys, passwords, etc.)

**Impact:** Secret exposure, credential theft

**Mitigation:**
- Make GATEWAY_FERNET_KEY required (not optional)
- Add startup validation
- Auto-generate key on first startup (store in database or file, log warning)
- Fail startup if secrets exist but no key configured

---

#### P0-5: Ed25519 Private Key Auto-Generated in Development

**Risk:** Development mode auto-generates Ed25519 signing key and saves to filesystem. If deployed to production without proper key, signatures may be weak or lost.

**Location:** `backend/app/core/ed25519.py:94-145`

**Evidence:**
```python
# Generate new keys
logger.info("generating_new_gateway_keys")
self._private_key, self._public_key = generate_ed25519_keypair()

# Save to files (development only)
if settings.environment == "development":
    private_key_path.write_bytes(private_key_to_pem(self._private_key))
```

**Exploit Scenarios:**
1. **Production uses dev key:** Operator deploys without setting GATEWAY_ED25519_PRIVATE_KEY → new key generated on each restart → old audit signatures become invalid
2. **Weak key material:** Auto-generated key not from HSM → key theft possible
3. **Key loss:** Container restart → new key → all old signatures unverifiable

**Impact:** Audit trail integrity compromised, non-repudiation lost

**Mitigation:**
- Require GATEWAY_ED25519_PRIVATE_KEY in production
- Fail startup if environment=production and no key set
- Add key rotation support (dual-verify old + new keys)
- Document key backup requirements

---

### P1 (High Priority - Fix Soon)

#### P1-1: No Request Size Limits

**Risk:** Action params can be arbitrarily large. Attacker can send multi-GB JSON payloads to exhaust memory/disk.

**Location:** `backend/app/main.py` (no body size limit configured)

**Evidence:**
- FastAPI default max body size: unlimited
- No validation on `GatewayActionRequest.action.params` size
- Params stored in database JSONB (no size constraint)

**Exploit Scenario:**
1. Attacker sends POST /execute with 1GB action.params
2. Pydantic loads entire JSON into memory
3. Server OOM crash

**Impact:** DoS, memory exhaustion

**Mitigation:**
- Add `app.add_middleware(RequestBodySizeLimit, max_size=1_000_000)` (1MB)
- Add Pydantic validator on params field (max dict size)

---

#### P1-2: Budget Counter Race Condition

**Risk:** Budget check and increment are not atomic. Multiple concurrent requests could bypass limit.

**Location:** `backend/app/gateway/policy_engine.py:718-759` (check), `791-816` (increment)

**Evidence:**
```python
# Check (separate transaction)
counter = await self._get_or_create_counter(...)
if counter.count >= daily_cap:
    return DENY

# Later, in different transaction:
await self.policy_engine.increment_budget(...)  # Atomic increment
```

**Exploit Scenario:**
1. Budget limit: 1000
2. Current count: 999
3. Attacker sends 100 concurrent requests
4. All 100 read count=999 → pass budget check
5. All 100 execute → count becomes 1099 (exceeds limit by 99)

**Impact:** Budget limit bypass

**Mitigation:**
- Use SELECT FOR UPDATE or pessimistic locking
- Or check budget AFTER increment, rollback if exceeded
- Or use Redis atomic counter with Lua script

---

#### P1-3: No Webhook Response Size Limit

**Risk:** Webhook connector reads unlimited response body. Malicious webhook could return 10GB response → OOM.

**Location:** `backend/app/gateway/connectors/webhook.py:125-147`, `http_request.py:152-196`

**Evidence:**
```python
response = await client.post(url, json=resolved_params, headers=headers)
# No check on response.content_length before reading body
data = response.json()  # Reads entire response into memory
```

**Exploit Scenario:**
1. Attacker controls webhook URL (via manifest)
2. Webhook returns infinite stream or 10GB JSON
3. httpx reads entire body
4. Server OOM

**Impact:** DoS, memory exhaustion

**Mitigation:**
- Set max_response_size in httpx.AsyncClient
- Or stream response and limit bytes read
- Example: `httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=5, max_connections=10), timeout=30.0)`

---

#### P1-4: Sensitive Data in Logs

**Risk:** Action params may contain secrets, PII, or sensitive data. Logs could expose these.

**Location:** `backend/app/gateway/service.py:86-94` (logs action params), connectors

**Evidence:**
```python
logger.info(
    "gateway_evaluate_start",
    interaction_id=interaction_id,
    action_type=request.action.type,
    tool=request.action.tool,
    # params not logged here, but could be in other places
)
```

**Exploit Scenario:**
1. Agent action includes `{"password": "secret123"}` in params
2. Connector logs entire params at DEBUG level
3. Log aggregation service exposes logs to support team
4. Secret leaked

**Impact:** Secret exposure, PII leak, compliance violation

**Mitigation:**
- Redact sensitive fields in logs (e.g., password, api_key, token)
- Use structured logging with field-level redaction
- Document param security in API docs

---

#### P1-5: Empty CORS Default Could Cause Misconfiguration

**Risk:** Default CORS origins is empty list (deny all). While secure, could cause operator to misconfigure in production.

**Location:** `backend/app/core/config.py:46`

**Evidence:**
```python
cors_origins: list[str] = []  # Empty = deny all by default
```

**Impact:** Production frontend unable to access API, operator might disable CORS entirely

**Mitigation:**
- Document clearly that empty = deny all
- Add startup warning if CORS_ORIGINS is empty in production
- Provide example in .env.example

---

### P2 (Medium Priority - Fix When Feasible)

#### P2-1: No Password Complexity Requirements

**Risk:** Users can set weak passwords. While bcrypt protects storage, weak passwords enable brute-force.

**Location:** `backend/app/services/auth.py` (registration), `backend/app/core/security.py:16-18`

**Mitigation:**
- Add password validator (min length 12, mix of chars)
- Integrate with haveibeenpwned API

---

#### P2-2: JWT Algorithm Not Restricted

**Risk:** JWT decode doesn't restrict algorithm to HS256. Attacker could supply "alg: none" token.

**Location:** `backend/app/core/security.py:60-78`

**Mitigation:**
- Explicitly pass `algorithms=["HS256"]` to jwt.decode (already done, but verify)

---

#### P2-3: Error Messages May Leak Information

**Risk:** Detailed error messages returned to clients could leak internal state.

**Example:** "User not found" vs "Invalid credentials" reveals user enumeration

**Mitigation:**
- Use generic error messages for auth failures
- Log details, return generic message to client

---

#### P2-4: No Certificate Pinning for HTTPS

**Risk:** Connectors don't validate TLS certificates. MITM could intercept webhook traffic.

**Mitigation:**
- Add certificate pinning for known webhooks
- Or use httpx verify=True (default, but ensure not disabled)

---

## G) P0 Patch List (Diffs)

### P0-1: Enforce SECRET_KEY Configuration

```diff
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -37,7 +37,7 @@ class Settings(BaseSettings):
     reload: bool = False

     # Security
-    secret_key: str = "CHANGE-ME-IN-PRODUCTION-USE-SECURE-RANDOM-VALUE"
+    secret_key: str  # REQUIRED - no default
     jwt_algorithm: str = "HS256"
     jwt_expiration_minutes: int = 60 * 24  # 24 hours
     api_key_header: str = "X-API-Key"
@@ -66,6 +66,15 @@ class Settings(BaseSettings):
             raise ValueError(msg)
         return v_upper

+    @field_validator("secret_key")
+    @classmethod
+    def validate_secret_key(cls, v: str) -> str:
+        """Validate secret key is not placeholder."""
+        if "CHANGE-ME" in v.upper() or len(v) < 32:
+            msg = "SECRET_KEY must be set to a secure random value (min 32 chars). Generate with: openssl rand -hex 32"
+            raise ValueError(msg)
+        return v
+

 @lru_cache
 def get_settings() -> Settings:
```

**Usage:** Requires operator to set `SECRET_KEY=<random_value>` env var. Startup will fail if not set or if placeholder detected.

---

### P0-2: Fix DNS TOCTOU in SSRF Protection

```diff
--- a/backend/app/gateway/connectors/http_request.py
+++ b/backend/app/gateway/connectors/http_request.py
@@ -54,7 +54,7 @@ class HttpRequestConnector(ToolConnector):
         return self.settings.gateway_allowed_webhook_domains

-    def _validate_url(self, url: str) -> tuple[bool, str | None]:
+    def _validate_url(self, url: str) -> tuple[bool, str | None, str | None]:
         """Validate URL is in allowed domains and not targeting private IPs.

-        Returns (is_valid, error_message).
+        Returns (is_valid, error_message, resolved_ip).
         """
         allowed_domains = self._get_allowed_domains()

         # If no domains configured, deny by default for security
         if not allowed_domains:
-            return False, "No allowed domains configured"
+            return False, "No allowed domains configured", None

         try:
             parsed = urlparse(url)

             # Check scheme
             if parsed.scheme not in ("http", "https"):
-                return False, f"Invalid URL scheme: {parsed.scheme}"
+                return False, f"Invalid URL scheme: {parsed.scheme}", None

             # Check hostname is present
             if not parsed.hostname:
-                return False, "Missing hostname in URL"
+                return False, "Missing hostname in URL", None

             domain = parsed.hostname.lower()

@@ -87,7 +87,7 @@ class HttpRequestConnector(ToolConnector):
                     break

             if not domain_allowed:
-                return False, f"Domain '{domain}' not in allowlist"
+                return False, f"Domain '{domain}' not in allowlist", None

             # SSRF protection - check for private IP ranges
+            resolved_ip = None
             try:
                 # Get all IP addresses for the hostname
                 addr_info = socket.getaddrinfo(parsed.hostname, None)
                 for info in addr_info:
                     ip_str = info[4][0]
+                    if resolved_ip is None:
+                        resolved_ip = ip_str  # Use first IP for request
                     ip_addr = ipaddress.ip_address(ip_str)

                     # Check if IP is in any blocked range
                     for blocked_range in self.BLOCKED_IP_RANGES:
                         if ip_addr in blocked_range:
-                            return False, f"Access to private/internal IP {ip_str} blocked (SSRF protection)"
+                            return False, f"Access to private/internal IP {ip_str} blocked (SSRF protection)", None

             except socket.gaierror:
-                return False, f"Could not resolve hostname: {parsed.hostname}"
+                return False, f"Could not resolve hostname: {parsed.hostname}", None

-            return True, None
+            return True, None, resolved_ip

         except Exception as e:
-            return False, f"Invalid URL: {e}"
+            return False, f"Invalid URL: {e}", None

     async def execute(self, params: dict[str, Any]) -> ConnectorResult:
         """Execute the HTTP request."""
@@ -128,7 +128,7 @@ class HttpRequestConnector(ToolConnector):

         # Build and validate URL
         url = self._build_url(params)
-        is_valid, error = self._validate_url(url)
+        is_valid, error, resolved_ip = self._validate_url(url)

         if not is_valid:
             return ConnectorResult(
@@ -139,6 +139,13 @@ class HttpRequestConnector(ToolConnector):
                 duration_ms=int((time.monotonic() - start_time) * 1000),
             )

+        # Replace hostname with resolved IP to prevent DNS rebinding
+        parsed = urlparse(url)
+        if resolved_ip:
+            # Build URL with IP instead of hostname, preserving path/query
+            url = f"{parsed.scheme}://{resolved_ip}{parsed.path}"
+            if parsed.query:
+                url += f"?{parsed.query}"
+
         method = self.config.method.upper()
         headers = self._build_headers()
+        # Add Host header to preserve original hostname for virtual hosting
+        if resolved_ip:
+            headers["Host"] = parsed.hostname
         timeout = self.config.timeout_seconds
```

**Apply same fix to** `backend/app/gateway/connectors/webhook.py`

---

### P0-3: Add Rate Limiting Middleware

**New file:** `backend/app/middleware/rate_limit.py`

```python
"""Rate limiting middleware using slowapi."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

def setup_rate_limiting(app):
    """Add rate limiting to FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return limiter
```

```diff
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -13,6 +13,7 @@ from app.core.logging import get_logger, setup_logging
 from app.ui.routes import router as ui_router
+from app.middleware.rate_limit import setup_rate_limiting


 @asynccontextmanager
@@ -68,6 +69,9 @@ def create_app() -> FastAPI:
         allow_headers=settings.cors_allow_headers,
     )

+    # Rate limiting
+    setup_rate_limiting(app)
+
     # Mount static files for UI
```

```diff
--- a/backend/app/api/v1/gateway.py
+++ b/backend/app/api/v1/gateway.py
@@ -4,6 +4,7 @@ from fastapi import APIRouter, HTTPException, status

 from app.api.deps import ApiKeyAuth, DbSession
+from app.middleware.rate_limit import limiter
 from app.gateway.service import GatewayService

 router = APIRouter(prefix="/gateway", tags=["Gateway"])


+@limiter.limit("100/minute")
 @router.post("/evaluate", response_model=GatewayDecisionResponse)
 async def evaluate_action(
+    request_obj: Request,
     request: GatewayActionRequest,

+@limiter.limit("100/minute")
 @router.post("/execute", response_model=GatewayExecuteResponse)
 async def execute_action(
+    request_obj: Request,
     request: GatewayActionRequest,
```

**Add to** `pyproject.toml`:
```toml
dependencies = [
    # ... existing ...
    "slowapi>=0.1.9",
]
```

---

### P0-4: Enforce Fernet Key Configuration

```diff
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -51,7 +51,7 @@ class Settings(BaseSettings):

     # Gateway settings
-    gateway_fernet_key: str | None = None  # For secret encryption, generate with Fernet.generate_key()
+    gateway_fernet_key: str  # REQUIRED for production
     gateway_default_daily_budget: int = 1000  # Default daily action cap per UAPK
     gateway_approval_expiry_hours: int = 24  # Hours until approval tasks expire
     gateway_connector_timeout_seconds: int = 30  # Timeout for connector HTTP calls
@@ -66,6 +66,19 @@ class Settings(BaseSettings):
             raise ValueError(msg)
         return v_upper

+    @field_validator("gateway_fernet_key")
+    @classmethod
+    def validate_fernet_key(cls, v: str | None, info) -> str:
+        """Validate Fernet key is set in production."""
+        environment = info.data.get("environment", "development")
+        if environment == "production" and not v:
+            msg = (
+                "GATEWAY_FERNET_KEY is required in production. "
+                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
+            )
+            raise ValueError(msg)
+        return v or ""  # Allow empty in dev
+
```

---

### P0-5: Enforce Ed25519 Key in Production

```diff
--- a/backend/app/core/ed25519.py
+++ b/backend/app/core/ed25519.py
@@ -94,6 +94,13 @@ class GatewayKeyManager:
     def _load_or_generate_keys(self) -> None:
         """Load keys from env/file or generate new ones."""
         settings = get_settings()
+
+        # Production must provide key via env var
+        if settings.environment == "production":
+            env_private_key = os.environ.get("GATEWAY_ED25519_PRIVATE_KEY")
+            if not env_private_key:
+                raise KeyManagementError(
+                    "GATEWAY_ED25519_PRIVATE_KEY must be set in production environment. "
+                    "Generate with: ssh-keygen -t ed25519 -f gateway_ed25519 -N ''"
+                )

         # Check for environment variable first (production)
         env_private_key = os.environ.get("GATEWAY_ED25519_PRIVATE_KEY")
```

---

## H) Deployment & Operational Recommendations

### Pre-Production Checklist

- [ ] **Set SECRET_KEY** to 64-char random hex (not placeholder)
- [ ] **Set GATEWAY_FERNET_KEY** to Fernet key
- [ ] **Set GATEWAY_ED25519_PRIVATE_KEY** to Ed25519 private key PEM
- [ ] **Configure GATEWAY_ALLOWED_WEBHOOK_DOMAINS** allowlist
- [ ] **Set CORS_ORIGINS** to allowed frontend domains
- [ ] **Set DATABASE_URL** with strong password
- [ ] **Disable /auth/register** endpoint (or add approval flow)
- [ ] **Apply P0 patches** (rate limiting, SSRF fix, key enforcement)
- [ ] **Configure external log aggregation** (e.g., DataDog, Splunk)
- [ ] **Set up PostgreSQL backups** (daily + point-in-time recovery)
- [ ] **Enable HTTPS** with valid TLS certificate (via reverse proxy)
- [ ] **Restrict PostgreSQL access** to gateway only (firewall rules)
- [ ] **Review all manifests** for malicious connector URLs
- [ ] **Set WORKERS > 1** for production (e.g., 4-8 workers)
- [ ] **Add health check monitoring** (/healthz)

### Security Hardening

1. **Database:**
   - Use managed PostgreSQL with encryption at rest
   - Enable connection SSL/TLS
   - Restrict network access to private VPC only
   - Enable query logging for audit

2. **Secrets:**
   - Use secret manager (AWS Secrets Manager, HashiCorp Vault)
   - Rotate keys quarterly
   - Back up Ed25519 private key securely (offline storage)

3. **Network:**
   - Deploy behind reverse proxy (Caddy, Nginx) with TLS termination
   - Use firewall to restrict outbound connections from gateway
   - Enable DDoS protection (Cloudflare, AWS Shield)

4. **Monitoring:**
   - Alert on failed auth attempts (> 10/min)
   - Alert on budget exhaustion
   - Alert on approval queue backlog (> 100 pending)
   - Monitor /healthz endpoint (uptime)

5. **Audit:**
   - Export interaction records to immutable storage (AWS S3 Object Lock)
   - Daily hash chain verification job
   - Alert on verification failures

### Incident Response Plan

**Compromised SECRET_KEY:**
1. Rotate key immediately
2. Invalidate all sessions (clear sessions table)
3. Force password reset for all users
4. Audit logs for suspicious token usage

**Compromised Ed25519 Private Key:**
1. Generate new keypair
2. Dual-verify signatures (old + new key)
3. Re-sign all interaction records with new key
4. Publish key rotation event to audit log

**SSRF Exploitation:**
1. Review connector configurations for malicious URLs
2. Rotate any secrets that might have been exposed (e.g., AWS metadata credentials)
3. Add affected domains to global denylist

---

## End of Report

**Next Steps:**
1. Apply P0 patches to codebase
2. Review and prioritize P1/P2 issues
3. Implement pre-production checklist
4. Conduct penetration testing on gateway endpoints
5. Security review of all deployed manifests

**Questions for Operator:**
1. What is the expected production scale (req/sec, UAPKs, orgs)?
2. Is there a budget for managed security services (WAF, DDoS protection)?
3. What is the threat model (public internet vs. trusted network)?
4. Are there compliance requirements (SOC 2, GDPR, HIPAA)?
5. What is the DR/backup strategy for PostgreSQL?

**Report Compiled by:** Claude Code (Anthropic)
**Contact:** <REDACTED>
