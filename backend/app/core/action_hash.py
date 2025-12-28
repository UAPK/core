"""Deterministic action hashing utilities.

Used to bind short-lived override tokens to *exactly one* approved action
payload (type/tool/params), preventing token reuse for a different action.

The hash must be:
- Deterministic (stable ordering)
- JSON-compatible
- Fast to compute
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_action_hash(action: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of an action dict."""
    canonical = json.dumps(action, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
