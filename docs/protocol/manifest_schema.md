# UAPK Manifest Schema - Canonical Format

**Version**: 1.0
**Status**: Stable
**Last Updated**: 2026-02-09

---

## Overview

This document defines the **canonical UAPK Gateway manifest schema** (version 1.0). All UAPK Gateway implementations should support this format for interoperability.

## Schema Structure

```json
{
  "version": "1.0",
  "agent": {...},
  "capabilities": {...},
  "constraints": {...},
  "metadata": {...},
  "policy": {...},
  "tools": {...},
  "extensions": {...}
}
```

---

## Field Definitions

### `version` (required)

**Type**: `string`
**Pattern**: `^1\.0$`
**Description**: Schema version. Must be "1.0" for this specification.

**Example**:
```json
"version": "1.0"
```

---

### `agent` (required)

**Type**: `object`
**Description**: Agent identification and metadata.

**Fields**:
- `id` (required): Agent identifier (pattern: `^[a-z0-9][a-z0-9-]{2,62}$`)
- `name` (required): Human-readable name (1-100 chars)
- `version` (required): Semantic version (pattern: `^\d+\.\d+\.\d+$`)
- `description` (optional): Agent description (max 500 chars)
- `organization` (optional): Organization ID (pattern: `^org-[a-z0-9-]+$`)
- `team` (optional): Team ID (pattern: `^team-[a-z0-9-]+$`)

**Example**:
```json
"agent": {
  "id": "opspilotos-001",
  "name": "OpsPilotOS",
  "version": "0.1.0",
  "description": "Autonomous SaaS Business-in-a-Box",
  "organization": "default",
  "team": null
}
```

---

### `capabilities` (required)

**Type**: `object`
**Description**: Capabilities requested by the agent.

**Fields**:
- `requested` (required): Array of capability strings (min 1 item)

**Capability Format**: `{agent_id}:{action}` or simple action name

**Example**:
```json
"capabilities": {
  "requested": [
    "billingagent:create_invoice",
    "fulfillmentagent:generate_content",
    "mint_nft",
    "send_invoice_email"
  ]
}
```

---

### `constraints` (optional)

**Type**: `object`
**Description**: Self-imposed constraints on agent behavior.

**Fields**:
- `max_actions_per_hour` (optional): Maximum actions per hour (≥1)
- `max_actions_per_day` (optional): Maximum actions per day (≥1)
- `require_human_approval` (optional): Actions requiring HITL approval (array of strings)
- `allowed_hours` (optional): Time-based restrictions (object)

**Example**:
```json
"constraints": {
  "max_actions_per_hour": 6000,
  "max_actions_per_day": 144000,
  "require_human_approval": [
    "mint_nft",
    "send_invoice_email",
    "charge_payment_method"
  ],
  "allowed_hours": null
}
```

---

### `metadata` (optional)

**Type**: `object`
**Description**: Additional metadata for discovery and documentation.

**Fields**:
- `contact` (optional): Contact information
- `documentation` (optional): URL to documentation
- `source` (optional): Source or origin description

**Example**:
```json
"metadata": {
  "contact": "admin@example.com",
  "documentation": "https://example.com/docs",
  "source": "OpsPilotOS Extended Schema"
}
```

---

### `policy` (optional)

**Type**: `object`
**Description**: Policy configuration for gateway enforcement.

**Fields**:
- `budgets` (optional): Budget limits per action type (object: action → BudgetConfig)
- `counterparty_allowlist` (optional): Allowed counterparties (array of domain suffixes)
- `counterparty_denylist` (optional): Blocked counterparties (array of domain suffixes)
- `jurisdiction_allowlist` (optional): Allowed jurisdictions (array of ISO country codes)
- `tool_allowlist` (optional): Allowed tools (array of tool names)
- `tool_denylist` (optional): Blocked tools (array of tool names)
- `amount_caps` (optional): Maximum amounts per currency (object: currency → amount)
- `approval_thresholds` (optional): Approval threshold configuration (object)
- `require_capability_token` (optional): Require capability token for all actions (boolean)

**BudgetConfig**:
```json
{
  "hourly_limit": 100,
  "daily_limit": 500,
  "total_limit": null
}
```

**ApprovalThreshold**:
```json
{
  "action_types": ["mint_nft", "send_invoice"],
  "tools": null,
  "amount": 10000.0,
  "currency": "USD"
}
```

**Example**:
```json
"policy": {
  "budgets": {
    "send_invoice_email": {
      "hourly_limit": 6000,
      "daily_limit": 500,
      "total_limit": null
    }
  },
  "counterparty_allowlist": null,
  "jurisdiction_allowlist": ["US", "EU"],
  "approval_thresholds": {
    "action_types": ["mint_nft", "send_invoice_email"],
    "amount": 10000.0,
    "currency": "USD"
  },
  "require_capability_token": false
}
```

---

### `tools` (optional)

**Type**: `object`
**Description**: Tool connector configurations (tool_name → ToolConfig).

**ToolConfig Fields**:
- `type` (required): Connector type (`http_request`, `webhook`, `mock`)
- `config` (required): Connector-specific configuration (object)

**Example**:
```json
"tools": {
  "email_service": {
    "type": "http_request",
    "config": {
      "method": "POST",
      "url": "https://api.sendgrid.com/v3/mail/send",
      "allowed_domains": ["*.sendgrid.com"]
    }
  },
  "webhook_receiver": {
    "type": "webhook",
    "config": {
      "url": "https://example.com/webhook",
      "allowed_domains": ["example.com"]
    }
  }
}
```

---

### `extensions` (optional)

**Type**: `object`
**Description**: Implementation-specific extensions. Preserves extended schemas.

**Example**:
```json
"extensions": {
  "opspilotos": {
    "@context": "https://uapk.ai/context/v0.1",
    "@id": "urn:uapk:opspilotos:v1",
    "corporateModules": {...},
    "aiOsModules": {...}
  }
}
```

---

## Migration from Extended Schemas

To migrate from OpsPilotOS extended schema to canonical:

```bash
python -m uapk.cli migrate manifests/opspilotos.uapk.jsonld \
  -o manifests/opspilotos_canonical.json
```

Or programmatically:

```python
from uapk.manifest_migrations import migrate_extended_to_canonical

canonical = migrate_extended_to_canonical(extended_manifest)
```

---

## Validation

To validate a canonical manifest:

```python
from uapk.manifest_migrations import validate_canonical_manifest

valid, errors = validate_canonical_manifest(manifest)
if not valid:
    for error in errors:
        print(f"Error: {error}")
```

---

## Conformance

A UAPK Gateway implementation is conformant if it:

1. Accepts all valid canonical manifests (version 1.0)
2. Rejects invalid manifests with clear error messages
3. Preserves extensions without modification
4. Implements policy enforcement according to the `policy` section

See [Conformance Test Suite](../conformance.md) for validation tests.

---

## Examples

### Minimal Manifest

```json
{
  "version": "1.0",
  "agent": {
    "id": "simple-agent",
    "name": "Simple Agent",
    "version": "1.0.0"
  },
  "capabilities": {
    "requested": ["read_data", "write_log"]
  }
}
```

### Full-Featured Manifest

See `manifests/opspilotos_canonical.json` for a complete example with all optional fields.

---

## Version History

- **1.0** (2026-02-09): Initial stable release

---

## References

- [UAPK Gateway Backend Schema](../../backend/app/schemas/manifest.py)
- [OpsPilotOS Extended Schema](../manifests/opspilotos.uapk.jsonld)
- [Migration Utilities](../../uapk/manifest_migrations.py)
