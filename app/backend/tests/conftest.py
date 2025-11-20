import os
import pytest
from fastapi.testclient import TestClient

import sys, pathlib

# Set test environment variables before any imports
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"

# repo root = .../iflow-robot
ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKEND = ROOT / "app" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.app import create_app
from core import db as core_db
from core import security as core_sec
from tests.utils_fake_db import FakeDB

@pytest.fixture(scope="session")
def test_app():
    # dev bypass for cron route
    os.environ["DEV_SKIP_OIDC"] = "1"
    app = create_app()
    # override auth dependency to avoid real Firebase in tests
    def _fake_user():
        return {"uid": "u_test", "email": "test@example.com"}
    app.dependency_overrides[core_sec.require_firebase_user] = _fake_user
    return app

@pytest.fixture()
def fake_db(monkeypatch):
    fdb = FakeDB()
    # Routers imported get_db by value; patch each module's symbol.
    from routers import schedules as r_schedules
    from routers import runs as r_runs
    from routers import cron as r_cron
    from routers import settings as r_settings
    monkeypatch.setattr(core_db, "get_db", lambda: fdb)   # for any future imports
    monkeypatch.setattr(r_schedules, "get_db", lambda: fdb)
    monkeypatch.setattr(r_runs, "get_db", lambda: fdb)
    monkeypatch.setattr(r_cron, "get_db", lambda: fdb)
    monkeypatch.setattr(r_settings, "get_db", lambda: fdb)

    # Mock password manager
    class MockPasswordManager:
        def get_password(self, uid):
            return None
        def store_password(self, uid, username, password):
            return True
        def delete_password(self, uid):
            return True
        def password_exists(self, uid):
            return False

    from services import user_passwords
    monkeypatch.setattr(user_passwords, "get_password_manager", lambda: MockPasswordManager())

    return fdb


@pytest.fixture()
def client(test_app, fake_db):
    return TestClient(test_app)
