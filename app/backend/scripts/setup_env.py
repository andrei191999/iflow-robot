"""
Setup script to initialize the development environment.

This script:
1. Creates test users in Firebase Authentication
2. Creates secrets in Google Cloud Secret Manager
3. Initializes Firestore user settings

Usage:
    python setup_env.py
"""

import os
import sys
import logging
import firebase_admin
from firebase_admin import auth, credentials, firestore
from pathlib import Path
from google.cloud import secretmanager

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(dotenv_path=backend_dir / ".env.local")

# Explicitly set credentials path if not set
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    # Try common locations
    possible_paths = [
        backend_dir.parent.parent / "firebase-sa-key.json",
        Path("c:/Workspace/Stuff/iflow-robot/firebase-sa-key.json")
    ]
    for path in possible_paths:
        if path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
            break

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test Users Configuration
TEST_USERS = [
    {
        "uid": "dev-test-user-001",
        "email": "dev-user@iflow-robot.dev",
        "password": "dev-test-password-123",
        "display_name": "Development Test User",
        "iflow_username": "dev-test@example.com",
        "iflow_password": "dev-test-password-123"
    },
    {
        "uid": "dev-demo-user-001",
        "email": "demo-user@iflow-robot.dev",
        "password": "demo-password-123",
        "display_name": "Demo User",
        "iflow_username": "demo@example.com",
        "iflow_password": "demo-password-123"
    }
]

def setup_environment():
    logger.info("🚀 Starting Environment Setup")

    # 1. Initialize Firebase
    try:
        # Check if already initialized
        if not firebase_admin._apps:
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not cred_path:
                logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
                return

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized")
    except Exception as e:
        logger.error(f"❌ Firebase initialization failed: {e}")
        return

    db = firestore.client()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "iflow-robot")

    # 2. Initialize Secret Manager
    try:
        sm_client = secretmanager.SecretManagerServiceClient()
        logger.info("✅ Secret Manager client initialized")
    except Exception as e:
        logger.error(f"❌ Secret Manager initialization failed: {e}")
        return

    for user in TEST_USERS:
        logger.info(f"\n👤 Processing user: {user['email']}")

        # --- Step A: Create Firebase Auth User ---
        try:
            try:
                auth.get_user(user['uid'])
                logger.info("   ℹ️  User already exists in Firebase Auth")
            except auth.UserNotFoundError:
                auth.create_user(
                    uid=user['uid'],
                    email=user['email'],
                    password=user['password'],
                    display_name=user['display_name'],
                    email_verified=True
                )
                logger.info("   ✅ Created user in Firebase Auth")
        except Exception as e:
            logger.error(f"   ❌ Failed to create Firebase user: {e}")

        # --- Step B: Create Secret in Secret Manager ---
        secret_id = f"iflow-cred-{user['uid']}"
        parent = f"projects/{project_id}"
        secret_path = f"{parent}/secrets/{secret_id}"

        try:
            # Check if secret exists
            try:
                sm_client.get_secret(request={"name": secret_path})
                logger.info(f"   ℹ️  Secret {secret_id} already exists")
            except Exception:
                # Create secret
                sm_client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {"replication": {"automatic": {}}}
                    }
                )
                logger.info(f"   ✅ Created secret {secret_id}")

            # Add secret version (payload)
            payload = user['iflow_password'].encode("UTF-8")
            sm_client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": payload}
                }
            )
            logger.info("   ✅ Added secret version (password)")

        except Exception as e:
            logger.error(f"   ❌ Failed to manage secret: {e}")

        # --- Step C: Initialize Firestore Settings ---
        try:
            doc_ref = db.collection("settings").document(user['uid'])
            doc = doc_ref.get()

            if not doc.exists:
                doc_ref.set({
                    "iflowUsername": user['iflow_username'],
                    "checkInTime": "09:00",
                    "checkOutTime": "17:00",
                    "isActive": True,
                    "emailNotifications": True
                })
                logger.info("   ✅ Created Firestore settings document")
            else:
                logger.info("   ℹ️  Firestore settings already exist")

        except Exception as e:
            logger.error(f"   ❌ Failed to update Firestore: {e}")

    logger.info("\n✨ Setup Complete!")

if __name__ == "__main__":
    setup_environment()
