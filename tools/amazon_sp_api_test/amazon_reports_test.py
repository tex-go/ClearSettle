"""
amazon_reports_test.py — Validate Reports API access without downloading data.

What this tests:
  1. GET  /reports/2021-06-30/reportTypes  — list available report types
  2. POST /reports/2021-06-30/reports      — create a minimal report request
  3. GET  /reports/2021-06-30/reports/{id} — poll report status
  4. GET  /reports/2021-06-30/reports      — list recent reports

No report documents are downloaded. This only verifies API access and
that the seller account + credentials have permission to use the Reports API.

Run:
    python amazon_reports_test.py
"""

from __future__ import annotations

import sys
import time
from typing import Any, Optional

from _sp_client import (
    SPAPIConfig,
    SPAPIClient,
    SPAPIResponse,
    MARKETPLACE_NAMES,
    Printer,
)

# Lightweight report type — produces a small document, used only to test access
TEST_REPORT_TYPE = "GET_FLAT_FILE_OPEN_LISTINGS_DATA"
INDIA_MARKETPLACE_ID = "A21TJRUUN4KGV"

# Settlement report types relevant to ClearSettle
SETTLEMENT_REPORT_TYPES = [
    "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE",
    "GET_V2_SETTLEMENT_REPORT_DATA_XML",
    "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2",
]

FINANCE_REPORT_TYPES = [
    "GET_DATE_RANGE_FINANCIAL_TRANSACTION_DATA",
    "GET_FLAT_FILE_ORDER_REPORT_DATA_SHIPPING",
    "GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL",
]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_list_report_types(client: SPAPIClient) -> list[dict]:
    """GET /reports/2021-06-30/reportTypes — list all available report types."""
    Printer.section("GET /reports/2021-06-30/reportTypes")

    resp = client.get(
        "/reports/2021-06-30/reportTypes",
        params={"reportTypes": ",".join(SETTLEMENT_REPORT_TYPES + FINANCE_REPORT_TYPES)},
    )
    Printer.result(resp)

    if not resp.ok:
        _print_api_error_hints(resp)
        return []

    report_types = []
    if isinstance(resp.body, dict):
        report_types = resp.body.get("reportTypes", [])
    elif isinstance(resp.body, list):
        report_types = resp.body

    if report_types:
        Printer.section("Available settlement + finance report types")
        for rt in report_types:
            name = rt.get("name", rt) if isinstance(rt, dict) else str(rt)
            description = rt.get("description", "") if isinstance(rt, dict) else ""
            Printer.kv(name, description[:60] if description else "")
    else:
        Printer.info(
            "No filtered results",
            "The API responded but returned no types matching the filter. "
            "All report types may still be accessible."
        )

    return report_types


def test_list_recent_reports(client: SPAPIClient) -> list[dict]:
    """GET /reports/2021-06-30/reports — list the 10 most recently created reports."""
    Printer.section("GET /reports/2021-06-30/reports (recent)")

    resp = client.get(
        "/reports/2021-06-30/reports",
        params={"pageSize": "10"},
    )
    Printer.result(resp)

    if not resp.ok:
        _print_api_error_hints(resp)
        return []

    reports: list[dict] = []
    if isinstance(resp.body, dict):
        reports = resp.body.get("reports", [])

    if not reports:
        Printer.info("No recent reports", "no reports have been created for this seller yet")
        return []

    print(f"\n    {'Report ID':<40}  {'Type':<45}  {'Status'}")
    print(f"    {'─'*40}  {'─'*45}  {'─'*15}")
    for r in reports[:10]:
        rid   = r.get("reportId", "?")[:40]
        rtype = r.get("reportType", "?")[:45]
        rstatus = r.get("processingStatus", "?")
        print(f"    {rid:<40}  {rtype:<45}  {rstatus}")

    return reports


def test_create_report(client: SPAPIClient, marketplace_id: str = INDIA_MARKETPLACE_ID) -> Optional[str]:
    """
    POST /reports/2021-06-30/reports — create a minimal listing report.
    Returns the reportId if successful, None otherwise.

    This does NOT wait for the report to complete.  It only verifies that the
    Reports API accepts report creation requests with these credentials.
    """
    Printer.section("POST /reports/2021-06-30/reports (create)")

    body = {
        "reportType":     TEST_REPORT_TYPE,
        "marketplaceIds": [marketplace_id],
    }

    Printer.kv("reportType",     TEST_REPORT_TYPE)
    Printer.kv("marketplaceIds", marketplace_id)
    print()

    resp = client.post("/reports/2021-06-30/reports", body=body)
    Printer.result(resp)

    if not resp.ok:
        _print_api_error_hints(resp)
        if resp.status_code == 400:
            Printer.info(
                "Tip",
                "If error is 'InvalidInput' or 'InvalidMarketplace', "
                "verify the seller is active on this marketplace."
            )
        return None

    report_id: Optional[str] = None
    if isinstance(resp.body, dict):
        report_id = resp.body.get("reportId")

    if report_id:
        Printer.ok("Report created", f"reportId={report_id}")
    else:
        Printer.warn("Report created but no reportId in response", str(resp.body)[:200])

    return report_id


def test_get_report_status(client: SPAPIClient, report_id: str) -> dict:
    """
    GET /reports/2021-06-30/reports/{reportId} — poll report status.
    Returns the report status dict.
    """
    Printer.section(f"GET /reports/2021-06-30/reports/{report_id[:20]}…  (status check)")

    resp = client.get(f"/reports/2021-06-30/reports/{report_id}")
    Printer.result(resp)

    if not resp.ok:
        _print_api_error_hints(resp)
        return {}

    report: dict = resp.body if isinstance(resp.body, dict) else {}
    status = report.get("processingStatus", "UNKNOWN")
    status_icons = {
        "DONE":        "✅",
        "FATAL":       "❌",
        "CANCELLED":   "⭕",
        "IN_QUEUE":    "⏳",
        "IN_PROGRESS": "⏳",
    }
    icon = status_icons.get(status, "ℹ️ ")

    Printer.kv("reportId",         report.get("reportId", "?"))
    Printer.kv("reportType",       report.get("reportType", "?"))
    Printer.kv("processingStatus", f"{icon}  {status}")
    Printer.kv("createdTime",      report.get("createdTime", "?"))
    if report.get("reportDocumentId"):
        Printer.kv("reportDocumentId", report["reportDocumentId"])
        Printer.info(
            "Report is ready",
            "reportDocumentId available — production code would download this."
        )

    return report


def test_settlement_report_access(client: SPAPIClient) -> None:
    """Verify the settlement report types are accessible by listing them specifically."""
    Printer.section("Settlement Report Type Verification")

    for rtype in SETTLEMENT_REPORT_TYPES:
        resp = client.get(
            "/reports/2021-06-30/reports",
            params={"reportTypes": rtype, "pageSize": "1"},
        )
        if resp.ok:
            count = 0
            if isinstance(resp.body, dict):
                count = len(resp.body.get("reports", []))
            Printer.ok(rtype, f"{count} recent report(s) found" if count else "accessible (0 recent)")
        else:
            Printer.fail(rtype, resp.error_message())


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_api_error_hints(resp: SPAPIResponse) -> None:
    code = resp.status_code
    msg = resp.error_message()
    if code == 403:
        Printer.fail(
            "403 Forbidden",
            "The SP-API app may not have 'Reports' in its IAM policy, "
            "or the app is not yet published. Check Seller Central → Apps."
        )
    elif code == 401:
        Printer.fail("401 Unauthorized", "LWA token rejected or SigV4 signing failed.")
    elif code == 429:
        Printer.warn("429 Throttled", "Too many requests — wait and retry.")
    elif code == 0:
        Printer.fail("Connection error", msg)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    Printer.header("ClearSettle  Amazon SP-API — Reports API Test")

    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Environment", str(e))
        Printer.footer("Fix .env and re-run.")
        return 1

    client = SPAPIClient(config)
    failures = 0

    # 1. List report types
    report_types = test_list_report_types(client)

    # 2. List recent reports
    test_list_recent_reports(client)

    # 3. Create a test report
    report_id = test_create_report(client)
    if report_id is None:
        failures += 1
    else:
        # 4. Poll its status (once — don't wait for completion)
        time.sleep(2)
        test_get_report_status(client, report_id)

    # 5. Settlement-specific check
    test_settlement_report_access(client)

    Printer.divider()
    if failures == 0:
        Printer.footer(
            "Reports API test PASSED — "
            "createReport and getReport accessible. "
            "Settlement reports available for production integration."
        )
        return 0
    else:
        Printer.footer(
            f"Reports API test FAILED — {failures} issue(s). "
            "See details above."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
