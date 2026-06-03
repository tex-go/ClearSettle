"""
Structured logging for ClearSettle backend.

Format (human-readable, grep-friendly):
  [INFO]    2026-06-03 12:00:00 | ingestion | Upload received file=report.xlsx bytes=245760
  [WARNING] 2026-06-03 12:00:01 | pipeline  | Schema drift detected platform=flipkart missing=Settlement ID
  [ERROR]   2026-06-03 12:00:02 | parser    | Column mapping failed missing_column=Settlement ID

Set LOG_LEVEL env-var (DEBUG/INFO/WARNING/ERROR) to control verbosity.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone


class _StructuredFormatter(logging.Formatter):
    """
    Emits one line per record:
      [LEVEL]   timestamp | logger | message
    Keeps the familiar Python log fields while being grep-friendly.
    """

    _LEVEL_TAG = {
        logging.DEBUG:    "[DEBUG]  ",
        logging.INFO:     "[INFO]   ",
        logging.WARNING:  "[WARNING]",
        logging.ERROR:    "[ERROR]  ",
        logging.CRITICAL: "[CRITICAL]",
    }

    def format(self, record: logging.LogRecord) -> str:
        tag = self._LEVEL_TAG.get(record.levelno, f"[{record.levelname}]")
        ts  = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        # Shorten logger name for readability (use last 2 parts)
        parts = record.name.split(".")
        short = ".".join(parts[-2:]) if len(parts) > 2 else record.name
        msg = record.getMessage()

        line = f"{tag} {ts} | {short:<28} | {msg}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging() -> None:
    """
    Call once at application startup (in lifespan or top of main.py).
    Configures the root logger and silences noisy third-party libraries.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = _StructuredFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Silence noisy libs
    for noisy in ("uvicorn.access", "httpx", "httpcore", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("app").setLevel(level)

    logging.getLogger(__name__).info(
        "Logging configured level=%s", level_name
    )
