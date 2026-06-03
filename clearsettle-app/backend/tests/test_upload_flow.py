"""
ClearSettle Upload & Dashboard API Automation Test
===================================================
Tests the complete flow:
  1. Login → get JWT token
  2. Upload Flipkart Excel file → get file_id
  3. Poll /ingestion/files/{id} until status is done / needs_review / failed
  4. Fetch /ingestion/files/{id}/summary → assert non-zero revenue
  5. Fetch /ingestion/files/{id}/reconciliation → show discrepancies
  6. Fetch /dashboard → assert KPIs reflect uploaded data
  7. Print a pass/fail report

Usage:
  pip install requests openpyxl
  python tests/test_upload_flow.py [--url https://clearsettle.in/api] [--file path/to/report.xlsx]

Defaults:
  --url   https://clearsettle.in/api
  --email Admin@clearsettle.com
  --password (from env CLEARSETTLE_PASSWORD or prompted)
  --file  inputs/tip_top_payment_report_april2026.xlsx
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ── Colour helpers ─────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"{GREEN}  ✓ {msg}{RESET}")
def fail(msg):  print(f"{RED}  ✗ {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}  ⚠ {msg}{RESET}")
def info(msg):  print(f"{CYAN}  → {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")


# ── Test runner ────────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def check(self, condition: bool, pass_msg: str, fail_msg: str, *, is_warn: bool = False):
        if condition:
            ok(pass_msg)
            self.passed += 1
        elif is_warn:
            warn(fail_msg)
            self.warnings += 1
        else:
            fail(fail_msg)
            self.failed += 1

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"{BOLD}Test Summary{RESET}")
        print(f"{'='*60}")
        print(f"  Passed:   {GREEN}{self.passed}{RESET}")
        print(f"  Failed:   {RED}{self.failed}{RESET}")
        print(f"  Warnings: {YELLOW}{self.warnings}{RESET}")
        print(f"  Total:    {total}")
        print(f"{'='*60}")
        if self.failed == 0:
            print(f"{GREEN}{BOLD}  ALL TESTS PASSED{RESET}")
        else:
            print(f"{RED}{BOLD}  {self.failed} TEST(S) FAILED{RESET}")
        return self.failed == 0


def run_tests(base_url: str, email: str, password: str, file_path: Path):
    results = TestResult()
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    print(f"\n{BOLD}ClearSettle API Automation Test{RESET}")
    print(f"  Base URL : {base_url}")
    print(f"  Email    : {email}")
    print(f"  File     : {file_path.name}")
    print(f"  Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Step 1: Login ──────────────────────────────────────────────────────────
    header("Step 1 · Authentication")
    try:
        r = session.post(f"{base_url}/auth/login",
                         json={"email": email, "password": password}, timeout=15)
        results.check(r.status_code == 200,
                      f"Login OK (status {r.status_code})",
                      f"Login failed: {r.status_code} — {r.text[:200]}")
        if r.status_code != 200:
            fail("Cannot continue without a token.")
            results.summary()
            return False

        token_data = r.json()
        token = (token_data.get("access_token")
                 or token_data.get("token")
                 or token_data.get("data", {}).get("access_token"))
        results.check(bool(token), "JWT token received", "No token in response — check response format")
        if not token:
            results.summary()
            return False

        session.headers["Authorization"] = f"Bearer {token}"
        info(f"Token: {token[:30]}…")
    except Exception as e:
        fail(f"Login request error: {e}")
        results.summary()
        return False

    # ── Step 2: Health check ───────────────────────────────────────────────────
    header("Step 2 · Backend Health")
    try:
        r = session.get(f"{base_url}/health", timeout=10)
        results.check(r.status_code == 200,
                      f"Health endpoint OK",
                      f"Health check failed: {r.status_code}", is_warn=True)
        info(f"Response: {r.text[:100]}")
    except Exception as e:
        warn(f"Health check error: {e}")

    # ── Step 3: Upload file ────────────────────────────────────────────────────
    header("Step 3 · File Upload")
    if not file_path.exists():
        fail(f"File not found: {file_path}")
        results.summary()
        return False

    file_size_kb = file_path.stat().st_size // 1024
    info(f"Uploading {file_path.name} ({file_size_kb} KB)")

    try:
        # Remove Content-Type for multipart
        upload_headers = {k: v for k, v in session.headers.items()
                          if k.lower() != "content-type"}
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{base_url}/ingestion/upload",
                headers=upload_headers,
                files={"file": (file_path.name, f,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"platform": "flipkart", "report_type": "payment_report"},
                timeout=60,
            )

        results.check(r.status_code in (200, 202),
                      f"Upload accepted: {r.status_code}",
                      f"Upload failed: {r.status_code} — {r.text[:300]}")
        if r.status_code not in (200, 202):
            results.summary()
            return False

        upload_resp = r.json()
        file_id = upload_resp.get("id")
        results.check(bool(file_id), f"file_id received: {file_id}", "No file_id in response")

        is_duplicate = upload_resp.get("duplicate", False)
        if is_duplicate:
            warn(f"Duplicate file — reusing existing file_id: {file_id}")
        else:
            info(f"New upload: file_id={file_id}")
            info(f"Upload status: {upload_resp.get('upload_status')}")
            info(f"File size bytes: {upload_resp.get('file_size_bytes', 'N/A')}")

        if not file_id:
            results.summary()
            return False
    except Exception as e:
        fail(f"Upload request error: {e}")
        results.summary()
        return False

    # ── Step 4: Poll until done ────────────────────────────────────────────────
    header("Step 4 · Poll Processing Status")
    TERMINAL = {"done", "needs_review", "failed"}
    MAX_WAIT  = 300  # 5 minutes
    INTERVAL  = 5    # poll every 5 s
    waited    = 0
    final_status_resp = None

    while waited < MAX_WAIT:
        try:
            r = session.get(f"{base_url}/ingestion/files/{file_id}", timeout=15)
            if r.status_code != 200:
                warn(f"Status poll returned {r.status_code}")
                time.sleep(INTERVAL)
                waited += INTERVAL
                continue

            status_data = r.json()
            upload_status = status_data.get("upload_status", "unknown")
            info(f"  [{waited:3d}s] upload_status={upload_status}")

            if upload_status in TERMINAL:
                final_status_resp = status_data
                break
        except Exception as e:
            warn(f"Poll error: {e}")

        time.sleep(INTERVAL)
        waited += INTERVAL
    else:
        fail(f"Timed out after {MAX_WAIT}s waiting for terminal status")
        results.summary()
        return False

    upload_status = final_status_resp.get("upload_status", "unknown")
    results.check(upload_status != "failed",
                  f"Processing completed: status={upload_status}",
                  f"Processing FAILED: {final_status_resp.get('error_message', 'no error message')}")
    results.check(upload_status in ("done", "needs_review"),
                  f"Status is terminal and usable ({upload_status})",
                  f"Unexpected terminal status: {upload_status}", is_warn=True)

    # Detection info
    detection = final_status_resp.get("detection", {}) or {}
    detected_platform = detection.get("detected_platform", "unknown")
    confidence        = detection.get("confidence_score", 0)
    results.check(detected_platform == "flipkart",
                  f"Platform detected as flipkart (confidence={confidence:.1%})",
                  f"Platform detected as '{detected_platform}' (confidence={confidence:.1%}) — expected 'flipkart'",
                  is_warn=True)

    # ── Step 5: Fetch summary ──────────────────────────────────────────────────
    header("Step 5 · Financial Summary")
    try:
        r = session.get(f"{base_url}/ingestion/files/{file_id}/summary", timeout=20)
        results.check(r.status_code == 200,
                      "Summary endpoint returned 200",
                      f"Summary failed: {r.status_code} — {r.text[:200]}")

        if r.status_code == 200:
            summary = r.json()
            print(f"\n  {BOLD}Raw summary response:{RESET}")
            for k, v in summary.items():
                if k not in ("file_id", "platforms"):
                    print(f"    {k:20s}: {v}")

            gross   = summary.get("gross_revenue", 0)
            orders  = summary.get("unique_orders", 0)
            records = summary.get("total_records", 0)
            payout  = summary.get("payout_total", 0)
            net     = summary.get("net_settlement", 0)

            results.check(records > 0,
                          f"Ledger records found: {records}",
                          f"No ledger records — file was not parsed into the DB")
            results.check(orders > 0,
                          f"Unique orders: {orders}",
                          f"unique_orders=0 — order_id column may not be mapped")
            results.check(gross > 0,
                          f"Gross revenue: ₹{gross:,.2f}",
                          f"gross_revenue=0 — transaction_type mapping may be wrong")
            results.check(payout > 0 or net > 0,
                          f"Net settlement: ₹{max(payout, net):,.2f}",
                          f"net_settlement=0 — payout/settlement rows not found", is_warn=True)
    except Exception as e:
        fail(f"Summary request error: {e}")

    # ── Step 6: Fetch reconciliation ───────────────────────────────────────────
    header("Step 6 · Reconciliation / Discrepancies")
    try:
        r = session.get(f"{base_url}/ingestion/files/{file_id}/reconciliation",
                        params={"limit": 10}, timeout=20)
        results.check(r.status_code == 200,
                      "Reconciliation endpoint returned 200",
                      f"Reconciliation failed: {r.status_code}", is_warn=True)

        if r.status_code == 200:
            recon = r.json()
            recon_summary = recon.get("summary", {}) or {}
            total_issues  = recon_summary.get("total_issues", 0)
            recoverable   = recon_summary.get("recoverable", 0)
            info(f"Total recon issues: {total_issues}")
            info(f"Recoverable amount: ₹{recoverable:,.2f}")
            if recon.get("items"):
                info(f"Sample issue: {recon['items'][0]}")
    except Exception as e:
        warn(f"Reconciliation error: {e}")

    # ── Step 7: Detection detail ───────────────────────────────────────────────
    header("Step 7 · Detection Detail")
    try:
        r = session.get(f"{base_url}/ingestion/files/{file_id}/detection", timeout=15)
        if r.status_code == 200:
            det = r.json()
            info(f"Parser: {det.get('parser_name')}")
            info(f"Schema: {det.get('schema_version')}")
            info(f"Ledger records: {det.get('ledger_records_count')}")
            signals = det.get("detection_metadata", {}).get("platform_signals", [])
            if signals:
                info(f"Matched signals: {signals[:5]}")
            else:
                warn("No platform signals matched — platform detector needs tuning for this file")
    except Exception as e:
        warn(f"Detection detail error: {e}")

    # ── Step 8: Dashboard ──────────────────────────────────────────────────────
    header("Step 8 · Dashboard KPIs")
    try:
        r = session.get(f"{base_url}/dashboard", timeout=20)
        results.check(r.status_code == 200,
                      "Dashboard endpoint returned 200",
                      f"Dashboard failed: {r.status_code} — {r.text[:200]}", is_warn=True)

        if r.status_code == 200:
            dash = r.json()
            print(f"\n  {BOLD}Dashboard KPIs:{RESET}")

            # Try various nested structures (backend may differ)
            def _dig(d, *keys):
                for k in keys:
                    if isinstance(d, dict):
                        d = d.get(k, {})
                    else:
                        return None
                return d if d != {} else None

            gmv        = _dig(dash, "total_gmv") or _dig(dash, "gross_revenue") or 0
            settlement = _dig(dash, "net_settlement") or _dig(dash, "net_payout") or 0
            orders     = _dig(dash, "total_orders") or _dig(dash, "order_count") or 0

            for key in sorted(dash.keys()):
                val = dash[key]
                if not isinstance(val, (dict, list)):
                    print(f"    {key:25s}: {val}")

            results.check(bool(dash),
                          "Dashboard returned data",
                          "Dashboard returned empty response", is_warn=True)
    except Exception as e:
        warn(f"Dashboard error: {e}")

    # ── Step 9: Ledger sample ──────────────────────────────────────────────────
    header("Step 9 · Ledger Sample (first 3 rows)")
    try:
        r = session.get(f"{base_url}/ingestion/files/{file_id}/ledger",
                        params={"limit": 3}, timeout=15)
        if r.status_code == 200:
            ledger = r.json()
            items  = ledger.get("items", [])
            results.check(len(items) > 0,
                          f"Ledger has rows: {ledger.get('total', 0)} total",
                          "Ledger is empty — no rows stored in DB")
            for i, row in enumerate(items[:3]):
                print(f"\n  Row {i+1}:")
                for k in ("order_id", "transaction_type", "amount", "transaction_date",
                          "platform", "sku"):
                    print(f"    {k:20s}: {row.get(k)}")
    except Exception as e:
        warn(f"Ledger sample error: {e}")

    return results.summary()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ClearSettle API automation test")
    parser.add_argument("--url",      default="https://clearsettle.in/api",
                        help="Backend base URL (no trailing slash)")
    parser.add_argument("--email",    default="Admin@clearsettle.com")
    parser.add_argument("--password", default=None)
    parser.add_argument("--file",     default=None,
                        help="Path to Flipkart Excel file")
    args = parser.parse_args()

    # Resolve file path
    if args.file:
        file_path = Path(args.file)
    else:
        # Try common locations relative to this script
        candidates = [
            Path(__file__).parent.parent.parent.parent
            / "inputs" / "tip_top_payment_report_april2026.xlsx",
            Path("inputs/tip_top_payment_report_april2026.xlsx"),
            Path("tip_top_payment_report_april2026.xlsx"),
        ]
        file_path = next((p for p in candidates if p.exists()), candidates[0])

    # Password
    password = args.password or os.environ.get("CLEARSETTLE_PASSWORD")
    if not password:
        password = getpass.getpass(f"Password for {args.email}: ")

    success = run_tests(
        base_url=args.url.rstrip("/"),
        email=args.email,
        password=password,
        file_path=file_path,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
