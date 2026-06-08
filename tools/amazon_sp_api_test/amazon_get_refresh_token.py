"""
amazon_get_refresh_token.py
───────────────────────────
One-shot OAuth helper to exchange an Amazon authorization code for
a long-lived SP-API refresh token.

WHEN TO RUN:
  • First-time setup
  • After a client secret rotation (new LWA credentials)
  • After the refresh token expires or is revoked

HOW IT WORKS:
  Step A — Print the Amazon seller authorization URL.
  Step B — You open it in a browser, log in as the seller, and click "Authorize".
  Step C — Amazon redirects to the redirect_uri (we use localhost as a placeholder).
           Copy the full redirect URL (or just the "spapi_oauth_code" query param).
  Step D — Paste it here. The script exchanges it for a refresh token.
  Step E — The token is written to .env automatically.

USAGE:
  python amazon_get_refresh_token.py
  python amazon_get_refresh_token.py --marketplace IN       # India (default)
  python amazon_get_refresh_token.py --marketplace NA       # North America
"""

from __future__ import annotations

import io
import re
import sys
from urllib.parse import urlencode, urlparse, parse_qs

import httpx
from dotenv import load_dotenv, set_key

# Force UTF-8 on Windows terminals
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import os
import argparse

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Marketplace-specific Seller Central domains
# ─────────────────────────────────────────────────────────────────────────────

SELLER_CENTRAL_DOMAINS = {
    "IN": "sellercentral.amazon.in",
    "US": "sellercentral.amazon.com",
    "UK": "sellercentral.amazon.co.uk",
    "DE": "sellercentral.amazon.de",
    "JP": "sellercentral.amazon.co.jp",
    "AU": "sellercentral.amazon.com.au",
    "CA": "sellercentral.amazon.ca",
}

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
REDIRECT_URI  = "https://clearsettle.in/oauth/callback"   # Must match your app config


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

W = 65

def hr(char="─"): print(char * W)
def hdr(t):
    print(); hr("═"); print(f"  {t}"); hr("═")
def section(t):
    print(f"\n  -- {t} {'─' * max(0, W - len(t) - 6)}")
def ok(msg):  print(f"  OK   {msg}")
def err(msg): print(f"  ERR  {msg}")
def info(msg): print(f"  >>   {msg}")
def kv(k, v): print(f"    {k:<28} {v}")


# ─────────────────────────────────────────────────────────────────────────────
# Step A — Build authorization URL
# ─────────────────────────────────────────────────────────────────────────────

def build_auth_url(client_id: str, marketplace: str) -> str:
    domain = SELLER_CENTRAL_DOMAINS.get(marketplace.upper(), SELLER_CENTRAL_DOMAINS["IN"])
    params = {
        "application_id": client_id,
        "state":          "clearsettle_sp_api_test",
        "version":        "beta",
    }
    return f"https://{domain}/apps/authorize/consent?{urlencode(params)}"


# ─────────────────────────────────────────────────────────────────────────────
# Step D — Exchange authorization code for refresh token
# ─────────────────────────────────────────────────────────────────────────────

def extract_auth_code(user_input: str) -> str:
    """
    Accept either:
      • A full redirect URL: https://...?spapi_oauth_code=Atza|...&selling_partner_id=...
      • Just the code:       Atza|IwEB...
    """
    user_input = user_input.strip()
    if user_input.startswith("http"):
        parsed = urlparse(user_input)
        qs     = parse_qs(parsed.query)
        code   = qs.get("spapi_oauth_code", [None])[0]
        if not code:
            raise ValueError(
                "Could not find 'spapi_oauth_code' in the URL.\n"
                "Make sure you copied the full redirect URL."
            )
        return code
    # Assume it's the raw code
    return user_input


def exchange_code(client_id: str, client_secret: str, auth_code: str) -> str:
    """POST to LWA token endpoint — returns the refresh token."""
    payload = {
        "grant_type":    "authorization_code",
        "code":          auth_code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     client_id,
        "client_secret": client_secret,
    }
    print()
    info(f"POST {LWA_TOKEN_URL}")
    r = httpx.post(LWA_TOKEN_URL, data=payload, timeout=20)
    info(f"HTTP {r.status_code}")

    if r.status_code != 200:
        body = r.json() if "json" in r.headers.get("content-type","") else r.text
        raise RuntimeError(
            f"Token exchange failed HTTP {r.status_code}:\n  {body}\n\n"
            "Common causes:\n"
            "  - Authorization code already used (codes are single-use)\n"
            "  - redirect_uri doesn't match what's configured in SPP\n"
            "  - client_id / client_secret are wrong"
        )

    data = r.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(f"No refresh_token in response: {data}")
    return refresh_token


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Get Amazon SP-API refresh token via OAuth")
    p.add_argument("--marketplace", default="IN",
                   help="Marketplace code: IN (default), US, UK, DE, JP, AU, CA")
    p.add_argument("--code", default="",
                   help="Authorization code (skips interactive prompt)")
    args = p.parse_args()

    hdr("ClearSettle  SP-API OAuth -- Get Refresh Token")

    client_id     = os.environ.get("LWA_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LWA_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        err("LWA_CLIENT_ID or LWA_CLIENT_SECRET not set in .env")
        return 1

    section("Your LWA Credentials")
    kv("LWA_CLIENT_ID",     client_id)
    kv("LWA_CLIENT_SECRET", client_secret[:12] + "..." + client_secret[-4:])
    kv("Marketplace",       args.marketplace.upper())

    # ── Step A: print the URL ─────────────────────────────────────────────────
    auth_url = build_auth_url(client_id, args.marketplace)

    section("Step A  Open this URL in your browser")
    print()
    print("  " + auth_url)
    print()
    info("Log in as the seller account you want to authorize.")
    info("Click 'Confirm' / 'Authorize' on the permissions page.")
    info("Amazon will redirect to your app's redirect URI.")
    info("Copy the FULL redirect URL from your browser's address bar.")
    print()
    info(f"Redirect URI registered in SPP: {REDIRECT_URI}")
    print()

    # ── Step B/C: get the auth code ──────────────────────────────────────────
    section("Step B  Paste the redirect URL (or just the auth code)")
    print()

    if args.code:
        raw = args.code
        info(f"Using --code flag: {raw[:20]}...")
    else:
        print("  Paste here and press Enter:")
        print("  > ", end="", flush=True)
        raw = input().strip()

    if not raw:
        err("Nothing entered. Exiting.")
        return 1

    try:
        auth_code = extract_auth_code(raw)
    except ValueError as e:
        err(str(e))
        return 1

    info(f"Authorization code: {auth_code[:16]}...")

    # ── Step D: exchange for refresh token ────────────────────────────────────
    section("Step C  Exchanging code for refresh token")

    try:
        refresh_token = exchange_code(client_id, client_secret, auth_code)
    except RuntimeError as e:
        err(str(e))
        return 1

    ok(f"Refresh token obtained:  {refresh_token[:20]}...{refresh_token[-6:]}")

    # ── Step E: write to .env ─────────────────────────────────────────────────
    section("Step D  Saving to .env")
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        set_key(env_path, "LWA_REFRESH_TOKEN", refresh_token)
        ok(f".env updated: LWA_REFRESH_TOKEN = {refresh_token[:20]}...{refresh_token[-6:]}")
    except Exception as e:
        err(f"Could not write .env: {e}")
        print()
        info("Copy this manually into .env:")
        print(f"  LWA_REFRESH_TOKEN={refresh_token}")

    print()
    hr("═")
    print("  Done! Now run the payment test:")
    print("    python amazon_payment_finance_test.py")
    hr("═")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
