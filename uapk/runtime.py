"""
Instance Runtime Management (M3.2)
Provides instance-scoped paths and multi-tenant isolation.
"""
import os
from pathlib import Path
from typing import Optional


class InstanceRuntime:
    """
    Manages runtime paths and resources for a UAPK instance.
    Provides instance isolation for multi-tenant deployments.
    """

    def __init__(self, instance_id: str, base_dir: str = "runtime"):
        """
        Initialize instance runtime.

        Args:
            instance_id: Unique instance identifier
            base_dir: Base runtime directory
        """
        self.instance_id = instance_id
        self.base_dir = Path(base_dir)
        self.instance_dir = self.base_dir / instance_id

    def get_audit_log_path(self) -> Path:
        """Get instance-scoped audit log path"""
        return self.instance_dir / "audit.jsonl"

    def get_plan_lock_path(self) -> Path:
        """Get instance-scoped plan lock path"""
        return self.instance_dir / "plan.lock.json"

    def get_manifest_path(self) -> Path:
        """Get instance-scoped manifest copy path"""
        return self.instance_dir / "manifest.jsonld"

    def get_cas_dir(self) -> Path:
        """Get instance-scoped content-addressed storage directory"""
        return self.instance_dir / "cas"

    def get_database_path(self) -> Path:
        """Get instance-scoped database path (SQLite)"""
        return self.instance_dir / f"{self.instance_id}.db"

    def get_artifacts_dir(self) -> Path:
        """Get instance-scoped artifacts directory"""
        return Path("artifacts") / self.instance_id

    def get_logs_dir(self) -> Path:
        """Get instance-scoped logs directory"""
        return Path("logs") / self.instance_id

    def get_keys_dir(self) -> Path:
        """Get instance-scoped keys directory"""
        return self.instance_dir / "keys"

    def ensure_directories(self):
        """Create all instance directories if they don't exist"""
        dirs = [
            self.instance_dir,
            self.get_cas_dir(),
            self.get_artifacts_dir(),
            self.get_logs_dir(),
            self.get_keys_dir()
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def get_database_url(self, use_postgresql: bool = False) -> str:
        """
        Get database URL for this instance.

        Args:
            use_postgresql: If True, return PostgreSQL URL pattern

        Returns:
            Database connection URL
        """
        if use_postgresql:
            # PostgreSQL with instance-scoped schema
            db_host = os.environ.get("DATABASE_HOST", "localhost")
            db_port = os.environ.get("DATABASE_PORT", "5432")
            db_user = os.environ.get("DATABASE_USER", "uapk")
            db_pass = os.environ.get("DATABASE_PASSWORD", "")
            db_name = os.environ.get("DATABASE_NAME", "uapk")

            return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?options=-c%20search_path={self.instance_id}"
        else:
            # SQLite (instance-scoped file)
            return f"sqlite:///{self.get_database_path()}"

    def cleanup(self, preserve_audit: bool = True):
        """
        Clean up instance runtime (for shutdown/deletion).

        Args:
            preserve_audit: If True, keep audit log (for compliance)
        """
        import shutil

        # Remove artifacts
        artifacts_dir = self.get_artifacts_dir()
        if artifacts_dir.exists():
            shutil.rmtree(artifacts_dir)

        # Remove CAS
        cas_dir = self.get_cas_dir()
        if cas_dir.exists():
            shutil.rmtree(cas_dir)

        # Remove database
        db_path = self.get_database_path()
        if db_path.exists():
            db_path.unlink()

        # Optionally preserve audit log
        if not preserve_audit:
            audit_path = self.get_audit_log_path()
            if audit_path.exists():
                audit_path.unlink()


# Global instance runtime (set during startup)
_current_runtime: Optional[InstanceRuntime] = None


def get_current_runtime() -> InstanceRuntime:
    """
    Get the current instance runtime.

    Returns:
        InstanceRuntime for current instance

    Raises:
        RuntimeError if no runtime has been initialized
    """
    global _current_runtime
    if _current_runtime is None:
        raise RuntimeError(
            "No instance runtime initialized. Call set_current_runtime() first."
        )
    return _current_runtime


def set_current_runtime(instance_id: str, base_dir: str = "runtime"):
    """
    Set the current instance runtime (called during startup).

    Args:
        instance_id: Instance identifier
        base_dir: Base runtime directory
    """
    global _current_runtime
    _current_runtime = InstanceRuntime(instance_id, base_dir)
    _current_runtime.ensure_directories()
    return _current_runtime
