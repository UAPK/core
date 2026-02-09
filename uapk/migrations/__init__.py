"""
Manifest migration modules.
Each module handles migration between specific versions.
"""
from pathlib import Path
from typing import Dict, Any, List
import importlib


def get_available_migrations() -> Dict[str, Any]:
    """
    Get list of available migration modules.

    Returns:
        Dict of {from_version: {to_version: module_path}}
    """
    migrations = {}

    # Scan migrations directory for vX_Y_to_vA_B.py files
    migrations_dir = Path(__file__).parent
    for migration_file in migrations_dir.glob("v*_to_v*.py"):
        # Parse filename: v0_1_to_v1_0.py → from: 0.1, to: 1.0
        name = migration_file.stem
        parts = name.split("_to_")
        if len(parts) == 2:
            from_ver = parts[0].replace("v", "").replace("_", ".")
            to_ver = parts[1].replace("v", "").replace("_", ".")

            if from_ver not in migrations:
                migrations[from_ver] = {}

            migrations[from_ver][to_ver] = f"uapk.migrations.{name}"

    return migrations


def find_migration_path(from_version: str, to_version: str) -> List[str]:
    """
    Find migration path between versions.
    Returns list of migration module names to apply in order.

    Args:
        from_version: Source version (e.g., "0.1")
        to_version: Target version (e.g., "1.0")

    Returns:
        List of migration module paths

    Raises:
        ValueError if no migration path exists
    """
    migrations = get_available_migrations()

    # Direct migration available?
    if from_version in migrations and to_version in migrations[from_version]:
        return [migrations[from_version][to_version]]

    # TODO: Implement multi-hop migration path finding (BFS)
    # For now, only support direct migrations

    raise ValueError(f"No migration path from v{from_version} to v{to_version}")


def apply_migration(manifest: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
    """
    Apply migration to manifest.

    Args:
        manifest: Source manifest
        from_version: Source version
        to_version: Target version

    Returns:
        Migrated manifest
    """
    migration_path = find_migration_path(from_version, to_version)

    result = manifest
    for migration_module_path in migration_path:
        # Import migration module
        module = importlib.import_module(migration_module_path)

        # Apply migration
        result = module.migrate(result)

    return result
