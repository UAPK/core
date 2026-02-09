"""
Fleet Registry and Management (M3.5)
Tracks and manages multiple UAPK instances.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class FleetRegistry:
    """
    Centralized registry for tracking UAPK instances.
    Stores instance metadata, status, and health information.
    """

    def __init__(self, registry_path: str = "runtime/fleet_registry.json"):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._instances: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        """Load registry from disk"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                self._instances = json.load(f)

    def _save(self):
        """Save registry to disk"""
        with open(self.registry_path, 'w') as f:
            json.dump(self._instances, f, indent=2)

    def register_instance(
        self,
        instance_id: str,
        manifest_hash: str,
        status: str = "stopped",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register a new instance in the fleet.

        Args:
            instance_id: Unique instance identifier
            manifest_hash: Hash of the instance's manifest
            status: Instance status (running, stopped, error)
            metadata: Additional metadata
        """
        now = datetime.utcnow().isoformat() + "Z"

        self._instances[instance_id] = {
            "instance_id": instance_id,
            "manifest_hash": manifest_hash,
            "status": status,
            "created_at": now,
            "last_seen": now,
            "metadata": metadata or {}
        }

        self._save()

    def update_status(self, instance_id: str, status: str, metadata: Optional[Dict[str, Any]] = None):
        """Update instance status and last_seen timestamp"""
        if instance_id not in self._instances:
            raise KeyError(f"Instance {instance_id} not found in registry")

        self._instances[instance_id]["status"] = status
        self._instances[instance_id]["last_seen"] = datetime.utcnow().isoformat() + "Z"

        if metadata:
            self._instances[instance_id]["metadata"].update(metadata)

        self._save()

    def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get instance information"""
        return self._instances.get(instance_id)

    def list_instances(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all instances in fleet.

        Args:
            status_filter: Optional status filter (running, stopped, error)

        Returns:
            List of instance metadata dicts
        """
        instances = list(self._instances.values())

        if status_filter:
            instances = [i for i in instances if i["status"] == status_filter]

        return sorted(instances, key=lambda x: x["created_at"])

    def detect_drift(self, instance_id: str, actual_manifest_hash: str) -> bool:
        """
        Detect if instance has drifted from registered manifest.

        Args:
            instance_id: Instance to check
            actual_manifest_hash: Current manifest hash from instance

        Returns:
            True if drifted (hashes don't match)
        """
        instance = self.get_instance(instance_id)
        if not instance:
            raise KeyError(f"Instance {instance_id} not found")

        expected_hash = instance["manifest_hash"]
        return actual_manifest_hash != expected_hash

    def get_fleet_stats(self) -> Dict[str, Any]:
        """Get fleet-wide statistics"""
        instances = list(self._instances.values())

        stats = {
            "total_instances": len(instances),
            "by_status": {
                "running": len([i for i in instances if i["status"] == "running"]),
                "stopped": len([i for i in instances if i["status"] == "stopped"]),
                "error": len([i for i in instances if i["status"] == "error"])
            },
            "oldest_instance": min((i["created_at"] for i in instances), default=None),
            "newest_instance": max((i["created_at"] for i in instances), default=None)
        }

        return stats

    def remove_instance(self, instance_id: str):
        """Remove instance from registry"""
        if instance_id in self._instances:
            del self._instances[instance_id]
            self._save()
