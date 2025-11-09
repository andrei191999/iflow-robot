from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as admin_auth

_bearer = HTTPBearer(auto_error=False)

def require_firebase_user(creds: HTTPAuthorizationCredentials = Security(_bearer)) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        decoded = admin_auth.verify_id_token(creds.credentials, check_revoked=True)
        return decoded  # contains 'uid', 'email', etc.
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
