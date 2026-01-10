"""
Secure user password storage service.

Replaces GCP Secret Manager with Encrypted Firestore documents.
Credentials are stored in `users/{uid}/private/credentials` protected by security rules,
and encrypted at rest using AES (via encryption.py).

This ensures persistence across all environments (Local/Dev/Prod) where Firestore is accessible.
"""

import json
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

from core.db import get_db
from services.encryption import encrypt_string, decrypt_string

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: Dict[str, Dict] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


class FirestoreUserPasswordManager:
    """Secure credential storage using Encrypted Firestore documents."""

    def __init__(self):
        self.db = get_db()
        logger.info("FirestoreUserPasswordManager initialized")

    def _get_ref(self, uid: str):
        """Get DocumentReference for user credentials."""
        # Stored in a subcollection 'private' to allow restricting access via Security Rules
        return self.db.collection("users").document(uid).collection("private").document("credentials")

    def _get_cache_key(self, uid: str) -> str:
        return f"userpw_{uid}"

    def _get_from_cache(self, uid: str) -> Optional[Dict[str, str]]:
        cache_key = self._get_cache_key(uid)
        if cache_key in _cache:
            entry = _cache[cache_key]
            if datetime.utcnow() < entry["expires_at"]:
                return entry["data"]
            else:
                del _cache[cache_key]
        return None

    def _set_cache(self, uid: str, data: Dict[str, str]) -> None:
        cache_key = self._get_cache_key(uid)
        _cache[cache_key] = {
            "data": data,
            "expires_at": datetime.utcnow() + timedelta(seconds=_CACHE_TTL_SECONDS)
        }

    def _invalidate_cache(self, uid: str) -> None:
        cache_key = self._get_cache_key(uid)
        if cache_key in _cache:
            del _cache[cache_key]

    def store_password(self, uid: str, username: str, password: str) -> bool:
        """Encrypt and store credentials in Firestore."""
        try:
            # Prepare data
            data = {
                "username": username,
                "password": password,
                "updated_at": datetime.utcnow().isoformat()
            }
            json_str = json.dumps(data)

            # Encrypt
            encrypted_token = encrypt_string(json_str)

            # Save to Firestore
            doc_ref = self._get_ref(uid)
            doc_ref.set({
                "encrypted_data": encrypted_token,
                "version": 1,
                "updated_at": firestore_timestamp()
            })

            self._invalidate_cache(uid)
            logger.info(f"Successfully stored encrypted credentials for user {uid}")
            return True

        except Exception as e:
            logger.error(f"Error storing credentials for user {uid}: {e}", exc_info=True)
            return False

    def get_password(self, uid: str) -> Optional[Dict[str, str]]:
        """Retrieve and decrypt credentials from Firestore."""
        # Check cache
        cached = self._get_from_cache(uid)
        if cached:
            return cached

        try:
            doc_ref = self._get_ref(uid)
            doc = doc_ref.get()

            if not doc.exists:
                logger.info(f"No credentials found for user {uid}")
                return None

            data = doc.to_dict()
            encrypted_token = data.get("encrypted_data")

            if not encrypted_token:
                logger.error(f"Credentials document exists but missing data for user {uid}")
                return None

            # Decrypt
            json_str = decrypt_string(encrypted_token)
            creds = json.loads(json_str)

            # Extract only username/password
            result = {
                "username": creds["username"],
                "password": creds["password"]
            }

            self._set_cache(uid, result)
            return result

        except Exception as e:
            logger.error(f"Error retrieving credentials for user {uid}: {e}")
            return None

    def delete_password(self, uid: str) -> bool:
        """Delete credentials document."""
        try:
            doc_ref = self._get_ref(uid)
            doc_ref.delete()
            self._invalidate_cache(uid)
            logger.info(f"Deleted credentials for user {uid}")
            return True
        except Exception as e:
            logger.error(f"Error deleting credentials for user {uid}: {e}")
            return False

    def password_exists(self, uid: str) -> bool:
        """Check if credentials document exists."""
        if self._get_from_cache(uid):
            return True
        try:
            doc_ref = self._get_ref(uid)
            # Use count/get fast check if possible, or just get
            snap = doc_ref.get(field_paths=["version"]) # minimal fetch
            return snap.exists
        except Exception as e:
            logger.error(f"Error checking password existence: {e}")
            return False

# Helper for timestamp
from google.cloud import firestore
def firestore_timestamp():
    return firestore.SERVER_TIMESTAMP

# Singleton
_mgr_instance = None

def get_password_manager() -> FirestoreUserPasswordManager:
    global _mgr_instance
    if _mgr_instance is None:
        _mgr_instance = FirestoreUserPasswordManager()
    return _mgr_instance
