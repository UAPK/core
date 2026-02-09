"""
Manifest Signing and Verification (M2.4)
Ed25519-based cryptographic signing for UAPK manifests.
"""
import json
import hashlib
import base64
from datetime import datetime
from typing import Dict, Any, Tuple
from pathlib import Path

from uapk.core.ed25519_keys import (
    generate_ed25519_keypair,
    save_private_key,
    save_public_key,
    load_private_key,
    load_public_key
)


def compute_manifest_hash(manifest: Dict[str, Any]) -> str:
    """
    Compute deterministic hash of manifest (excludes cryptoHeader.signature).

    Args:
        manifest: Manifest dict

    Returns:
        SHA-256 hash (hex)
    """
    # Create copy without signature
    manifest_copy = json.loads(json.dumps(manifest))

    # Remove signature fields if present
    if "cryptoHeader" in manifest_copy:
        manifest_copy["cryptoHeader"]["signature"] = ""
        manifest_copy["cryptoHeader"]["signedBy"] = ""
        manifest_copy["signedAt"] = None

    # Canonical JSON
    canonical = json.dumps(manifest_copy, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def sign_manifest(manifest: Dict[str, Any], private_key_path: Path) -> Dict[str, Any]:
    """
    Sign manifest with Ed25519 private key.

    Args:
        manifest: Manifest to sign
        private_key_path: Path to Ed25519 private key (PEM)

    Returns:
        Signed manifest (with updated cryptoHeader)
    """
    # Load private key
    private_key = load_private_key(private_key_path)

    # Compute manifest hash
    manifest_hash = compute_manifest_hash(manifest)

    # Sign hash
    message = manifest_hash.encode('utf-8')
    signature_bytes = private_key.sign(message)
    signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')

    # Get key fingerprint (last 8 chars of public key hash)
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes_raw()
    key_fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[-8:]

    # Update manifest
    signed_manifest = json.loads(json.dumps(manifest))  # Deep copy

    if "cryptoHeader" not in signed_manifest:
        signed_manifest["cryptoHeader"] = {}

    signed_manifest["cryptoHeader"]["signature"] = signature_b64
    signed_manifest["cryptoHeader"]["signedBy"] = f"key-{key_fingerprint}"
    signed_manifest["cryptoHeader"]["signedAt"] = datetime.utcnow().isoformat() + "Z"
    signed_manifest["cryptoHeader"]["hashAlg"] = "sha256"

    return signed_manifest


def verify_manifest_signature(
    manifest: Dict[str, Any],
    public_key_path: Path
) -> Tuple[bool, str]:
    """
    Verify manifest signature using Ed25519 public key.

    Args:
        manifest: Signed manifest
        public_key_path: Path to Ed25519 public key (PEM)

    Returns:
        (valid: bool, message: str)
    """
    try:
        # Check signature exists
        if "cryptoHeader" not in manifest:
            return False, "No cryptoHeader found in manifest"

        crypto_header = manifest["cryptoHeader"]
        if "signature" not in crypto_header or not crypto_header["signature"]:
            return False, "No signature found in cryptoHeader"

        signature_b64 = crypto_header["signature"]

        # Load public key
        public_key = load_public_key(public_key_path)

        # Compute manifest hash (without signature)
        manifest_hash = compute_manifest_hash(manifest)

        # Verify signature
        message = manifest_hash.encode('utf-8')
        signature_bytes = base64.b64decode(signature_b64)

        try:
            public_key.verify(signature_bytes, message)
            return True, "Signature valid"
        except Exception:
            return False, "Signature verification failed: invalid signature"

    except FileNotFoundError:
        return False, f"Public key not found: {public_key_path}"
    except Exception as e:
        return False, f"Verification error: {str(e)}"


def keygen(output_dir: Path) -> Tuple[Path, Path]:
    """
    Generate Ed25519 keypair for manifest signing.

    Args:
        output_dir: Directory to save keys

    Returns:
        (private_key_path, public_key_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    private_key, public_key = generate_ed25519_keypair()

    private_path = output_dir / "private.pem"
    public_path = output_dir / "public.pem"

    save_private_key(private_key, private_path)
    save_public_key(public_key, public_path)

    return private_path, public_path
