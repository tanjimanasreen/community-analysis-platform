#!/usr/bin/env python3
"""Live API smoke testing script against deployed API Gateway and Cognito.

Verifies:
- Public endpoints (/api/v1/health, /api/v1/ready)
- 401 Unauthorized rejection for protected endpoints without authentication
- Temporary Cognito user lifecycle (AdminCreateUser -> AdminSetUserPassword -> AdminInitiateAuth -> AdminDeleteUser)
- Clean credential redaction in all log messages
- Authenticated retrieval of run-scoped analytical endpoints (/runs, /overview, /communities, /networks, /topics, /themes, /evolution)
"""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import string
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smoke_live_api")


def _redact(text: str) -> str:
    """Redact tokens and passwords for safe logging."""
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def _generate_temporary_password(length: int = 18) -> str:
    """Generate a compliant strong password meeting standard Cognito password policies."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    # Ensure at least one lowercase, one uppercase, one digit, one symbol
    pwd = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    pwd += [secrets.choice(chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


class CognitoAuthContext:
    """Manages the lifecycle of a temporary Cognito test user."""

    def __init__(
        self,
        cognito_client: Any,
        user_pool_id: str,
        client_id: str,
    ) -> None:
        self.client = cognito_client
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.username = f"smoke-test-{uuid.uuid4().hex[:10]}"
        self._password = _generate_temporary_password()
        self.id_token: str | None = None
        self._user_created: bool = False

    def _cleanup_user(self) -> None:
        """Attempt to delete temporary user if created, logging safely without raising."""
        if not self._user_created:
            return
        logger.info("Cleaning up temporary Cognito smoke test user '%s'...", self.username)
        try:
            self.client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=self.username,
            )
            self._user_created = False
            logger.info("Temporary Cognito user '%s' deleted successfully.", self.username)
        except Exception as e:
            logger.warning("Failed to delete temporary Cognito user '%s': %s", self.username, e)

    def __enter__(self) -> str:
        logger.info(
            "Creating temporary Cognito smoke test user '%s' in pool '%s'...",
            self.username,
            self.user_pool_id,
        )
        self.client.admin_create_user(
            UserPoolId=self.user_pool_id,
            Username=self.username,
            TemporaryPassword=self._password,
            MessageAction="SUPPRESS",
        )
        self._user_created = True

        try:
            logger.info("Setting permanent password for temporary Cognito user...")
            self.client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=self.username,
                Password=self._password,
                Permanent=True,
            )
            logger.info("Authenticating temporary Cognito user to acquire ID token...")
            auth_response = self.client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": self.username,
                    "PASSWORD": self._password,
                },
            )
            self.id_token = auth_response["AuthenticationResult"]["IdToken"]
            logger.info("Acquired ID token successfully: %s", _redact(self.id_token))
            return self.id_token
        except Exception:
            # Clean up partial state on setup/auth failure while preserving original exception
            self._cleanup_user()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._cleanup_user()


def _http_request(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> tuple[int, dict[str, Any] | bytes, dict[str, str]]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read()
            resp_headers = dict(resp.headers)
            try:
                parsed = json.loads(body.decode("utf-8"))
                return status, parsed, resp_headers
            except (json.JSONDecodeError, UnicodeDecodeError):
                return status, body, resp_headers
    except urllib.error.HTTPError as err:
        body = err.read()
        try:
            parsed = json.loads(body.decode("utf-8"))
            return err.code, parsed, dict(err.headers)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return err.code, body, dict(err.headers)


def smoke_test_api(
    *,
    api_url: str,
    run_id: str,
    id_token: str | None = None,
    timeout: float = 15.0,
) -> None:
    """Execute smoke test suite against live API."""
    base_url = api_url.rstrip("/")
    if not base_url.endswith("/api/v1"):
        api_root = f"{base_url}/api/v1"
    else:
        api_root = base_url

    logger.info("Starting API smoke testing against: %s (run_id: %s)", api_root, run_id)

    # 1. Public Health Check
    health_url = f"{api_root}/health"
    logger.info("Checking unauthenticated public health endpoint: %s", health_url)
    status, payload, _ = _http_request(health_url, timeout=timeout)
    assert status == 200, f"Health endpoint returned {status} (expected 200)"
    assert isinstance(payload, dict) and payload.get("status") == "ok", (
        f"Health endpoint payload mismatch: {payload}"
    )
    logger.info("Health check passed: status=%s, schema_version=%s", status, payload.get("schema_version"))

    # 2. Public / Ready Check
    ready_url = f"{api_root}/ready"
    logger.info("Checking readiness endpoint: %s", ready_url)
    status, payload, _ = _http_request(ready_url, timeout=timeout)
    assert status in (200, 503), f"Readiness endpoint returned {status} (expected 200 or 503)"
    logger.info("Readiness check returned status=%s", status)

    if id_token:
        # 3. Unauthenticated Rejection on Protected Endpoint
        runs_url = f"{api_root}/runs"
        logger.info("Verifying unauthenticated access is rejected on: %s", runs_url)
        status, _, _ = _http_request(runs_url, timeout=timeout)
        assert status == 401, f"Expected 401 Unauthorized for unauthenticated access, got {status}"
        logger.info("Protected endpoint correctly rejected unauthenticated request with 401.")

        auth_headers = {"Authorization": f"Bearer {id_token}"}

        # 4. Authenticated Runs Catalog
        logger.info("Checking authenticated runs list: %s", runs_url)
        status, payload, _ = _http_request(runs_url, headers=auth_headers, timeout=timeout)
        assert status == 200, f"Runs list returned {status} (expected 200)"
        assert isinstance(payload, dict) and "runs" in payload, f"Malformed runs payload: {payload}"
        run_ids = [r.get("run_id") for r in payload.get("runs", []) if isinstance(r, dict)]
        assert run_id in run_ids, f"Expected run_id '{run_id}' not found in catalog runs: {run_ids}"
        logger.info("Run catalog contains expected run_id '%s' (total runs: %d)", run_id, len(run_ids))

        # 5. Authenticated Specific Run Status
        run_detail_url = f"{api_root}/runs/{run_id}"
        logger.info("Checking run details: %s", run_detail_url)
        status, payload, _ = _http_request(run_detail_url, headers=auth_headers, timeout=timeout)
        assert status == 200, f"Run details returned {status} (expected 200)"
        assert isinstance(payload, dict) and payload.get("status") == "completed", (
            f"Run status is not completed: {payload.get('status')}"
        )

        # 6. Authenticated Analytical Endpoints
        endpoints_to_check = [
            f"{api_root}/runs/{run_id}/overview",
            f"{api_root}/runs/{run_id}/communities",
            f"{api_root}/runs/{run_id}/networks/graph",
            f"{api_root}/runs/{run_id}/networks/centrality",
            f"{api_root}/runs/{run_id}/topics",
            f"{api_root}/runs/{run_id}/themes",
            f"{api_root}/runs/{run_id}/transitions",
            f"{api_root}/runs/{run_id}/evolution/paths",
        ]

        for ep in endpoints_to_check:
            logger.info("Checking endpoint: %s", ep)
            status, payload, _ = _http_request(ep, headers=auth_headers, timeout=timeout)
            assert status == 200, f"Endpoint {ep} failed with status {status}"

        logger.info("All authenticated analytical endpoints responded with HTTP 200 OK.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live API smoke test for community-analysis.")
    parser.add_argument("--api-url", required=True, help="Base API URL (API Gateway or CloudFront)")
    parser.add_argument("--run-id", required=True, help="Run ID to smoke test")
    parser.add_argument("--user-pool-id", help="Cognito User Pool ID")
    parser.add_argument("--client-id", help="Cognito App Client ID")
    parser.add_argument("--id-token", help="Explicit pre-acquired ID token")
    parser.add_argument("--region", default="us-east-1", help="AWS Region (default: us-east-1)")
    parser.add_argument("--skip-auth", action="store_true", help="Skip authenticated tests")
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds")

    args = parser.parse_args(argv)

    id_token = args.id_token

    if not args.skip_auth and not id_token and args.user_pool_id and args.client_id:
        import boto3

        cognito_client = boto3.client("cognito-idp", region_name=args.region)
        try:
            with CognitoAuthContext(cognito_client, args.user_pool_id, args.client_id) as token:
                smoke_test_api(
                    api_url=args.api_url,
                    run_id=args.run_id,
                    id_token=token,
                    timeout=args.timeout,
                )
        except Exception as e:
            logger.error("API smoke test failed: %s", e)
            return 1
    else:
        try:
            smoke_test_api(
                api_url=args.api_url,
                run_id=args.run_id,
                id_token=id_token if not args.skip_auth else None,
                timeout=args.timeout,
            )
        except Exception as e:
            logger.error("API smoke test failed: %s", e)
            return 1

    logger.info("Live API smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
