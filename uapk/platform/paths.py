"""
Platform Paths (Phase 0)
Canonical path resolution for UAPK VM transformator node.
"""
import os
from pathlib import Path
from typing import Optional


class PlatformPaths:
    """
    Manages canonical paths for UAPK VM transformator.

    Paths can be overridden via environment variables:
    - UAPK_CODE_DIR (default: /opt/uapk)
    - UAPK_DATA_DIR (default: /var/lib/uapk)
    - UAPK_LOG_DIR (default: /var/log/uapk)
    """

    def __init__(self):
        # Code directory (repo location)
        self.code_dir = Path(os.environ.get('UAPK_CODE_DIR', '/opt/uapk'))

        # Data directory (persistent state)
        self.data_dir = Path(os.environ.get('UAPK_DATA_DIR', '/var/lib/uapk'))

        # Log directory
        self.log_dir = Path(os.environ.get('UAPK_LOG_DIR', '/var/log/uapk'))

    # Data directories
    def instances_dir(self) -> Path:
        """Instances directory: /var/lib/uapk/instances"""
        return self.data_dir / 'instances'

    def cas_dir(self) -> Path:
        """Content-addressed storage: /var/lib/uapk/cas"""
        return self.data_dir / 'cas'

    def db_dir(self) -> Path:
        """Database directory: /var/lib/uapk/db"""
        return self.data_dir / 'db'

    def runtime_dir(self) -> Path:
        """Runtime state: /var/lib/uapk/runtime"""
        return self.data_dir / 'runtime'

    def chain_data_dir(self) -> Path:
        """Chain data: /var/lib/uapk/chain"""
        return self.data_dir / 'chain'

    # Specific files
    def fleet_db_path(self) -> Path:
        """Fleet registry database"""
        return self.db_dir() / 'fleet.db'

    def nft_contract_path(self) -> Path:
        """NFT contract deployment info"""
        return self.runtime_dir() / 'nft_contract.json'

    # Instance-specific paths
    def instance_dir(self, instance_id: str) -> Path:
        """Instance directory: /var/lib/uapk/instances/<instance_id>"""
        return self.instances_dir() / instance_id

    def instance_manifest_path(self, instance_id: str) -> Path:
        """Instance manifest"""
        return self.instance_dir(instance_id) / 'manifest.jsonld'

    def instance_plan_lock_path(self, instance_id: str) -> Path:
        """Instance plan lock"""
        return self.instance_dir(instance_id) / 'plan.lock.json'

    def instance_package_path(self, instance_id: str) -> Path:
        """Instance package"""
        return self.instance_dir(instance_id) / 'package.zip'

    def instance_nft_receipt_path(self, instance_id: str) -> Path:
        """NFT mint receipt"""
        return self.instance_dir(instance_id) / 'nft_mint_receipt.json'

    # Log files
    def chain_log_path(self) -> Path:
        """Chain service log"""
        return self.log_dir / 'chain.log'

    def compiler_log_path(self) -> Path:
        """Compiler service log"""
        return self.log_dir / 'compiler.log'

    def gateway_log_path(self) -> Path:
        """Gateway service log"""
        return self.log_dir / 'gateway.log'

    # Ensure directories exist
    def ensure_directories(self):
        """Create all platform directories if they don't exist"""
        dirs = [
            self.data_dir,
            self.instances_dir(),
            self.cas_dir(),
            self.db_dir(),
            self.runtime_dir(),
            self.chain_data_dir(),
            self.log_dir
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
            # Set permissions (readable by all, writable by owner)
            try:
                directory.chmod(0o755)
            except Exception:
                pass  # May not have permissions

    def check_writable(self) -> dict:
        """
        Check if platform paths are writable.

        Returns:
            Dict with path: writable status
        """
        results = {}

        paths_to_check = {
            'data_dir': self.data_dir,
            'instances_dir': self.instances_dir(),
            'cas_dir': self.cas_dir(),
            'db_dir': self.db_dir(),
            'runtime_dir': self.runtime_dir(),
            'log_dir': self.log_dir
        }

        for name, path in paths_to_check.items():
            try:
                # Try to create directory
                path.mkdir(parents=True, exist_ok=True)
                # Try to write test file
                test_file = path / '.uapk_test'
                test_file.write_text('test')
                test_file.unlink()
                results[name] = {'path': str(path), 'writable': True, 'exists': True}
            except Exception as e:
                results[name] = {'path': str(path), 'writable': False, 'exists': path.exists(), 'error': str(e)}

        return results


# Global platform paths instance
_platform_paths: Optional[PlatformPaths] = None


def get_platform_paths() -> PlatformPaths:
    """
    Get the global platform paths instance.
    Creates and caches on first call.
    """
    global _platform_paths
    if _platform_paths is None:
        _platform_paths = PlatformPaths()
    return _platform_paths
