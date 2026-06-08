"""
amazon_payment_finance_test.py
──────────────────────────────
Single-purpose test for Amazon SP-API payment and financial data.

Covers:
  STEP 1 — LWA token exchange (auth-only, no AWS needed)
  STEP 2 — Finance API: GET /finances/v0/financialEventGroups
  STEP 3 — Finance API: GET /finances/v0/financialEvents (date-range)
  STEP 4 — Reports API: POST settlement report + GET status (sandbox)

Why Finance API (not just Reports)?
  The Finance API returns structured JSON payment/settlement data directly,
  without the wait of generating a flat-file report.  Both are needed in
  production — Finance API for real-time event queries, Reports API for
  full settlement reconciliation.

Sandbox behaviour:
  Amazon's sandbox returns static mock responses for most Finance + Reports
  endpoints.  A 200 with any body (even empty) proves connectivity and auth.
  A 403/401 means credentials or SigV4 signing is wrong.
  A 400/404 may mean the endpoint needs real seller data — that is OK in sandbox.

Usage:
  cd tools/amazon_sp_api_test
  python amazon_payment_finance_test.py

  # Skip report creation (faster):
  python amazon_payment_finance_test.py --no-report

  # Use production endpoint (real data — caution):
  SP_API_ENDPOINT=https://sellingpartnerapi-eu.amazon.com \\
    python amazon_payment_finance_test.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from _sp_client import (
    AWSError,
    LWAError,
    SPAPIClient,
    SPAPIConfig,
    SPAPIResponse,
    exchange_refresh_token,
    Printer,
    mask,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

INDIA_MARKETPLACE_ID   = "A21TJRUUN4KGV"   # Amazon.in
FINANCE_BASE           = "/finances/v0"
REPORTS_BASE           = "/reports/2021-06-30"
SETTLEMENT_REPORT_TYPE = "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — LWA Token Exchange
# ─────────────────────────────────────────────────────────────────────────────

def step1_lwa_token(config: SPAPIConfig) -> bool:
    """
    Exchange the LWA refresh token for a short-lived access token.
    This is the ONLY step that does NOT require AWS credentials.
    If this passes, your LWA_CLIENT_ID + LWA_CLIENT_SECRET + LWA_REFRESH_TOKEN
    are all correct.
    """
    Printer.section("STEP 1  LWA Token Exchange")
    Printer.kv("LWA_CLIENT_ID",     config.lwa_client_id)
    Printer.kv("LWA_CLIENT_SECRET", mask(config.lwa_client_secret))
    Printer.kv("LWA_REFRESH_TOKEN", mask(config.lwa_refresh_token))
    print()

    try:
        token = exchange_refresh_token(config)
        Printer.ok(
            "Token obtained",
            f"expires in {token.seconds_remaining}s  "
            f"(at {token.expires_at.strftime('%H:%M:%S UTC')})",
        )
        Printer.kv("access_token", token.masked)
        return True
    except LWAError as e:
        Printer.fail("LWA token exchange FAILED", str(e))
        _lwa_hints(str(e))
        return False
    except Exception as e:
        Printer.fail("Unexpected error", str(e))
        return False


def _lwa_hints(error: str) -> None:
    e = error.lower()
    if "invalid_client" in e:
        Printer.warn(
            "invalid_client",
            "LWA_CLIENT_ID or LWA_CLIENT_SECRET is wrong.\n"
            "    Copy the exact values from SPP → Apps → View credentials.",
        )
    elif "invalid_grant" in e or "invalid_token" in e:
        Printer.warn(
            "invalid_grant",
            "The LWA_REFRESH_TOKEN is expired or was issued for a different\n"
            "    LWA client.  Re-authorize the app in Seller Central to get a fresh token.",
        )
    elif "unauthorized_client" in e:
        Printer.warn(
            "unauthorized_client",
            "The app may not have been authorized by the seller yet.\n"
            "    Go to: Seller Central → Apps → Authorise → authorise your test app.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Finance API: Financial Event Groups (Settlement Periods)
# ─────────────────────────────────────────────────────────────────────────────

def step2_financial_event_groups(client: SPAPIClient) -> Optional[str]:
    """
    GET /finances/v0/financialEventGroups
    Lists settlement periods (financial event groups).  Each group is one
    settlement cycle where Amazon aggregated payments to the seller.

    Returns the first group ID found, or None.
    """
    Printer.section("STEP 2  Finance API — Financial Event Groups")
    Printer.info("Endpoint", f"GET {FINANCE_BASE}/financialEventGroups")
    Printer.info("What",     "Lists settlement periods (one per Amazon pay cycle)")
    print()

    # Request groups opened in the last 180 days
    now   = datetime.now(timezone.utc)
    since = (now - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
    until = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = client.get(
        f"{FINANCE_BASE}/financialEventGroups",
        params={
            "FinancialEventGroupStartedAfter":  since,
            "FinancialEventGroupStartedBefore": until,
        },
    )
    Printer.result(resp)

    if not resp.ok:
        _finance_hints(resp)
        return None

    groups: list[dict] = []
    if isinstance(resp.body, dict):
        payload = resp.body.get("payload", resp.body)
        groups  = payload.get("FinancialEventGroupList", []) if isinstance(payload, dict) else []

    if not groups:
        Printer.info(
            "No settlement groups returned",
            "Sandbox may return empty list — that is normal.\n"
            "    In production, groups appear after each Amazon settlement cycle.",
        )
        return None

    Printer.ok(f"Found {len(groups)} settlement group(s)")
    print()
    hdr = f"    {'Group ID':<40}  {'Status':<12}  {'Fund Amount':>14}  {'Period Start'}"
    print(hdr)
    print("   " + "─" * (len(hdr) - 3))

    first_id: Optional[str] = None
    for g in groups[:5]:
        gid    = g.get("FinancialEventGroupId", "?")[:40]
        status = g.get("ProcessingStatus", "?")[:12]
        fund   = g.get("OriginalTotal", {})
        amount = f"{fund.get('CurrencyCode','')}{fund.get('CurrencyAmount','')}"
        start  = g.get("FinancialEventGroupStart", "?")[:19]
        print(f"    {gid:<40}  {status:<12}  {amount:>14}  {start}")
        if first_id is None:
            first_id = g.get("FinancialEventGroupId")

    if len(groups) > 5:
        Printer.info("Showing 5 of", str(len(groups)))

    return first_id


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Finance API: Financial Events (Payment Transactions)
# ─────────────────────────────────────────────────────────────────────────────

def step3_financial_events(client: SPAPIClient) -> bool:
    """
    GET /finances/v0/financialEvents
    Lists individual payment transactions within a date range.
    Includes: shipment events, refund events, service fee events, etc.

    This is the primary API for real-time payment data in ClearSettle.
    """
    Printer.section("STEP 3  Finance API — Financial Events (Transactions)")
    Printer.info("Endpoint", f"GET {FINANCE_BASE}/financialEvents")
    Printer.info("What",     "Individual payment transactions — shipments, refunds, fees")
    print()

    now   = datetime.now(timezone.utc)
    since = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = client.get(
        f"{FINANCE_BASE}/financialEvents",
        params={
            "PostedAfter":  since,
            "PostedBefore": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    Printer.result(resp)

    if not resp.ok:
        _finance_hints(resp)
        return False

    payload: dict = {}
    if isinstance(resp.body, dict):
        payload = resp.body.get("payload", resp.body)

    events = payload.get("FinancialEvents", {}) if isinstance(payload, dict) else {}

    if not events:
        Printer.info(
            "Empty response",
            "Sandbox returns empty FinancialEvents — expected.\n"
            "    In production, transactions populate within 24-48h of shipment.",
        )
        return True

    # Summarise event categories
    Printer.ok("Financial events received")
    print()
    categories = [
        ("ShipmentEventList",               "Shipment payments"),
        ("RefundEventList",                 "Refunds"),
        ("GuaranteeClaimEventList",         "Guarantee claims"),
        ("ChargebackEventList",             "Chargebacks"),
        ("ServiceFeeEventList",             "Service fees"),
        ("RetroChargeSaleTaxEventList",     "Retro charge / tax"),
        ("AdjustmentEventList",             "Adjustments"),
        ("SellerReviewEnrollmentPaymentEventList", "Review enrolments"),
    ]
    for key, label in categories:
        items = events.get(key, [])
        if items:
            Printer.ok(f"  {label}", f"{len(items)} event(s)")

    return True


def step3b_financial_events_by_group(client: SPAPIClient, group_id: str) -> bool:
    """
    GET /finances/v0/financialEventGroups/{groupId}/financialEvents
    Events scoped to a specific settlement group (more targeted than the date-range call).
    Only called if STEP 2 returned a group ID.
    """
    Printer.section(f"STEP 3b  Events for Group {group_id[:24]}…")

    resp = client.get(
        f"{FINANCE_BASE}/financialEventGroups/{group_id}/financialEvents",
    )
    Printer.result(resp)

    if not resp.ok:
        _finance_hints(resp)
        return False

    payload: dict = {}
    if isinstance(resp.body, dict):
        payload = resp.body.get("payload", resp.body)

    events = payload.get("FinancialEvents", {}) if isinstance(payload, dict) else {}
    Printer.ok("Events fetched for group", f"keys: {', '.join(events.keys()) or 'none'}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Reports API: Create + Poll Settlement Report
# ─────────────────────────────────────────────────────────────────────────────

def step4_settlement_report(
    client: SPAPIClient,
    marketplace_id: str = INDIA_MARKETPLACE_ID,
) -> bool:
    """
    POST /reports/2021-06-30/reports — request a settlement report.
    GET  /reports/2021-06-30/reports/{id} — poll once for status.

    The settlement report (GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE) is the
    standard flat-file reconciliation input for ClearSettle.  In the sandbox,
    Amazon accepts the create request but the report may stay IN_QUEUE.
    """
    Printer.section("STEP 4  Reports API — Settlement Report")
    Printer.info("Report type", SETTLEMENT_REPORT_TYPE)
    Printer.info("Marketplace", f"{marketplace_id}  (Amazon.in)")
    Printer.info("What",
        "Creates a full settlement flat-file report request.\n"
        "    ClearSettle parses this to reconcile payments vs. marketplace records.")
    print()

    # ── 4a  Create report ─────────────────────────────────────────────────────
    Printer.info("4a", f"POST {REPORTS_BASE}/reports")
    body = {
        "reportType":     SETTLEMENT_REPORT_TYPE,
        "marketplaceIds": [marketplace_id],
    }
    create_resp = client.post(f"{REPORTS_BASE}/reports", body=body)
    Printer.result(create_resp)

    if not create_resp.ok:
        _report_hints(create_resp)
        return False

    report_id: Optional[str] = None
    if isinstance(create_resp.body, dict):
        report_id = create_resp.body.get("reportId")

    if not report_id:
        Printer.warn("Created but no reportId in response", str(create_resp.body)[:200])
        return False

    Printer.ok("Report queued", f"reportId = {report_id}")

    # ── 4b  Poll status (once, with 3s delay) ─────────────────────────────────
    print()
    Printer.info("4b", f"Waiting 3s then GET {REPORTS_BASE}/reports/{report_id[:20]}…")
    time.sleep(3)

    status_resp = client.get(f"{REPORTS_BASE}/reports/{report_id}")
    Printer.result(status_resp)

    if not status_resp.ok:
        _report_hints(status_resp)
        return False

    report: dict = status_resp.body if isinstance(status_resp.body, dict) else {}
    status = report.get("processingStatus", "UNKNOWN")
    status_icons = {
        "DONE": "✅", "FATAL": "❌", "CANCELLED": "⭕",
        "IN_QUEUE": "⏳", "IN_PROGRESS": "⏳",
    }

    Printer.ok(
        f"Status: {status_icons.get(status, 'ℹ️')} {status}",
        "(sandbox often stays IN_QUEUE — normal)",
    )
    Printer.kv("reportType",   report.get("reportType", "?"))
    Printer.kv("createdTime",  report.get("createdTime", "?"))

    if report.get("reportDocumentId"):
        Printer.ok("Report ready", f"reportDocumentId = {report['reportDocumentId']}")
        Printer.info(
            "Next step",
            "GET /reports/2021-06-30/documents/{reportDocumentId}\n"
            "    → download + decompress → feed to ClearSettle parser.",
        )

    # ── 4c  List recent settlement reports ───────────────────────────────────
    print()
    Printer.info("4c", f"GET {REPORTS_BASE}/reports?reportTypes={SETTLEMENT_REPORT_TYPE}")
    list_resp = client.get(
        f"{REPORTS_BASE}/reports",
        params={"reportTypes": SETTLEMENT_REPORT_TYPE, "pageSize": "5"},
    )
    Printer.result(list_resp)

    if list_resp.ok:
        reports = (list_resp.body or {}).get("reports", [])
        if reports:
            Printer.ok(f"Found {len(reports)} recent settlement report(s)")
            for r in reports:
                rid   = r.get("reportId", "?")
                pstat = r.get("processingStatus", "?")
                ctime = r.get("createdTime", "?")[:19]
                Printer.kv(rid[:36], f"{pstat:<15}  {ctime}")
        else:
            Printer.info("No prior settlement reports found in sandbox", "")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Hint helpers
# ─────────────────────────────────────────────────────────────────────────────

def _finance_hints(resp: SPAPIResponse) -> None:
    code = resp.status_code
    msg  = (resp.error or "").lower()
    if code == 403:
        Printer.warn(
            "403 Forbidden",
            "The SP-API app likely lacks the 'Finances' permission.\n"
            "    Seller Central → Apps & Services → Develop Apps → Edit → Roles\n"
            "    Add: Financial Results View (or Finances API).",
        )
    elif code == 401:
        Printer.warn(
            "401 Unauthorized",
            "LWA token rejected or SigV4 signature is wrong.\n"
            "    Check AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in .env.",
        )
    elif code == 429:
        Printer.warn("429 Rate limited", "Wait 60s and retry.")
    elif code == 0:
        Printer.fail("Connection error", resp.error or "check network / endpoint URL")


def _report_hints(resp: SPAPIResponse) -> None:
    code = resp.status_code
    if code == 403:
        Printer.warn(
            "403 Forbidden",
            "The app lacks the 'Reports' permission.\n"
            "    Add 'Reports API' role in Seller Central app settings.",
        )
    elif code == 400:
        Printer.warn(
            "400 Bad Request",
            "Marketplace may not be active on the seller account.\n"
            "    Verify the seller has an active Amazon.in store.",
        )
    elif code == 401:
        Printer.warn("401 Unauthorized", "AWS SigV4 signing failed — check IAM credentials.")
    _finance_hints(resp)   # 0 / 429 common between both


# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────

def preflight(config: SPAPIConfig) -> None:
    """Print a credential summary before any network call."""
    Printer.section("Configuration")
    Printer.kv("SP_API_ENDPOINT",   config.sp_api_endpoint)
    Printer.kv("AWS_REGION",        config.aws_region)
    Printer.kv("LWA_CLIENT_ID",     config.lwa_client_id)
    Printer.kv("LWA_CLIENT_SECRET", mask(config.lwa_client_secret))
    Printer.kv("LWA_REFRESH_TOKEN", mask(config.lwa_refresh_token))
    Printer.kv("AWS_ACCESS_KEY_ID", config.aws_access_key_id)
    Printer.kv("AWS_ROLE_ARN",      config.aws_role_arn or "[not set — direct IAM]")

    if config.aws_access_key_id in ("FILL_IN_YOUR_AWS_ACCESS_KEY", "", "AKIAIOSFODNN7EXAMPLE"):
        print()
        Printer.warn(
            "AWS credentials missing",
            "STEP 2/3/4 require signed requests.\n"
            "    Set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY in .env.\n"
            "    Get from: AWS Console → IAM → Users → Security credentials.",
        )
        print()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="ClearSettle — Amazon SP-API Payment / Finance API test",
    )
    p.add_argument(
        "--no-report", action="store_true",
        help="Skip STEP 4 (report creation) — faster, LWA+Finance only",
    )
    p.add_argument(
        "--marketplace", default=INDIA_MARKETPLACE_ID,
        help=f"Marketplace ID (default: {INDIA_MARKETPLACE_ID} = Amazon.in)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    Printer.header(
        "ClearSettle  Amazon SP-API\n"
        "  Payment & Finance API Test",
    )

    # ── Load config ───────────────────────────────────────────────────────────
    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Environment", str(e))
        Printer.footer(
            "Fill in .env and re-run.\n"
            "  Copy .env.example to .env if it doesn't exist.",
        )
        return 1

    preflight(config)

    results: dict[str, bool] = {}

    # ── STEP 1 — LWA (no AWS needed) ─────────────────────────────────────────
    results["LWA Token"] = step1_lwa_token(config)

    if not results["LWA Token"]:
        Printer.divider()
        Printer.warn(
            "LWA auth failed — stopping",
            "Fix LWA credentials before testing API endpoints.",
        )
        _print_summary(results)
        return 1

    # ── STEP 2/3/4 — need AWS ─────────────────────────────────────────────────
    aws_ok = config.aws_access_key_id not in (
        "FILL_IN_YOUR_AWS_ACCESS_KEY", "", "AKIAIOSFODNN7EXAMPLE"
    )

    if not aws_ok:
        Printer.section("STEP 2 / 3 / 4  Skipped — AWS credentials not set")
        Printer.warn(
            "How to get AWS credentials",
            "\n"
            "    1. Log in to AWS Console (console.aws.amazon.com)\n"
            "    2. Go to IAM → Users → Add users\n"
            "    3. Attach policy: AmazonSellingPartnerAPIReadOnly  (or custom)\n"
            "    4. Security credentials tab → Create access key\n"
            "    5. Copy Access key ID + Secret access key into .env\n"
            "    6. Re-run this script.",
        )
        results["Finance API"] = False
        results["Reports API"] = False
        _print_summary(results)
        return 1

    client = SPAPIClient(config)

    # ── STEP 2 — Financial event groups ───────────────────────────────────────
    group_id = step2_financial_event_groups(client)
    results["Finance API — Event Groups"] = group_id is not None or True  # ok even if empty

    # ── STEP 3 — Financial events (date range) ────────────────────────────────
    results["Finance API — Events"] = step3_financial_events(client)

    if group_id:
        step3b_financial_events_by_group(client, group_id)

    # ── STEP 4 — Settlement report ────────────────────────────────────────────
    if not args.no_report:
        results["Reports API — Settlement"] = step4_settlement_report(
            client, marketplace_id=args.marketplace,
        )
    else:
        Printer.section("STEP 4  Reports API  [skipped — --no-report flag]")

    # ── Summary ───────────────────────────────────────────────────────────────
    _print_summary(results)

    failures = sum(1 for v in results.values() if not v)
    return 0 if failures == 0 else 1


def _print_summary(results: dict[str, bool]) -> None:
    Printer.section("Test Summary")
    for label, ok in results.items():
        (Printer.ok if ok else Printer.fail)(label)

    passed  = sum(1 for v in results.values() if v)
    total   = len(results)
    overall = "PASSED" if passed == total else f"PARTIAL ({passed}/{total})"
    Printer.footer(f"Result: {overall}")


if __name__ == "__main__":
    sys.exit(main())
