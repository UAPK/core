# UAPK Manifest Versioning Policy

**Version**: 1.0
**Status**: Stable
**Last Updated**: 2026-02-09

---

## Overview

This document defines the versioning policy for UAPK manifests and provides guidelines for version upgrades and backwards compatibility.

---

## Semantic Versioning

UAPK manifests follow **Semantic Versioning 2.0.0** (semver.org):

```
MAJOR.MINOR.PATCH
```

### Version Components

- **MAJOR**: Incompatible schema changes (breaking changes)
  - Example: Renaming required fields, removing fields, changing field types
  - Requires migration tool to upgrade
  - Gateway supports N-1 major versions for transition period

- **MINOR**: New features, backwards-compatible additions
  - Example: Adding new optional fields, new capability types
  - No migration required
  - Gateway supports all minor versions within current major

- **PATCH**: Bug fixes, no schema changes
  - Example: Documentation updates, clarifications
  - No migration required

---

## Current Version

**Canonical Schema Version**: `1.0`

This is the first stable release of the canonical UAPK Gateway manifest schema.

---

## Version Compatibility

### Gateway Support Matrix

| Gateway Version | Supports Manifest Versions | Notes |
|----------------|---------------------------|-------|
| 1.x | 1.0, 0.1 (extended) | Transition period: supports legacy extended schemas via migration |
| 2.x | 2.0, 1.x | Will support 1.x manifests with deprecation warnings |

### Compatibility Rules

1. **Forward Compatibility**: Gateways MUST ignore unknown fields in minor/patch updates
2. **Backward Compatibility**: Major version N SHOULD support N-1 manifests during transition (6-12 months)
3. **Deprecation Period**: Features deprecated in version N.x are removed in N+1.0

---

## Migration Process

### Automatic Migration

For minor/patch upgrades, no migration is required. The gateway will handle new optional fields automatically.

### Manual Migration (Major Versions)

For major version upgrades, use the migration CLI:

```bash
# Check what migration is needed
python -m uapk.cli migrate --from 1.0 --to 2.0 manifest.json --dry-run

# Perform migration
python -m uapk.cli migrate --from 1.0 --to 2.0 manifest.json -o manifest_v2.json

# Validate migrated manifest
python -m uapk.cli verify manifest_v2.json
```

---

## Version History

### Version 1.0 (2026-02-09)

**Status**: Current stable release

**Schema Changes**:
- Initial canonical schema definition
- Core fields: `version`, `agent`, `capabilities`, `constraints`, `metadata`, `policy`, `tools`, `extensions`

**Breaking Changes from 0.1 Extended**:
- Renamed `corporateModules` → `policy`
- Renamed `aiOsModules` → `tools`
- Flattened structure to canonical format
- Added required `version` field

**Migration**: Use `migrate_extended_to_canonical()` to upgrade from 0.1 extended schema

### Version 0.1 (2025-12-01)

**Status**: Legacy (OpsPilotOS Extended Schema)

**Schema**: Extended format with `corporateModules` and `aiOsModules`

**Support**: Supported via migration layer in Gateway 1.x

---

## Upcoming Changes

### Planned for 1.1 (Minor)

- Add `agent.tags[]` for categorization
- Add `policy.time_windows` for time-based restrictions
- Add `tools.*.health_check` for connector health monitoring

**Migration**: None required (backwards compatible)

### Planned for 2.0 (Major)

- Remove `extensions` field (fully canonical only)
- Require `agent.organization` (currently optional)
- Change `capabilities.requested` to `capabilities.declared` (naming clarity)
- Add `capabilities.dynamic` for runtime capability requests

**Migration**: Tool will be provided 3 months before release

---

## Deprecation Policy

### Announcement

Deprecations are announced at least **6 months** before removal:

1. Add deprecation notice in documentation
2. Add warning log when deprecated field is used
3. Provide migration guide
4. Update conformance tests

### Warning Format

Deprecated fields trigger warnings:

```
WARN: Field 'old_field' is deprecated in v1.5, will be removed in v2.0.
      Use 'new_field' instead. See migration guide: https://...
```

---

## Migration Examples

### Example 1: 0.1 Extended → 1.0 Canonical

**Before (0.1 Extended)**:
```json
{
  "@id": "urn:uapk:myagent:v1",
  "name": "MyAgent",
  "corporateModules": {
    "policyGuardrails": {
      "liveActionGates": ["send_email"]
    }
  }
}
```

**After (1.0 Canonical)**:
```json
{
  "version": "1.0",
  "agent": {
    "id": "myagent-v1",
    "name": "MyAgent",
    "version": "0.1.0"
  },
  "capabilities": {
    "requested": ["send_email"]
  },
  "constraints": {
    "require_human_approval": ["send_email"]
  },
  "extensions": {
    "opspilotos": {
      "@id": "urn:uapk:myagent:v1",
      ...
    }
  }
}
```

**Migration Command**:
```bash
python -m uapk.cli migrate manifest_v0.1.jsonld -o manifest_v1.0.json
```

---

## Best Practices

### For Manifest Authors

1. **Always specify version**: Include `"version": "1.0"` in all manifests
2. **Avoid extensions for core features**: Use canonical fields when available
3. **Document custom extensions**: Add documentation URLs in metadata
4. **Test migrations**: Validate manifests after version upgrades

### For Gateway Implementers

1. **Support N-1 versions**: Provide 6-12 month overlap for major versions
2. **Log deprecation warnings**: Help users migrate proactively
3. **Validate strictly**: Reject manifests with unknown major versions
4. **Ignore unknown fields**: Forward compatibility for minor versions

---

## Version Detection

### Automatic Detection

Gateways detect manifest version from:

1. `version` field (canonical schema)
2. `uapkVersion` field (extended schema)
3. Presence of `@context` (indicates extended schema)

### Fallback Behavior

If no version field is present:
- Assume 0.1 extended schema
- Log warning
- Attempt migration to 1.0

---

## FAQ

**Q: Can I use both extended and canonical formats?**
A: Yes, during transition. Extended schemas are automatically migrated to canonical by the gateway.

**Q: How long will 0.1 extended format be supported?**
A: Until Gateway 2.0 (estimated 12-18 months). Deprecation warnings will start 6 months before removal.

**Q: What happens if I use an unsupported version?**
A: Gateway will reject the manifest with error: `"Unsupported manifest version: X.Y"`

**Q: Can I downgrade manifest versions?**
A: No. Migrations are one-way (upgrade only). Downgrades would require manual editing.

**Q: How do I test compatibility before upgrading?**
A: Use `--dry-run` flag: `python -m uapk.cli migrate --from 1.0 --to 2.0 manifest.json --dry-run`

---

## References

- [Semantic Versioning](https://semver.org)
- [Manifest Schema Documentation](./manifest_schema.md)
- [Migration Utilities](../../uapk/manifest_migrations.py)
- [Conformance Tests](../conformance.md)

---

## Contact

For questions about versioning policy:
- GitHub Issues: https://github.com/UAPK/core/issues
- Documentation: https://uapk.ai/docs/versioning
