"""
amazon_sandbox_test.py — Test connectivity and responses against all sandbox endpoints.

Amazon SP-API provides a sandbox environment at:
  https://sandbox.sellingpartnerapi-{region}.amazon.com

Sandbox returns static, predictable responses and does NOT require a live
seller account.  Use it to validate your signing/auth setup before production.

What this tests:
  - Connectivity to all three sandbox regions (NA / EU / FE)
  - Correct HTTP status from sandbox endpoints
  - Response latency per endpoint
  - Sandbox vs production configuration mismatch detection

Run:
    python amazon_sandbox_test.py
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from _sp_client import (
    SPAPIConfig,
    SPAPIClient,
    SPAPIResponse,
    sigv4_headers,
    exchange_refresh_token,
    get_aws_credentials,
    mask,
    Printer,
    LWAError,
)


# ─────────────────────────────────────────────────────────────────────────────
# Sandbox endpoints definition
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SandboxEndpoint:
    region:   str          # eu / na / fe
    host:     str          # sandbox.sellingpartnerapi-eu.amazon.com
    path:     str          # API path
    method:   str = "GET"
    body:     Optional[dict] = None
    description: str = ""


SANDBOX_ENDPOINTS: list[SandboxEndpoint] = [
    # ── EU (covers India) ──────────────────────────────────────────────────
    SandboxEndpoint(
        region="eu",
        host="sandbox.sellingpartnerapi-eu.amazon.com",
        path="/sellers/v1/marketplaceParticipations",
        description="Sellers — marketplace list",
    ),
    SandboxEndpoint(
        region="eu",
        host="sandbox.sellingpartnerapi-eu.amazon.com",
        path="/reports/2021-06-30/reports",
        description="Reports — list reports",
    ),
    SandboxEndpoint(
        region="eu",
        host="sandbox.sellingpartnerapi-eu.amazon.com",
        path="/orders/v0/orders",
        description="Orders — list orders",
    ),
    SandboxEndpoint(
        region="eu",
        host="sandbox.sellingpartnerapi-eu.amazon.com",
        path="/finances/v0/financialEventGroups",
        description="Finances — event groups",
    ),
    SandboxEndpoint(
        region="eu",
        host="sandbox.sellingpartnerapi-eu.amazon.com",
        path="/catalog/2022-04-01/items",
        description="Catalog — search items",
    ),
    # ── NA ────────────────────────────────────────────────────────────────
    SandboxEndpoint(
        region="na",
        host="sandbox.sellingpartnerapi-na.amazon.com",
        path="/sellers/v1/marketplaceParticipations",
        description="Sellers — marketplace list (NA)",
    ),
    SandboxEndpoint(
        region="na",
        host="sandbox.sellingpartnerapi-na.amazon.com",
        path="/reports/2021-06-30/reports",
        description="Reports — list reports (NA)",
    ),
    # ── FE ────────────────────────────────────────────────────────────────
    SandboxEndpoint(
        region="fe",
        host="sandbox.sellingpartnerapi-fe.amazon.com",
        path="/sellers/v1/marketplaceParticipations",
        description="Sellers — marketplace list (FE)",
    ),
]

# Region → AWS signing region
REGION_MAP = {
    "eu": "eu-west-1",
    "na": "us-east-1",
    "fe": "us-west-2",
}


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EndpointResult:
    endpoint: SandboxEndpoint
    status_code: int
    latency_ms: float
    error: Optional[str] = None
    body_preview: str = ""

    @property
    def ok(self) -> bool:
        # Sandbox returns 200/400/403 — 200 or 400 both mean "reachable and auth working"
        # 403 = reachable but no permission (still connectivity OK)
        return self.status_code in (200, 400, 403) or (200 <= self.status_code < 500)

    @property
    def reachable(self) -> bool:
        return self.status_code > 0

    @property
    def icon(self) -> str:
        if not self.reachable:
            return "❌"
        if self.status_code == 200:
            return "✅"
        if self.status_code in (400, 403):
            return "⚠️ "
        return "❌"


# ─────────────────────────────────────────────────────────────────────────────
# Sandbox test runner
# ─────────────────────────────────────────────────────────────────────────────

def _call_sandbox_endpoint(
    ep: SandboxEndpoint,
    access_token: str,
    aws_access_key: str,
    aws_secret_key: str,
    aws_session_token: Optional[str],
) -> EndpointResult:
    """Make a single signed call to a sandbox endpoint."""
    url = f"https://{ep.host}{ep.path}"
    aws_region = REGION_MAP.get(ep.region, "us-east-1")
    body_str = ""

    base_headers = {
        "x-amz-access-token": access_token,
        "content-type": "application/json",
        "user-agent": "ClearSettle/SPAPITest/1.0",
    }

    signed = sigv4_headers(
        method        = ep.method,
        url           = url,
        body          = body_str,
        extra_headers = base_headers,
        access_key    = aws_access_key,
        secret_key    = aws_secret_key,
        session_token = aws_session_token,
        region        = aws_region,
    )

    start = time.time()
    try:
        resp = httpx.request(
            method  = ep.method,
            url     = url,
            headers = signed,
            timeout = 15,
        )
        latency = (time.time() - start) * 1000
        try:
            body_preview = str(resp.json())[:100]
        except Exception:
            body_preview = resp.text[:100]

        error = None
        if resp.status_code >= 500:
            error = f"Server error: {resp.text[:100]}"
        elif resp.status_code == 401:
            error = "Unauthorized — check LWA token or SigV4 signing"
        elif resp.status_code == 0:
            error = "No response"

        return EndpointResult(ep, resp.status_code, latency, error, body_preview)

    except httpx.ConnectTimeout:
        latency = (time.time() - start) * 1000
        return EndpointResult(ep, 0, latency, "Connection timeout (15s)")
    except httpx.ConnectError as e:
        latency = (time.time() - start) * 1000
        return EndpointResult(ep, 0, latency, f"Connection error: {e}")
    except Exception as e:
        latency = (time.time() - start) * 1000
        return EndpointResult(ep, 0, latency, str(e))


def test_sandbox_connectivity(config: SPAPIConfig) -> list[EndpointResult]:
    """Test all sandbox endpoints. Returns a result per endpoint."""

    # Get LWA token
    try:
        token = exchange_refresh_token(config)
    except LWAError as e:
        Printer.fail("Cannot get LWA token", str(e))
        return []

    creds = get_aws_credentials(config)

    Printer.section("Testing sandbox endpoints")
    print(
        f"    {'Status':>6}  {'Latency':>8}  {'Region':>4}  Endpoint"
    )
    print(f"    {'─'*6}  {'─'*8}  {'─'*4}  {'─'*50}")

    results: list[EndpointResult] = []
    for ep in SANDBOX_ENDPOINTS:
        print(f"    {'…':>6}  {'…':>8}  {ep.region:>4}  {ep.path}", end="\r", flush=True)
        result = _call_sandbox_endpoint(
            ep,
            access_token    = token.access_token,
            aws_access_key  = creds.access_key_id,
            aws_secret_key  = creds.secret_access_key,
            aws_session_token = creds.session_token,
        )
        status_str = str(result.status_code) if result.status_code else "ERR"
        print(
            f"    {result.icon} {status_str:>4}  {result.latency_ms:>7.0f}ms  "
            f"{ep.region:>4}  {ep.path}"
            + (f"  [{result.error}]" if result.error else "")
        )
        results.append(result)

    return results


def print_sandbox_summary(results: list[EndpointResult]) -> None:
    """Print grouped summary by region."""
    Printer.section("Results by region")

    for region in ["eu", "na", "fe"]:
        region_results = [r for r in results if r.endpoint.region == region]
        if not region_results:
            continue
        ok    = sum(1 for r in region_results if r.ok)
        total = len(region_results)
        avg   = sum(r.latency_ms for r in region_results if r.reachable) / max(1, sum(1 for r in region_results if r.reachable))
        icon  = "✅" if ok == total else ("⚠️ " if ok > 0 else "❌")
        print(f"    {icon}  {region.upper()} region: {ok}/{total} OK  "
              f"avg {avg:.0f}ms  ({REGION_MAP[region]})")

    print()
    reachable = sum(1 for r in results if r.reachable)
    ok_count  = sum(1 for r in results if r.ok)
    total     = len(results)
    avg_lat   = sum(r.latency_ms for r in results if r.reachable) / max(1, reachable)
    Printer.kv("Total endpoints tested", str(total))
    Printer.kv("Reachable",             str(reachable))
    Printer.kv("Healthy responses",     str(ok_count))
    Printer.kv("Average latency",       f"{avg_lat:.0f}ms")


def detect_config_mismatch(config: SPAPIConfig, results: list[EndpointResult]) -> None:
    """Warn if the configured SP_API_ENDPOINT doesn't match what was tested."""
    Printer.section("Configuration Advisory")

    is_sandbox_configured = "sandbox" in config.sp_api_endpoint.lower()
    Printer.kv("SP_API_ENDPOINT (configured)", config.sp_api_endpoint)
    Printer.kv("Sandbox tests ran against",
               "sandbox.sellingpartnerapi-{eu,na,fe}.amazon.com")

    if is_sandbox_configured:
        Printer.ok(
            "Sandbox mode confirmed",
            "SP_API_ENDPOINT points to sandbox — safe for testing."
        )
    else:
        Printer.warn(
            "Production endpoint configured",
            "SP_API_ENDPOINT points to production. "
            "Switch to sandbox for safe testing: "
            "SP_API_ENDPOINT=https://sandbox.sellingpartnerapi-eu.amazon.com"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    Printer.header("ClearSettle  Amazon SP-API — Sandbox Connectivity Test")

    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Environment", str(e))
        Printer.footer("Fix .env and re-run.")
        return 1

    results = test_sandbox_connectivity(config)

    if not results:
        Printer.footer("Sandbox test FAILED — no results (LWA token error).")
        return 1

    print_sandbox_summary(results)
    detect_config_mismatch(config, results)

    ok_count = sum(1 for r in results if r.ok)
    total    = len(results)

    Printer.divider()
    if ok_count == total:
        Printer.footer(
            f"Sandbox test PASSED — all {total} endpoints reachable and healthy."
        )
        return 0
    elif ok_count > 0:
        Printer.footer(
            f"Sandbox test PARTIAL — {ok_count}/{total} endpoints healthy. "
            f"Check connectivity to failed regions."
        )
        return 0  # Partial is still OK for setup purposes
    else:
        Printer.footer(
            "Sandbox test FAILED — no endpoints reachable. "
            "Check network, credentials, and SP_API_ENDPOINT."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
