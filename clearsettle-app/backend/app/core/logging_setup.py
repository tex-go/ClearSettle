"""
Structured JSON logging for ClearSettle backend.

Output format: one JSON object per line on stdout.
GCP Cloud Logging automatically parses JSON from stdout when:
  - Running on Compute Engine / Cloud Run
  - Using the 'gcplogs' Docker logging driver
  - Or via the Cloud Logging agent reading Docker json-file logs

Special GCP fields used:
  severity  → maps to Cloud Logging severity (INFO/WARNING/ERROR/CRITICAL)
  message   → the log message body
  timestamp → ISO-8601 UTC  (GCP uses this for log ordering)
  labels    → searchable key-value filters in Cloud Logging UI
  httpRequest → populated by middleware for request logs

All extra kwargs passed to logger.info(..., extra={...}) are
serialised as top-level JSON fields → searchable in Cloud Logging.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


# ── GCP severity mapping ──────────────────────────────────────────────────────
_SEVERITY = {
    logging.DEBUG:    "DEBUG",
    logging.INFO:     "INFO",
    logging.WARNING:  "WARNING",
    logging.ERROR:    "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class _GCPJsonFormatter(logging.Formatter):
    """
    Formats every log record as a single JSON line understood by GCP Cloud Logging.
    Extra fields added via `logger.info(msg, extra={"key": val})` are included
    as top-level JSON keys — fully indexed and filterable in the GCP console.
    """

    # Fields that are already encoded at the top level; skip from 'extra' dump
    _SKIP = frozenset({
        "args", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message",
        "module", "msecs", "msg", "name", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "taskName",
        "thread", "threadName",
    })

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "severity":  _SEVERITY.get(record.levelno, record.levelname),
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "message":   record.message,
            "logger":    record.name,
            "module":    record.module,
            "line":      record.lineno,
        }

        # Include all extra fields passed via extra={...}
        for key, val in record.__dict__.items():
            if key not in self._SKIP and not key.startswith("_"):
                try:
                    json.dumps(val)          # only include JSON-serialisable values
                    payload[key] = val
                except (TypeError, ValueError):
                    payload[key] = str(val)

        # Exception traceback as a structured string
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
            payload["traceback"] = traceback.format_exception(*record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """
    Call once at application startup.
    Sets up JSON logging to stdout and silences noisy third-party libraries.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = _GCPJsonFormatter()
    handler   = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Silence noisy libraries — still get WARNING+ from them
    for noisy in ("uvicorn.access", "httpx", "httpcore", "sqlalchemy.engine",
                  "multipart", "asyncio", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("app").setLevel(level)

    logging.getLogger(__name__).info(
        "Logging configured",
        extra={"log_level": level_name, "format": "json", "gcp_compatible": True},
    )
