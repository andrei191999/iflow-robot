"""
Migration script to move existing user passwords from Firestore to Secret Manager.

Run this script after deploying the updated backend with Secret Manager support.
It will:
1. Read all user settings from Firestore
2. For users with passwords in Firestore, migrate to Secret Manager
3. Remove passwords from Firestore
4. Generate a migration report

Usage:
    python migrate_credentials.py [--dry-run]

Flags:
    --dry-run: Show what would be migrated without making changes
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(dotenv_path=backend_dir / ".env.local")

from google.cloud import firestore
from services.user_passwords import get_password_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_credentials(dry_run=False):
    """
    Migrate user credentials from Firestore to Secret Manager.

    Args:
        dry_run: If True, show what would be migrated without making changes
    """
    logger.info("=" * 60)
    logger.info("iFlow Robot - Credential Migration Script")
    logger.info("Migrating from Firestore to Google Secret Manager")
    logger.info("=" * 60)

    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    # Initialize Firestore
    try:
        db = firestore.Client()
        logger.info("✅ Connected to Firestore")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Firestore: {e}")
        return False

    # Initialize Secret Manager
    try:
        pw_mgr = get_password_manager()
        logger.info("✅ Connected to Secret Manager")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Secret Manager: {e}")
        return False

    logger.info("")
    logger.info("Scanning for users with credentials...")

    # Get all user settings
    settings_ref = db.collection("settings")
    docs = settings_ref.stream()

    migration_stats = {
        "total_users": 0,
        "users_with_passwords": 0,
        "migrated": 0,
        "already_in_sm": 0,
        "failed": 0,
        "errors": []
    }

    for doc in docs:
        migration_stats["total_users"] += 1
        uid = doc.id
        data = doc.to_dict()

        if not data:
            continue

        username = data.get("iflowUsername")
        password = data.get("iflowPassword")

        if not password:
            logger.debug(f"  ⏭️  User {uid}: No password in Firestore")
            continue

        migration_stats["users_with_passwords"] += 1
        logger.info(f"\n📋 User: {uid}")
        logger.info(f"   Username: {username}")

        # Check if already in Secret Manager
        if pw_mgr.password_exists(uid):
            logger.info(f"   ℹ️  Already exists in Secret Manager")
            migration_stats["already_in_sm"] += 1

            if not dry_run:
                # Clean up Firestore
                logger.info(f"   🧹 Cleaning up Firestore password field")
                try:
                    doc.reference.update({"iflowPassword": None})
                    logger.info(f"   ✅ Cleaned up")
                except Exception as e:
                    logger.error(f"   ⚠️  Failed to clean up: {e}")
            continue

        # Migrate to Secret Manager
        if dry_run:
            logger.info(f"   [DRY RUN] Would migrate password to Secret Manager")
            migration_stats["migrated"] += 1
        else:
            try:
                success = pw_mgr.store_password(uid, username, password)
                if success:
                    logger.info(f"   ✅ Migrated to Secret Manager")

                    # Remove from Firestore
                    doc.reference.update({"iflowPassword": None})
                    logger.info(f"   🧹 Removed from Firestore")

                    migration_stats["migrated"] += 1
                else:
                    logger.error(f"   ❌ Failed to migrate")
                    migration_stats["failed"] += 1
                    migration_stats["errors"].append({
                        "uid": uid,
                        "error": "store_password returned False"
                    })
            except Exception as e:
                logger.error(f"   ❌ Migration error: {e}")
                migration_stats["failed"] += 1
                migration_stats["errors"].append({
                    "uid": uid,
                    "error": str(e)
                })

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total users scanned:           {migration_stats['total_users']}")
    logger.info(f"Users with passwords:          {migration_stats['users_with_passwords']}")
    logger.info(f"Migrated to Secret Manager:    {migration_stats['migrated']}")
    logger.info(f"Already in Secret Manager:     {migration_stats['already_in_sm']}")
    logger.info(f"Failed migrations:             {migration_stats['failed']}")

    if migration_stats["errors"]:
        logger.info("")
        logger.info("ERRORS:")
        for error in migration_stats["errors"]:
            logger.info(f"  - User {error['uid']}: {error['error']}")

    logger.info("=" * 60)

    if dry_run:
        logger.info("🔍 DRY RUN COMPLETE - No changes were made")
        logger.info("Run without --dry-run to perform the migration")
    else:
        logger.info("✅ MIGRATION COMPLETE")

    return migration_stats["failed"] == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate user credentials from Firestore to Secret Manager")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    args = parser.parse_args()

    success = migrate_credentials(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
