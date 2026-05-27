#!/usr/bin/env python3
"""
Amazon SP-API Connection Test
==============================
Logs into ClearSettle, then calls GET /sp-api/test-connection.
The refresh token is read automatically from the database — no manual token needed.

Usage
-----
    pip install httpx python-dotenv
    python test_connection.py

.env (optional — all have defaults)
-------------------------------------
    CLEARSETTLE_URL      = http://localhost:8000   # backend URL
    CLEARSETTLE_EMAIL    = demo@clearsettle.in     # login email
    CLEARSETTLE_PASSWORD = demo123                 # login password

Expected output
---------------
    -> Logging in as demo@clearsettle.in...
    [OK] Logged in

    -> Testing Amazon SP-API connection...
    [OK] Connected!

    {
      "status": "connected",
      "marketplace": "IN",
      "sp_api_access": true,
      ...
    }
"""
import json
import os
import sys


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _explain_http_error(status: int, body: str) -> str:
    if status == 401:
        return "Login failed — wrong email or password."
    if status == 400:
        b = body.lower()
        if "oauth" in b or "refresh" in b:
            return "Amazon OAuth not completed yet. Run GET /sp-api/authorize first."
        if "connected" in b:
            return "Amazon connection status is not 'connected'. Complete the OAuth flow."
        return body[:200]
    if status == 503:
        return "SP API credentials not configured. Use POST /sp-api/config first."
    if status == 504:
        return "SP API request timed out. Check your network or VPN."
    return body[:200]


def run() -> None:
    try:
        import httpx
    except ImportError:
        print("ERROR: Run: pip install httpx", file=sys.stderr)
        sys.exit(1)

    _load_env()

    base_url = os.environ.get("CLEARSETTLE_URL", "http://localhost:8000").rstrip("/")
    email    = os.environ.get("CLEARSETTLE_EMAIL",    "demo@clearsettle.in")
    password = os.environ.get("CLEARSETTLE_PASSWORD", "demo123")

    # ── Step 1: Login ─────────────────────────────────────────────────────────

    print(f"-> Logging in as {email}...")
    try:
        login_resp = httpx.post(
            f"{base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to ClearSettle at {base_url}", file=sys.stderr)
        print("       Is the backend running? (docker compose up)", file=sys.stderr)
        sys.exit(1)
    except httpx.TimeoutException:
        print("ERROR: Login request timed out.", file=sys.stderr)
        sys.exit(1)

    if login_resp.status_code != 200:
        print(f"ERROR: Login failed (HTTP {login_resp.status_code})", file=sys.stderr)
        print(f"       {_explain_http_error(login_resp.status_code, login_resp.text)}", file=sys.stderr)
        sys.exit(1)

    token = login_resp.json().get("access_token")
    if not token:
        print("ERROR: No access_token in login response.", file=sys.stderr)
        sys.exit(1)

    print("[OK] Logged in\n")

    # ── Step 2: Test SP-API connection ────────────────────────────────────────

    print("-> Testing Amazon SP-API connection...")
    try:
        test_resp = httpx.get(
            f"{base_url}/sp-api/test-connection",
            headers={"Authorization": f"Bearer {token}"},
            timeout=35,
        )
    except httpx.TimeoutException:
        print("ERROR: SP-API test request timed out.", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as exc:
        print(f"ERROR: Network error: {exc}", file=sys.stderr)
        sys.exit(1)

    if test_resp.status_code != 200:
        body = test_resp.text
        try:
            detail = test_resp.json().get("detail", body)
        except Exception:
            detail = body

        result = {
            "status":      "failed",
            "http_status": test_resp.status_code,
            "error":       detail,
            "hint":        _explain_http_error(test_resp.status_code, str(detail)),
        }
        print(f"\n[FAIL] Failed (HTTP {test_resp.status_code})\n", file=sys.stderr)
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)

    data = test_resp.json()
    print("[OK] Connected!\n")
    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    run()
