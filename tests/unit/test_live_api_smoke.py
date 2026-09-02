"""Unit tests for scripts/smoke_live_api.py live API smoke test helper."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.smoke_live_api import (
    CognitoAuthContext,
    _generate_temporary_password,
    _redact,
    smoke_test_api,
)


def test_redact() -> None:
    assert _redact("") == ""
    assert _redact("short") == "***"
    assert _redact("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9") == "eyJh...VCJ9"


def test_generate_temporary_password() -> None:
    pwd = _generate_temporary_password(20)
    assert len(pwd) == 20
    assert any(c.islower() for c in pwd)
    assert any(c.isupper() for c in pwd)
    assert any(c.isdigit() for c in pwd)
    assert any(c in "!@#$%^&*" for c in pwd)


def test_cognito_auth_context_normal_lifecycle() -> None:
    """Normal success path: create, set password, auth, and cleanup in __exit__."""
    cognito_mock = MagicMock()
    cognito_mock.admin_initiate_auth.return_value = {
        "AuthenticationResult": {"IdToken": "mock-id-token-12345678"}
    }

    with CognitoAuthContext(cognito_mock, "us-east-1_TestPool", "test-client-id") as token:
        assert token == "mock-id-token-12345678"
        cognito_mock.admin_create_user.assert_called_once()
        cognito_mock.admin_set_user_password.assert_called_once()
        cognito_mock.admin_initiate_auth.assert_called_once()
        assert cognito_mock.admin_delete_user.call_count == 0

    # Verify cleanup occurred upon __exit__
    cognito_mock.admin_delete_user.assert_called_once()


def test_cognito_cleanup_when_admin_create_user_fails() -> None:
    """Case 1: AdminCreateUser fails -> no delete attempt since user was never created."""
    cognito_mock = MagicMock()
    cognito_mock.admin_create_user.side_effect = RuntimeError("Failed to create user in pool")

    ctx = CognitoAuthContext(cognito_mock, "us-east-1_TestPool", "test-client-id")
    with pytest.raises(RuntimeError, match="Failed to create user in pool"):
        ctx.__enter__()

    cognito_mock.admin_delete_user.assert_not_called()


def test_cognito_cleanup_when_set_password_fails() -> None:
    """Case 2: AdminCreateUser succeeds, AdminSetUserPassword fails -> user must be deleted, original error preserved."""
    cognito_mock = MagicMock()
    cognito_mock.admin_set_user_password.side_effect = RuntimeError("Password policy violation")

    ctx = CognitoAuthContext(cognito_mock, "us-east-1_TestPool", "test-client-id")
    with pytest.raises(RuntimeError, match="Password policy violation"):
        ctx.__enter__()

    cognito_mock.admin_create_user.assert_called_once()
    cognito_mock.admin_delete_user.assert_called_once()


def test_cognito_cleanup_when_initiate_auth_fails() -> None:
    """Case 3: Create & set password succeed, AdminInitiateAuth fails -> user must be deleted, original error preserved."""
    cognito_mock = MagicMock()
    cognito_mock.admin_initiate_auth.side_effect = RuntimeError("Auth flow disabled")

    ctx = CognitoAuthContext(cognito_mock, "us-east-1_TestPool", "test-client-id")
    with pytest.raises(RuntimeError, match="Auth flow disabled"):
        ctx.__enter__()

    cognito_mock.admin_create_user.assert_called_once()
    cognito_mock.admin_set_user_password.assert_called_once()
    cognito_mock.admin_delete_user.assert_called_once()


def test_cognito_cleanup_fails_preserves_original_exception() -> None:
    """Case 4: Setup fails AND admin_delete_user fails -> original exception is still raised without masking."""
    cognito_mock = MagicMock()
    cognito_mock.admin_set_user_password.side_effect = ValueError("Original setup failure")
    cognito_mock.admin_delete_user.side_effect = RuntimeError("Cognito deletion network timeout")

    ctx = CognitoAuthContext(cognito_mock, "us-east-1_TestPool", "test-client-id")
    with pytest.raises(ValueError, match="Original setup failure"):
        ctx.__enter__()

    cognito_mock.admin_delete_user.assert_called_once()


def test_cognito_auth_context_cleanup_on_in_context_error() -> None:
    """Case 5: Context manager body raises -> cleanup still invoked in __exit__."""
    cognito_mock = MagicMock()
    cognito_mock.admin_initiate_auth.return_value = {
        "AuthenticationResult": {"IdToken": "mock-id-token-12345678"}
    }

    with pytest.raises(RuntimeError, match="Simulated smoke test failure"):
        with CognitoAuthContext(cognito_mock, "us-east-1_TestPool", "test-client-id"):
            raise RuntimeError("Simulated smoke test failure")

    cognito_mock.admin_delete_user.assert_called_once()


@patch("scripts.smoke_live_api._http_request")
def test_smoke_test_api(mock_http: MagicMock) -> None:
    def fake_http(url, headers=None, timeout=15.0):
        if url.endswith("/health"):
            return 200, {"status": "ok", "schema_version": "1.0"}, {}
        elif url.endswith("/ready"):
            return 200, {"status": "ready"}, {}
        elif url.endswith("/runs") and not headers:
            return 401, {"detail": "Unauthorized"}, {}
        elif url.endswith("/runs") and headers:
            return 200, {"runs": [{"run_id": "test-run-001"}]}, {}
        elif url.endswith("/runs/test-run-001"):
            return 200, {"run_id": "test-run-001", "status": "completed"}, {}
        else:
            return 200, {"data": []}, {}

    mock_http.side_effect = fake_http

    smoke_test_api(
        api_url="https://test.execute-api.us-east-1.amazonaws.com/api/v1",
        run_id="test-run-001",
        id_token="valid-token-123",
    )
    assert mock_http.call_count >= 5
