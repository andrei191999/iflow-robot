import os
from typing import List, Dict, Any

from fastapi import FastAPI, Request, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from google.cloud import firestore
from firebase_admin import auth as admin_auth, initialize_app

from datetime import datetime
from dateutil import tz

from models import NextEvent, ScheduleDoc, RunDoc
from scheduler_math import compute_next_event
from iso_task import run_iso_check

# --- Firebase Admin init (Cloud Run uses Workload Identity; local uses ADC if present)
try:
    initialize_app()
except ValueError:
    pass

# --- Project ID: prefer GOOGLE_CLOUD_PROJECT on Cloud Run; fallback to FIREBASE_PROJECT_ID
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIREBASE_PROJECT_ID")
if not PROJECT_ID:
    raise RuntimeError("Set GOOGLE_CLOUD_PROJECT or FIREBASE_PROJECT_ID")

app = FastAPI(
    title="ISO Backend",
    description=(
        "Paste ONLY the raw Firebase ID token in Authorize (no 'Bearer ' prefix). "
        "Use /auth/me to verify your token."
    ),
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

# Swagger security: HTTP Bearer (paste only the token in UI)
bearer_scheme = HTTPBearer(auto_error=False)

def require_firebase_user(
    creds: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Reads Bearer token from Authorization header, verifies Firebase ID token,
    and returns decoded claims (contains 'uid', 'email', etc.).
    In Swagger, paste ONLY the raw token; Swagger will add 'Bearer ' automatically.
    """
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = creds.credentials
    try:
        decoded = admin_auth.verify_id_token(token, check_revoked=True)
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

# CORS — allow your hosting + localhost
ALLOWED_ORIGINS = [
    "https://iflow-robot.web.app",
    "https://iflow-robot.firebaseapp.com",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

db = firestore.Client(project=PROJECT_ID)

# ---------- Collections
def schedules_col():
    return db.collection("schedules")

def runs_col():
    return db.collection("runs")

# ---------- Health & auth debug
@app.get("/health")
def health():
    return {"ok": True, "project": PROJECT_ID}

@app.get("/auth/me")
def auth_me(user: dict = Security(require_firebase_user)):
    return {"uid": user.get("uid"), "email": user.get("email")}

# ---------- User API
@app.get("/api/schedules")
def list_schedules(user: dict = Security(require_firebase_user)) -> List[Dict[str, Any]]:
    uid = user["uid"]
    docs = schedules_col().where("uid", "==", uid).stream()
    items = []
    for d in docs:
        obj = d.to_dict()
        obj["id"] = d.id
        items.append(obj)
    return items

@app.post("/api/schedules")
def create_schedule(
    body: dict,
    user: dict = Security(require_firebase_user),
) -> Dict[str, Any]:
    uid = user["uid"]
    body["uid"] = uid

    # Validate the incoming schedule
    try:
        schedule = ScheduleDoc(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {e}")

    # Compute next_event (strings only in the model_dump)
    ev_type, fire_utc, local_date, location = compute_next_event(schedule.spec.model_dump())
    schedule.next_event = NextEvent.model_validate(
        {"type": ev_type, "at": fire_utc.isoformat(), "localDate": local_date, "location": location}
    )

    # IMPORTANT: serialize with mode="json" so dates/datetimes become strings
    ref = schedules_col().document()
    ref.set(schedule.model_dump(mode="json"))

    out = ref.get().to_dict()
    out["id"] = ref.id
    return out

@app.get("/api/runs")
def list_runs(
    scheduleId: str,
    user: dict = Security(require_firebase_user),
) -> List[Dict[str, Any]]:
    uid = user["uid"]
    q = (
        runs_col()
        .where("uid", "==", uid)
        .where("scheduleId", "==", scheduleId)
        .order_by("scheduledAt")
        .stream()
    )
    return [{**d.to_dict(), "id": d.id} for d in q]

# ---------- Cron (internal) — OIDC from Cloud Scheduler
from google.oauth2 import id_token
from google.auth.transport import requests as g_requests

def _verify_scheduler_oidc(request: Request, expected_audience: str):
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing OIDC token")
    tok = auth_header.split(" ", 1)[1].strip()
    try:
        id_token.verify_oauth2_token(tok, g_requests.Request(), audience=expected_audience)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid OIDC token: {e}")

@app.post("/cron/tick")
def cron_tick(request: Request):
    # Build audience from the request host (no env var needed)
    expected_aud = f"{request.url.scheme}://{request.url.hostname}"
    _verify_scheduler_oidc(request, expected_audience=expected_aud)

    now = datetime.utcnow().replace(tzinfo=tz.UTC)

    # Due: active == true AND next_event.at <= now (we store ISO strings)
    due = (
        schedules_col()
        .where("active", "==", True)
        .where("next_event.at", "<=", now.isoformat())
        .stream()
    )

    processed = 0
    for doc in due:
        data = doc.to_dict()
        schedule_id = doc.id
        uid = data["uid"]
        ne = data.get("next_event", {}) or {}
        event_type = ne.get("type")
        location = ne.get("location")

        status, message = run_iso_check(event_type, location)
        if status not in ("success", "failure", "skipped"):
            status = "success"

        # Write run (no date objects, all strings)
        runs_col().document().set(
            RunDoc(
                scheduleId=schedule_id,
                uid=uid,
                eventType=event_type,
                scheduledAt=ne.get("at"),
                status=status,  # type: ignore
                message=message,
                location=location,
            ).model_dump(mode="json")
        )

        # Compute and update next event
        ev_type, fire_utc, local_date, loc = compute_next_event(data["spec"])
        doc.reference.update(
            {"next_event": {"type": ev_type, "at": fire_utc.isoformat(), "localDate": local_date, "location": loc}}
        )
        processed += 1

    return {"processed": processed}
