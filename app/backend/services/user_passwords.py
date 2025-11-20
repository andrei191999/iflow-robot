"""
Google Cloud Secret Manager service for secure user password storage.

This service provides encrypted storage for user iFlow passwords using Google Cloud Secret Manager
instead of storing passwords directly in Firestore. Implements caching to minimize API calls
and reduce costs on pay-as-you-go billing.
"""

import os
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from google.cloud import secretmanager
from google.api_core import exceptions as gcp_exceptions

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: Dict[str, Dict] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


class UserPasswordManager:
    """Service for managing user passwords in Google Cloud Secret Manager."""

    def __init__(self):
        """Initialize Secret Manager client."""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIREBASE_PROJECT_ID")
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT or FIREBASE_PROJECT_ID environment variable must be set")

        self.client = secretmanager.SecretManagerServiceClient()
        self.parent = f"projects/{self.project_id}"
        logger.info(f"UserPasswordManager initialized for project: {self.project_id}")

    def _get_secret_name(self, uid: str) -> str:
        """Generate secret name for user credentials."""
        # Secret names must match [a-zA-Z0-9-_]+
        safe_uid = uid.replace("@", "_at_").replace(".", "_").replace("-", "_")
        return f"iflow-user-password-{safe_uid}"

    def _get_cache_key(self, uid: str) -> str:
        """Generate cache key for credentials."""
        return f"userpw_{uid}"

    def _get_from_cache(self, uid: str) -> Optional[Dict[str, str]]:
        """Retrieve credentials from cache if not expired."""
        cache_key = self._get_cache_key(uid)
        if cache_key in _cache:
            entry = _cache[cache_key]
            if datetime.utcnow() < entry["expires_at"]:
                logger.debug(f"Cache hit for user {uid}")
                return entry["data"]
            else:
                # Expired, remove from cache
                del _cache[cache_key]
                logger.debug(f"Cache expired for user {uid}")
        return None

    def _set_cache(self, uid: str, data: Dict[str, str]) -> None:
        """Store credentials in cache with TTL."""
        cache_key = self._get_cache_key(uid)
        _cache[cache_key] = {
            "data": data,
            "expires_at": datetime.utcnow() + timedelta(seconds=_CACHE_TTL_SECONDS)
        }
        logger.debug(f"Cached credentials for user {uid}")

    def _invalidate_cache(self, uid: str) -> None:
        """Remove credentials from cache."""
        cache_key = self._get_cache_key(uid)
        if cache_key in _cache:
            del _cache[cache_key]
            logger.debug(f"Invalidated cache for user {uid}")

    def store_password(self, uid: str, username: str, password: str) -> bool:
        """
        Store user iFlow credentials in Secret Manager.

        Args:
            uid: User ID (Firebase UID)
            username: iFlow username/email
            password: iFlow password

        Returns:
            True if successful, False otherwise
        """
        try:
            secret_name = self._get_secret_name(uid)
            secret_path = f"{self.parent}/secrets/{secret_name}"

            # Create payload: store both username and password as JSON-like string
            payload = f"{username}|||{password}"

            # Check if secret exists
            try:
                self.client.get_secret(name=secret_path)
                # Secret exists, add new version
                logger.info(f"Updating existing password for user {uid}")
                parent = secret_path
                response = self.client.add_secret_version(
                    request={
                        "parent": parent,
                        "payload": {"data": payload.encode("utf-8")}
                    }
                )
            except gcp_exceptions.NotFound:
                # Secret doesn't exist, create it
                logger.info(f"Creating new password entry for user {uid}")
                secret = self.client.create_secret(
                    request={
                        "parent": self.parent,
                        "secret_id": secret_name,
                        "secret": {
                            "replication": {"automatic": {}},
                            "labels": {"user_uid": safe_uid[:63] for safe_uid in [uid.replace("@", "_at_").replace(".", "_").replace("-", "_")]}
                        }
                    }
                )
                # Add first version
                response = self.client.add_secret_version(
                    request={
                        "parent": secret.name,
                        "payload": {"data": payload.encode("utf-8")}
                    }
                )

            # Invalidate cache since we updated credentials
            self._invalidate_cache(uid)

            logger.info(f"Successfully stored password for user {uid}")
            return True

        except Exception as e:
            logger.error(f"Error storing password for user {uid}: {e}", exc_info=True)
            return False

    def get_password(self, uid: str) -> Optional[Dict[str, str]]:
        """
        Retrieve user iFlow credentials from Secret Manager.

        Args:
            uid: User ID (Firebase UID)

        Returns:
            Dict with 'username' and 'password' keys, or None if not found
        """
        # Check cache first
        cached = self._get_from_cache(uid)
        if cached:
            return cached

        try:
            secret_name = self._get_secret_name(uid)
            secret_version_path = f"{self.parent}/secrets/{secret_name}/versions/latest"

            response = self.client.access_secret_version(name=secret_version_path)
            payload = response.payload.data.decode("utf-8")

            # Parse payload
            parts = payload.split("|||")
            if len(parts) != 2:
                logger.error(f"Invalid password format for user {uid}")
                return None

            data = {
                "username": parts[0],
                "password": parts[1]
            }

            # Cache the result
            self._set_cache(uid, data)

            logger.info(f"Successfully retrieved password for user {uid}")
            return data

        except gcp_exceptions.NotFound:
            logger.info(f"No password found for user {uid}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving password for user {uid}: {e}", exc_info=True)
            return None

    def delete_password(self, uid: str) -> bool:
        """
        Delete user iFlow credentials from Secret Manager.

        Args:
            uid: User ID (Firebase UID)

        Returns:
            True if successful, False otherwise
        """
        try:
            secret_name = self._get_secret_name(uid)
            secret_path = f"{self.parent}/secrets/{secret_name}"

            self.client.delete_secret(name=secret_path)

            # Invalidate cache
            self._invalidate_cache(uid)

            logger.info(f"Successfully deleted password for user {uid}")
            return True

        except gcp_exceptions.NotFound:
            logger.info(f"No password to delete for user {uid}")
            return True  # Already doesn't exist
        except Exception as e:
            logger.error(f"Error deleting password for user {uid}: {e}", exc_info=True)
            return False

    def password_exists(self, uid: str) -> bool:
        """
        Check if iFlow password exists for a user.

        Args:
            uid: User ID (Firebase UID)

        Returns:
            True if password exists, False otherwise
        """
        # Check cache first
        if self._get_from_cache(uid):
            return True

        try:
            secret_name = self._get_secret_name(uid)
            secret_path = f"{self.parent}/secrets/{secret_name}"

            self.client.get_secret(name=secret_path)
            return True

        except gcp_exceptions.NotFound:
            return False
        except Exception as e:
            logger.error(f"Error checking password for user {uid}: {e}", exc_info=True)
            return False


# Singleton instance
_password_manager: Optional[UserPasswordManager] = None


def get_password_manager() -> UserPasswordManager:
    """Get or create UserPasswordManager singleton."""
    global _password_manager
    if _password_manager is None:
        _password_manager = UserPasswordManager()
    return _password_manager
