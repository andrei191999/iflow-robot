import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from core.db import get_db
from core.security import require_firebase_user
from core.test_users import get_test_user_credentials, is_test_user
from schemas.settings import UserSettings, UserSettingsUpdate
from services.user_passwords import get_password_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def get_settings(user: dict = Depends(require_firebase_user)) -> Dict[str, Any]:
    """
    Get user settings. Password is NEVER returned in the response for security.
    For production users, password is stored in Secret Manager.
    For test users (dev only), credentials are auto-configured.
    """
    db = get_db()
    uid = user["uid"]
    user_email = user.get("email", "")

    logger.info(f"Fetching settings for user {uid}")

    # Check if this is a test user (dev environment only)
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "development" and is_test_user(user_email):
        logger.info(f"Test user detected: {user_email}")
        defaults = UserSettings(uid=uid)
        result = defaults.model_dump()
        result["iflowUsername"] = get_test_user_credentials(uid).get("username", "")
        result["credentialsConfigured"] = True
        result.pop("iflowPassword", None)
        return result

    ref = db.collection("settings").document(uid)
    snap = ref.get()

    if not snap.exists:
        logger.info(f"No settings found for user {uid}, returning defaults")
        defaults = UserSettings(uid=uid)
        result = defaults.model_dump()
        result.pop("iflowPassword", None)

        # Check if password exists in Secret Manager
        pw_mgr = get_password_manager()
        result["credentialsConfigured"] = pw_mgr.password_exists(uid)
        return result

    settings = snap.to_dict()
    if settings is None:
        settings = {}

    # Password is never stored in Firestore anymore - remove if present
    settings.pop("iflowPassword", None)

    # Check if password exists in Secret Manager
    pw_mgr = get_password_manager()
    settings["credentialsConfigured"] = pw_mgr.password_exists(uid)

    logger.info(f"Settings retrieved for user {uid}")
    return settings


@router.put("/settings")
def update_settings(
    body: UserSettingsUpdate,
    user: dict = Depends(require_firebase_user),
) -> Dict[str, Any]:
    """
    Update user settings. Only provided fields are updated.
    Password is stored in Secret Manager, NOT in Firestore.
    Password is never returned in the response.
    """
    db = get_db()
    uid = user["uid"]
    user_email = user.get("email", "")

    logger.info(f"Updating settings for user {uid}")

    # Check if this is a test user
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "development" and is_test_user(user_email):
        logger.warning(f"Cannot update settings for test user: {user_email}")
        raise HTTPException(status_code=403, detail="Cannot modify test user settings")

    ref = db.collection("settings").document(uid)
    snap = ref.get()

    # Get existing settings or create defaults
    if snap.exists:
        current = snap.to_dict()
        if current is None:
            current = {}
        logger.debug(f"Existing settings found for user {uid}")
    else:
        current = UserSettings(uid=uid).model_dump()
        logger.info(f"Creating new settings for user {uid}")

    # Update only provided fields
    updates = body.model_dump(exclude_unset=True)

    # Extract password if provided - it goes to Secret Manager
    password = updates.pop("iflowPassword", None)
    username = updates.get("iflowUsername", current.get("iflowUsername"))

    # Log what's being updated (but don't log password)
    safe_updates = {k: v for k, v in updates.items()}
    if password:
        logger.info(f"Password will be stored in Secret Manager for user {uid}")

    logger.info(f"Updating Firestore fields for user {uid}: {safe_updates}")

    # Merge updates with current settings
    current.update(updates)

    # Password should never be in Firestore
    current.pop("iflowPassword", None)

    # Validate the merged settings (without password)
    try:
        # Create a temp settings object for validation
        temp_settings = current.copy()
        if password:
            temp_settings["iflowPassword"] = "temp"  # Just for validation
        validated = UserSettings(**temp_settings)
    except ValidationError as e:
        logger.error(f"Settings validation failed for user {uid}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid settings: {e}")
    except (TypeError, ValueError) as e:
        logger.error(f"Settings format error for user {uid}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid settings format: {e}")

    # Save to Firestore (without password)
    firestore_data = validated.model_dump(mode="json")
    firestore_data.pop("iflowPassword", None)
    ref.set(firestore_data)

    # If password was provided, store it in Secret Manager
    if password and username:
        try:
            pw_mgr = get_password_manager()
            success = pw_mgr.store_password(uid, username, password)
            if success:
                logger.info(f"Password stored in Secret Manager for user {uid}")
            else:
                logger.error(f"Failed to store password in Secret Manager for user {uid}")
                raise HTTPException(status_code=500, detail="Failed to store password securely")
        except Exception as e:
            logger.error(f"Error storing password in Secret Manager: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to store password securely")

    logger.info(f"Settings saved successfully for user {uid}")

    # Return settings without password
    result = firestore_data.copy()

    # Add credential status
    pw_mgr = get_password_manager()
    result["credentialsConfigured"] = pw_mgr.password_exists(uid)

    return result


@router.delete("/settings/credentials", status_code=204)
def delete_credentials(user: dict = Depends(require_firebase_user)):
    """
    Delete stored iFlow credentials from Secret Manager.
    User will need to re-enter them.
    """
    db = get_db()
    uid = user["uid"]
    user_email = user.get("email", "")

    logger.info(f"Deleting iFlow credentials for user {uid}")

    # Check if this is a test user
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "development" and is_test_user(user_email):
        logger.warning(f"Cannot delete credentials for test user: {user_email}")
        raise HTTPException(status_code=403, detail="Cannot modify test user credentials")

    # Delete from Secret Manager
    try:
        pw_mgr = get_password_manager()
        pw_mgr.delete_password(uid)
        logger.info(f"Deleted credentials from Secret Manager for user {uid}")
    except Exception as e:
        logger.error(f"Error deleting credentials from Secret Manager: {e}", exc_info=True)
        # Continue to clean up Firestore even if Secret Manager delete fails

    # Also clean up Firestore (remove username as well)
    ref = db.collection("settings").document(uid)
    snap = ref.get()

    if snap.exists:
        ref.update({
            "iflowUsername": None,
            "iflowPassword": None,
        })

    logger.info(f"Credentials deleted for user {uid}")
    return


@router.post("/settings/test-credentials")
def test_credentials(user: dict = Depends(require_firebase_user)) -> Dict[str, Any]:
    """
    Test if stored credentials work by attempting a login.
    Retrieves password from Secret Manager.
    Returns success/failure without executing actual check-in/out.
    """
    from services.iso_task import test_credentials as test_creds

    db = get_db()
    uid = user["uid"]
    user_email = user.get("email", "")

    logger.info(f"Testing credentials for user {uid}")

    # Check if this is a test user
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "development" and is_test_user(user_email):
        logger.info(f"Using test user credentials for {user_email}")
        test_creds_data = get_test_user_credentials(uid)
        if not test_creds_data:
            raise HTTPException(status_code=400, detail="Test user credentials not configured")

        username = test_creds_data["username"]
        password = test_creds_data["password"]
        url = "https://app.hriflow.ro/#/dashboard"
        headless = True
        timeout = 30000
    else:
        # Get settings from Firestore
        ref = db.collection("settings").document(uid)
        snap = ref.get()

        if not snap.exists:
            logger.warning(f"No settings found for user {uid}")
            raise HTTPException(status_code=400, detail="No credentials configured")

        settings = snap.to_dict()
        if settings is None:
            logger.warning(f"Settings document exists but is empty for user {uid}")
            raise HTTPException(status_code=400, detail="No credentials configured")

        username = settings.get("iflowUsername")

        # Get password from Secret Manager
        try:
            pw_mgr = get_password_manager()
            creds = pw_mgr.get_password(uid)
            if not creds:
                logger.warning(f"No password found in Secret Manager for user {uid}")
                raise HTTPException(status_code=400, detail="Password not configured")
            password = creds["password"]
        except HTTPException:
            # Re-raise HTTP exceptions (like 400 errors) without modification
            raise
        except Exception as e:
            logger.error(f"Error retrieving password from Secret Manager: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve password")

        if not username or not password:
            logger.warning(f"Missing credentials for user {uid}")
            raise HTTPException(status_code=400, detail="Credentials not configured")

        url = settings.get("iflowUrl", "https://app.hriflow.ro/#/dashboard")
        headless = settings.get("iflowHeadless", True)
        timeout = settings.get("iflowTimeout", 30000)

    logger.info(f"Testing login to {url} for user {uid}")

    success, message = test_creds(url, username, password, headless, timeout)

    if success:
        logger.info(f"Credential test successful for user {uid}")
    else:
        logger.warning(f"Credential test failed for user {uid}: {message}")

    return {
        "success": success,
        "message": message,
    }
