"""
Migration: v0.1 Extended Schema → v1.0 Canonical Schema
Converts OpsPilotOS extended format to canonical UAPK Gateway format.
"""
from typing import Dict, Any
from uapk.manifest_migrations import migrate_extended_to_canonical


def migrate(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate manifest from v0.1 extended to v1.0 canonical.

    Args:
        manifest: Source manifest in v0.1 extended format

    Returns:
        Migrated manifest in v1.0 canonical format
    """
    # Validate source version
    source_version = manifest.get("uapkVersion", "0.1")
    if source_version != "0.1":
        raise ValueError(f"Expected v0.1 manifest, got v{source_version}")

    # Perform migration
    canonical = migrate_extended_to_canonical(manifest)

    # Ensure version is set correctly
    canonical["version"] = "1.0"

    return canonical


def get_migration_info() -> Dict[str, Any]:
    """
    Get metadata about this migration.

    Returns:
        Migration metadata
    """
    return {
        "from_version": "0.1",
        "to_version": "1.0",
        "description": "Migrate OpsPilotOS extended schema to canonical UAPK Gateway format",
        "breaking_changes": [
            "Restructured corporateModules → policy",
            "Restructured aiOsModules → tools",
            "Added required version field",
            "Changed agent identification format"
        ],
        "data_preservation": "Original extended manifest preserved in extensions.opspilotos",
        "reversible": True,  # Can recover original from extensions
        "estimated_time_seconds": 1
    }
