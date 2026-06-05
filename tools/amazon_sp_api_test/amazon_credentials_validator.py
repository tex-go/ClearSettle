"""
amazon_credentials_validator.py — Validate all SP-API credentials before testing.

Checks (in order):
  1. LWA_CLIENT_ID        — format + non-empty
  2. LWA_CLIENT_SECRET    — non-empty
  3. LWA_REFRESH_TOKEN    — non-empty + exchange against LWA endpoint
  4. AWS_ACCESS_KEY_ID    — format (AKIA... or ASIA...)
  5. AWS_SECRET_ACCESS_KEY — non-empty
  6. SP_API_ENDPOINT      — valid URL + reachability
  7. AWS_ROLE_ARN         — format if set
  8. AWS_REGION           — valid / inferred

Run:
    python amazon_credentials_validator.py
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional

import httpx

from _sp_client import (
    SPAPIConfig,
    LWAToken,
    exchange_refresh_token,
    get_caller_identity,
    mask,
    Printer,
    LWAError,
    AWSError,
)

# ─────────────────────────────────────────────────────────────────────────────
# Check result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    warning: bool = False  # True = passed but with advisory

    @property
    def icon(self) -> str:
        if self.warning:
            return "⚠️ "
        return "✅" if self.passed else "❌"


# ─────────────────────────────────────────────────────────────────────────────
# Individual validators
# ─────────────────────────────────────────────────────────────────────────────

def _check_lwa_client_id(config: SPAPIConfig) -> CheckResult:
    cid = config.lwa_client_id
    pattern = re.compile(r"^amzn1\.application-oa2-client\.[a-f0-9]{32}$")
    if not cid:
        return CheckResult("LWA_CLIENT_ID", False, "empty")
    if pattern.match(cid):
        return CheckResult("LWA_CLIENT_ID", True, cid)
    # Allow other formats in case Amazon changes their scheme
    if cid.startswith("amzn1."):
        return CheckResult("LWA_CLIENT_ID", True, cid, warning=True)
    return CheckResult(
        "LWA_CLIENT_ID", False,
        f"unexpected format (got: {cid[:30]}…); expected amzn1.application-oa2-client.<32hex>"
    )


def _check_lwa_client_secret(config: SPAPIConfig) -> CheckResult:
    secret = config.lwa_client_secret
    if not secret:
        return CheckResult("LWA_CLIENT_SECRET", False, "empty")
    if len(secret) < 20:
        return CheckResult("LWA_CLIENT_SECRET", False, "suspiciously short — verify the value")
    return CheckResult("LWA_CLIENT_SECRET", True, mask(secret))


def _check_lwa_refresh_token(config: SPAPIConfig) -> CheckResult:
    token = config.lwa_refresh_token
    if not token:
        return CheckResult("LWA_REFRESH_TOKEN", False, "empty")
    if not (token.startswith("Atzr|") or token.startswith("Atza|")):
        return CheckResult(
            "LWA_REFRESH_TOKEN", False,
            f"unexpected format — must start with 'Atzr|' or 'Atza|' (got: {token[:12]}…)"
        )

    # Actually exchange the token to validate it's live
    try:
        lwa_token: LWAToken = exchange_refresh_token(config)
        return CheckResult(
            "LWA_REFRESH_TOKEN", True,
            f"{mask(token)} → access token obtained (expires in {lwa_token.expires_in}s)"
        )
    except LWAError as e:
        msg = str(e)
        if "invalid_client" in msg.lower():
            hint = " (check LWA_CLIENT_ID / LWA_CLIENT_SECRET)"
        elif "invalid_grant" in msg.lower():
            hint = " (refresh token revoked or expired — re-authorise the app)"
        elif "unauthorized" in msg.lower():
            hint = " (credentials rejected by Amazon LWA endpoint)"
        else:
            hint = ""
        return CheckResult("LWA_REFRESH_TOKEN", False, f"exchange failed: {msg}{hint}")
    except Exception as e:
        return CheckResult("LWA_REFRESH_TOKEN", False, f"network error: {e}")


def _check_aws_access_key_id(config: SPAPIConfig) -> CheckResult:
    kid = config.aws_access_key_id
    if not kid:
        return CheckResult("AWS_ACCESS_KEY_ID", False, "empty")
    # IAM user key starts AKIA, temporary (STS) starts ASIA
    if re.match(r"^(AKIA|ASIA)[A-Z0-9]{16}$", kid):
        prefix = "IAM user key" if kid.startswith("AKIA") else "STS/assumed-role key"
        return CheckResult("AWS_ACCESS_KEY_ID", True, f"{kid}  [{prefix}]")
    return CheckResult(
        "AWS_ACCESS_KEY_ID", False,
        f"unexpected format '{kid[:8]}…' — expected AKIA… or ASIA… + 16 uppercase chars"
    )


def _check_aws_secret_access_key(config: SPAPIConfig) -> CheckResult:
    key = config.aws_secret_access_key
    if not key:
        return CheckResult("AWS_SECRET_ACCESS_KEY", False, "empty")
    if len(key) < 20:
        return CheckResult("AWS_SECRET_ACCESS_KEY", False, "suspiciously short — verify the value")
    return CheckResult("AWS_SECRET_ACCESS_KEY", True, mask(key))


def _check_aws_credentials_live(config: SPAPIConfig) -> CheckResult:
    """Validate AWS credentials are accepted by STS GetCallerIdentity."""
    try:
        identity = get_caller_identity(config)
        return CheckResult(
            "AWS credentials (STS)", True,
            f"Account={identity['account']}  ARN={identity['arn']}"
        )
    except AWSError as e:
        msg = str(e)
        if "InvalidClientTokenId" in msg or "security token" in msg.lower():
            hint = " — key ID / secret mismatch or key has been deactivated"
        elif "SignatureDoesNotMatch" in msg:
            hint = " — AWS_SECRET_ACCESS_KEY is incorrect"
        else:
            hint = ""
        return CheckResult("AWS credentials (STS)", False, f"{msg}{hint}")
    except Exception as e:
        return CheckResult("AWS credentials (STS)", False, f"network error: {e}")


def _check_sp_api_endpoint(config: SPAPIConfig) -> CheckResult:
    ep = config.sp_api_endpoint
    if not ep:
        return CheckResult("SP_API_ENDPOINT", False, "empty")
    if not ep.startswith("https://"):
        return CheckResult("SP_API_ENDPOINT", False, f"must start with https://  (got: {ep})")

    known_hosts = [
        "sellingpartnerapi-na.amazon.com",
        "sellingpartnerapi-eu.amazon.com",
        "sellingpartnerapi-fe.amazon.com",
        "sandbox.sellingpartnerapi-na.amazon.com",
        "sandbox.sellingpartnerapi-eu.amazon.com",
        "sandbox.sellingpartnerapi-fe.amazon.com",
    ]
    is_known = any(h in ep for h in known_hosts)
    is_sandbox = "sandbox" in ep

    # Reachability check (HTTPS HEAD to root)
    try:
        start = time.time()
        resp = httpx.head(ep, timeout=10, follow_redirects=True)
        latency = (time.time() - start) * 1000
        env_tag = "SANDBOX" if is_sandbox else "PRODUCTION"
        return CheckResult(
            "SP_API_ENDPOINT", True,
            f"{ep}  [{env_tag}]  reachable ({latency:.0f}ms)"
        )
    except Exception as e:
        warn = " (unknown endpoint)" if not is_known else ""
        return CheckResult(
            "SP_API_ENDPOINT", False,
            f"not reachable: {e}{warn}"
        )


def _check_aws_role_arn(config: SPAPIConfig) -> CheckResult:
    arn = config.aws_role_arn
    if not arn:
        return CheckResult(
            "AWS_ROLE_ARN", True,
            "[not set] — using direct IAM user credentials", warning=True
        )
    pattern = re.compile(r"^arn:aws[a-z\-]*:iam::\d{12}:role/.+$")
    if not pattern.match(arn):
        return CheckResult(
            "AWS_ROLE_ARN", False,
            f"invalid ARN format: {arn}\nExpected: arn:aws:iam::<account_id>:role/<role_name>"
        )
    # Try assuming the role
    try:
        from _sp_client import _assume_role
        temp = _assume_role(config)
        return CheckResult(
            "AWS_ROLE_ARN", True,
            f"{arn} → assumed OK  key={temp.access_key_id}"
        )
    except AWSError as e:
        return CheckResult("AWS_ROLE_ARN", False, f"AssumeRole failed: {e}")
    except Exception as e:
        return CheckResult("AWS_ROLE_ARN", False, f"error: {e}")


def _check_aws_region(config: SPAPIConfig) -> CheckResult:
    region = config.aws_region
    valid_regions = {
        "us-east-1", "us-west-2", "eu-west-1",
        "ap-southeast-1", "ap-northeast-1",
    }
    if region in valid_regions:
        return CheckResult("AWS_REGION", True, region)
    return CheckResult(
        "AWS_REGION", True,
        f"{region} (non-standard — verify this is correct for your SP-API endpoint)", warning=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main validation runner
# ─────────────────────────────────────────────────────────────────────────────

CHECKS: list[tuple[str, Callable[[SPAPIConfig], CheckResult]]] = [
    ("LWA Client ID",              _check_lwa_client_id),
    ("LWA Client Secret",          _check_lwa_client_secret),
    ("LWA Refresh Token",          _check_lwa_refresh_token),
    ("AWS Access Key ID",          _check_aws_access_key_id),
    ("AWS Secret Access Key",      _check_aws_secret_access_key),
    ("AWS Credentials (live STS)", _check_aws_credentials_live),
    ("SP-API Endpoint",            _check_sp_api_endpoint),
    ("AWS Role ARN",               _check_aws_role_arn),
    ("AWS Region",                 _check_aws_region),
]


def validate_all(config: SPAPIConfig) -> list[CheckResult]:
    results: list[CheckResult] = []
    for label, fn in CHECKS:
        print(f"  Checking {label}…", end="\r", flush=True)
        result = fn(config)
        print(" " * 50, end="\r")  # clear the "Checking…" line
        results.append(result)
    return results


def print_results(results: list[CheckResult]) -> None:
    for r in results:
        if not r.passed:
            Printer.fail(r.name, r.detail)
        elif r.warning:
            Printer.warn(r.name, r.detail)
        else:
            Printer.ok(r.name, r.detail)


def main() -> int:
    Printer.header("ClearSettle  Amazon SP-API — Credential Validator")

    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Environment", str(e))
        Printer.footer("Fix missing variables in .env and re-run.")
        return 1

    Printer.section("Loaded configuration")
    for k, v in config.summary().items():
        Printer.kv(k, v)

    Printer.section("Running checks")
    results = validate_all(config)
    print_results(results)

    passed  = sum(1 for r in results if r.passed)
    failed  = sum(1 for r in results if not r.passed)
    warned  = sum(1 for r in results if r.passed and r.warning)
    total   = len(results)

    Printer.divider()
    if failed == 0:
        Printer.footer(
            f"All {total} checks passed"
            + (f" ({warned} advisory warning{'s' if warned != 1 else ''})" if warned else "")
            + ".  Ready to run SP-API tests."
        )
        return 0
    else:
        Printer.footer(
            f"{passed}/{total} checks passed, {failed} failed.  "
            f"Fix the issues above before running SP-API tests."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
