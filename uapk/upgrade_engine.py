"""
Upgrade and Rollback Engine (M3.3)
Manages manifest upgrades with state backup and rollback capability.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


def compute_manifest_diff(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Compute diff between two manifests.

    Args:
        old: Old manifest dict
        new: New manifest dict

    Returns:
        Dict with 'added', 'removed', 'changed' lists
    """
    diff = {
        "added": [],
        "removed": [],
        "changed": []
    }

    def get_paths(obj: Any, prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dict to dot-notation paths"""
        paths = {}
        if isinstance(obj, dict):
            for key, value in obj.items():
                path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    paths.update(get_paths(value, path))
                else:
                    paths[path] = value
        elif isinstance(obj, list):
            paths[prefix] = obj
        else:
            paths[prefix] = obj
        return paths

    old_paths = get_paths(old)
    new_paths = get_paths(new)

    # Find added, removed, and changed
    for path in new_paths:
        if path not in old_paths:
            diff["added"].append(f"{path} = {new_paths[path]}")
        elif old_paths[path] != new_paths[path]:
            diff["changed"].append(f"{path}: {old_paths[path]} → {new_paths[path]}")

    for path in old_paths:
        if path not in new_paths:
            diff["removed"].append(f"{path} = {old_paths[path]}")

    return diff


class UpgradeManager:
    """
    Manages instance upgrades with backup and rollback.
    """

    def __init__(self, instance_id: str, runtime_dir: Path = Path("runtime")):
        self.instance_id = instance_id
        self.runtime_dir = runtime_dir
        self.instance_dir = runtime_dir / instance_id
        self.backup_dir = runtime_dir / f"{instance_id}_backups"

    def create_backup(self) -> Path:
        """
        Create backup of current instance state.

        Returns:
            Path to backup directory
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        # Create backup directory
        backup_path.mkdir(parents=True, exist_ok=True)

        # Copy instance directory
        if self.instance_dir.exists():
            shutil.copytree(
                self.instance_dir,
                backup_path / "runtime",
                dirs_exist_ok=True
            )

        # Copy artifacts
        artifacts_dir = Path("artifacts") / self.instance_id
        if artifacts_dir.exists():
            shutil.copytree(
                artifacts_dir,
                backup_path / "artifacts",
                dirs_exist_ok=True
            )

        # Save backup metadata
        metadata = {
            "instance_id": self.instance_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "runtime_dir": str(self.instance_dir),
            "artifacts_dir": str(artifacts_dir)
        }

        with open(backup_path / "backup_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        return backup_path

    def restore_backup(self, backup_name: str = None) -> bool:
        """
        Restore instance from backup.

        Args:
            backup_name: Backup name to restore (defaults to latest)

        Returns:
            True if restore successful
        """
        # Find backup
        if backup_name:
            backup_path = self.backup_dir / backup_name
        else:
            # Get latest backup
            backups = sorted(self.backup_dir.glob("backup_*"))
            if not backups:
                raise FileNotFoundError("No backups found")
            backup_path = backups[-1]

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Restore runtime
        runtime_backup = backup_path / "runtime"
        if runtime_backup.exists():
            if self.instance_dir.exists():
                shutil.rmtree(self.instance_dir)
            shutil.copytree(runtime_backup, self.instance_dir)

        # Restore artifacts
        artifacts_backup = backup_path / "artifacts"
        artifacts_dir = Path("artifacts") / self.instance_id
        if artifacts_backup.exists():
            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)
            shutil.copytree(artifacts_backup, artifacts_dir)

        return True

    def upgrade(
        self,
        new_manifest_path: Path,
        auto_backup: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Upgrade instance to new manifest version.

        Args:
            new_manifest_path: Path to new manifest
            auto_backup: Automatically create backup before upgrade
            dry_run: Only compute diff, don't apply

        Returns:
            Upgrade result dict
        """
        # Load current and new manifests
        current_manifest_path = self.instance_dir / "manifest.jsonld"

        if not current_manifest_path.exists():
            return {
                "success": False,
                "message": "No current manifest found (instance not initialized)"
            }

        with open(current_manifest_path, 'r') as f:
            old_manifest = json.load(f)

        with open(new_manifest_path, 'r') as f:
            new_manifest = json.load(f)

        # Compute diff
        diff = compute_manifest_diff(old_manifest, new_manifest)

        # Dry run mode
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "diff": diff,
                "message": "Dry run: no changes applied"
            }

        # Create backup if requested
        backup_path = None
        if auto_backup:
            backup_path = self.create_backup()

        try:
            # Apply upgrade: replace manifest
            with open(current_manifest_path, 'w') as f:
                json.dump(new_manifest, f, indent=2)

            # TODO: Run database migrations if needed
            # TODO: Restart instance services

            return {
                "success": True,
                "diff": diff,
                "backup_path": str(backup_path) if backup_path else None,
                "message": "Upgrade successful"
            }

        except Exception as e:
            # Rollback on error
            if backup_path:
                self.restore_backup(backup_path.name)

            return {
                "success": False,
                "error": str(e),
                "message": "Upgrade failed, restored from backup"
            }

    def rollback(self) -> Dict[str, Any]:
        """
        Rollback to previous version (restore latest backup).

        Returns:
            Rollback result dict
        """
        try:
            # Restore from latest backup
            success = self.restore_backup()

            return {
                "success": success,
                "message": "Rollback successful"
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Rollback failed: no backups available"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Rollback failed"
            }

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups for this instance.

        Returns:
            List of backup metadata dicts
        """
        if not self.backup_dir.exists():
            return []

        backups = []
        for backup_path in sorted(self.backup_dir.glob("backup_*")):
            metadata_file = backup_path / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    metadata["backup_name"] = backup_path.name
                    backups.append(metadata)

        return backups
