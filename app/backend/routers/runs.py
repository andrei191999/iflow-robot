from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud.firestore_v1 import FieldFilter

from core.db import get_db
from core.security import require_firebase_user

router = APIRouter(prefix="/api", tags=["runs"])

@router.get("/runs")
def list_runs(
    scheduleId: str = Query(..., description="ID of the schedule"),
    user: dict = Depends(require_firebase_user),
) -> List[Dict[str, Any]]:
    db = get_db()
    uid = user["uid"]

    # uid == X AND scheduleId == Y ORDER BY scheduledAt
    q = (
        db.collection("runs")
          .where(filter=FieldFilter("uid", "==", uid))
          .where(filter=FieldFilter("scheduleId", "==", scheduleId))
          .order_by("scheduledAt")
          .stream()
    )
    out: List[Dict[str, Any]] = []
    for d in q:
        obj = d.to_dict()
        obj["id"] = d.id
        out.append(obj)
    return out
