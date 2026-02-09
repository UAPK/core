"""
Ed25519 Key Management
Handles generation and loading of Ed25519 keypairs for signing.
"""
import os
from pathlib import Path
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


DEFAULT_KEY_DIR = Path("runtime/keys")
PRIVATE_KEY_FILE = "gateway_ed25519.pem"
PUBLIC_KEY_FILE = "gateway_ed25519.pub"


def generate_ed25519_keypair() -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """
    Generate a new Ed25519 keypair.
    Returns (private_key, public_key).
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def save_private_key(private_key: Ed25519PrivateKey, path: Path):
    """Save Ed25519 private key to PEM file"""
    path.parent.mkdir(parents=True, exist_ok=True)

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    path.write_bytes(pem)
    # Set restrictive permissions (owner read/write only)
    path.chmod(0o600)


def save_public_key(public_key: Ed25519PublicKey, path: Path):
    """Save Ed25519 public key to PEM file"""
    path.parent.mkdir(parents=True, exist_ok=True)

    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    path.write_bytes(pem)


def load_private_key(path: Path) -> Ed25519PrivateKey:
    """Load Ed25519 private key from PEM file"""
    if not path.exists():
        raise FileNotFoundError(f"Private key not found at {path}")

    pem = path.read_bytes()
    return serialization.load_pem_private_key(pem, password=None)


def load_public_key(path: Path) -> Ed25519PublicKey:
    """Load Ed25519 public key from PEM file"""
    if not path.exists():
        raise FileNotFoundError(f"Public key not found at {path}")

    pem = path.read_bytes()
    return serialization.load_pem_public_key(pem)


def load_or_generate_keypair(key_dir: Path = DEFAULT_KEY_DIR) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """
    Load existing Ed25519 keypair or generate new one.
    Checks for UAPK_ED25519_PRIVATE_KEY env var first (production).
    Falls back to runtime/keys/ (development).

    Returns (private_key, public_key).
    """
    # Try environment variable first (production mode)
    env_key = os.environ.get("UAPK_ED25519_PRIVATE_KEY")
    if env_key:
        # Load from PEM string in env var
        pem = env_key.encode('utf-8')
        private_key = serialization.load_pem_private_key(pem, password=None)
        public_key = private_key.public_key()
        print("✅ Loaded Ed25519 private key from UAPK_ED25519_PRIVATE_KEY env var")
        return private_key, public_key

    # Development mode: use or generate file-based keys
    private_path = key_dir / PRIVATE_KEY_FILE
    public_path = key_dir / PUBLIC_KEY_FILE

    if private_path.exists():
        # Load existing keypair
        private_key = load_private_key(private_path)
        public_key = load_public_key(public_path) if public_path.exists() else private_key.public_key()
        print(f"✅ Loaded Ed25519 keypair from {key_dir}")
        return private_key, public_key

    # Generate new keypair
    print(f"⚠️  Generating new Ed25519 keypair at {key_dir}")
    print("⚠️  For production, use UAPK_ED25519_PRIVATE_KEY env var instead")

    private_key, public_key = generate_ed25519_keypair()
    save_private_key(private_key, private_path)
    save_public_key(public_key, public_path)

    print(f"✅ Generated and saved Ed25519 keypair to {key_dir}")
    return private_key, public_key


# Global keypair cache
_private_key: Ed25519PrivateKey | None = None
_public_key: Ed25519PublicKey | None = None


def get_gateway_keypair() -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """
    Get the gateway Ed25519 keypair (cached).
    Loads from env var or file, generates if needed.
    """
    global _private_key, _public_key

    if _private_key is None or _public_key is None:
        _private_key, _public_key = load_or_generate_keypair()

    return _private_key, _public_key


def get_private_key() -> Ed25519PrivateKey:
    """Get gateway Ed25519 private key"""
    private_key, _ = get_gateway_keypair()
    return private_key


def get_public_key() -> Ed25519PublicKey:
    """Get gateway Ed25519 public key"""
    _, public_key = get_gateway_keypair()
    return public_key
