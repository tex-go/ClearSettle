"""
amazon_sp_api_test.py — Full SP-API integration test suite for ClearSettle.

Runs all test modules in sequence and produces a consolidated report.
Can also be used as a pytest module: pytest amazon_sp_api_test.py -v

Run standalone:
    python amazon_sp_api_test.py

Run with pytest:
    pip install pytest
    pytest amazon_sp_api_test.py -v --tb=short
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import pytest

from _sp_client import (
    SPAPIConfig,
    SPAPIClient,
    LWAToken,
    exchange_refresh_token,
    get_caller_identity,
    get_aws_credentials,
    Printer,
    LWAError,
    AWSError,
    INDIA_MARKETPLACE_ID,
)

# Shared state for pytest fixtures
_config: Optional[SPAPIConfig] = None
_token:  Optional[LWAToken]   = None
_client: Optional[SPAPIClient] = None

INDIA_MARKETPLACE_ID = "A21TJRUUN4KGV"


# ─────────────────────────────────────────────────────────────────────────────
# pytest fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config() -> SPAPIConfig:
    return SPAPIConfig.from_env()


@pytest.fixture(scope="session")
def lwa_token(config: SPAPIConfig) -> LWAToken:
    return exchange_refresh_token(config)


@pytest.fixture(scope="session")
def sp_client(config: SPAPIConfig, lwa_token: LWAToken) -> SPAPIClient:
    client = SPAPIClient(config)
    client._token = lwa_token
    return client


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 1 — Environment / Configuration
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvironment:

    def test_all_required_env_vars_present(self, config: SPAPIConfig) -> None:
        """All mandatory env vars must be non-empty."""
        assert config.lwa_client_id,       "LWA_CLIENT_ID is empty"
        assert config.lwa_client_secret,   "LWA_CLIENT_SECRET is empty"
        assert config.lwa_refresh_token,   "LWA_REFRESH_TOKEN is empty"
        assert config.aws_access_key_id,   "AWS_ACCESS_KEY_ID is empty"
        assert config.aws_secret_access_key, "AWS_SECRET_ACCESS_KEY is empty"
        assert config.sp_api_endpoint,     "SP_API_ENDPOINT is empty"
        assert config.aws_region,          "AWS_REGION could not be determined"

    def test_lwa_client_id_format(self, config: SPAPIConfig) -> None:
        """LWA client ID must follow Amazon's amzn1.application-oa2-client.* format."""
        assert config.lwa_client_id.startswith("amzn1."), (
            f"LWA_CLIENT_ID should start with 'amzn1.' — got: {config.lwa_client_id[:20]}"
        )

    def test_refresh_token_format(self, config: SPAPIConfig) -> None:
        """Refresh token must start with Atzr| or Atza|."""
        prefix_ok = (
            config.lwa_refresh_token.startswith("Atzr|") or
            config.lwa_refresh_token.startswith("Atza|")
        )
        assert prefix_ok, (
            f"LWA_REFRESH_TOKEN should start with 'Atzr|' or 'Atza|' "
            f"— got: {config.lwa_refresh_token[:10]}"
        )

    def test_aws_key_format(self, config: SPAPIConfig) -> None:
        """AWS Access Key ID must start with AKIA or ASIA."""
        assert config.aws_access_key_id.startswith(("AKIA", "ASIA")), (
            f"AWS_ACCESS_KEY_ID should start with AKIA or ASIA — "
            f"got: {config.aws_access_key_id[:8]}"
        )

    def test_sp_api_endpoint_is_https(self, config: SPAPIConfig) -> None:
        """SP_API_ENDPOINT must use HTTPS."""
        assert config.sp_api_endpoint.startswith("https://"), (
            f"SP_API_ENDPOINT must use HTTPS — got: {config.sp_api_endpoint}"
        )

    def test_aws_region_is_valid(self, config: SPAPIConfig) -> None:
        """AWS region must be a known SP-API region."""
        valid = {"us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"}
        assert config.aws_region in valid, (
            f"AWS_REGION '{config.aws_region}' is not a standard SP-API region. "
            f"Expected one of: {sorted(valid)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 2 — AWS Credentials
# ─────────────────────────────────────────────────────────────────────────────

class TestAWSCredentials:

    def test_get_caller_identity(self, config: SPAPIConfig) -> None:
        """STS GetCallerIdentity must succeed with the configured credentials."""
        identity = get_caller_identity(config)
        assert identity["account"], "STS returned empty Account ID"
        assert identity["arn"],     "STS returned empty ARN"

    def test_caller_identity_account_format(self, config: SPAPIConfig) -> None:
        """AWS account ID must be a 12-digit number."""
        identity = get_caller_identity(config)
        account = identity["account"]
        assert account.isdigit() and len(account) == 12, (
            f"Expected 12-digit AWS account ID, got: {account}"
        )

    def test_aws_credentials_effective(self, config: SPAPIConfig) -> None:
        """get_aws_credentials must return non-empty key ID."""
        creds = get_aws_credentials(config)
        assert creds.access_key_id,     "No access key ID in effective credentials"
        assert creds.secret_access_key, "No secret access key in effective credentials"
        if config.aws_role_arn:
            assert creds.session_token, (
                "Session token expected when using role assumption"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 3 — LWA OAuth
# ─────────────────────────────────────────────────────────────────────────────

class TestLWAOAuth:

    def test_token_exchange_succeeds(self, lwa_token: LWAToken) -> None:
        """LWA token exchange must return a non-empty access token."""
        assert lwa_token.access_token, "Access token is empty"
        assert lwa_token.token_type,   "Token type is empty"

    def test_token_expires_in_positive(self, lwa_token: LWAToken) -> None:
        """Token expiry must be a positive integer (seconds)."""
        assert lwa_token.expires_in > 0, (
            f"expires_in must be positive, got: {lwa_token.expires_in}"
        )

    def test_token_not_immediately_expired(self, lwa_token: LWAToken) -> None:
        """Freshly obtained token must have > 60s remaining."""
        remaining = lwa_token.seconds_remaining
        assert remaining > 60, (
            f"Token expires too soon: {remaining}s remaining. "
            "System clock may be skewed."
        )

    def test_token_type_is_bearer(self, lwa_token: LWAToken) -> None:
        """Amazon LWA always returns 'bearer' token type."""
        assert lwa_token.token_type.lower() == "bearer", (
            f"Expected token_type='bearer', got '{lwa_token.token_type}'"
        )

    def test_refresh_token_is_reusable(self, config: SPAPIConfig) -> None:
        """Refresh token must work for multiple consecutive exchanges."""
        t1 = exchange_refresh_token(config)
        t2 = exchange_refresh_token(config)
        assert t1.access_token, "First exchange produced empty token"
        assert t2.access_token, "Second exchange produced empty token"
        # Both should be valid (may be same cached token or different)


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 4 — Sellers API
# ─────────────────────────────────────────────────────────────────────────────

class TestSellersAPI:

    def test_get_marketplace_participations(self, sp_client: SPAPIClient) -> None:
        """GET /sellers/v1/marketplaceParticipations must return HTTP 200."""
        resp = sp_client.get("/sellers/v1/marketplaceParticipations")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. "
            f"Error: {resp.error_message()}"
        )

    def test_response_has_payload(self, sp_client: SPAPIClient) -> None:
        """Marketplace participations response must contain a 'payload' list."""
        resp = sp_client.get("/sellers/v1/marketplaceParticipations")
        assert resp.ok, f"Request failed: {resp.error_message()}"
        assert isinstance(resp.body, dict), "Response body is not a dict"
        assert "payload" in resp.body, (
            f"Response missing 'payload' key. Body keys: {list(resp.body.keys())}"
        )

    def test_at_least_one_marketplace(self, sp_client: SPAPIClient) -> None:
        """Seller must participate in at least one marketplace."""
        resp = sp_client.get("/sellers/v1/marketplaceParticipations")
        assert resp.ok
        payload = resp.body.get("payload", [])
        assert len(payload) > 0, (
            "Seller has no marketplace participations. "
            "Verify the seller account is active."
        )

    def test_marketplace_has_required_fields(self, sp_client: SPAPIClient) -> None:
        """Each marketplace entry must have id, name, countryCode."""
        resp = sp_client.get("/sellers/v1/marketplaceParticipations")
        assert resp.ok
        for item in resp.body.get("payload", []):
            mkt = item.get("marketplace", {})
            assert mkt.get("id"),          f"Marketplace missing 'id': {item}"
            assert mkt.get("countryCode"), f"Marketplace missing 'countryCode': {item}"

    def test_response_latency_under_5s(self, sp_client: SPAPIClient) -> None:
        """Sellers API should respond within 5 seconds."""
        resp = sp_client.get("/sellers/v1/marketplaceParticipations")
        assert resp.latency_ms < 5000, (
            f"Response too slow: {resp.latency_ms:.0f}ms (limit: 5000ms)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 5 — Reports API
# ─────────────────────────────────────────────────────────────────────────────

class TestReportsAPI:

    def test_list_reports_accessible(self, sp_client: SPAPIClient) -> None:
        """GET /reports/2021-06-30/reports must return HTTP 200."""
        resp = sp_client.get("/reports/2021-06-30/reports", params={"pageSize": "1"})
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Error: {resp.error_message()}"
        )

    def test_list_reports_response_structure(self, sp_client: SPAPIClient) -> None:
        """Reports list response must have 'reports' key."""
        resp = sp_client.get("/reports/2021-06-30/reports", params={"pageSize": "1"})
        assert resp.ok
        assert isinstance(resp.body, dict), "Response body is not a dict"
        assert "reports" in resp.body, (
            f"Expected 'reports' key in response. Keys: {list(resp.body.keys())}"
        )

    def test_create_report_accepted(self, sp_client: SPAPIClient) -> None:
        """POST /reports/2021-06-30/reports must return HTTP 202 (accepted)."""
        body = {
            "reportType":     "GET_FLAT_FILE_OPEN_LISTINGS_DATA",
            "marketplaceIds": [INDIA_MARKETPLACE_ID],
        }
        resp = sp_client.post("/reports/2021-06-30/reports", body=body)
        # 202 = accepted (async), 200 = immediate, both are valid
        assert resp.status_code in (200, 202), (
            f"Expected 202/200 (accepted), got {resp.status_code}. "
            f"Error: {resp.error_message()}"
        )

    def test_create_report_returns_id(self, sp_client: SPAPIClient) -> None:
        """Created report must return a reportId."""
        body = {
            "reportType":     "GET_FLAT_FILE_OPEN_LISTINGS_DATA",
            "marketplaceIds": [INDIA_MARKETPLACE_ID],
        }
        resp = sp_client.post("/reports/2021-06-30/reports", body=body)
        if resp.status_code not in (200, 202):
            pytest.skip(f"Report creation returned {resp.status_code}")
        assert isinstance(resp.body, dict), "Response body is not a dict"
        assert resp.body.get("reportId"), (
            f"No reportId in response: {resp.body}"
        )

    def test_get_report_after_create(self, sp_client: SPAPIClient) -> None:
        """A freshly created report must be retrievable by its reportId."""
        body = {
            "reportType":     "GET_FLAT_FILE_OPEN_LISTINGS_DATA",
            "marketplaceIds": [INDIA_MARKETPLACE_ID],
        }
        create_resp = sp_client.post("/reports/2021-06-30/reports", body=body)
        if create_resp.status_code not in (200, 202):
            pytest.skip(f"Report creation unavailable: HTTP {create_resp.status_code}")
        if not isinstance(create_resp.body, dict) or not create_resp.body.get("reportId"):
            pytest.skip("No reportId returned from createReport")

        report_id = create_resp.body["reportId"]
        time.sleep(2)

        get_resp = sp_client.get(f"/reports/2021-06-30/reports/{report_id}")
        assert get_resp.status_code == 200, (
            f"getReport returned {get_resp.status_code} for id={report_id}. "
            f"Error: {get_resp.error_message()}"
        )
        assert isinstance(get_resp.body, dict)
        assert get_resp.body.get("reportId") == report_id


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 6 — Sandbox
# ─────────────────────────────────────────────────────────────────────────────

class TestSandboxConnectivity:

    def test_sandbox_eu_reachable(self, config: SPAPIConfig, lwa_token: LWAToken) -> None:
        """EU sandbox endpoint must be reachable and return a non-5xx response."""
        import httpx
        from _sp_client import sigv4_headers, get_aws_credentials

        url = "https://sandbox.sellingpartnerapi-eu.amazon.com/sellers/v1/marketplaceParticipations"
        creds = get_aws_credentials(config)
        signed = sigv4_headers(
            method="GET", url=url, body="",
            extra_headers={
                "x-amz-access-token": lwa_token.access_token,
                "content-type": "application/json",
            },
            access_key=creds.access_key_id,
            secret_key=creds.secret_access_key,
            session_token=creds.session_token,
            region="eu-west-1",
        )
        resp = httpx.get(url, headers=signed, timeout=15)
        assert resp.status_code < 500, (
            f"Sandbox EU returned server error {resp.status_code}"
        )

    def test_sandbox_na_reachable(self, config: SPAPIConfig, lwa_token: LWAToken) -> None:
        """NA sandbox endpoint must be reachable."""
        import httpx
        from _sp_client import sigv4_headers, get_aws_credentials

        url = "https://sandbox.sellingpartnerapi-na.amazon.com/sellers/v1/marketplaceParticipations"
        creds = get_aws_credentials(config)
        signed = sigv4_headers(
            method="GET", url=url, body="",
            extra_headers={
                "x-amz-access-token": lwa_token.access_token,
                "content-type": "application/json",
            },
            access_key=creds.access_key_id,
            secret_key=creds.secret_access_key,
            session_token=creds.session_token,
            region="us-east-1",
        )
        resp = httpx.get(url, headers=signed, timeout=15)
        assert resp.status_code < 500, (
            f"Sandbox NA returned server error {resp.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Standalone runner (non-pytest)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SuiteResult:
    name:    str
    passed:  int = 0
    failed:  int = 0
    errors:  list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed

    @property
    def ok(self) -> bool:
        return self.failed == 0


def _run_suite(name: str, tests: list[tuple[str, object]]) -> SuiteResult:
    result = SuiteResult(name=name)
    Printer.section(name)
    for label, fn in tests:
        try:
            fn()
            Printer.ok(label)
            result.passed += 1
        except AssertionError as e:
            Printer.fail(label, str(e)[:100])
            result.failed += 1
            result.errors.append(f"{label}: {e}")
        except Exception as e:
            Printer.fail(label, f"unexpected: {e}")
            result.failed += 1
            result.errors.append(f"{label}: {e}")
    return result


def run_standalone() -> int:
    Printer.header("ClearSettle  Amazon SP-API — Full Integration Test Suite")

    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Configuration", str(e))
        return 1

    # Obtain token once for the whole suite
    try:
        token = exchange_refresh_token(config)
    except LWAError as e:
        Printer.fail("LWA Token Exchange", str(e))
        Printer.footer("Cannot run tests without LWA access token.")
        return 1

    client = SPAPIClient(config)
    client._token = token

    suites: list[SuiteResult] = []

    # ── Environment ───────────────────────────────────────────────────────
    env_suite = TestEnvironment()
    suites.append(_run_suite("Environment / Configuration", [
        ("Required env vars present",    lambda: env_suite.test_all_required_env_vars_present(config)),
        ("LWA client ID format",         lambda: env_suite.test_lwa_client_id_format(config)),
        ("Refresh token format",         lambda: env_suite.test_refresh_token_format(config)),
        ("AWS key ID format",            lambda: env_suite.test_aws_key_format(config)),
        ("SP-API endpoint is HTTPS",     lambda: env_suite.test_sp_api_endpoint_is_https(config)),
        ("AWS region is valid",          lambda: env_suite.test_aws_region_is_valid(config)),
    ]))

    # ── AWS ───────────────────────────────────────────────────────────────
    aws_suite = TestAWSCredentials()
    suites.append(_run_suite("AWS Credentials", [
        ("STS GetCallerIdentity",        lambda: aws_suite.test_get_caller_identity(config)),
        ("Account ID format",            lambda: aws_suite.test_caller_identity_account_format(config)),
        ("Effective credentials",        lambda: aws_suite.test_aws_credentials_effective(config)),
    ]))

    # ── OAuth ─────────────────────────────────────────────────────────────
    oauth_suite = TestLWAOAuth()
    suites.append(_run_suite("LWA OAuth", [
        ("Token exchange succeeds",      lambda: oauth_suite.test_token_exchange_succeeds(token)),
        ("expires_in is positive",       lambda: oauth_suite.test_token_expires_in_positive(token)),
        ("Token not immediately expired",lambda: oauth_suite.test_token_not_immediately_expired(token)),
        ("Token type is bearer",         lambda: oauth_suite.test_token_type_is_bearer(token)),
        ("Refresh token reusable",       lambda: oauth_suite.test_refresh_token_is_reusable(config)),
    ]))

    # ── Sellers API ───────────────────────────────────────────────────────
    seller_suite = TestSellersAPI()
    suites.append(_run_suite("Sellers API", [
        ("GET marketplaceParticipations", lambda: seller_suite.test_get_marketplace_participations(client)),
        ("Response has payload",          lambda: seller_suite.test_response_has_payload(client)),
        ("At least one marketplace",      lambda: seller_suite.test_at_least_one_marketplace(client)),
        ("Marketplace has required fields",lambda: seller_suite.test_marketplace_has_required_fields(client)),
        ("Latency under 5s",              lambda: seller_suite.test_response_latency_under_5s(client)),
    ]))

    # ── Reports API ───────────────────────────────────────────────────────
    reports_suite = TestReportsAPI()
    suites.append(_run_suite("Reports API", [
        ("List reports accessible",      lambda: reports_suite.test_list_reports_accessible(client)),
        ("Response structure",           lambda: reports_suite.test_list_reports_response_structure(client)),
        ("Create report accepted",       lambda: reports_suite.test_create_report_accepted(client)),
        ("Create report returns ID",     lambda: reports_suite.test_create_report_returns_id(client)),
        ("Get report after create",      lambda: reports_suite.test_get_report_after_create(client)),
    ]))

    # ── Sandbox ───────────────────────────────────────────────────────────
    sb_suite = TestSandboxConnectivity()
    suites.append(_run_suite("Sandbox Connectivity", [
        ("Sandbox EU reachable",         lambda: sb_suite.test_sandbox_eu_reachable(config, token)),
        ("Sandbox NA reachable",         lambda: sb_suite.test_sandbox_na_reachable(config, token)),
    ]))

    # ── Summary ───────────────────────────────────────────────────────────
    Printer.section("Test Summary")
    total_passed = sum(s.passed for s in suites)
    total_failed = sum(s.failed for s in suites)
    total_tests  = sum(s.total  for s in suites)

    for s in suites:
        icon = "✅" if s.ok else "❌"
        print(f"  {icon}  {s.name:<35} {s.passed}/{s.total}")

    Printer.divider()
    if total_failed == 0:
        Printer.footer(
            f"ALL {total_tests} TESTS PASSED ✅  "
            f"SP-API integration fully validated."
        )
        return 0
    else:
        Printer.footer(
            f"{total_passed}/{total_tests} tests passed, {total_failed} failed. "
            f"See details above."
        )
        return 1


if __name__ == "__main__":
    sys.exit(run_standalone())
