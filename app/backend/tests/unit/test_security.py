"""
Tests for security module.
Increase coverage of security.py from 42% to >80%
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from core.security import require_firebase_user


def test_require_firebase_user_success():
    """Test successful token verification"""
    # Mock credentials
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "valid_token_123"

    # Mock Firebase admin verify_id_token
    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        mock_verify.return_value = {
            "uid": "user123",
            "email": "test@example.com",
            "name": "Test User",
        }

        result = require_firebase_user(mock_creds)

        assert result["uid"] == "user123"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"

        # Verify verify_id_token was called correctly
        mock_verify.assert_called_once_with("valid_token_123", check_revoked=True)


def test_require_firebase_user_missing_credentials():
    """Test with missing credentials (None)"""
    with pytest.raises(HTTPException) as exc_info:
        require_firebase_user(None)

    assert exc_info.value.status_code == 401
    assert "Missing bearer token" in exc_info.value.detail


def test_require_firebase_user_empty_credentials():
    """Test with empty credentials string"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = ""

    with pytest.raises(HTTPException) as exc_info:
        require_firebase_user(mock_creds)

    assert exc_info.value.status_code == 401
    assert "Missing bearer token" in exc_info.value.detail


def test_require_firebase_user_invalid_token():
    """Test with invalid Firebase token"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "invalid_token"

    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        # Firebase raises ValueError for invalid tokens
        mock_verify.side_effect = ValueError("Invalid token format")

        with pytest.raises(HTTPException) as exc_info:
            require_firebase_user(mock_creds)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


def test_require_firebase_user_expired_token():
    """Test with expired Firebase token"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "expired_token"

    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        # Firebase raises specific exception for expired tokens
        from firebase_admin import auth
        mock_verify.side_effect = auth.ExpiredIdTokenError("Token expired", "cause")

        with pytest.raises(HTTPException) as exc_info:
            require_firebase_user(mock_creds)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


def test_require_firebase_user_revoked_token():
    """Test with revoked Firebase token"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "revoked_token"

    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        # Firebase raises specific exception for revoked tokens
        from firebase_admin import auth
        mock_verify.side_effect = auth.RevokedIdTokenError("Token revoked")

        with pytest.raises(HTTPException) as exc_info:
            require_firebase_user(mock_creds)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


def test_require_firebase_user_certificate_error():
    """Test with certificate/network error"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "some_token"

    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        # Network/certificate errors
        mock_verify.side_effect = Exception("Certificate verification failed")

        with pytest.raises(HTTPException) as exc_info:
            require_firebase_user(mock_creds)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


def test_require_firebase_user_minimal_decoded_token():
    """Test with minimal decoded token (only uid)"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "minimal_token"

    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        # Minimal valid token with just uid
        mock_verify.return_value = {"uid": "user456"}

        result = require_firebase_user(mock_creds)

        assert result["uid"] == "user456"
        assert "email" not in result


def test_require_firebase_user_full_decoded_token():
    """Test with full decoded token containing all fields"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "full_token"

    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        # Full token with many fields
        mock_verify.return_value = {
            "uid": "user789",
            "email": "full@example.com",
            "email_verified": True,
            "name": "Full User",
            "picture": "https://example.com/pic.jpg",
            "iss": "https://securetoken.google.com/project-id",
            "aud": "project-id",
            "auth_time": 1234567890,
            "sub": "user789",
            "iat": 1234567890,
            "exp": 1234571490,
            "firebase": {
                "identities": {
                    "email": ["full@example.com"]
                },
                "sign_in_provider": "password"
            }
        }

        result = require_firebase_user(mock_creds)

        # Check key fields are present
        assert result["uid"] == "user789"
        assert result["email"] == "full@example.com"
        assert result["email_verified"] is True
        assert result["name"] == "Full User"
        assert "firebase" in result


def test_require_firebase_user_check_revoked_flag():
    """Test that check_revoked parameter is always True"""
    mock_creds = Mock(spec=HTTPAuthorizationCredentials)
    mock_creds.credentials = "test_token"

    with patch("core.security.admin_auth.verify_id_token") as mock_verify:
        mock_verify.return_value = {"uid": "user123"}

        require_firebase_user(mock_creds)

        # Verify check_revoked=True was passed
        args, kwargs = mock_verify.call_args
        assert kwargs.get("check_revoked") is True
