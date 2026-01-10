"""
Encryption service for securing user credentials.
Uses cryptography.fernet (AES) with key derivation from APP_SECRET.
"""

import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

_fernet_instance = None

def _get_fernet() -> Fernet:
    """Get or create singleton Fernet instance derived from APP_SECRET."""
    global _fernet_instance
    if _fernet_instance is None:
        secret = os.getenv("APP_SECRET", "default-insecure-secret-for-dev-only")
        if secret == "default-insecure-secret-for-dev-only":
            logger.warning("Using insecure default APP_SECRET for encryption. Set APP_SECRET env var in production.")

        # Derive a 32-byte key using PBKDF2
        # We use a static salt to ensure the key is deterministic for the same APP_SECRET
        # This allows redeployments to decrypt data encrypted by previous instances
        salt = b'static-salt-iflow-v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        _fernet_instance = Fernet(key)

    return _fernet_instance

def encrypt_string(data: str) -> str:
    """Encrypt a string and return utf-8 encoded token."""
    try:
        f = _get_fernet()
        token = f.encrypt(data.encode())
        return token.decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise

def decrypt_string(token: str) -> str:
    """Decrypt a token string and return original string."""
    try:
        f = _get_fernet()
        data = f.decrypt(token.encode())
        return data.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Decryption failed") from e
