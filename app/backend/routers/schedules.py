from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1 import FieldFilter
from pydantic import ValidationError

from core.db import get_db
from core.security import require_firebase_user
from schemas.schedule import ScheduleDoc, NextEvent
from services.scheduler_math import compute_next_event

from datetime import datetime, timedelta
from dateutil import tz as _tz

router = APIRouter(prefix="/api", tags=["schedules"])

@router.get("/schedules")
def list_schedules(user: dict = Depends(require_firebase_user)) -> List[Dict[str, Any]]:
    db = get_db()
    uid = user["uid"]
    q = db.collection("schedules").where(filter=FieldFilter("uid", "==", uid)).stream()
    items = []
    for d in q:
        obj = d.to_dict()
        obj["id"] = d.id
        items.append(obj)
    return items

@router.post("/schedules")
def create_schedule(body: dict, user: dict = Depends(require_firebase_user)) -> Dict[str, Any]:
    db = get_db()
    uid = user["uid"]
    body["uid"] = uid

    try:
        schedule = ScheduleDoc(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {e}")

    ev_type, fire_utc, local_date, location = compute_next_event(schedule.spec.model_dump())
    schedule.next_event = NextEvent.model_validate(
        {"type": ev_type, "at": fire_utc.isoformat(), "localDate": local_date, "location": location}
    )

    ref = db.collection("schedules").document()
    ref.set(schedule.model_dump(mode="json"))
    out = schedule.model_dump()
    out["id"] = ref.id
    return out

@router.put("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: str,
    body: dict,
    user: dict = Depends(require_firebase_user),
) -> Dict[str, Any]:
    db = get_db()
    uid = user["uid"]

    ref = db.collection("schedules").document(schedule_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Schedule not found")

    existing = snap.to_dict()
    if not existing or existing.get("uid") != uid:
        raise HTTPException(status_code=403, detail="Not your schedule")

    # Merge: keep owner uid fixed
    body["uid"] = uid

    # Validate full document via Pydantic (simple approach)
    try:
        schedule = ScheduleDoc(**body)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {e}")
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid schedule format: {e}")

    # Recompute next_event whenever spec/active may change
    ev_type, fire_utc, local_date, location = compute_next_event(schedule.spec.model_dump())
    schedule.next_event = NextEvent.model_validate(
        {"type": ev_type, "at": fire_utc.isoformat(), "localDate": local_date, "location": location}
    )

    ref.set(schedule.model_dump(mode="json"))
    out = schedule.model_dump()
    out["id"] = ref.id
    return out

@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str,
    user: dict = Depends(require_firebase_user),
):
    db = get_db()
    uid = user["uid"]

    ref = db.collection("schedules").document(schedule_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Schedule not found")

    doc = snap.to_dict()
    if not doc or doc.get("uid") != uid:
        raise HTTPException(status_code=403, detail="Not your schedule")

    ref.delete()
    return

@router.post("/schedules/preview")
def preview_schedule(body: dict, user: dict = Depends(require_firebase_user)) -> Dict[str, Any]:
    """
    Body example:
    {
      "spec": { ...same shape you save... },
      "count": 10   // optional, default 14
    }
    """
    spec = body.get("spec")
    if not spec:
        raise HTTPException(status_code=400, detail="Missing 'spec'")

    count = int(body.get("count", 14))
    # Start from "now" UTC
    now_utc = datetime.utcnow().replace(tzinfo=_tz.UTC)

    items = []
    # We iteratively compute next_event, then advance "now" to just after that event
    # so the next iteration yields the following event.
    sim_spec = spec  # dict-like
    sim_now = now_utc
    for _ in range(max(1, min(100, count))):
        ev_type, fire_utc, local_date, location = compute_next_event(sim_spec, now_utc=sim_now)
        items.append({
            "type": ev_type,
            "at": fire_utc.isoformat(),
            "localDate": local_date,
            "location": location,
        })
        # Advance simulation time to just after the event fired
        sim_now = fire_utc + timedelta(seconds=1)

    return {"events": items}
