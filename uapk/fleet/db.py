"""
Fleet Database (Phase 2)
SQLite database for tracking UAPK instances.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from uapk.platform.paths import get_platform_paths


class FleetDB:
    """
    Fleet registry database using SQLite.
    Tracks instances, versions, and deployment state.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            paths = get_platform_paths()
            db_path = str(paths.fleet_db_path())

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Dict-like rows
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Instances table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                instance_id TEXT PRIMARY KEY,
                template_id TEXT,
                created_at TEXT NOT NULL,
                manifest_path TEXT,
                manifest_hash TEXT,
                plan_hash TEXT,
                package_hash TEXT,
                nft_token_id INTEGER,
                nft_contract TEXT,
                status TEXT DEFAULT 'created'
            )
        """)

        # Instance versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS instance_versions (
                instance_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                manifest_hash TEXT NOT NULL,
                plan_hash TEXT,
                package_hash TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (instance_id, version)
            )
        """)

        self.conn.commit()

    def register_instance(
        self,
        instance_id: str,
        template_id: str,
        manifest_path: str,
        manifest_hash: str
    ):
        """Register a new instance"""
        cursor = self.conn.cursor()

        now = datetime.utcnow().isoformat() + "Z"

        cursor.execute("""
            INSERT INTO instances (instance_id, template_id, created_at, manifest_path, manifest_hash, status)
            VALUES (?, ?, ?, ?, ?, 'compiled')
        """, (instance_id, template_id, now, manifest_path, manifest_hash))

        # Create version 1
        cursor.execute("""
            INSERT INTO instance_versions (instance_id, version, manifest_hash, created_at)
            VALUES (?, 1, ?, ?)
        """, (instance_id, manifest_hash, now))

        self.conn.commit()

    def update_plan_hash(self, instance_id: str, plan_hash: str):
        """Update instance with plan hash"""
        cursor = self.conn.cursor()

        cursor.execute("""
            UPDATE instances
            SET plan_hash = ?, status = 'planned'
            WHERE instance_id = ?
        """, (plan_hash, instance_id))

        # Update latest version
        cursor.execute("""
            UPDATE instance_versions
            SET plan_hash = ?
            WHERE instance_id = ? AND version = (
                SELECT MAX(version) FROM instance_versions WHERE instance_id = ?
            )
        """, (plan_hash, instance_id, instance_id))

        self.conn.commit()

    def update_package_hash(self, instance_id: str, package_hash: str):
        """Update instance with package hash"""
        cursor = self.conn.cursor()

        cursor.execute("""
            UPDATE instances
            SET package_hash = ?, status = 'packaged'
            WHERE instance_id = ?
        """, (package_hash, instance_id))

        # Update latest version
        cursor.execute("""
            UPDATE instance_versions
            SET package_hash = ?
            WHERE instance_id = ? AND version = (
                SELECT MAX(version) FROM instance_versions WHERE instance_id = ?
            )
        """, (package_hash, instance_id, instance_id))

        self.conn.commit()

    def update_nft_info(self, instance_id: str, token_id: int, contract: str):
        """Update instance with NFT info"""
        cursor = self.conn.cursor()

        cursor.execute("""
            UPDATE instances
            SET nft_token_id = ?, nft_contract = ?, status = 'minted'
            WHERE instance_id = ?
        """, (token_id, contract, instance_id))

        self.conn.commit()

    def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get instance by ID"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM instances WHERE instance_id = ?", (instance_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def list_instances(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all instances"""
        cursor = self.conn.cursor()

        if status_filter:
            cursor.execute("SELECT * FROM instances WHERE status = ? ORDER BY created_at DESC", (status_filter,))
        else:
            cursor.execute("SELECT * FROM instances ORDER BY created_at DESC")

        return [dict(row) for row in cursor.fetchall()]

    def get_versions(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get version history for instance"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM instance_versions
            WHERE instance_id = ?
            ORDER BY version DESC
        """, (instance_id,))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def get_fleet_db() -> FleetDB:
    """Get fleet database instance"""
    return FleetDB()
