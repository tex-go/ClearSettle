"""
Agent 1: File Intake & Validation.

Validates raw file bytes: computes SHA-256, detects MIME type,
checks file integrity, identifies encoding, and confirms supported format.
"""
from __future__ import annotations

import hashlib
import time
from typing import Optional

from app.services.intelligence.models import AgentStatus, IntakeResult

_SUPPORTED_FORMATS = {
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".xlsm": "xlsx",
    ".xlsb": "xls",
    ".csv": "csv",
    ".tsv": "tsv",
    ".txt": "csv",
    ".pdf": "pdf",
    ".zip": "zip",
    ".json": "json",
    ".xml": "xml",
}

_PROCESSABLE_FORMATS = frozenset(["xlsx", "xls", "csv", "tsv"])


class AgentIntake:
    AGENT_ID = 1
    AGENT_NAME = "Agent 1: File Intake & Validation"

    def run(self, context: dict) -> IntakeResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return IntakeResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                upload_id=str(context.get("upload_id", "")),
                file_hash="",
                file_size_bytes=0,
                mime_type="application/octet-stream",
                is_corrupt=True,
                encoding=None,
                supported_format=False,
                format_type="unknown",
            )

    def _process(self, context: dict) -> IntakeResult:
        file_bytes: bytes = context["file_bytes"]
        filename: str = context.get("filename", "unknown")
        upload_id: str = str(context.get("upload_id", ""))
        messages = []

        # SHA-256 hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_size = len(file_bytes)

        # Determine format from extension
        ext = ""
        if "." in filename:
            ext = "." + filename.lower().rsplit(".", 1)[-1]
        format_type = _SUPPORTED_FORMATS.get(ext, "unknown")
        supported = format_type in _PROCESSABLE_FORMATS

        if not supported:
            messages.append(f"Format '{format_type}' not in processable formats: {_PROCESSABLE_FORMATS}")

        # MIME type detection
        mime_type = _detect_mime(ext, file_bytes)

        # Integrity check + encoding detection
        is_corrupt = False
        encoding: Optional[str] = None

        if format_type in ("csv", "tsv"):
            encoding, is_corrupt = _check_text_encoding(file_bytes, messages)
        elif format_type in ("xlsx", "xls"):
            is_corrupt = _check_excel_integrity(file_bytes, messages)
            encoding = "binary"

        # Guard against empty file
        if file_size == 0:
            is_corrupt = True
            messages.append("File is empty (0 bytes).")

        status = AgentStatus.error if is_corrupt else (
            AgentStatus.warning if not supported else AgentStatus.success
        )

        return IntakeResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            upload_id=upload_id,
            file_hash=file_hash,
            file_size_bytes=file_size,
            mime_type=mime_type,
            is_corrupt=is_corrupt,
            encoding=encoding,
            supported_format=supported,
            format_type=format_type,
        )


def _detect_mime(ext: str, file_bytes: bytes) -> str:
    _mime_map = {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls":  "application/vnd.ms-excel",
        ".xlsm": "application/vnd.ms-excel.sheet.macroenabled.12",
        ".csv":  "text/csv",
        ".tsv":  "text/tab-separated-values",
        ".txt":  "text/plain",
        ".pdf":  "application/pdf",
        ".zip":  "application/zip",
        ".json": "application/json",
        ".xml":  "application/xml",
    }
    if ext in _mime_map:
        return _mime_map[ext]
    # Magic bytes sniffing as fallback
    if file_bytes[:4] == b'PK\x03\x04':
        return "application/zip"
    if file_bytes[:2] in (b'\xd0\xcf', b'\xcf\xd0'):
        return "application/vnd.ms-excel"
    return "application/octet-stream"


def _check_text_encoding(file_bytes: bytes, messages: list) -> tuple:
    """Try common encodings; return (encoding, is_corrupt)."""
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            file_bytes.decode(enc)
            return enc, False
        except UnicodeDecodeError:
            continue
    messages.append("Could not decode file with any known encoding.")
    return None, True


def _check_excel_integrity(file_bytes: bytes, messages: list) -> bool:
    """Attempt to open with openpyxl; return True if corrupt."""
    try:
        import io
        import openpyxl
        openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        return False
    except Exception as e:
        # Try xlrd for .xls
        try:
            import xlrd
            xlrd.open_workbook(file_contents=file_bytes)
            return False
        except Exception:
            messages.append(f"Excel integrity check failed: {e}")
            return True
