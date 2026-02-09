"""
Content-Addressed Storage (CAS)
Provides immutable storage where content is addressed by its SHA-256 hash.
Used for NFT metadata, manifests, plans, and other tamper-evident artifacts.
"""
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional


class ContentAddressedStore:
    """Local content-addressed storage using filesystem"""

    def __init__(self, base_path: str = "runtime/cas"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content).hexdigest()

    def put(self, content: bytes) -> str:
        """
        Store content and return its hash.
        Content is stored at cas/<hash>
        """
        content_hash = self._compute_hash(content)
        file_path = self.base_path / content_hash

        # Only write if doesn't exist (idempotent)
        if not file_path.exists():
            file_path.write_bytes(content)

        return content_hash

    def put_json(self, data: Dict[str, Any]) -> str:
        """Store JSON data and return its hash"""
        # Canonical JSON: sorted keys, no whitespace
        content = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return self.put(content)

    def put_str(self, text: str) -> str:
        """Store text and return its hash"""
        return self.put(text.encode('utf-8'))

    def get(self, content_hash: str) -> Optional[bytes]:
        """Retrieve content by hash"""
        file_path = self.base_path / content_hash
        if not file_path.exists():
            return None
        return file_path.read_bytes()

    def get_json(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve JSON data by hash"""
        content = self.get(content_hash)
        if content is None:
            return None
        return json.loads(content.decode('utf-8'))

    def get_str(self, content_hash: str) -> Optional[str]:
        """Retrieve text by hash"""
        content = self.get(content_hash)
        if content is None:
            return None
        return content.decode('utf-8')

    def exists(self, content_hash: str) -> bool:
        """Check if content exists"""
        return (self.base_path / content_hash).exists()

    def uri(self, content_hash: str) -> str:
        """Generate a URI for the content (for NFT tokenURI)"""
        return f"cas://{content_hash}"


def compute_merkle_root(hashes: list[str]) -> str:
    """
    Compute Merkle root from a list of hashes.
    Simple implementation: if empty, return empty; if one, return it;
    otherwise, hash all hashes concatenated.
    """
    if not hashes:
        return ""
    if len(hashes) == 1:
        return hashes[0]

    # Simple merkle: concatenate sorted hashes and hash result
    combined = "".join(sorted(hashes))
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
