import os, sys, traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from firebase_admin import initialize_app

from routers import schedules, runs, cron, auth_debug, settings, demo
from services.mock_iflow import mock_iflow_router

# Initialize Firebase Admin (ADC on Cloud Run / local)
try:
    initialize_app()
except ValueError:
    pass

from dotenv import load_dotenv
load_dotenv(dotenv_path=".env.local")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIREBASE_PROJECT_ID") or "unknown"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()  # development, staging, production

def create_app() -> FastAPI:
    app = FastAPI(
        title="ISO Backend",
        description="Paste ONLY the raw Firebase ID token in Authorize (no 'Bearer ' prefix). Use /auth/me to verify.",
        version="0.1.0",
        swagger_ui_parameters={"persistAuthorization": True},
    )

    class ErrorLoggerMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            try:
                return await call_next(request)
            except Exception:
                exc_text = "".join(traceback.format_exception(*sys.exc_info()))
                print(f"[ERROR] {request.method} {request.url}\n{exc_text}")
                raise
    app.add_middleware(ErrorLoggerMiddleware)

    # Configure CORS based on environment
    allow_origins = []
    if ENVIRONMENT == "production":
        # Production: strict CORS - only allow production domains
        allow_origin_regex = r"https://(iflow-robot\.web\.app|iflow-robot\.firebaseapp\.com)"
    else:
        # Development/Staging: allow Firebase preview URLs and localhost (http and https)
        allow_origin_regex = r"https?://(iflow-robot(--[\w-]+)?\.(web|firebaseapp)\.app|localhost:\d+|127\.0\.0\.1:\d+)"
        allow_origins = ["http://localhost:5173", "http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )


    @app.get("/health")
    def health():
        return {"ok": True, "project": PROJECT_ID}

    # Mount routers
    app.include_router(auth_debug.router)
    app.include_router(schedules.router)
    app.include_router(runs.router)
    app.include_router(cron.router)
    app.include_router(settings.router)
    app.include_router(demo.router)
    app.include_router(mock_iflow_router)

    # Mount static files for screenshots (local development)
    from fastapi.staticfiles import StaticFiles
    import os

    # Ensure project root screenshots directory exists
    # We are in app/backend, so root is ../../
    screenshots_dir = os.path.abspath("../../screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    app.mount("/screenshots", StaticFiles(directory=screenshots_dir), name="screenshots")

    return app

app = create_app()
