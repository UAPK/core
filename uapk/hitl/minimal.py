"""
Minimal HITL Queue (Phase 4)
Lightweight approval workflow for minting actions.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from uapk.platform.paths import get_platform_paths
from uapk.core.ed25519_token import create_override_token


class HITLQueue:
    """
    Minimal human-in-the-loop approval queue.
    Uses SQLite for persistence.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            paths = get_platform_paths()
            db_path = str(paths.db_dir() / 'hitl.db')

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize HITL queue schema"""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hitl_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                approved_at TEXT,
                override_token_hash TEXT
            )
        """)

        self.conn.commit()

    def create_request(self, action: str, payload: Dict[str, Any]) -> int:
        """
        Create a new HITL request.

        Returns:
            Request ID
        """
        cursor = self.conn.cursor()

        now = datetime.utcnow().isoformat() + "Z"

        cursor.execute("""
            INSERT INTO hitl_requests (action, payload_json, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (action, json.dumps(payload), now))

        self.conn.commit()

        return cursor.lastrowid

    def approve_request(self, request_id: int) -> Optional[str]:
        """
        Approve a request and generate override token.

        Returns:
            Override token (Ed25519-signed JWT-like)
        """
        cursor = self.conn.cursor()

        # Get request
        cursor.execute("SELECT * FROM hitl_requests WHERE id = ?", (request_id,))
        row = cursor.fetchone()

        if not row:
            return None

        if row['status'] != 'pending':
            raise ValueError(f"Request {request_id} already {row['status']}")

        # Generate override token
        payload = json.loads(row['payload_json'])
        override_token = create_override_token(
            approval_id=request_id,
            action=row['action'],
            params=payload,
            expiry_minutes=5
        )

        # Update request
        now = datetime.utcnow().isoformat() + "Z"

        import hashlib
        token_hash = hashlib.sha256(override_token.encode('utf-8')).hexdigest()

        cursor.execute("""
            UPDATE hitl_requests
            SET status = 'approved', approved_at = ?, override_token_hash = ?
            WHERE id = ?
        """, (now, token_hash, request_id))

        self.conn.commit()

        return override_token

    def list_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List HITL requests"""
        cursor = self.conn.cursor()

        if status:
            cursor.execute("SELECT * FROM hitl_requests WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM hitl_requests ORDER BY created_at DESC")

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def get_hitl_queue() -> HITLQueue:
    """Get HITL queue instance"""
    return HITLQueue()
