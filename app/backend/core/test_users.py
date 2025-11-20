"""
Test user configuration for development environment.

Provides pre-configured test users with known credentials for easier development and testing.
Only available when ENVIRONMENT=development.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Test user configuration - only used in development
TEST_USERS = {
    "dev-user@iflow-robot.dev": {
        "uid": "dev-test-user-001",
        "email": "dev-user@iflow-robot.dev",
        "iflow_username": "dev-test@example.com",
        "iflow_password": "dev-test-password-123",
        "display_name": "Development Test User"
    },
    "demo-user@iflow-robot.dev": {
        "uid": "dev-demo-user-001",
        "email": "demo-user@iflow-robot.dev",
        "iflow_username": "demo@example.com",
        "iflow_password": "demo-password-123",
        "display_name": "Demo User"
    }
}


def is_test_user(email: str) -> bool:
    """
    Check if email belongs to a test user.

    Args:
        email: User email address

    Returns:
        True if this is a test user and ENVIRONMENT=development
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment != "development":
        return False

    return email in TEST_USERS


def get_test_user_info(email: str) -> dict:
    """
    Get test user information.

    Args:
        email: Test user email

    Returns:
        Dict with test user info, or None if not a test user
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment != "development":
        logger.warning(f"Attempted to get test user in {environment} environment")
        return None

    return TEST_USERS.get(email)


def get_test_user_credentials(uid: str) -> dict:
    """
    Get iFlow credentials for a test user.

    Args:
        uid: User ID

    Returns:
        Dict with 'username' and 'password' keys, or None
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment != "development":
        return None

    # Find user by UID
    for email, user_data in TEST_USERS.items():
        if user_data["uid"] == uid:
            return {
                "username": user_data["iflow_username"],
                "password": user_data["iflow_password"]
            }

    return None


def initialize_test_users_in_firestore():
    """
    Initialize test users in Firestore with pre-configured settings.
    This should be called on dev environment startup.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment != "development":
        logger.info("Skipping test user initialization - not in development environment")
        return

    logger.info("Test users available for development:")
    for email, user_data in TEST_USERS.items():
        logger.info(f"  - {email} (UID: {user_data['uid']})")

    logger.info("Test users will auto-populate credentials when needed")
