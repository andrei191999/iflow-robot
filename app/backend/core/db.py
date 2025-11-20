"""
Database connection for Firestore.
"""
import os
from google.cloud import firestore

# Lazy initialization - don't create client at import time
_client = None


def get_db() -> firestore.Client:
    """Get or create Firestore client. Lazy initialization for test compatibility."""
    global _client
    if _client is None:
        # In test environment, this will be mocked by conftest.py
        _client = firestore.Client()
    return _client
