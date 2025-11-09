import os
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException, Request
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token
from google.cloud.firestore_v1 import FieldFilter
from google.cloud import firestore
from dateutil import tz

from core.db import get_db
from schemas.schedule import RunDoc
from services.iso_task import run_iso_check
from services.scheduler_math import compute_next_event

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cron"])

def _verify_scheduler_oidc(request: Request, expected_audience: str):
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing OIDC token")
    tok = auth_header.split(" ", 1)[1].strip()
    id_token.verify_oauth2_token(tok, g_requests.Request(), audience=expected_audience)

@router.post("/cron/tick")
def cron_tick(request: Request) -> Dict[str, int]:
    db = get_db()

    logger.info("=== Cron tick started ===")

    # Dev bypass; in prod Scheduler provides OIDC
    if request.headers.get("x-bypass-oidc") == "true" or os.getenv("DEV_SKIP_OIDC") == "1":
        logger.info("OIDC verification bypassed (dev mode)")
    else:
        expected_aud = f"{request.url.scheme}://{request.url.hostname}"
        _verify_scheduler_oidc(request, expected_audience=expected_aud)
        logger.info("OIDC verification successful")

    now = datetime.utcnow().replace(tzinfo=tz.UTC)
    logger.info(f"Checking for due schedules at {now.isoformat()}")

    due = (
        db.collection("schedules")
          .where(filter=FieldFilter("active", "==", True))
          .where(filter=FieldFilter("next_event.at", "<=", now.isoformat()))
          .stream()
    )

    processed = 0
    for doc in due:
        data = doc.to_dict()
        schedule_id = doc.id
        uid = data["uid"]
        ne = data.get("next_event") or {}
        event_type = ne.get("type")
        location = ne.get("location")
        scheduled_at = ne.get("at") or ""

        logger.info(f"Processing schedule {schedule_id} for user {uid}: {event_type} at {location}")

        # Use transaction to prevent race condition with concurrent cron ticks
        # Check if this event was already processed by comparing lastProcessedAt
        transaction = db.transaction()

        @firestore.transactional
        def process_schedule(transaction, schedule_ref):
            # Re-read schedule within transaction to get latest state
            schedule_snap = schedule_ref.get(transaction=transaction)
            if not schedule_snap.exists:
                logger.warning(f"Schedule {schedule_id} disappeared during processing")
                return False

            schedule_data = schedule_snap.to_dict()
            last_processed = schedule_data.get("lastProcessedAt")
            current_scheduled = schedule_data.get("next_event", {}).get("at")

            # If lastProcessedAt matches current scheduled time, skip (already processed)
            if last_processed == current_scheduled:
                logger.info(f"Schedule {schedule_id} already processed at {last_processed}, skipping")
                return False

            # Mark as processed by setting lastProcessedAt
            transaction.update(schedule_ref, {"lastProcessedAt": current_scheduled})
            return True

        try:
            should_process = process_schedule(transaction, doc.reference)
            if not should_process:
                continue
        except Exception as e:
            logger.error(f"Transaction failed for schedule {schedule_id}: {e}")
            continue

        # Ensure event_type is a string for run_iso_check (fallback to empty string if missing)
        if not isinstance(event_type, str):
            event_type = ""
            logger.warning(f"Event type is not a string for schedule {schedule_id}, using empty string")

        # Fetch user settings for this user
        user_settings = None
        try:
            settings_ref = db.collection("settings").document(uid)
            settings_snap = settings_ref.get()
            if settings_snap.exists:
                user_settings = settings_snap.to_dict()
                logger.info(f"Using per-user settings for {uid}")
            else:
                logger.info(f"No user settings found for {uid}, using environment defaults")
        except Exception as e:
            logger.error(f"Error fetching user settings for {uid}: {e}")
            # Continue with environment defaults

        # Execute the check-in/out with user settings
        status, message = run_iso_check(event_type, location, user_settings)
        if status not in ("success", "failure", "skipped"):
            logger.warning(f"Invalid status '{status}' returned, defaulting to 'success'")
            status = "success"

        logger.info(f"Execution result: {status} - {message}")

        # Record the run
        db.collection("runs").document().set(
            RunDoc(
                scheduleId=schedule_id,
                uid=uid,
                eventType=event_type if event_type in ("checkIn", "checkOut") else "checkIn",
                scheduledAt=scheduled_at,
                status=status,  # type: ignore
                message=message,
                location=location,
            ).model_dump(mode="json")
        )
        logger.info(f"Run recorded in database for schedule {schedule_id}")

        # Compute and update next event
        ev_type, fire_utc, local_date, loc = compute_next_event(data["spec"])
        doc.reference.update(
            {"next_event": {"type": ev_type, "at": fire_utc.isoformat(), "localDate": local_date, "location": loc}}
        )
        logger.info(f"Next event updated: {ev_type} at {fire_utc.isoformat()}")

        processed += 1

    logger.info(f"=== Cron tick completed: {processed} schedules processed ===")
    return {"processed": processed}
