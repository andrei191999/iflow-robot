import os
from fastapi import APIRouter, Depends, HTTPException
import httpx

from core.security import require_firebase_user

router = APIRouter(tags=["auth"])

@router.get("/auth/me")
def auth_me(user: dict = Depends(require_firebase_user)):
    return {"uid": user.get("uid"), "email": user.get("email")}

@router.post("/debug/login")
def debug_login(payload: dict):
    """
    DEV ONLY: exchange email+password for Firebase ID token.
    Enable by setting env ENABLE_DEBUG_LOGIN=1 and FIREBASE_WEB_API_KEY.
    """
    if os.getenv("ENABLE_DEBUG_LOGIN") != "1":
        raise HTTPException(status_code=404, detail="Not enabled")
    api_key = os.getenv("FIREBASE_WEB_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FIREBASE_WEB_API_KEY not set")

    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="email & password required")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    r = httpx.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=20.0)
    r.raise_for_status()
    return r.json()
