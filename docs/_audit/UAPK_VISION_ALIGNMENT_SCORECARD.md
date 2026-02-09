# UAPK Vision Alignment Scorecard

**Document Version**: 2.0.0
**Generated**: 2026-02-08
**Evaluation Subject**: OpsPilotOS Reference Implementation
**Comparison Baseline**: UAPK Gateway v0.1 + Canonical Vision Documents
**Evaluator**: Claude Code (Automated Analysis)

---

## Executive Summary

This scorecard evaluates the **OpsPilotOS reference implementation** against the **UAPK vision** as defined in the canonical repository documents:

- README.md (UAPK Gateway overview)
- website/docs/architecture/*.md (architecture, concepts, security)
- DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md
- DLTEST/SYSTEM_ARCHITECTURE_DIAGRAM.md
- manifests/opspilotos.uapk.jsonld

### Overall Alignment Score

**48/75 (64%) - Good foundation with implementation gaps**

### Pillar Breakdown

| Pillar | Score | Max | Percent | Grade |
|--------|-------|-----|---------|-------|
| **A. UAPK Gateway (Enforcement & Operations)** | 34 | 45 | 76% | ✅ Strong |
| **B. UAPK Protocol (Canonical Spec & Interoperability)** | 8 | 15 | 53% | ⚠️ Moderate |
| **C. UAPK Compiler (Instantiation & Fleet Management)** | 6 | 15 | 40% | ⚠️ Emerging |

### Key Findings

**Strengths**:
- ✅ Excellent deterministic execution and plan locking (5/5)
- ✅ Strong policy enforcement with tool permissions, deny rules, rate limits (4/5)
- ✅ Functional HITL workflow with approval tracking (4/5)
- ✅ Hash-chained audit trail with merkle root (4/5)
- ✅ Observability with health checks and metrics (4/5)

**Critical Gaps**:
- ⚠️ **Missing connector framework** - No ToolConnector abstraction, SSRF protection, or external tool execution (2/5)
- ⚠️ **Schema divergence** - OpsPilotOS manifest incompatible with UAPK Gateway canonical schema (2/5)
- ⚠️ **No override tokens** - Approvals don't generate Ed25519-signed tokens for retry (4/5, needs 5/5)
- ⚠️ **Missing Ed25519 audit signatures** - Events lack gateway signatures (4/5, needs 5/5)
- ⚠️ **No fleet management** - Cannot deploy or govern multiple instances (0/5)

### Recommendation

**OpsPilotOS successfully extends the UAPK Gateway vision** into full autonomous business instantiation (adding tax/VAT, billing, NFT minting). However, to achieve full alignment:

1. **Converge on canonical schema** (Milestone 2) or formalize the extended schema
2. **Implement missing gateway components** (Milestone 1): override tokens, Ed25519 signatures, connector framework
3. **Add compiler/factory capabilities** (Milestone 3): templates, multi-instance deployment, fleet governance

**Timeline**: 11-15 weeks total (see UAPK_VISION_ALIGNMENT_SCORECARD_DIFF.md for detailed roadmap)

---

## Scoring Model

### Scale

| Score | Meaning | Criteria |
|-------|---------|----------|
| **0** | Not implemented | No code or placeholder only |
| **1** | Minimal stub | Basic structure, non-functional |
| **2** | Basic implementation | Works but significant gaps vs. vision |
| **3** | Functional implementation | Core functionality present, minor gaps |
| **4** | Production-ready | Solid implementation, polish needed |
| **5** | Exemplary | Exceeds vision requirements, reference quality |

### Rubrics by Pillar

**Pillar A (Gateway)**:
- 0: No policy enforcement or audit
- 1: Basic logging, no real enforcement
- 3: Policy checks work, audit log exists, some gaps
- 5: Production-grade enforcement, comprehensive audit, HITL, connectors

**Pillar B (Protocol)**:
- 0: No schema or validation
- 1: Custom format, no interoperability
- 3: Validated schema, some divergence from canonical
- 5: Fully conformant, versioned, interoperable with UAPK Gateway

**Pillar C (Compiler)**:
- 0: Single hardcoded instance
- 1: Plan resolution exists
- 3: Can deploy multiple instances with manual config
- 5: Template engine, multi-tenant factory, fleet governance, automated deployment

---

## Pillar A: UAPK Gateway (Enforcement & Operations)

**Vision**: "The agent firewall + black box recorder for high-stakes AI" (README.md:2) - non-bypassable enforcement point with policy, approvals, and tamper-evident audit logs.

**Score**: **34/45 (76%)** ✅ Strong

### A1. Policy Membrane (Tool Allow/Deny, Rate Limits, Action Gates)

**Score**: 4/5

**Current State**:
- ✅ PolicyEngine implemented with 5-step evaluation process
  - Step 1: Check tool permissions (agent → tool mapping)
  - Step 2: Check deny rules (blacklist)
  - Step 3: Check rate limits (sliding window)
  - Step 4: Check live action gates (HITL escalation in dry_run)
  - Step 5: Check execution mode constraints
- ✅ Tool permissions per agent defined in manifest (toolPermissions map)
- ✅ Deny rules: `delete_audit_events`, `modify_closed_invoices`
- ✅ Rate limiting: 100 actions/min (global), 500 invoices/day, 10 NFT mints/day
- ✅ Live action gates: 5 gated actions requiring approval in dry_run mode
- ✅ Decision model: ALLOW | DENY | ESCALATE

**Target State** (from UAPK Gateway README.md:84-96, backend/app/gateway/policy_engine.py):
- 15-step policy evaluation with structured trace:
  1. Manifest exists and active
  2. Capability token validation
  3. Override token validation
  4. Require capability token check
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
  15. Override token bypass
- Policy trace returned with decision (structured reasons)
- Capability-based security model (README.md:90-103)
- Budget limits, jurisdiction constraints, counterparty constraints

**Gap**:
- Missing capability token support (steps 2, 6, 9, 11-13)
- Missing override token validation (steps 3, 15)
- Missing amount caps per action
- Missing jurisdiction allowlist
- Missing counterparty constraints
- Missing daily budget cap tracking
- Missing structured policy trace
- Simplified 5-step vs. full 15-step evaluation

**Evidence**:
- Current: `uapk/policy.py:37-107` (PolicyEngine.evaluate)
- Current: `manifests/opspilotos.uapk.jsonld:30-56` (policyGuardrails)
- Target: `README.md:84-103` (capability tokens, budgets)
- Target: `website/docs/architecture/concepts.md:34-54` (capability token spec)

**Next Action**:
Implement capability token validation in PolicyEngine.evaluate() following backend/app/gateway/policy_engine.py pattern. Add CapabilityToken model with scoped constraints (amounts, jurisdictions, counterparties, expiry).

---

### A2. HITL Workflow (Approval Queues, Escalation, Overrides)

**Score**: 4/5

**Current State**:
- ✅ HITLRequest model with status tracking (uapk/db/models.py:178-189)
- ✅ Approval queue API endpoints (uapk/api/hitl.py:17-75)
- ✅ Status lifecycle: pending → approved/rejected
- ✅ Approved_by tracking (user_id)
- ✅ Approval reason recording
- ✅ Integration with policy engine (escalation on HITL gate hit)

**Target State** (from UAPK Gateway README.md:236-246):
- Approval creates Ed25519-signed override token
- Override token structure:
  - approval_id (reference to HITLRequest)
  - action_hash (binds to specific request)
  - 5-minute expiry (short-lived, single-use)
  - Ed25519 signature from gateway private key
- Agent retries action with `override_token` parameter
- PolicyEngine validates override token and grants ALLOW
- One-time-use enforced atomically (consumed_at timestamp)
- Approval expiry/timeout (60 minutes default)

**Gap**:
- Missing override token generation on approval
- Missing Ed25519 signing infrastructure for override tokens
- Missing override token validation in PolicyEngine
- Missing one-time-use consumption tracking
- Missing approval expiry/timeout logic
- Agent retry mechanism not documented (no override_token in API spec)

**Evidence**:
- Current: `uapk/api/hitl.py`, `uapk/db/models.py:178-189`
- Current: `manifests/opspilotos.uapk.jsonld:22-27` (approval workflow config)
- Target: `README.md:236-246` (approval workflow section)
- Target: `website/docs/architecture/concepts.md:34-42` (capability token as model)

**Next Action**:
Implement override token generation in HITLRequest.approve() using Ed25519 signing. Return override token in approval response. Add override_token validation in PolicyEngine step 3.

---

### A3. Auditability (Append-Only Logs, Hash-Chaining, Merkle Root, Replay)

**Score**: 4/5

**Current State**:
- ✅ Append-only JSONL audit log (uapk/audit.py:18-145)
- ✅ SHA-256 hash chaining (each event contains previousHash)
- ✅ Hash chain verification function (audit.verify_chain())
- ✅ Merkle root computation (audit.compute_merkle_root())
- ✅ Tamper-evident design (modification breaks chain)
- ✅ Event types: agent_action, policy_check, system, nft
- ⚠️ No Ed25519 signatures on individual events
- ⚠️ Audit log stored in JSONL file (not database)
- ⚠️ No S3 Object Lock exports

**Target State** (from UAPK Gateway README.md:115-125, website/docs/architecture/concepts.md:74-100):
- InteractionRecord model stored in PostgreSQL
- Every record includes:
  - `signature`: Ed25519 signature of record contents
  - `previous_hash`: hash including previous record ID
  - `gateway_signature`: signed by gateway private key
- Chain verification API endpoint: `GET /api/v1/logs/{id}/verify`
- Export audit bundle: `POST /api/v1/logs/export`
- S3 Object Lock for immutable compliance exports (optional)
- Query audit logs via API (filtering, pagination)
- Replay capability (re-execute from audit log)

**Gap**:
- Missing Ed25519 signatures on audit events
- Audit log not stored in database (file-only)
- Missing audit log query API endpoints
- Missing chain verification API endpoint
- Missing S3 Object Lock export capability
- Missing replay functionality
- No JSONL → database sync mechanism

**Evidence**:
- Current: `uapk/audit.py:18-145` (AuditLog class)
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:138-167` (hash chain documentation)
- Target: `website/docs/architecture/concepts.md:74-100` (InteractionRecord spec)
- Target: `README.md:240-247` (audit log endpoints)

**Next Action**:
Add Ed25519 signature to each audit event using gateway private key. Sign canonical JSON of event (excluding signature field itself). Store signature in eventSignature field.

---

### A4. Deterministic Execution (Plan Locking, Idempotency, Reproducible Runs)

**Score**: 5/5 ✅ Exemplary

**Current State**:
- ✅ Manifest → Plan resolution (uapk/interpreter.py:22-78)
- ✅ Deterministic plan hashing: SHA-256 of canonical JSON (sorted keys, no whitespace)
- ✅ plan.json (human-readable) + plan.lock.json (deterministic)
- ✅ manifestHash computed and stored in cryptoHeader
- ✅ planHash computed from resolved plan
- ✅ Idempotency window configured (manifest productOps.idempotencyWindowSeconds: 3600)
- ✅ Retry policy with exponential backoff (manifest productOps.retryPolicy)
- ✅ Same manifest → same planHash (verified in tests)

**Target State** (from UAPK Gateway README.md:91-95):
- Manifest hash computed and stored
- Deterministic policy evaluation (no randomness)
- Reproducible runs from same manifest + inputs

**Gap**:
- None significant. OpsPilotOS **exceeds** UAPK Gateway here by adding:
  - Full plan resolution step (not present in UAPK Gateway)
  - Dual output: plan.json + plan.lock.json
  - Comprehensive hash tracking (manifest + plan + merkle root)

**Evidence**:
- Current: `uapk/interpreter.py:22-78` (resolve_manifest function)
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:40-82` (cryptographic identity section)
- Current: `test_opspilotos.py:103-130` (hash verification tests)
- Target: `README.md:91-95` (manifest concept)

**Next Action**:
None required. This is exemplary implementation. Consider: Document plan resolution algorithm for external evaluators in architecture docs.

---

### A5. Observability (Metrics, Logs, Traces, Incident Lifecycle)

**Score**: 4/5

**Current State**:
- ✅ Health check endpoints: `/healthz`, `/readyz`
- ✅ Prometheus-compatible metrics endpoint: `/metrics`
- ✅ Structured logging with structlog (JSON format)
- ✅ Log levels configurable
- ✅ Metrics: `opspilotos_events_total{type="X"}` counter
- ✅ SREAgent for incident detection and management
- ✅ Incident workflow: detect → create_ticket → escalate
- ⚠️ No distributed tracing (OpenTelemetry mentioned but not implemented)
- ⚠️ Limited business metrics (only event counts)

**Target State** (from UAPK Gateway README.md:248-249):
- `/healthz` - Liveness probe (exists)
- `/readyz` - Readiness probe (exists)
- Structured logging (exists)
- Prometheus metrics (exists)
- Distributed tracing with OpenTelemetry (planned)
- Custom business metrics

**Gap**:
- Missing OpenTelemetry distributed tracing
- Limited business metrics (no latency, throughput, error rates per agent/workflow)
- No metrics dashboard or alerting configuration
- SREAgent exists but incident lifecycle incomplete (no auto-remediation)

**Evidence**:
- Current: `uapk/api/system.py:11-25` (health endpoints)
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:663-686` (observability section)
- Current: `manifests/opspilotos.uapk.jsonld:203-209` (SREAgent config)
- Target: `README.md:248-249` (health check endpoints)

**Next Action**:
Add business metrics: agent execution latency, workflow completion rate, approval queue depth, policy denial rate. Implement OpenTelemetry tracing for request flows.

---

### A6. Connector Framework (Tool Execution, SSRF Protection, External Tools)

**Score**: 2/5

**Current State**:
- ⚠️ No ToolConnector abstraction or framework
- ⚠️ Tools hardcoded in agent code (e.g., FulfillmentAgent.generate_content)
- ⚠️ No external tool execution (all tools are internal Python functions)
- ⚠️ No SSRF protection mechanisms
- ⚠️ No webhook, HTTP, or custom tool connectors
- ⚠️ Connector config in manifest (httpApi, database, objectStore) but not a framework

**Target State** (from UAPK Gateway README.md:70-86, website/docs/architecture/overview.md:22-26):
- ToolConnector framework for external tools:
  - Webhook connector (HTTP POST to external URL)
  - HTTP connector (generic HTTP requests with allowlist)
  - Mock connector (for testing)
  - Custom connectors (extensible)
- SSRF protection:
  - URL allowlist (manifest-defined)
  - Deny private IP ranges (10.0.0.0/8, 192.168.0.0/16, 127.0.0.0/8)
  - TLS verification enforced
- Tool execution flow:
  - PolicyEngine.evaluate() → ALLOW
  - GatewayService.execute_action() → ToolConnector.execute()
  - Result logged in InteractionRecord
- Tools configured in manifest with connector type

**Gap**:
- Missing entire ToolConnector framework
- No external tool execution capability
- No SSRF protection (critical security gap)
- No webhook/HTTP connectors
- Tools are hardcoded Python functions, not manifest-driven
- Cannot add custom tools without code changes

**Evidence**:
- Current: `manifests/opspilotos.uapk.jsonld:169-202` (saasModules.connectors - config only)
- Current: `uapk/agents/fulfillment.py:20-54` (hardcoded tools)
- Target: `README.md:27` (connector framework diagram)
- Target: `README.md:70-86` (tool execution section)

**Next Action**:
Implement ToolConnector abstraction with WebhookConnector and HTTPConnector subclasses. Add SSRF protection (allowlist + deny private IPs). Refactor agents to use connector framework.

---

### A7. Evidence-Grade Exports (Compliance Bundles, S3 Object Lock, Tamper-Proof)

**Score**: 1/5

**Current State**:
- ⚠️ Audit log is JSONL file (runtime/audit.jsonl)
- ⚠️ No export API endpoint
- ⚠️ No bundled export format (single file only)
- ⚠️ No S3 Object Lock integration
- ⚠️ No compliance bundle generation

**Target State** (from UAPK Gateway README.md:242-243):
- `POST /api/v1/logs/export` endpoint
- Export formats:
  - Full JSONL audit log
  - Filtered by time range, agent, action type
  - Bundled with verification metadata (chain proof, signature list)
- S3 Object Lock for immutable storage (compliance mode)
- Export includes:
  - Audit log events
  - Manifest snapshot
  - Signature verification keys
  - Chain verification proof

**Gap**:
- Missing export API endpoint entirely
- No S3 integration
- No bundled format with verification metadata
- No compliance bundle generation
- Cannot produce evidence-grade exports for auditors

**Evidence**:
- Current: `uapk/audit.py` (file-only logging)
- Target: `README.md:242-243` (audit log export)

**Next Action**:
Implement `POST /api/v1/audit/export` endpoint returning tar.gz bundle with: audit.jsonl, manifest.json, verification_proof.json (chain hashes, merkle root, signatures).

---

### A8. Secrets Management (Env Vars, Vault, Rotation)

**Score**: 2/5

**Current State**:
- ✅ Secret storage model (uapk/db/models.py:151-176) with Fernet encryption
- ✅ secrets.get_connector_secret() API
- ⚠️ Master key hardcoded in codebase (`MASTER_FERNET_KEY` constant)
- ⚠️ No environment variable integration for secrets
- ⚠️ No secrets rotation capability
- ⚠️ No external secrets manager (Vault, AWS Secrets Manager)

**Target State** (from UAPK Gateway website/docs/architecture/security.md:63-68):
- Secrets via environment variables (not hardcoded)
- Never logged or exposed in API responses
- Database credentials isolated in .env file
- Optional: Integration with HashiCorp Vault or AWS Secrets Manager
- Secrets rotation supported

**Gap**:
- Master key should be from environment variable (FERNET_KEY)
- No secrets rotation mechanism
- No Vault or external secrets manager integration
- Connector secrets hardcoded in manifest (should reference secret names)

**Evidence**:
- Current: `uapk/db/models.py:151-176` (Secret model)
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:775-789` (secret storage section)
- Target: `website/docs/architecture/security.md:63-68` (secrets management)

**Next Action**:
Move MASTER_FERNET_KEY to environment variable. Add secrets rotation API endpoint. Document connector secret references (use secret names in manifest, not values).

---

### A9. RBAC (Role-Based Access Control, Scoped Permissions)

**Score**: 3/5

**Current State**:
- ✅ Four roles defined: Owner, Admin, Operator, Viewer
- ✅ Role descriptions in manifest (governance.roles)
- ⚠️ RBAC not enforced on API endpoints (JWT auth exists but no role checks)
- ⚠️ No role-to-permission mapping
- ⚠️ No scoped permissions (all authenticated users have same access)

**Target State** (from UAPK Gateway website/docs/architecture/security.md:8-30):
- JWT tokens include role claim
- API endpoints enforce role-based access:
  - Owner: Full control, can delete org
  - Admin: Manage users, approve actions, view audit
  - Operator: Create projects, request deliverables, view invoices
  - Viewer: Read-only access
- Role checks in middleware or endpoint decorators
- Audit log records user role for all actions

**Gap**:
- RBAC defined but not enforced
- No role checks on API endpoints
- No middleware or decorators for role enforcement
- Role not included in JWT token claims
- Cannot restrict actions by role

**Evidence**:
- Current: `manifests/opspilotos.uapk.jsonld:20-21` (roles defined)
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:369-377` (governance roles)
- Target: `website/docs/architecture/security.md:8-16` (RBAC section)

**Next Action**:
Add role claim to JWT tokens. Implement role check decorators (@require_role("admin")). Enforce RBAC on all API endpoints per role definitions.

---

## Pillar B: UAPK Protocol (Canonical Spec & Interoperability)

**Vision**: Standardized manifest format, versioning, conformance, and attestation model for interoperability between UAPK Gateway instances and agent developers.

**Score**: **8/15 (53%)** ⚠️ Moderate

### B1. Manifest Semantics (JSON-LD Context, Schema, Module Contracts)

**Score**: 2/5

**Current State**:
- ✅ JSON-LD format with @context (manifests/opspilotos.uapk.jsonld:2)
- ✅ Pydantic schema for validation (uapk/manifest_schema.py)
- ✅ Six module structure: corporateModules, aiOsModules, saasModules, etc.
- ⚠️ **Incompatible with UAPK Gateway canonical schema**
- ⚠️ OpsPilotOS manifest is complex extended schema (250 lines)
- ⚠️ UAPK Gateway manifest is simple (agent, capabilities, constraints)

**Target State** (from website/docs/architecture/concepts.md:5-31):
- Canonical UAPK manifest format:
  ```json
  {
    "$schema": "https://uapk.dev/schemas/manifest.v1.json",
    "version": "1.0",
    "agent": {
      "id": "agent-001",
      "name": "Customer Support Bot",
      "version": "1.0.0",
      "organization": "org-acme"
    },
    "capabilities": {
      "requested": ["email:send", "crm:read", "crm:update"]
    },
    "constraints": {
      "max_actions_per_hour": 100,
      "require_human_approval": ["crm:delete"]
    }
  }
  ```
- Simple, focused schema for interoperability
- Module contracts defined separately (not in manifest)
- Schema versioning and migration path

**Gap**:
- OpsPilotOS manifest diverges significantly from canonical schema
- No `agent` object (uses @id, name, description instead)
- No simple `capabilities.requested` array (uses complex toolPermissions map)
- No simple `constraints` object (uses nested policyGuardrails)
- Cannot load OpsPilotOS manifest in UAPK Gateway without schema changes
- No schema migration or compatibility layer

**Evidence**:
- Current: `manifests/opspilotos.uapk.jsonld:1-250` (full manifest)
- Current: `uapk/manifest_schema.py:1-200` (Pydantic schema)
- Target: `website/docs/architecture/concepts.md:5-31` (canonical manifest)

**Next Action**:
Decision required: (1) Converge OpsPilotOS to canonical schema, OR (2) Formalize extended schema and document divergence rationale. Option 1 recommended for interoperability.

---

### B2. Versioning (Semantic Versioning, Migrations, Backward-Compat)

**Score**: 2/5

**Current State**:
- ✅ uapkVersion field exists (manifests/opspilotos.uapk.jsonld:4)
- ✅ cryptoHeader includes version info
- ⚠️ No semantic versioning policy documented
- ⚠️ No migration framework
- ⚠️ No backward compatibility guarantees
- ⚠️ Version changes require manual manifest editing

**Target State**:
- Semantic versioning: MAJOR.MINOR.PATCH
- Migration framework:
  - `uapk migrate --from 0.1 --to 0.2 manifest.jsonld`
  - Automated field mapping
  - Deprecation warnings
- Backward compatibility:
  - Gateway supports manifests from N-1 and N-2 versions
  - Clear breaking change documentation
- Version negotiation in API (Accept: application/vnd.uapk.v1+json)

**Gap**:
- No versioning policy documented
- No migration tooling
- No backward compatibility testing
- Version bumps are manual and error-prone
- Cannot smoothly upgrade manifests

**Evidence**:
- Current: `manifests/opspilotos.uapk.jsonld:4` (uapkVersion: "0.1")
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:817-845` (versioning section)

**Next Action**:
Document semantic versioning policy in docs/protocol/versioning.md. Implement `uapk manifest migrate` command with 0.1 → 0.2 example migration.

---

### B3. Conformance (Validation Rules, Third-Party Verification, Test Suite)

**Score**: 2/5

**Current State**:
- ✅ `uapk verify` command validates manifest (uapk/cli.py)
- ✅ Pydantic validation on load
- ⚠️ No conformance test suite
- ⚠️ No third-party verification workflow
- ⚠️ Validation rules not documented separately from code

**Target State**:
- Conformance test suite:
  - tests/conformance/ with 20+ test cases
  - Valid manifests (positive tests)
  - Invalid manifests (negative tests)
  - Edge cases (empty fields, max lengths, special chars)
- Third-party verification:
  - External validators can run conformance tests
  - CLI command: `uapk conformance-test manifest.jsonld`
  - Machine-readable test results (JUnit XML, JSON)
- Validation rules documented in specification

**Gap**:
- No tests/conformance/ directory
- No separate test manifests for validation
- Validation rules embedded in Pydantic schemas (not documented)
- Third parties cannot verify conformance independently

**Evidence**:
- Current: `uapk/cli.py:30-60` (verify command)
- Current: `uapk/manifest_schema.py` (Pydantic schemas)

**Next Action**:
Create tests/conformance/ directory with 10 valid and 10 invalid manifest examples. Add `uapk conformance-test` command that runs test suite and reports pass/fail.

---

### B4. Attestation Model (Claims, Signatures, Evidence Bundles)

**Score**: 1/5

**Current State**:
- ✅ Manifest includes cryptoHeader with signature field
- ⚠️ Signature is placeholder ("dev-signature-placeholder")
- ⚠️ No real signing implementation
- ⚠️ No verification of manifest signatures
- ⚠️ No attestation claims model

**Target State**:
- Manifest signing:
  - Ed25519 signature of canonical JSON (excluding cryptoHeader)
  - Signature stored in cryptoHeader.signature
  - Public key stored in cryptoHeader.signedBy (or key ID)
- Signature verification:
  - `uapk verify --check-signature manifest.jsonld`
  - Verify against known public keys
- Attestation claims:
  - Who: signedBy (identity)
  - What: manifestHash (content)
  - When: signedAt (timestamp)
  - Evidence: audit trail, test results

**Gap**:
- No real Ed25519 signing implementation
- Signatures are placeholders (not cryptographically valid)
- No public key management (registry, distribution)
- No attestation claims model documented
- Cannot verify manifest authenticity

**Evidence**:
- Current: `manifests/opspilotos.uapk.jsonld:9-17` (cryptoHeader with placeholder)
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:72-81` (signature section)

**Next Action**:
Implement Ed25519 signing in `uapk sign manifest.jsonld --key private.pem`. Store real signature in cryptoHeader.signature. Add `uapk verify --check-signature` command.

---

### B5. Security Model (Key Mgmt, Revocation, Trust Anchors)

**Score**: 1/5

**Current State**:
- ⚠️ No key management framework
- ⚠️ Keys assumed to exist but not managed
- ⚠️ No revocation mechanism
- ⚠️ No trust anchors defined

**Target State**:
- Key management:
  - Ed25519 key pairs generated via CLI (`uapk keygen`)
  - Private keys stored securely (encrypted, HSM for production)
  - Public keys distributed via key registry or PKI
- Revocation:
  - Certificate Revocation List (CRL) or OCSP
  - Revoked signatures rejected by verify command
- Trust anchors:
  - Root signing authorities (e.g., "UAPK Foundation")
  - Chain of trust (root → intermediate → manifest signer)
  - Trust policy configurable (which roots to trust)

**Gap**:
- No `uapk keygen` command
- No key storage or distribution mechanism
- No revocation support
- No trust model documented
- Keys are assumed to be managed out-of-band

**Evidence**:
- Current: No key management implementation
- Target: Standard PKI/certificate practices

**Next Action**:
Implement `uapk keygen` command to generate Ed25519 key pairs. Document key management best practices in docs/security/key-management.md.

---

## Pillar C: UAPK Compiler (Instantiation & Fleet Management)

**Vision**: Turn manifest templates into deployed instances with multi-tenant isolation, upgrade management, and fleet governance at scale.

**Score**: **6/15 (40%)** ⚠️ Emerging

### C1. Template → Instance Compilation

**Score**: 2/5

**Current State**:
- ✅ Plan resolution: manifest → plan.json + plan.lock.json (uapk/interpreter.py)
- ✅ Deterministic compilation (same manifest → same plan)
- ⚠️ No template variables or substitution
- ⚠️ Cannot parameterize manifests (no {{org_name}}, {{api_key}}, etc.)
- ⚠️ Each instance requires a separate manifest file

**Target State**:
- Template manifests with variables:
  ```json
  {
    "name": "{{business_name}}",
    "agents": [
      {"id": "{{agent_prefix}}-intake", ...}
    ],
    "connectors": {
      "database": {"connection_string": "{{DATABASE_URL}}"}
    }
  }
  ```
- Compilation command:
  - `uapk compile template.jsonld --vars vars.yaml --output instance.jsonld`
- Variable substitution with validation (type checking, required vars)
- Template library: docs/templates/ with reusable templates

**Gap**:
- No template variable syntax (e.g., Jinja2, Mustache)
- No variable substitution engine
- No `uapk compile` command
- Cannot create multiple instances from one template
- Each instance needs manual manifest duplication and editing

**Evidence**:
- Current: `uapk/interpreter.py:22-78` (plan resolution, no templating)
- Current: Single manifest file per instance (manifests/opspilotos.uapk.jsonld)

**Next Action**:
Implement template variable substitution using Jinja2. Add `uapk compile` command that accepts template + vars file and produces instance manifest.

---

### C2. Multi-Tenant Isolation (Namespaces, Storage, Policy Inheritance)

**Score**: 2/5

**Current State**:
- ✅ Organization model exists (uapk/db/models.py)
- ✅ Users belong to organizations (multi-tenant data model)
- ⚠️ No namespace isolation for deployed instances
- ⚠️ Storage not namespaced (shared artifacts/ directory)
- ⚠️ Database tables not namespaced (shared across instances)
- ⚠️ Policy not inherited (each instance has separate policies)

**Target State**:
- Namespace isolation:
  - Each instance deployed in separate namespace (e.g., k8s namespace, docker network)
  - Storage isolated: artifacts/{instance_id}/, runtime/{instance_id}/
- Database isolation:
  - Separate database per instance, OR
  - Shared database with org_id filtering on all queries
- Policy inheritance:
  - Global policies (org-level) + instance-specific policies
  - Policy hierarchy: global → instance → agent
- Resource quotas per instance (CPU, memory, disk)

**Gap**:
- No namespace concept in deployment
- Storage shared across instances (collision risk)
- Database shared without clear isolation (org_id not consistently enforced)
- No policy inheritance model
- No resource quotas or limits per instance

**Evidence**:
- Current: `uapk/db/models.py` (Organization model)
- Current: Single runtime/ directory (no instance isolation)

**Next Action**:
Implement instance namespacing: runtime/{instance_id}/, artifacts/{instance_id}/. Add instance_id to all database queries for multi-tenant isolation.

---

### C3. Upgrade Manifests / Migrations / Rollout Strategy

**Score**: 0/5

**Current State**:
- ⚠️ No upgrade mechanism
- ⚠️ Manifest changes require manual editing and re-deploy
- ⚠️ No migration scripts or tooling
- ⚠️ No rollout strategy (blue/green, canary, rolling)

**Target State**:
- Upgrade workflow:
  1. Create new manifest version (e.g., opspilotos-v0.2.jsonld)
  2. Run `uapk upgrade instance-001 --manifest opspilotos-v0.2.jsonld`
  3. System computes diff (manifest changes)
  4. Runs migration scripts (if needed)
  5. Deploys new version with rollout strategy
- Rollout strategies:
  - Blue/green: Deploy v0.2 alongside v0.1, switch traffic
  - Canary: Deploy v0.2 to 10% of instances, monitor, roll out
  - Rolling: Upgrade instances one-by-one with health checks
- Rollback: `uapk rollback instance-001` restores previous version

**Gap**:
- No `uapk upgrade` command
- No rollout strategy implementation
- No rollback capability
- Upgrades are manual and risky
- No migration script framework

**Evidence**:
- Current: No upgrade implementation
- Current: `DLTEST/UAPK_BUSINESS_INSTANCE_CERTIFICATE.md:832-845` (mentions upgrade path but no tooling)

**Next Action**:
Design upgrade workflow and implement `uapk upgrade` command with manifest diff, migration execution, and rollback support.

---

### C4. Packaging + Deployment (OCI Images, SBOM, Provenance)

**Score**: 2/5

**Current State**:
- ✅ Docker Compose deployment (docker-compose.opspilotos.yml exists)
- ⚠️ No OCI image publishing
- ⚠️ No SBOM (Software Bill of Materials)
- ⚠️ No provenance attestation (SLSA)
- ⚠️ No container registry integration

**Target State**:
- OCI image packaging:
  - `uapk package manifest.jsonld --output image.tar`
  - Produces OCI-compliant image with:
    - Manifest embedded
    - Runtime binaries
    - Dependencies
- SBOM generation:
  - CycloneDX or SPDX format
  - Lists all dependencies, licenses, versions
- Provenance attestation:
  - SLSA Level 2+ compliance
  - Build attestation (who built, when, from what source)
- Container registry:
  - Push images to registry (Docker Hub, GitHub Packages, etc.)
  - Signed images with Sigstore/Cosign

**Gap**:
- No `uapk package` command
- No OCI image building
- No SBOM generation
- No provenance attestation
- Manual Docker Compose deployment only

**Evidence**:
- Current: `docker-compose.opspilotos.yml` (Docker Compose config)
- Current: `scripts/` (deployment scripts but no packaging)

**Next Action**:
Implement `uapk package` command to build OCI image with embedded manifest. Generate SBOM using pip-licenses or syft.

---

### C5. Fleet Governance (Policies at Scale, Audits, Drift Detection)

**Score**: 0/5

**Current State**:
- ⚠️ Single instance deployment only
- ⚠️ No fleet registry or instance tracking
- ⚠️ No fleet-level policies
- ⚠️ No drift detection
- ⚠️ No centralized audit aggregation across instances

**Target State**:
- Fleet registry:
  - Database or API tracking all deployed instances
  - Instance metadata: ID, manifest hash, status, health, last seen
- Fleet governance:
  - Global policies enforced across all instances
  - Compliance reports aggregated from all instances
  - Audit trail aggregation (centralized log collection)
- Drift detection:
  - Detect when instance manifest diverges from expected
  - Alert on drift or unauthorized changes
  - `uapk fleet drift` command shows all drifted instances
- Fleet operations:
  - `uapk fleet list` - List all instances
  - `uapk fleet status` - Check health of all instances
  - `uapk fleet upgrade --manifest v0.2` - Upgrade all instances

**Gap**:
- No fleet concept implemented
- Cannot deploy or manage multiple instances
- No fleet registry or instance tracking
- No drift detection capability
- Single-instance-only mindset in current code

**Evidence**:
- Current: No fleet implementation
- Inference: UAPK Gateway's org-based multi-agent model implies fleet capability

**Next Action**:
Design fleet architecture: centralized registry + federated instances. Implement `uapk fleet init` command to set up registry. Add instance registration on startup.

---

## Scoring Heatmap

**Dimension-level scores** (0=not implemented, 5=exemplary):

```
┌─────────────────────────────────────────────┬───────┬───────┐
│ Dimension                                    │ Score │ Max   │
├─────────────────────────────────────────────┼───────┼───────┤
│ PILLAR A: UAPK GATEWAY                      │       │       │
├─────────────────────────────────────────────┼───────┼───────┤
│ A1. Policy Membrane                          │   4   │   5   │
│ A2. HITL Workflow                            │   4   │   5   │
│ A3. Auditability                             │   4   │   5   │
│ A4. Deterministic Execution                  │   5   │   5   │ ⭐
│ A5. Observability                            │   4   │   5   │
│ A6. Connector Framework                      │   2   │   5   │ ⚠️
│ A7. Evidence-Grade Exports                   │   1   │   5   │ ⚠️
│ A8. Secrets Management                       │   2   │   5   │ ⚠️
│ A9. RBAC                                     │   3   │   5   │
├─────────────────────────────────────────────┼───────┼───────┤
│ SUBTOTAL: Gateway                            │  34   │  45   │
├─────────────────────────────────────────────┼───────┼───────┤
│ PILLAR B: UAPK PROTOCOL                     │       │       │
├─────────────────────────────────────────────┼───────┼───────┤
│ B1. Manifest Semantics                       │   2   │   5   │ ⚠️
│ B2. Versioning                               │   2   │   5   │
│ B3. Conformance                              │   2   │   5   │
│ B4. Attestation Model                        │   1   │   5   │ ⚠️
│ B5. Security Model                           │   1   │   5   │ ⚠️
├─────────────────────────────────────────────┼───────┼───────┤
│ SUBTOTAL: Protocol                           │   8   │  15   │
├─────────────────────────────────────────────┼───────┼───────┤
│ PILLAR C: UAPK COMPILER                     │       │       │
├─────────────────────────────────────────────┼───────┼───────┤
│ C1. Template → Instance Compilation          │   2   │   5   │
│ C2. Multi-Tenant Isolation                   │   2   │   5   │
│ C3. Upgrade Manifests / Migrations           │   0   │   5   │ ⚠️
│ C4. Packaging + Deployment                   │   2   │   5   │
│ C5. Fleet Governance                         │   0   │   5   │ ⚠️
├─────────────────────────────────────────────┼───────┼───────┤
│ SUBTOTAL: Compiler                           │   6   │  15   │
├─────────────────────────────────────────────┼───────┼───────┤
│ TOTAL ALIGNMENT SCORE                        │  48   │  75   │
│ PERCENTAGE                                   │      64%      │
│ GRADE                                        │     Good      │
└─────────────────────────────────────────────┴───────┴───────┘

Legend:
⭐ Exemplary (5/5) - Exceeds vision
✅ Strong (4/5) - Production-ready
⚠️ Gaps (0-2/5) - Needs significant work
```

---

## Top 5 Gaps (Prioritized by Impact)

### 1. Missing Connector Framework (A6: 2/5)
**Impact**: **CRITICAL** - Security and extensibility gap
**Why**: Cannot execute external tools safely. No SSRF protection. Agents are limited to hardcoded Python functions.
**Fix**: Implement ToolConnector abstraction with WebhookConnector and HTTPConnector. Add SSRF protection (allowlist + deny private IPs).
**Timeline**: 1 week (Milestone 1.3)

### 2. Schema Divergence (B1: 2/5)
**Impact**: **HIGH** - Interoperability blocker
**Why**: OpsPilotOS manifest incompatible with UAPK Gateway. Cannot load each other's manifests. Breaks ecosystem.
**Fix**: Converge on canonical schema OR formalize extended schema with migration path.
**Timeline**: 2 weeks (Milestone 2.1)

### 3. No Override Tokens (A2: 4/5, needs 5/5)
**Impact**: **HIGH** - Approval workflow incomplete
**Why**: Approvals don't produce override tokens. Agents cannot retry with approval proof. Manual re-execution required.
**Fix**: Generate Ed25519-signed override tokens on approval. Add override_token validation in PolicyEngine.
**Timeline**: 3 days (Milestone 1.1)

### 4. Missing Ed25519 Audit Signatures (A3: 4/5, needs 5/5)
**Impact**: **HIGH** - Evidence-grade logging incomplete
**Why**: Audit events not signed by gateway. Cannot prove authenticity. Chain verification exists but lacks signatures.
**Fix**: Sign each audit event with gateway Ed25519 private key. Store signature in eventSignature field.
**Timeline**: 2 days (Milestone 1.2)

### 5. No Fleet Management (C5: 0/5)
**Impact**: **MEDIUM** - Cannot scale beyond single instance
**Why**: No fleet registry, drift detection, or centralized governance. Limits deployment to one instance per org.
**Fix**: Implement fleet registry and instance tracking. Add `uapk fleet` commands for governance.
**Timeline**: 2 weeks (Milestone 3.2)

---

## Narrative Summary

### What OpsPilotOS Does Well

OpsPilotOS **successfully demonstrates the UAPK compiler vision** by turning a manifest into a fully operational autonomous SaaS business. The implementation excels at:

1. **Deterministic execution** (5/5): Manifest → plan resolution with hash-locked plans is exemplary. Same manifest produces same plan hash, enabling reproducibility.

2. **Policy enforcement** (4/5): PolicyEngine with tool permissions, deny rules, rate limits, and live action gates provides solid governance. The 5-step evaluation model works well for the current scope.

3. **Audit trail** (4/5): SHA-256 hash chaining with merkle root computation creates tamper-evident logs. Chain verification tests pass.

4. **HITL workflow** (4/5): Approval queue with status tracking and approved_by attribution works functionally.

5. **Observability** (4/5): Health checks, metrics, and structured logging provide operational visibility.

6. **Domain-specific innovation**: OpsPilotOS extends UAPK vision with tax/VAT compliance, invoicing, ledger, and NFT minting - features not in UAPK Gateway but highly valuable for autonomous businesses.

### Where OpsPilotOS Diverges from UAPK Vision

The reference implementation has **architectural choices that diverge** from the canonical UAPK Gateway model:

1. **Custom manifest schema** (B1: 2/5): OpsPilotOS uses a 6-module extended schema incompatible with UAPK Gateway's simple agent/capabilities/constraints model. This breaks interoperability.

2. **Simplified policy engine** (A1: 4/5): 5 steps vs. 15 steps. Missing capability tokens, jurisdiction constraints, amount caps, and policy traces.

3. **No connector framework** (A6: 2/5): Tools are hardcoded Python functions instead of manifest-driven connectors with SSRF protection.

4. **File-based audit log** (A3: 4/5): Audit log is JSONL file, not database-backed InteractionRecords with Ed25519 signatures.

5. **Single instance only** (C5: 0/5): No fleet management, template compilation, or multi-instance deployment.

### Strategic Options

**Option A: Converge to Canonical UAPK** (Recommended)
- Adopt UAPK Gateway's simple manifest schema
- Implement full 15-step policy engine with capability tokens
- Add connector framework with SSRF protection
- Store audit log in database with Ed25519 signatures
- Add fleet management and template compilation

**Outcome**: Full alignment with UAPK ecosystem, interoperability with other UAPK Gateway instances, easier adoption by external evaluators.

**Timeline**: 11-15 weeks (Milestones 1-3)

**Option B: Formalize Extended Schema** (Alternative)
- Document OpsPilotOS extended schema as "UAPK-Extended v0.1"
- Provide schema migration tool: canonical ↔ extended
- Maintain compatibility layer
- Position as "business-focused UAPK variant"

**Outcome**: Preserves OpsPilotOS innovations (tax/VAT, billing, NFT) while acknowledging divergence. Requires schema governance and migration tooling.

**Timeline**: 8-12 weeks (Milestones 1, 2B, 3)

**Option C: Hybrid Approach** (Pragmatic)
- Implement gateway-critical components (override tokens, Ed25519 signatures, connectors) - Milestone 1
- Converge on core manifest structure (agent, capabilities, constraints) - Milestone 2A
- Keep extended modules as optional (corporateModules, aiOsModules) - extensions
- Add compiler/fleet capabilities - Milestone 3

**Outcome**: Balances interoperability with OpsPilotOS innovations. Canonical core + opt-in extensions.

**Timeline**: 10-14 weeks

### Scoring Interpretation

**64% alignment** means:
- ✅ **Core enforcement working** - Policy engine, audit trail, approvals functional
- ✅ **Proof-of-concept complete** - Demonstrates UAPK compiler vision end-to-end
- ⚠️ **Production gaps** - Missing connector framework, RBAC enforcement, fleet management
- ⚠️ **Interoperability issues** - Schema divergence prevents ecosystem integration
- ⚠️ **Security hardening needed** - SSRF protection, Ed25519 signatures, secrets management

For **evaluation/demo purposes**: 64% is **good** - shows the vision works.
For **production deployment**: 64% needs **improvement** - close critical gaps first.
For **ecosystem adoption**: 64% is **insufficient** - schema convergence required.

### Recommended Path Forward

1. **Milestone 1** (2-3 weeks): Gateway Hardening
   - Close critical security gaps (override tokens, Ed25519 signatures, connector framework)
   - Target: 54/75 (72%)

2. **Milestone 2** (3-4 weeks): Protocol Formalization
   - Converge on canonical schema or formalize extended schema
   - Add conformance test suite and versioning
   - Target: 58/75 (77%)

3. **Milestone 3** (6-8 weeks): Compiler & Fleet
   - Template compilation, multi-instance deployment, fleet governance
   - Target: 65/75 (87%)

**Total timeline**: 11-15 weeks to **87% alignment** (production-ready across all pillars).

---

## Methodology Notes

### Document Analysis
- Read 5 canonical UAPK documents (README.md, architecture docs, manifest, certificate, diagram)
- Extracted explicit vision statements for Gateway, Protocol, Compiler
- Cross-referenced OpsPilotOS implementation against vision

### Scoring Criteria
- 0-5 scale per dimension (19 dimensions total)
- Evidence-based: every score backed by file references
- Conservative: when uncertain, scored lower (no aspirational scores)
- Consistent: same rubric applied across all dimensions

### Inference vs. Explicit
- Explicit vision: Direct statements from README.md or docs (e.g., "15-step policy engine")
- Inferred vision: Logical extensions (e.g., "fleet governance" implied by multi-org model)
- All inferences labeled clearly in "Target State" sections

### Limitations
- Scorecard reflects current state as of 2026-02-08
- No runtime testing (static code analysis only)
- Some gaps may be documented elsewhere (out of scope docs)
- Scoring is relative to UAPK Gateway v0.1 vision (not future versions)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-02-08 | Complete regeneration with 3-pillar structure, 19 dimensions, evidence-based scoring |
| 1.0.0 | 2026-02-08 | Initial scorecard (superseded) |

---

**End of Scorecard**

For implementation roadmap and milestone details, see: **UAPK_VISION_ALIGNMENT_SCORECARD_DIFF.md**
For machine-readable version, see: **UAPK_VISION_ALIGNMENT_SCORECARD.yaml**
