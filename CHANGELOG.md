# Changelog

All notable changes to the UAPK Gateway project.

## [0.2.1] - 2025-12-16

### 🚨 Critical Security Fixes

- **Removed leaked secrets from distribution**:
  - Deleted `.env` file with credentials
  - Deleted `.claude/settings.local.json` with GitHub PAT
  - Added `.claude/` to `.gitignore`
  - **ACTION REQUIRED**: Rotate secrets if you deployed v0.2.0

- **Fixed token type confusion**:
  - Added explicit `token_type` claim to distinguish capability vs override tokens
  - Override tokens now have `token_type="override"` and MUST include `action_hash`/`approval_id`
  - Capability tokens have `token_type="capability"` and must NOT include `action_hash`/`approval_id`
  - Prevents malicious token substitution attacks

### Fixed

- **Tool existence validation**: PolicyEngine now validates tool is configured in manifest before allowing action
  - Prevents confusing "allowed but failed" scenarios
  - Returns clear error message with list of configured tools

### Changed

- Token validation now enforces token type correctness
- Tool checks happen at evaluation time, not execution time

---

## [0.2.0] - 2025-12-16

### Added
- **Approval Thresholds**: New feature allowing policies to require human approval based on amount, action type, or tool
  - Added `ApprovalThreshold` schema class (`backend/app/schemas/manifest.py`)
  - Added `approval_thresholds` field to `PolicyConfig`
  - Implemented enforcement in `PolicyEngine._check_approval_thresholds()`
  - Updated JSON schema with enforcement status indicators
- **Demo Harness**: Complete end-to-end demo script (`scripts/demo_harness.py`)
  - Demonstrates budget caps, approval workflows, and audit verification
  - Uses correct auth model (Bearer for operators, X-API-Key for agents)
  - Colorized output for presentations
- **Documentation**:
  - `DEMO_GUIDE.md`: Comprehensive testing and sales guide (truthful version)
  - `P0_BLOCKERS_FIX_GUIDE.md`: Critical issue documentation
  - `CODEBASE_GAP_MAP.md`: File-by-file gap analysis

### Fixed
- **P0-1: Manifest Selection** (2025-12-16)
  - Modified `PolicyEngine._get_manifest()` to only select ACTIVE manifests
  - Added `include_inactive` parameter to `ManifestService.get_manifest_by_uapk_id()`
  - Prevents PENDING staging manifests from breaking production

- **P0-2: Token System Deprecation** (2025-12-16)
  - Deprecated `/api/v1/orgs/{org_id}/tokens` endpoints with HTTP 410 Gone
  - All endpoints now direct users to `/capabilities/issue` (EdDSA tokens)
  - Prevents confusion between HS256 tokens (not used) and EdDSA tokens (used)

- **P0-3: UI Approval RBAC** (2025-12-16)
  - Added role checks to `/ui/approvals/{id}/approve` and `/ui/approvals/{id}/deny`
  - Only OPERATOR, ADMIN, or OWNER roles can approve/deny actions
  - Prevents VIEWER role from making critical decisions

- **P0-4: Metrics Endpoint** (2025-12-16)
  - Fixed field reference: `InteractionRecord.timestamp` → `InteractionRecord.created_at`
  - Added API key authentication requirement
  - Fixed UTC timezone handling

- **P0-5: Schema Documentation** (2025-12-16)
  - Marked unenforced fields with "⚠️ NOT YET ENFORCED" warnings:
    - `constraints.max_actions_per_hour`
    - `constraints.allowed_hours`
    - `policy.budgets.hourly_limit`
    - `policy.budgets.total_limit`
  - Marked enforced fields with "✅ ENFORCED"

### Changed
- **Schema Strictness**: Enforcement status now explicitly documented in JSON schema
- **Auth Model Clarity**: Demo scripts and docs now clearly separate operator (Bearer) vs agent (API Key) auth
- **Policy Engine**: Added approval threshold check between tool validation and amount caps

### Security
- UI approval routes now enforce RBAC
- Metrics endpoint requires authentication
- Deprecated insecure token system

---

## [0.1.0] - 2025-12-15

### Initial Release
- Core gateway evaluate/execute flow
- Approval + override token system
- Interaction record audit chain (tamper-evident)
- Basic connectors with SSRF protection
- Database models
- Amount caps enforcement
- Daily budget enforcement
- Capability token system (EdDSA)

### Known Limitations
- Hourly budget caps not enforced (schema only)
- Time window restrictions not enforced (schema only)
- Per-action-type budgets partially enforced
- UI security hardening incomplete (CSRF, secure cookies)
- No secrets management API
- No retention policy automation
