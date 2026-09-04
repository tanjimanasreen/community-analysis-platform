"""Unit tests for scripts/smoke_live_api.py live API smoke test helper."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.smoke_live_api import (
    CognitoAuthContext,
    _generate_temporary_password,
    _redact,
    main,
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
    requested_calls: list[tuple[str, dict[str, str] | None]] = []

    def fake_http(url: str, headers: dict[str, str] | None = None, timeout: float = 15.0):
        requested_calls.append((url, headers))
        if url.endswith("/health"):
            assert headers is None or not headers
            return 200, {"status": "ok", "schema_version": "1.0"}, {}
        elif url.endswith("/ready"):
            # API Gateway Cognito authorizer returns 401 without Bearer token
            if not headers or "Authorization" not in headers:
                return 401, {"message": "Unauthorized"}, {}
            return 200, {"status": "ready", "discovered_runs": 1}, {}
        elif url.endswith("/runs") and not headers:
            return 401, {"message": "Unauthorized"}, {}
        elif url.endswith("/runs") and headers:
            return 200, {"runs": [{"run_id": "test-run-001"}]}, {}
        elif url.endswith("/runs/test-run-001"):
            return 200, {"run_id": "test-run-001", "status": "completed"}, {}
        elif url.endswith("/networks/graph") or url.endswith("/networks/centrality"):
            # Regress if obsolete paths are ever called
            return 404, {"detail": "Not Found"}, {}
        elif url.endswith("/runs/test-run-001/network"):
            return 200, {"nodes": [], "edges": []}, {}
        elif url.endswith("/runs/test-run-001/centrality"):
            return 200, {"records": []}, {}
        else:
            return 200, {"records": []}, {}

    mock_http.side_effect = fake_http

    smoke_test_api(
        api_url="https://test.execute-api.us-east-1.amazonaws.com/api/v1",
        run_id="test-run-001",
        id_token="valid-token-123",
    )

    # Verify exact endpoints requested
    urls = [call[0] for call in requested_calls]
    auth_urls = [call[0] for call in requested_calls if call[1] and "Authorization" in call[1]]
    unauth_urls = [call[0] for call in requested_calls if not call[1] or "Authorization" not in call[1]]

    # 1. Health was called unauthenticated
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/health" in unauth_urls

    # 2. Runs was tested unauthenticated for 401 rejection
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/runs" in unauth_urls

    # 3. Ready was called ONLY authenticated with Bearer token
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/ready" in auth_urls
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/ready" not in unauth_urls

    # 4. Authenticated runs catalog and exact run details
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/runs" in auth_urls
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/runs/test-run-001" in auth_urls

    # 5. Correct canonical paths were used for network and centrality
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/runs/test-run-001/network" in auth_urls
    assert "https://test.execute-api.us-east-1.amazonaws.com/api/v1/runs/test-run-001/centrality" in auth_urls

    # 6. All intended analytical requests were made with authentication
    for endpoint_suffix in [
        "overview",
        "communities",
        "network",
        "centrality",
        "topics",
        "themes",
        "transitions",
        "evolution/paths",
    ]:
        expected_url = f"https://test.execute-api.us-east-1.amazonaws.com/api/v1/runs/test-run-001/{endpoint_suffix}"
        assert expected_url in auth_urls, f"Expected analytical endpoint {expected_url} not called"

    # 7. Obsolete paths were NOT called
    assert not any("networks/graph" in u for u in urls)
    assert not any("networks/centrality" in u for u in urls)


@patch("scripts.smoke_live_api._http_request")
def test_smoke_test_api_skip_auth(mock_http: MagicMock) -> None:
    mock_http.return_value = (200, {"status": "ok", "schema_version": "1.0"}, {})

    smoke_test_api(
        api_url="https://test.execute-api.us-east-1.amazonaws.com/api/v1",
        run_id="test-run-001",
        id_token=None,
    )

    # When id_token is None, only the public health check should be called
    assert mock_http.call_count == 1
    call_url = mock_http.call_args[0][0]
    assert call_url.endswith("/health")


@patch("scripts.smoke_live_api._http_request")
def test_smoke_test_api_readiness_503_fails(mock_http: MagicMock) -> None:
    """Readiness endpoint returning 503 must fail CD deployment acceptance."""
    def fake_http(url: str, headers: dict[str, str] | None = None, timeout: float = 15.0):
        if url.endswith("/health"):
            return 200, {"status": "ok", "schema_version": "1.0"}, {}
        elif url.endswith("/runs") and not headers:
            return 401, {"message": "Unauthorized"}, {}
        elif url.endswith("/ready"):
            # Deployed API readiness contract: 503 indicates artifact serving not ready
            return 503, {"status": "not_ready", "discovered_runs": 0}, {}
        return 200, {}, {}

    mock_http.side_effect = fake_http

    with pytest.raises(AssertionError, match="Readiness endpoint returned 503"):
        smoke_test_api(
            api_url="https://test.execute-api.us-east-1.amazonaws.com/api/v1",
            run_id="test-run-001",
            id_token="valid-token-123",
        )


@patch("scripts.smoke_live_api._http_request")
def test_smoke_test_api_unauthenticated_runs_rejection_assertion(mock_http: MagicMock) -> None:
    def fake_http(url: str, headers: dict[str, str] | None = None, timeout: float = 15.0):
        if url.endswith("/health"):
            return 200, {"status": "ok"}, {}
        elif url.endswith("/runs") and not headers:
            # Bug: returns 200 instead of 401
            return 200, {"runs": []}, {}
        return 200, {}, {}

    mock_http.side_effect = fake_http

    with pytest.raises(AssertionError, match="Expected 401 Unauthorized"):
        smoke_test_api(
            api_url="https://test.execute-api.us-east-1.amazonaws.com/api/v1",
            run_id="test-run-001",
            id_token="valid-token-123",
        )


@patch("scripts.smoke_live_api._http_request")
def test_smoke_endpoints_match_fastapi_routes(mock_http: MagicMock) -> None:
    """Verify that every route actually requested by smoke_test_api exists in FastAPI OpenAPI."""
    from urllib.parse import urlparse
    from src.api.app import create_app

    test_run_id = "test-smoke-contract-run"
    captured_urls: list[str] = []

    valid_auth_analytical = {
        f"/api/v1/runs/{test_run_id}/overview",
        f"/api/v1/runs/{test_run_id}/communities",
        f"/api/v1/runs/{test_run_id}/network",
        f"/api/v1/runs/{test_run_id}/centrality",
        f"/api/v1/runs/{test_run_id}/topics",
        f"/api/v1/runs/{test_run_id}/themes",
        f"/api/v1/runs/{test_run_id}/transitions",
        f"/api/v1/runs/{test_run_id}/evolution/paths",
    }

    def fake_http(url: str, headers: dict[str, str] | None = None, timeout: float = 15.0):
        captured_urls.append(url)
        parsed_path = urlparse(url).path

        if parsed_path == "/api/v1/health":
            return 200, {"status": "ok", "schema_version": "1.0"}, {}
        elif parsed_path == "/api/v1/runs" and not headers:
            return 401, {"message": "Unauthorized"}, {}
        elif parsed_path == "/api/v1/ready" and headers:
            return 200, {"status": "ready"}, {}
        elif parsed_path == "/api/v1/runs" and headers:
            return 200, {"runs": [{"run_id": test_run_id}]}, {}
        elif parsed_path == f"/api/v1/runs/{test_run_id}" and headers:
            return 200, {"run_id": test_run_id, "status": "completed"}, {}
        elif parsed_path in valid_auth_analytical and headers:
            return 200, {}, {}
        else:
            # Reject any unknown URL or typo with 404 to ensure typos fail the smoke run
            return 404, {"detail": f"Unknown or unauthorized URL: {parsed_path}"}, {}

    mock_http.side_effect = fake_http

    # 1. Invoke smoke_test_api using mock
    smoke_test_api(
        api_url="https://api.test/api/v1",
        run_id=test_run_id,
        id_token="valid-token-xyz",
    )

    # 2. Capture actual URLs requested
    assert len(captured_urls) > 0

    # 3. Extract/normalize API paths
    normalized_paths = [
        urlparse(u).path.replace(test_run_id, "{run_id}")
        for u in captured_urls
    ]

    # 4. Load OpenAPI paths
    app = create_app()
    openapi_paths = set(app.openapi()["paths"].keys())

    # 5. Assert every path actually emitted by smoke_test_api exists in OpenAPI route inventory
    for path in normalized_paths:
        assert path in openapi_paths, (
            f"Path '{path}' emitted by smoke_test_api does not exist in FastAPI OpenAPI schema"
        )

    # Retain explicit assertions that obsolete paths are absent from OpenAPI
    assert "/api/v1/runs/{run_id}/networks/graph" not in openapi_paths
    assert "/api/v1/runs/{run_id}/networks/centrality" not in openapi_paths


@patch("scripts.smoke_live_api.smoke_test_api")
def test_main_missing_auth_fails_closed(mock_smoke: MagicMock) -> None:
    exit_code = main(["--api-url", "https://api.test/api/v1", "--run-id", "run-123"])
    assert exit_code != 0
    mock_smoke.assert_not_called()


@patch("scripts.smoke_live_api.smoke_test_api")
def test_main_only_user_pool_id_fails_closed(mock_smoke: MagicMock) -> None:
    exit_code = main([
        "--api-url", "https://api.test/api/v1",
        "--run-id", "run-123",
        "--user-pool-id", "us-east-1_Pool123",
    ])
    assert exit_code != 0
    mock_smoke.assert_not_called()


@patch("scripts.smoke_live_api.smoke_test_api")
def test_main_only_client_id_fails_closed(mock_smoke: MagicMock) -> None:
    exit_code = main([
        "--api-url", "https://api.test/api/v1",
        "--run-id", "run-123",
        "--client-id", "client123",
    ])
    assert exit_code != 0
    mock_smoke.assert_not_called()


@patch("scripts.smoke_live_api.smoke_test_api")
def test_main_skip_auth_supported(mock_smoke: MagicMock) -> None:
    exit_code = main([
        "--api-url", "https://api.test/api/v1",
        "--run-id", "run-123",
        "--skip-auth",
    ])
    assert exit_code == 0
    mock_smoke.assert_called_once_with(
        api_url="https://api.test/api/v1",
        run_id="run-123",
        id_token=None,
        timeout=15.0,
    )


@patch("boto3.client")
@patch("scripts.smoke_live_api.smoke_test_api")
def test_main_explicit_id_token_supported(mock_smoke: MagicMock, mock_boto: MagicMock) -> None:
    exit_code = main([
        "--api-url", "https://api.test/api/v1",
        "--run-id", "run-123",
        "--id-token", "explicit-token-abc",
    ])
    assert exit_code == 0
    mock_smoke.assert_called_once_with(
        api_url="https://api.test/api/v1",
        run_id="run-123",
        id_token="explicit-token-abc",
        timeout=15.0,
    )
    mock_boto.assert_not_called()
