"""
_sp_client.py — Shared SP-API client core.

Imported by all test modules. Provides:
  - Environment config loading + validation
  - LWA (Login with Amazon) token exchange
  - AWS SigV4 request signing via botocore
  - IAM role assumption via STS
  - Structured logging with secret masking
  - SPAPIClient for signed HTTP calls
  - PrintHelper for consistent CLI output
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse, urlencode, quote

import httpx
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
STS_URL = "https://sts.amazonaws.com/"
SP_API_SERVICE = "execute-api"
STS_SERVICE = "sts"
STS_REGION = "us-east-1"

ENDPOINT_REGION_MAP: dict[str, str] = {
    "sellingpartnerapi-na.amazon.com": "us-east-1",
    "sellingpartnerapi-eu.amazon.com": "eu-west-1",
    "sellingpartnerapi-fe.amazon.com": "us-west-2",
    "sandbox.sellingpartnerapi-na.amazon.com": "us-east-1",
    "sandbox.sellingpartnerapi-eu.amazon.com": "eu-west-1",
    "sandbox.sellingpartnerapi-fe.amazon.com": "us-west-2",
}

# Marketplace reference data
MARKETPLACE_NAMES: dict[str, str] = {
    "A21TJRUUN4KGV": "Amazon India (IN)",
    "ATVPDKIKX0DER": "Amazon US (NA)",
    "A1F83G8C2ARO7P": "Amazon UK (EU)",
    "A1PA6795UKMFR9": "Amazon Germany (EU)",
    "APJ6JRA9NG5V4":  "Amazon Italy (EU)",
    "A13V1IB3VIYZZH": "Amazon France (EU)",
    "A1RKKUPIHCS9HS": "Amazon Spain (EU)",
    "A2EUQ1WTGCTBG2": "Amazon Canada (NA)",
    "A39IBJ37TRP1C6": "Amazon Australia (FE)",
    "A1VC38T7YXB528": "Amazon Japan (FE)",
}

# ─────────────────────────────────────────────────────────────────────────────
# Secret masking
# ─────────────────────────────────────────────────────────────────────────────

def mask(value: str, visible_start: int = 6, visible_end: int = 3) -> str:
    """Return a masked version showing only a few chars at each end."""
    if not value:
        return "[EMPTY]"
    if len(value) <= visible_start + visible_end + 4:
        return "[SET]"
    return f"{value[:visible_start]}{'*' * 8}{value[-visible_end:]}"


def mask_url(url: str) -> str:
    """Remove query-string credentials from logged URLs."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

class _RidAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        rid = self.extra.get("request_id", "-")
        return f"[{rid}] {msg}", kwargs


def get_logger(name: str = "sp_api") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


_log = get_logger()


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SPAPIConfig:
    lwa_client_id: str
    lwa_client_secret: str
    lwa_refresh_token: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    sp_api_endpoint: str
    aws_role_arn: Optional[str] = None

    @classmethod
    def from_env(cls) -> "SPAPIConfig":
        required = {
            "LWA_CLIENT_ID":       os.environ.get("LWA_CLIENT_ID", ""),
            "LWA_CLIENT_SECRET":   os.environ.get("LWA_CLIENT_SECRET", ""),
            "LWA_REFRESH_TOKEN":   os.environ.get("LWA_REFRESH_TOKEN", ""),
            "AWS_ACCESS_KEY_ID":   os.environ.get("AWS_ACCESS_KEY_ID", ""),
            "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            "SP_API_ENDPOINT":     os.environ.get("SP_API_ENDPOINT", ""),
        }
        missing = [k for k, v in required.items() if not v.strip()]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Copy .env.example to .env and fill in your credentials."
            )

        endpoint = required["SP_API_ENDPOINT"].rstrip("/")
        region = os.environ.get("AWS_REGION") or _region_from_endpoint(endpoint)

        return cls(
            lwa_client_id      = required["LWA_CLIENT_ID"],
            lwa_client_secret  = required["LWA_CLIENT_SECRET"],
            lwa_refresh_token  = required["LWA_REFRESH_TOKEN"],
            aws_access_key_id  = required["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key = required["AWS_SECRET_ACCESS_KEY"],
            aws_region         = region,
            sp_api_endpoint    = endpoint,
            aws_role_arn       = os.environ.get("AWS_ROLE_ARN") or None,
        )

    def summary(self) -> dict[str, str]:
        return {
            "LWA_CLIENT_ID":       self.lwa_client_id,
            "LWA_CLIENT_SECRET":   mask(self.lwa_client_secret),
            "LWA_REFRESH_TOKEN":   mask(self.lwa_refresh_token),
            "AWS_ACCESS_KEY_ID":   self.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": mask(self.aws_secret_access_key),
            "AWS_REGION":          self.aws_region,
            "SP_API_ENDPOINT":     self.sp_api_endpoint,
            "AWS_ROLE_ARN":        self.aws_role_arn or "[not set]",
        }


def _region_from_endpoint(endpoint: str) -> str:
    for host, region in ENDPOINT_REGION_MAP.items():
        if host in endpoint:
            return region
    # Fallback: infer from subdomain
    if "-eu" in endpoint:
        return "eu-west-1"
    if "-fe" in endpoint:
        return "us-west-2"
    return "us-east-1"


# ─────────────────────────────────────────────────────────────────────────────
# LWA Token Exchange
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LWAToken:
    access_token: str
    token_type: str
    expires_in: int
    _fetched_at: float = field(default_factory=time.time, repr=False)

    @property
    def expires_at(self) -> datetime:
        return datetime.fromtimestamp(self._fetched_at + self.expires_in, tz=timezone.utc)

    @property
    def seconds_remaining(self) -> int:
        return max(0, int(self._fetched_at + self.expires_in - time.time()))

    @property
    def is_expired(self) -> bool:
        return self.seconds_remaining < 60

    @property
    def masked(self) -> str:
        return mask(self.access_token, 8, 4)


def exchange_refresh_token(config: SPAPIConfig) -> LWAToken:
    """
    Exchange an LWA refresh token for a short-lived access token.
    POST https://api.amazon.com/auth/o2/token
    """
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     config.lwa_client_id,
        "client_secret": config.lwa_client_secret,
        "refresh_token": config.lwa_refresh_token,
    }
    _log.debug("LWA token exchange → %s", LWA_TOKEN_URL)
    start = time.time()
    resp = httpx.post(LWA_TOKEN_URL, data=payload, timeout=30)
    latency = (time.time() - start) * 1000
    _log.debug("LWA response: %d (%.0fms)", resp.status_code, latency)

    if resp.status_code != 200:
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        error = body.get("error_description") if isinstance(body, dict) else str(body)
        raise LWAError(f"HTTP {resp.status_code}: {error}")

    data = resp.json()
    if "access_token" not in data:
        raise LWAError(f"Unexpected response: {data}")

    return LWAToken(
        access_token = data["access_token"],
        token_type   = data.get("token_type", "bearer"),
        expires_in   = int(data.get("expires_in", 3600)),
    )


class LWAError(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# AWS SigV4 Signing (manual — no boto3 required)
# ─────────────────────────────────────────────────────────────────────────────

def _hmac_sha256(key: bytes, data: str) -> bytes:
    return hmac.new(key, data.encode("utf-8"), hashlib.sha256).digest()


def _derive_signing_key(secret_key: str, date: str, region: str, service: str) -> bytes:
    k = _hmac_sha256(("AWS4" + secret_key).encode("utf-8"), date)
    k = _hmac_sha256(k, region)
    k = _hmac_sha256(k, service)
    return _hmac_sha256(k, "aws4_request")


def sigv4_headers(
    method: str,
    url: str,
    body: str,
    extra_headers: dict[str, str],
    access_key: str,
    secret_key: str,
    session_token: Optional[str],
    region: str,
    service: str = SP_API_SERVICE,
) -> dict[str, str]:
    """
    Return a dict of HTTP headers (including Authorization) for a SigV4-signed request.
    The caller should use exactly these headers — do not add extras after signing.
    """
    parsed = urlparse(url)
    now = datetime.now(timezone.utc)
    amz_date  = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    # Build the full headers set (all lowercase keys for canonical form)
    headers: dict[str, str] = {k.lower(): v for k, v in extra_headers.items()}
    headers["host"]       = parsed.netloc
    headers["x-amz-date"] = amz_date
    if session_token:
        headers["x-amz-security-token"] = session_token

    # Canonical headers — sorted alphabetically
    sorted_keys = sorted(headers.keys())
    canonical_headers = "".join(f"{k}:{headers[k].strip()}\n" for k in sorted_keys)
    signed_headers = ";".join(sorted_keys)

    # Canonical URI — percent-encode the path (keep / and safe chars)
    canonical_uri = parsed.path or "/"

    # Canonical query string — sort parameters
    canonical_qs = ""
    if parsed.query:
        pairs = sorted(parsed.query.split("&"))
        canonical_qs = "&".join(pairs)

    # Body hash
    body_bytes = body.encode("utf-8") if isinstance(body, str) else body
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    canonical_request = "\n".join([
        method.upper(),
        canonical_uri,
        canonical_qs,
        canonical_headers,
        signed_headers,
        body_hash,
    ])

    algorithm      = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    cr_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = "\n".join([algorithm, amz_date, credential_scope, cr_hash])

    signing_key = _derive_signing_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    headers["authorization"] = (
        f"{algorithm} "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    # Return with original-case keys where possible (httpx accepts lowercase too)
    return headers


# ─────────────────────────────────────────────────────────────────────────────
# AWS Credentials (direct or assumed role)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AWSCredentials:
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None

    @property
    def masked(self) -> dict[str, str]:
        return {
            "access_key_id":     self.access_key_id,
            "secret_access_key": mask(self.secret_access_key),
            "session_token":     mask(self.session_token) if self.session_token else "[not set]",
        }


def get_aws_credentials(config: SPAPIConfig) -> AWSCredentials:
    """Return effective AWS credentials, assuming the IAM role if AWS_ROLE_ARN is set."""
    if not config.aws_role_arn:
        return AWSCredentials(
            access_key_id     = config.aws_access_key_id,
            secret_access_key = config.aws_secret_access_key,
        )
    return _assume_role(config)


def _assume_role(config: SPAPIConfig) -> AWSCredentials:
    """Assume an IAM role via AWS STS AssumeRole and return temporary credentials."""
    import xml.etree.ElementTree as ET

    session_name = f"ClearSettleSPAPITest-{int(time.time())}"
    params = {
        "Action":          "AssumeRole",
        "RoleArn":         config.aws_role_arn,
        "RoleSessionName": session_name,
        "DurationSeconds": "3600",
        "Version":         "2011-06-15",
    }
    query = "&".join(
        f"{quote(k, safe='')}={quote(v, safe='')}"
        for k, v in sorted(params.items())
    )
    url = f"{STS_URL}?{query}"

    base_headers: dict[str, str] = {
        "content-type": "application/x-www-form-urlencoded",
    }
    signed = sigv4_headers(
        method        = "GET",
        url           = url,
        body          = "",
        extra_headers = base_headers,
        access_key    = config.aws_access_key_id,
        secret_key    = config.aws_secret_access_key,
        session_token = None,
        region        = STS_REGION,
        service       = STS_SERVICE,
    )

    _log.debug("STS AssumeRole → %s", config.aws_role_arn)
    resp = httpx.get(url, headers=signed, timeout=30)
    if resp.status_code != 200:
        raise AWSError(f"STS AssumeRole failed HTTP {resp.status_code}: {resp.text[:400]}")

    ns = "https://sts.amazonaws.com/doc/2011-06-15/"
    root = ET.fromstring(resp.text)
    creds_el = root.find(f".//{{{ns}}}Credentials")
    if creds_el is None:
        raise AWSError(f"STS response missing Credentials element: {resp.text[:400]}")

    return AWSCredentials(
        access_key_id     = creds_el.findtext(f"{{{ns}}}AccessKeyId") or "",
        secret_access_key = creds_el.findtext(f"{{{ns}}}SecretAccessKey") or "",
        session_token     = creds_el.findtext(f"{{{ns}}}SessionToken"),
    )


def get_caller_identity(config: SPAPIConfig) -> dict[str, str]:
    """Call STS GetCallerIdentity to validate AWS credentials. Returns account/arn/userid."""
    import xml.etree.ElementTree as ET

    params = {"Action": "GetCallerIdentity", "Version": "2011-06-15"}
    query = urlencode(sorted(params.items()))
    url = f"{STS_URL}?{query}"

    signed = sigv4_headers(
        method        = "GET",
        url           = url,
        body          = "",
        extra_headers = {"content-type": "application/x-www-form-urlencoded"},
        access_key    = config.aws_access_key_id,
        secret_key    = config.aws_secret_access_key,
        session_token = None,
        region        = STS_REGION,
        service       = STS_SERVICE,
    )
    resp = httpx.get(url, headers=signed, timeout=30)
    if resp.status_code != 200:
        raise AWSError(f"GetCallerIdentity failed HTTP {resp.status_code}: {resp.text[:400]}")

    ns = "https://sts.amazonaws.com/doc/2011-06-15/"
    root = ET.fromstring(resp.text)
    result = root.find(f".//{{{ns}}}GetCallerIdentityResult")
    if result is None:
        raise AWSError(f"Unexpected STS response: {resp.text[:400]}")

    return {
        "account": result.findtext(f"{{{ns}}}Account") or "",
        "arn":     result.findtext(f"{{{ns}}}Arn") or "",
        "user_id": result.findtext(f"{{{ns}}}UserId") or "",
    }


class AWSError(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# SP-API HTTP Client
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SPAPIResponse:
    status_code: int
    body: Any
    request_id: str
    latency_ms: float
    endpoint: str
    method: str = "GET"
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def icon(self) -> str:
        return "✅" if self.ok else "❌"

    def error_message(self) -> str:
        if self.error:
            return self.error
        if isinstance(self.body, dict):
            errors = self.body.get("errors", [])
            if errors:
                return f"{errors[0].get('code', 'ERR')}: {errors[0].get('message', '')}"
        return f"HTTP {self.status_code}"

    def __str__(self) -> str:
        status = f"HTTP {self.status_code}" if self.status_code else "CONN_ERR"
        return (
            f"{self.icon} {self.method} {self.endpoint} "
            f"→ {status} ({self.latency_ms:.0f}ms)"
        )


class SPAPIClient:
    """Signed SP-API HTTP client with automatic LWA token management."""

    def __init__(self, config: SPAPIConfig):
        self.config = config
        self._token:   Optional[LWAToken]      = None
        self._creds:   Optional[AWSCredentials] = None

    # ── Token / credential management ────────────────────────────────────────

    def get_token(self) -> LWAToken:
        if self._token is None or self._token.is_expired:
            self._token = exchange_refresh_token(self.config)
        return self._token

    def get_creds(self) -> AWSCredentials:
        if self._creds is None:
            self._creds = get_aws_credentials(self.config)
        return self._creds

    # ── Core request ─────────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict]   = None,
    ) -> SPAPIResponse:
        rid = str(uuid.uuid4())[:8]
        url = f"{self.config.sp_api_endpoint}{path}"
        if params:
            url += "?" + urlencode({k: v for k, v in params.items() if v is not None})

        token = self.get_token()
        creds = self.get_creds()
        body_str = json.dumps(body) if body else ""

        base_headers: dict[str, str] = {
            "x-amz-access-token": token.access_token,
            "content-type":       "application/json",
            "user-agent":         "ClearSettle/SPAPITest/1.0 (Python/3.12)",
        }

        signed = sigv4_headers(
            method        = method.upper(),
            url           = url,
            body          = body_str,
            extra_headers = base_headers,
            access_key    = creds.access_key_id,
            secret_key    = creds.secret_access_key,
            session_token = creds.session_token,
            region        = self.config.aws_region,
        )

        _log.debug("[%s] → %s %s", rid, method.upper(), mask_url(url))
        start = time.time()
        try:
            resp = httpx.request(
                method  = method.upper(),
                url     = url,
                headers = signed,
                content = body_str.encode("utf-8") if body_str else None,
                timeout = 30,
            )
            latency = (time.time() - start) * 1000
            _log.debug("[%s] ← %d (%.0fms)", rid, resp.status_code, latency)

            try:
                resp_body = resp.json()
            except Exception:
                resp_body = resp.text

            error = None
            if resp.status_code >= 400:
                if isinstance(resp_body, dict):
                    errors = resp_body.get("errors", [])
                    if errors:
                        error = f"{errors[0].get('code', 'ERR')}: {errors[0].get('message', '')}"
                    else:
                        error = resp_body.get("message") or str(resp_body)[:200]
                else:
                    error = str(resp_body)[:200]

            return SPAPIResponse(
                status_code = resp.status_code,
                body        = resp_body,
                request_id  = rid,
                latency_ms  = latency,
                endpoint    = path,
                method      = method.upper(),
                error       = error,
            )

        except httpx.ConnectTimeout:
            latency = (time.time() - start) * 1000
            return SPAPIResponse(0, None, rid, latency, path, method.upper(),
                                 "Connection timeout after 30s")
        except httpx.ConnectError as e:
            latency = (time.time() - start) * 1000
            return SPAPIResponse(0, None, rid, latency, path, method.upper(),
                                 f"Connection error: {e}")
        except Exception as e:
            latency = (time.time() - start) * 1000
            return SPAPIResponse(0, None, rid, latency, path, method.upper(), str(e))

    def get(self, path: str, params: Optional[dict] = None) -> SPAPIResponse:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Optional[dict] = None) -> SPAPIResponse:
        return self.request("POST", path, body=body)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Print Helpers
# ─────────────────────────────────────────────────────────────────────────────

WIDTH = 65

class Printer:
    """Consistent formatted terminal output for all test scripts."""

    @staticmethod
    def header(title: str) -> None:
        print()
        print("═" * WIDTH)
        print(f"  {title}")
        print("═" * WIDTH)

    @staticmethod
    def section(title: str) -> None:
        print(f"\n  ── {title} {'─' * (WIDTH - len(title) - 6)}")

    @staticmethod
    def divider() -> None:
        print("─" * WIDTH)

    @staticmethod
    def footer(msg: str) -> None:
        print("─" * WIDTH)
        print(f"  {msg}")
        print("═" * WIDTH)
        print()

    @staticmethod
    def ok(label: str, detail: str = "") -> None:
        suffix = f"  {detail}" if detail else ""
        print(f"  ✅  {label:<30}{suffix}")

    @staticmethod
    def fail(label: str, detail: str = "") -> None:
        suffix = f"  {detail}" if detail else ""
        print(f"  ❌  {label:<30}{suffix}")

    @staticmethod
    def warn(label: str, detail: str = "") -> None:
        suffix = f"  {detail}" if detail else ""
        print(f"  ⚠️   {label:<29}{suffix}")

    @staticmethod
    def info(label: str, detail: str = "") -> None:
        suffix = f"  {detail}" if detail else ""
        print(f"  ℹ️   {label:<29}{suffix}")

    @staticmethod
    def kv(key: str, value: str) -> None:
        print(f"    {key:<28} {value}")

    @staticmethod
    def result(response: SPAPIResponse) -> None:
        icon = "✅" if response.ok else "❌"
        detail = response.error_message() if not response.ok else ""
        suffix = f"  {detail}" if detail else ""
        print(f"  {icon}  {response.method} {response.endpoint:<30} "
              f"{response.status_code} ({response.latency_ms:.0f}ms){suffix}")
