"""
Agent 2: File Structure Analysis.

Analyses the FileFingerprint to build a structural blueprint:
  - sheet inventory (name, rows, cols, headers)
  - multi-section detection
  - date range extraction from title/header rows
  - report title extraction
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from app.services.intelligence.models import AgentStatus, StructureResult

# Regex patterns for date detection
_DATE_PATTERNS = [
    re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b'),   # dd/mm/yyyy or dd-mm-yyyy
    re.compile(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b'),      # yyyy-mm-dd
    re.compile(
        r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s*[\d,\s]*\d{4}\b',
        re.IGNORECASE,
    ),
]

_REPORT_TITLE_KEYWORDS = [
    "profit & loss", "profit and loss", "p&l", "payment report",
    "settlement report", "returns report", "tax report", "commission invoice",
    "order report", "fulfillment report", "sales report", "pnl summary",
]


class AgentStructure:
    AGENT_ID = 2
    AGENT_NAME = "Agent 2: File Structure Analysis"

    def run(self, context: dict) -> StructureResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return StructureResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                sheet_count=0,
                sheets=[],
                has_multi_section=False,
                has_hidden_sheets=False,
                detected_date_range=None,
                detected_report_title=None,
                total_data_rows=0,
                blueprint={},
            )

    def _process(self, context: dict) -> StructureResult:
        fp = context.get("fingerprint")
        messages: List[str] = []

        if fp is None:
            return StructureResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=["No fingerprint available — skipped."],
                sheet_count=0,
                sheets=[],
                has_multi_section=False,
                has_hidden_sheets=False,
                detected_date_range=None,
                detected_report_title=None,
                total_data_rows=0,
                blueprint={},
            )

        sheets_info: List[Dict[str, Any]] = []
        total_data_rows = 0

        for sh in fp.sheets:
            sheet_dict = {
                "name": sh.sheet_name,
                "row_count": sh.row_count,
                "col_count": sh.col_count,
                "headers": sh.flat_columns[:30],  # cap to 30
                "has_merged_cells": _detect_merged_cells(sh.raw_headers),
                "sample_token_count": len(sh.content_tokens),
            }
            sheets_info.append(sheet_dict)
            # data rows = total rows minus the header scan window (up to 20)
            data_rows = max(0, sh.row_count - min(20, sh.row_count))
            total_data_rows += data_rows

        # Multi-section: multiple sheets OR single sheet with repeated header-like rows
        has_multi_section = len(fp.sheets) > 1 or _detect_multi_section(fp)

        # Date range extraction from content tokens + raw headers
        date_range = _extract_date_range(fp)

        # Report title extraction
        report_title = _extract_report_title(fp)

        # Blueprint: summary of what we found
        blueprint = {
            "file_name": fp.file_name,
            "file_hash": fp.file_hash_sha256,
            "is_excel": fp.is_excel,
            "is_csv": fp.is_csv,
            "total_columns": len(fp.all_column_names),
            "schema_signature": fp.schema_signature,
            "parse_warnings": fp.parse_warnings,
            "sheets": [s["name"] for s in sheets_info],
        }

        if fp.parse_warnings:
            messages.extend(fp.parse_warnings[:5])

        status = AgentStatus.warning if fp.parse_warnings else AgentStatus.success

        return StructureResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            sheet_count=len(fp.sheets),
            sheets=sheets_info,
            has_multi_section=has_multi_section,
            has_hidden_sheets=False,  # openpyxl read-only doesn't expose hidden state
            detected_date_range=date_range,
            detected_report_title=report_title,
            total_data_rows=total_data_rows,
            blueprint=blueprint,
        )


def _detect_merged_cells(raw_headers: List[List[str]]) -> bool:
    """Heuristic: if the row immediately before the densest row has partial data, cells may be merged."""
    if len(raw_headers) < 2:
        return False
    max_idx = max(range(len(raw_headers)), key=lambda i: sum(1 for c in raw_headers[i] if c.strip()))
    if max_idx > 0:
        prev = raw_headers[max_idx - 1]
        prev_non_empty = sum(1 for c in prev if c.strip())
        best_non_empty = sum(1 for c in raw_headers[max_idx] if c.strip())
        # Merged: previous row has some cells but fewer than header row
        return 0 < prev_non_empty < best_non_empty
    return False


def _detect_multi_section(fp) -> bool:
    """Detect if a single-sheet file has multiple report sections (e.g. Flipkart P&L)."""
    if not fp.sheets:
        return False
    tokens = fp.all_content_tokens
    section_markers = [
        "pnl summary", "settlement summary", "earnings on platform",
        "payment details", "gst details",
    ]
    hits = sum(1 for m in section_markers for tok in tokens if m in tok)
    return hits >= 2


def _extract_date_range(fp) -> Optional[str]:
    """Extract a date range string from file name and content tokens."""
    candidates = [fp.file_name] + fp.all_content_tokens[:50]
    dates_found = []
    for text in candidates:
        for pat in _DATE_PATTERNS:
            matches = pat.findall(str(text))
            if matches:
                dates_found.extend(matches)
                if len(dates_found) >= 2:
                    break
        if len(dates_found) >= 2:
            break

    if dates_found:
        # Just return raw matched strings from the file name if possible
        for pat in _DATE_PATTERNS:
            hits = pat.findall(fp.file_name)
            if hits:
                return f"Detected from filename: {hits}"
        # Fallback: return first token match
        for tok in fp.all_content_tokens[:30]:
            for pat in _DATE_PATTERNS:
                if pat.search(str(tok)):
                    return str(tok)[:80]
    return None


def _extract_report_title(fp) -> Optional[str]:
    """Extract a human-readable report title from content tokens."""
    tokens_lower = [t.lower() for t in fp.all_content_tokens[:40]]
    for kw in _REPORT_TITLE_KEYWORDS:
        for tok in tokens_lower:
            if kw in tok:
                return tok.title()[:80]
    # Try sheet names
    for sh in fp.sheets:
        name_lower = sh.sheet_name.lower()
        for kw in _REPORT_TITLE_KEYWORDS:
            if kw in name_lower:
                return sh.sheet_name[:80]
    return None
