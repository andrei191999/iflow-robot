"""
Tests for settings API endpoints - Updated for Secret Manager
"""
import pytest
from unittest.mock import Mock, patch


def test_get_settings_no_existing_settings(client, fake_db):
    """GET /api/settings when user has no settings - returns defaults"""
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["uid"] == "u_test"
    assert "iflowPassword" not in data


def test_get_settings_existing_settings(client, fake_db):
    """GET /api/settings when user has existing settings"""
    fake_db.collection("settings").document("u_test").set({
        "uid": "u_test",
        "iflowUrl": "https://custom.url",
        "iflowUsername": "testuser",
        # Password is in Secret Manager, not Firestore
        "iflowHeadless": False,
        "iflowTimeout": 60000,
    })

    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["iflowUsername"] == "testuser"
    assert "iflowPassword" not in data


def test_update_settings_create_new(client, fake_db, monkeypatch):
    """PUT /api/settings creates new settings when none exist"""
    stored_password = {}

    class MockPasswordManager:
        def get_password(self, uid):
            return stored_password.get(uid)
        def store_password(self, uid, username, password):
            stored_password[uid] = {"username": username, "password": password}
            return True
        def delete_password(self, uid):
            return True
        def password_exists(self, uid):
            return uid in stored_password

    from routers import settings as r_settings
    monkeypatch.setattr(r_settings, "get_password_manager", lambda: MockPasswordManager())

    update_body = {
        "iflowUsername": "newuser",
        "iflowPassword": "newpass",
        "iflowUrl": "https://new.url",
    }

    r = client.put("/api/settings", json=update_body)
    assert r.status_code == 200
    assert "iflowPassword" not in r.json()

    # Password stored in Secret Manager, NOT in Firestore
    saved = fake_db.collection("settings").document("u_test").get().to_dict()
    assert saved["iflowUsername"] == "newuser"
    assert "iflowPassword" not in saved
    assert "u_test" in stored_password


def test_update_settings_partial_update(client, fake_db, monkeypatch):
    """PUT /api/settings updates only provided fields"""
    stored_password = {"u_test": {"username": "olduser", "password": "oldpass"}}

    class MockPasswordManager:
        def get_password(self, uid):
            return stored_password.get(uid)
        def store_password(self, uid, username, password):
            stored_password[uid] = {"username": username, "password": password}
            return True
        def delete_password(self, uid):
            if uid in stored_password:
                del stored_password[uid]
            return True
        def password_exists(self, uid):
            return uid in stored_password

    from routers import settings as r_settings
    monkeypatch.setattr(r_settings, "get_password_manager", lambda: MockPasswordManager())

    fake_db.collection("settings").document("u_test").set({
        "uid": "u_test",
        "iflowUrl": "https://old.url",
        "iflowUsername": "olduser",
        "iflowHeadless": True,
        "iflowTimeout": 30000,
    })

    r = client.put("/api/settings", json={"iflowUsername": "newuser", "iflowTimeout": 45000})
    assert r.status_code == 200
    # Password unchanged in Secret Manager
    assert stored_password["u_test"]["password"] == "oldpass"


def test_delete_credentials_success(client, fake_db, monkeypatch):
    """DELETE /api/settings/credentials removes credentials"""
    stored_password = {"u_test": {"username": "testuser", "password": "testpass"}}

    class MockPasswordManager:
        def get_password(self, uid):
            return stored_password.get(uid)
        def store_password(self, uid, username, password):
            stored_password[uid] = {"username": username, "password": password}
            return True
        def delete_password(self, uid):
            if uid in stored_password:
                del stored_password[uid]
            return True
        def password_exists(self, uid):
            return uid in stored_password

    from routers import settings as r_settings
    monkeypatch.setattr(r_settings, "get_password_manager", lambda: MockPasswordManager())

    fake_db.collection("settings").document("u_test").set({
        "uid": "u_test",
        "iflowUrl": "https://test.url",
        "iflowUsername": "testuser",
        "iflowHeadless": True,
        "iflowTimeout": 30000,
    })

    r = client.delete("/api/settings/credentials")
    assert r.status_code == 204
    # Password removed from Secret Manager
    assert "u_test" not in stored_password


@patch("services.iso_task.test_credentials")
def test_test_credentials_success(mock_test_creds, client, fake_db, monkeypatch):
    """POST /api/settings/test-credentials with valid credentials"""

    class MockPasswordManager:
        def get_password(self, uid):
            return {"username": "testuser", "password": "testpass"}
        def password_exists(self, uid):
            return True

    from routers import settings as r_settings
    monkeypatch.setattr(r_settings, "get_password_manager", lambda: MockPasswordManager())

    fake_db.collection("settings").document("u_test").set({
        "uid": "u_test",
        "iflowUrl": "https://test.url",
        "iflowUsername": "testuser",
        "iflowHeadless": True,
        "iflowTimeout": 30000,
    })

    mock_test_creds.return_value = (True, "Login successful")

    r = client.post("/api/settings/test-credentials")
    assert r.status_code == 200
    assert r.json()["success"] is True


@patch("services.iso_task.test_credentials")
def test_test_credentials_failure(mock_test_creds, client, fake_db, monkeypatch):
    """POST /api/settings/test-credentials with invalid credentials"""

    class MockPasswordManager:
        def get_password(self, uid):
            return {"username": "testuser", "password": "wrongpass"}
        def password_exists(self, uid):
            return True

    from routers import settings as r_settings
    monkeypatch.setattr(r_settings, "get_password_manager", lambda: MockPasswordManager())

    fake_db.collection("settings").document("u_test").set({
        "uid": "u_test",
        "iflowUrl": "https://test.url",
        "iflowUsername": "testuser",
        "iflowHeadless": True,
        "iflowTimeout": 30000,
    })

    mock_test_creds.return_value = (False, "Invalid credentials")

    r = client.post("/api/settings/test-credentials")
    assert r.status_code == 200
    assert r.json()["success"] is False


def test_test_credentials_no_settings(client, fake_db):
    """POST /api/settings/test-credentials when no settings exist"""
    r = client.post("/api/settings/test-credentials")
    assert r.status_code == 400


def test_test_credentials_missing_username(client, fake_db):
    """POST /api/settings/test-credentials with missing username"""
    fake_db.collection("settings").document("u_test").set({"uid": "u_test"})

    r = client.post("/api/settings/test-credentials")
    assert r.status_code == 400


def test_test_credentials_missing_password(client, fake_db, monkeypatch):
    """POST /api/settings/test-credentials with missing password"""

    class MockPasswordManager:
        def get_password(self, uid):
            return None
        def password_exists(self, uid):
            return False

    from routers import settings as r_settings
    monkeypatch.setattr(r_settings, "get_password_manager", lambda: MockPasswordManager())

    fake_db.collection("settings").document("u_test").set({
        "uid": "u_test",
        "iflowUsername": "testuser",
    })

    r = client.post("/api/settings/test-credentials")
    assert r.status_code == 400
