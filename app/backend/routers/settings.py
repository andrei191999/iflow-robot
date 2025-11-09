import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from core.db import get_db
from core.security import require_firebase_user
from schemas.settings import UserSettings, UserSettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def get_settings(user: dict = Depends(require_firebase_user)) -> Dict[str, Any]:
    """
    Get user settings. Password is never returned in the response.
    """
    db = get_db()
    uid = user["uid"]

    logger.info(f"Fetching settings for user {uid}")

    ref = db.collection("settings").document(uid)
    snap = ref.get()

    if not snap.exists:
        logger.info(f"No settings found for user {uid}, returning defaults")
        # Return default settings
        defaults = UserSettings(uid=uid)
        result = defaults.model_dump()
        # Don't expose password in response
        result.pop("iflowPassword", None)
        return result

    settings = snap.to_dict()
    if settings is None:
        settings = {}
    # Don't expose password in response
    settings.pop("iflowPassword", None)

    logger.info(f"Settings retrieved for user {uid}")
    return settings


@router.put("/settings")
def update_settings(
    body: UserSettingsUpdate,
    user: dict = Depends(require_firebase_user),
) -> Dict[str, Any]:
    """
    Update user settings. Only provided fields are updated.
    Password is never returned in the response.
    """
    db = get_db()
    uid = user["uid"]

    logger.info(f"Updating settings for user {uid}")

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

    # Log what's being updated (but don't log password)
    safe_updates = {k: v for k, v in updates.items() if k != "iflowPassword"}
    if "iflowPassword" in updates:
        safe_updates["iflowPassword"] = "***REDACTED***"
    logger.info(f"Updating fields for user {uid}: {safe_updates}")

    current.update(updates)

    # Validate the merged settings
    try:
        validated = UserSettings(**current)
    except ValidationError as e:
        logger.error(f"Settings validation failed for user {uid}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid settings: {e}")
    except (TypeError, ValueError) as e:
        logger.error(f"Settings format error for user {uid}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid settings format: {e}")

    # Save to Firestore
    ref.set(validated.model_dump(mode="json"))

    logger.info(f"Settings saved successfully for user {uid}")

    # Return settings without password
    result = validated.model_dump()
    result.pop("iflowPassword", None)
    return result


@router.delete("/settings/credentials", status_code=204)
def delete_credentials(user: dict = Depends(require_firebase_user)):
    """
    Delete stored iFlow credentials. User will need to re-enter them.
    """
    db = get_db()
    uid = user["uid"]

    logger.info(f"Deleting iFlow credentials for user {uid}")

    ref = db.collection("settings").document(uid)
    snap = ref.get()

    if not snap.exists:
        logger.debug(f"No settings found for user {uid}, nothing to delete")
        return

    # Remove credentials but keep other settings
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
    Returns success/failure without executing actual check-in/out.
    """
    from services.iso_task import test_credentials as test_creds

    db = get_db()
    uid = user["uid"]

    logger.info(f"Testing credentials for user {uid}")

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
    password = settings.get("iflowPassword")

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
