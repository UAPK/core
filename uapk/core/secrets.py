"""
Secrets Management (M1.5)
Load secrets from environment variables instead of hardcoded values.
"""
import os
import base64
from cryptography.fernet import Fernet
from typing import Optional


def get_jwt_secret_key() -> str:
    """
    Get JWT signing secret key from environment.
    Raises ValueError if not set.

    Environment variable: UAPK_JWT_SECRET_KEY
    """
    secret = os.environ.get('UAPK_JWT_SECRET_KEY')

    if not secret:
        raise ValueError(
            "UAPK_JWT_SECRET_KEY environment variable required. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    return secret


def get_fernet_key() -> bytes:
    """
    Get Fernet encryption key from environment.
    Used for encrypting stored secrets in database.
    Raises ValueError if not set.

    Environment variable: UAPK_FERNET_KEY (base64-encoded)
    """
    key_str = os.environ.get('UAPK_FERNET_KEY')

    if not key_str:
        raise ValueError(
            "UAPK_FERNET_KEY environment variable required. "
            "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    try:
        # Decode from base64
        return base64.urlsafe_b64decode(key_str.encode('utf-8'))
    except Exception as e:
        raise ValueError(f"Invalid UAPK_FERNET_KEY format: {e}")


def get_secret(name: str, required: bool = True) -> Optional[str]:
    """
    Get a connector secret from environment.
    Secrets are loaded from UAPK_SECRET_<NAME_UPPER> env vars.

    Args:
        name: Secret name (e.g., "openai_api_key")
        required: If True, raise ValueError if secret not found

    Returns:
        Secret value (string) or None if not found and not required

    Example:
        get_secret("openai_api_key")
        # Loads from: UAPK_SECRET_OPENAI_API_KEY
    """
    # Convert name to env var format: openai_api_key → OPENAI_API_KEY
    env_var_name = f"UAPK_SECRET_{name.upper()}"

    value = os.environ.get(env_var_name)

    if not value and required:
        raise ValueError(
            f"Secret '{name}' not found in environment. "
            f"Set {env_var_name} environment variable."
        )

    return value


def get_ed25519_private_key_pem() -> Optional[str]:
    """
    Get Ed25519 private key PEM from environment (optional).
    If not set, keys will be loaded from runtime/keys/ or auto-generated.

    Environment variable: UAPK_ED25519_PRIVATE_KEY (PEM format)
    """
    return os.environ.get('UAPK_ED25519_PRIVATE_KEY')


def validate_required_secrets() -> dict:
    """
    Validate that all required secrets are set.
    Called during startup health check.

    Returns:
        {'valid': bool, 'missing': list, 'message': str}
    """
    missing = []

    # Check required secrets
    if not os.environ.get('UAPK_JWT_SECRET_KEY'):
        missing.append('UAPK_JWT_SECRET_KEY')

    if not os.environ.get('UAPK_FERNET_KEY'):
        missing.append('UAPK_FERNET_KEY')

    # UAPK_ED25519_PRIVATE_KEY is optional (can auto-generate in dev)

    if missing:
        return {
            'valid': False,
            'missing': missing,
            'message': f"Missing required environment variables: {', '.join(missing)}"
        }

    return {
        'valid': True,
        'missing': [],
        'message': 'All required secrets present'
    }
