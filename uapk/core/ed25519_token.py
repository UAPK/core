"""
Ed25519 Override Token Signing and Verification
Implements short-lived, single-use override tokens for HITL approval flow.
"""
import json
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from uapk.core.ed25519_keys import get_private_key, get_public_key


def compute_action_hash(action: str, params: Dict[str, Any]) -> str:
    """
    Compute deterministic hash of an action and its parameters.
    Used to bind override token to specific action.
    """
    canonical = json.dumps({"action": action, "params": params}, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def create_override_token(
    approval_id: int,
    action: str,
    params: Dict[str, Any],
    expiry_minutes: int = 5
) -> str:
    """
    Create an Ed25519-signed override token for approved HITL request.

    Token format (JWT-like but Ed25519):
    - Header: {"alg": "EdDSA", "typ": "OVR"}
    - Payload: {"approval_id": int, "action_hash": str, "iat": int, "exp": int}
    - Signature: Ed25519

    Token string: base64url(header).base64url(payload).base64url(signature)

    Args:
        approval_id: HITLRequest ID
        action: Action being approved
        params: Action parameters
        expiry_minutes: Token validity (default 5 minutes)

    Returns:
        Signed override token (string)
    """
    private_key = get_private_key()

    # Create header
    header = {"alg": "EdDSA", "typ": "OVR"}

    # Create payload
    now = datetime.utcnow()
    action_hash = compute_action_hash(action, params)

    payload = {
        "approval_id": approval_id,
        "action_hash": action_hash,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expiry_minutes)).timestamp())
    }

    # Encode header and payload
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header, separators=(',', ':')).encode('utf-8')
    ).decode('utf-8').rstrip('=')

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).decode('utf-8').rstrip('=')

    # Sign (header.payload)
    message = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = private_key.sign(message)

    # Encode signature
    signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

    # Construct token
    token = f"{header_b64}.{payload_b64}.{signature_b64}"

    return token


def verify_override_token(
    token: str,
    action: str,
    params: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any] | None]:
    """
    Verify an override token.

    Args:
        token: Override token string
        action: Action being attempted
        params: Action parameters

    Returns:
        (valid: bool, reason: str, payload: dict | None)
    """
    try:
        # Parse token
        parts = token.split('.')
        if len(parts) != 3:
            return False, "Invalid token format (expected 3 parts)", None

        header_b64, payload_b64, signature_b64 = parts

        # Decode header
        header_json = base64.urlsafe_b64decode(header_b64 + '==')
        header = json.loads(header_json)

        if header.get('alg') != 'EdDSA' or header.get('typ') != 'OVR':
            return False, "Invalid token type or algorithm", None

        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + '==')
        payload = json.loads(payload_json)

        # Decode signature
        signature = base64.urlsafe_b64decode(signature_b64 + '==')

        # Verify signature
        public_key = get_public_key()
        message = f"{header_b64}.{payload_b64}".encode('utf-8')

        try:
            public_key.verify(signature, message)
        except InvalidSignature:
            return False, "Invalid signature", None

        # Check expiry
        now = datetime.utcnow()
        exp = datetime.fromtimestamp(payload['exp'])

        if now > exp:
            return False, f"Token expired at {exp.isoformat()}Z", None

        # Check action binding
        expected_action_hash = compute_action_hash(action, params)
        if payload['action_hash'] != expected_action_hash:
            return False, "Token not valid for this action (action_hash mismatch)", None

        return True, "Token valid", payload

    except Exception as e:
        return False, f"Token verification failed: {str(e)}", None


def hash_override_token(token: str) -> str:
    """
    Compute SHA-256 hash of override token for storage.
    Store hash (not plaintext token) in database.
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
