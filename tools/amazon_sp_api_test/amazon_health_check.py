"""
amazon_health_check.py — One-command SP-API readiness check for ClearSettle.

Runs all checks in sequence and prints a clear ✅/❌ summary.
Designed to be the first thing you run before any SP-API integration work.

Run:
    python amazon_health_check.py

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional

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
)


# ─────────────────────────────────────────────────────────────────────────────
# Health check result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HealthResult:
    name:    str
    passed:  bool
    detail:  str
    elapsed: float = 0.0  # seconds


# ─────────────────────────────────────────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────────────────────────────────────────

def _check_env_vars(config: SPAPIConfig) -> HealthResult:
    start = time.time()
    required = {
        "LWA_CLIENT_ID":        config.lwa_client_id,
        "LWA_CLIENT_SECRET":    config.lwa_client_secret,
        "LWA_REFRESH_TOKEN":    config.lwa_refresh_token,
        "AWS_ACCESS_KEY_ID":    config.aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": config.aws_secret_access_key,
        "SP_API_ENDPOINT":      config.sp_api_endpoint,
    }
    missing = [k for k, v in required.items() if not v.strip()]
    elapsed = time.time() - start
    if missing:
        return HealthResult(
            "Environment variables",
            False,
            f"missing: {', '.join(missing)}",
            elapsed,
        )
    is_sandbox = "sandbox" in config.sp_api_endpoint.lower()
    env_tag = "SANDBOX" if is_sandbox else "PRODUCTION"
    return HealthResult(
        "Environment variables",
        True,
        f"all set  [{env_tag}: {config.sp_api_endpoint}]",
        elapsed,
    )


def _check_lwa_token(config: SPAPIConfig) -> tuple[HealthResult, Optional[LWAToken]]:
    start = time.time()
    try:
        token = exchange_refresh_token(config)
        elapsed = time.time() - start
        return HealthResult(
            "OAuth / LWA token",
            True,
            f"obtained  expires in {token.expires_in}s  ({elapsed*1000:.0f}ms)",
            elapsed,
        ), token
    except LWAError as e:
        msg = str(e)
        hints = {
            "invalid_client": " → check LWA_CLIENT_ID / LWA_CLIENT_SECRET",
            "invalid_grant":  " → refresh token expired, re-authorise the app",
            "unauthorized":   " → credentials rejected by Amazon LWA",
        }
        hint = next((h for k, h in hints.items() if k in msg.lower()), "")
        return HealthResult(
            "OAuth / LWA token", False,
            f"exchange failed: {msg}{hint}",
            time.time() - start,
        ), None
    except Exception as e:
        return HealthResult(
            "OAuth / LWA token", False,
            f"unexpected error: {e}",
            time.time() - start,
        ), None


def _check_aws_identity(config: SPAPIConfig) -> HealthResult:
    start = time.time()
    try:
        identity = get_caller_identity(config)
        elapsed = time.time() - start
        return HealthResult(
            "AWS credentials (STS)",
            True,
            f"Account={identity['account']}  ({elapsed*1000:.0f}ms)",
            elapsed,
        )
    except AWSError as e:
        msg = str(e)
        hints = {
            "InvalidClientTokenId": " → key ID invalid or deactivated",
            "SignatureDoesNotMatch": " → AWS_SECRET_ACCESS_KEY is wrong",
            "ExpiredToken":         " → temporary credentials have expired",
        }
        hint = next((h for k, h in hints.items() if k in msg), "")
        return HealthResult(
            "AWS credentials (STS)", False,
            f"{msg}{hint}",
            time.time() - start,
        )
    except Exception as e:
        return HealthResult(
            "AWS credentials (STS)", False,
            str(e),
            time.time() - start,
        )


def _check_seller_api(config: SPAPIConfig, token: LWAToken) -> HealthResult:
    start = time.time()
    client = SPAPIClient(config)
    client._token = token  # reuse existing token

    resp = client.get("/sellers/v1/marketplaceParticipations")
    elapsed = time.time() - start

    if resp.ok:
        count = 0
        if isinstance(resp.body, dict):
            count = len(resp.body.get("payload", []))
        return HealthResult(
            "Sellers API",
            True,
            f"{count} marketplace(s)  ({resp.latency_ms:.0f}ms)",
            elapsed,
        )

    if resp.status_code == 403:
        return HealthResult(
            "Sellers API", False,
            "403 Forbidden — app may not be published or seller hasn't authorised it",
            elapsed,
        )
    return HealthResult(
        "Sellers API", False,
        f"HTTP {resp.status_code}: {resp.error_message()}",
        elapsed,
    )


def _check_reports_api(config: SPAPIConfig, token: LWAToken) -> HealthResult:
    start = time.time()
    client = SPAPIClient(config)
    client._token = token

    resp = client.get("/reports/2021-06-30/reports", params={"pageSize": "1"})
    elapsed = time.time() - start

    if resp.ok:
        return HealthResult(
            "Reports API",
            True,
            f"accessible  ({resp.latency_ms:.0f}ms)",
            elapsed,
        )
    if resp.status_code == 403:
        return HealthResult(
            "Reports API", False,
            "403 Forbidden — add 'reports' to the app's IAM policy or publish the app",
            elapsed,
        )
    return HealthResult(
        "Reports API", False,
        f"HTTP {resp.status_code}: {resp.error_message()}",
        elapsed,
    )


def _check_sandbox(config: SPAPIConfig, token: LWAToken) -> HealthResult:
    """Quick sandbox ping: hit EU sandbox sellers endpoint."""
    import httpx
    from _sp_client import sigv4_headers

    start = time.time()
    sandbox_url = "https://sandbox.sellingpartnerapi-eu.amazon.com/sellers/v1/marketplaceParticipations"
    creds = get_aws_credentials(config)

    base_headers = {
        "x-amz-access-token": token.access_token,
        "content-type":       "application/json",
        "user-agent":         "ClearSettle/SPAPITest/1.0",
    }
    signed = sigv4_headers(
        method        = "GET",
        url           = sandbox_url,
        body          = "",
        extra_headers = base_headers,
        access_key    = creds.access_key_id,
        secret_key    = creds.secret_access_key,
        session_token = creds.session_token,
        region        = "eu-west-1",
    )

    try:
        resp = httpx.get(sandbox_url, headers=signed, timeout=15)
        elapsed = time.time() - start
        reachable = resp.status_code > 0
        status_ok = resp.status_code < 500
        if reachable and status_ok:
            return HealthResult(
                "Sandbox (EU)",
                True,
                f"HTTP {resp.status_code}  ({elapsed*1000:.0f}ms)",
                elapsed,
            )
        return HealthResult(
            "Sandbox (EU)", False,
            f"HTTP {resp.status_code} — server error",
            elapsed,
        )
    except Exception as e:
        return HealthResult(
            "Sandbox (EU)", False,
            f"unreachable: {e}",
            time.time() - start,
        )


def _check_role_arn(config: SPAPIConfig) -> Optional[HealthResult]:
    """Only run if AWS_ROLE_ARN is configured."""
    if not config.aws_role_arn:
        return None
    start = time.time()
    try:
        from _sp_client import _assume_role
        temp = _assume_role(config)
        return HealthResult(
            "IAM Role Assumption",
            True,
            f"{config.aws_role_arn} → key={temp.access_key_id}",
            time.time() - start,
        )
    except AWSError as e:
        return HealthResult(
            "IAM Role Assumption", False, str(e),
            time.time() - start,
        )
    except Exception as e:
        return HealthResult(
            "IAM Role Assumption", False, str(e),
            time.time() - start,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Print helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_result(r: HealthResult) -> None:
    if r.passed:
        Printer.ok(r.name, r.detail)
    else:
        Printer.fail(r.name, r.detail)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    Printer.header("ClearSettle  Amazon SP-API — Health Check")
    print(f"  Running at: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    Printer.divider()

    # ── Load config ───────────────────────────────────────────────────────
    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Environment setup", str(e))
        Printer.footer("FAILED — fix .env and re-run.")
        return 1

    results: list[HealthResult] = []

    # 1. Environment variables
    r = _check_env_vars(config)
    _print_result(r)
    results.append(r)

    # 2. AWS credentials
    r = _check_aws_identity(config)
    _print_result(r)
    results.append(r)

    # 3. IAM Role (if configured)
    role_result = _check_role_arn(config)
    if role_result:
        _print_result(role_result)
        results.append(role_result)

    # 4. OAuth / LWA token exchange
    lwa_result, token = _check_lwa_token(config)
    _print_result(lwa_result)
    results.append(lwa_result)

    if token is None:
        # Cannot proceed without a token
        Printer.fail(
            "Sellers API",       "skipped — no LWA token"
        )
        Printer.fail("Reports API",      "skipped — no LWA token")
        Printer.fail("Sandbox (EU)",     "skipped — no LWA token")
        Printer.divider()
        Printer.footer("FAILED — resolve OAuth issue first.")
        return 1

    # 5. Sellers API
    r = _check_seller_api(config, token)
    _print_result(r)
    results.append(r)

    # 6. Reports API
    r = _check_reports_api(config, token)
    _print_result(r)
    results.append(r)

    # 7. Sandbox
    r = _check_sandbox(config, token)
    _print_result(r)
    results.append(r)

    # ── Summary ───────────────────────────────────────────────────────────
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total  = len(results)
    total_elapsed = sum(r.elapsed for r in results)

    Printer.divider()
    Printer.kv("Checks passed",  f"{passed}/{total}")
    Printer.kv("Total time",     f"{total_elapsed:.1f}s")

    if failed == 0:
        Printer.footer(
            f"ALL CHECKS PASSED ✅  "
            f"ClearSettle SP-API integration is ready."
        )
        return 0
    else:
        Printer.footer(
            f"FAILED — {failed}/{total} check(s) failed. "
            f"Fix the issues above before production integration."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
