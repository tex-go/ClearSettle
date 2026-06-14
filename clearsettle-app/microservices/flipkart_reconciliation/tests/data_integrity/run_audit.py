#!/usr/bin/env python3
"""
Flipkart ETL Data Integrity Audit -- Main Runner

Usage:
    # From the microservice root:
    cd clearsettle-app/microservices/flipkart_reconciliation
    python tests/data_integrity/run_audit.py

    # With custom DB or file path:
    python tests/data_integrity/run_audit.py \
        --db "postgresql://user:pass@localhost:5432/flipkart_recon" \
        --inputs /path/to/inputs/tiptop_garments_flipkart/2026_APR

    # Single file type only:
    python tests/data_integrity/run_audit.py --only orders
    python tests/data_integrity/run_audit.py --only fees
    python tests/data_integrity/run_audit.py --only settlements

Exit codes:
    0 -- All rules PASSED
    1 -- One or more rules FAILED
    2 -- Cannot connect to DB or find Excel files
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Locate project root so we can find the .env and inputs
_HERE = Path(__file__).resolve().parent          # tests/data_integrity/
_MICRO = _HERE.parent.parent                      # flipkart_reconciliation/
_PROJECT_ROOT = _MICRO.parent.parent.parent       # ClearSettle/

# Default paths
_DEFAULT_INPUTS = _PROJECT_ROOT / "inputs" / "tiptop_garments_flipkart" / "2026_APR"
_REPORTS_DIR = _HERE / "audit_reports"


def _load_db_url_from_env() -> str:
    env_file = _MICRO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                raw = line.split("=", 1)[1].strip()
                # Convert asyncpg URL to psycopg2 format
                return re.sub(r"^\s*postgresql\+asyncpg://", "postgresql://", raw)
    return "postgresql://clearsettle_user:clearsettle_pass@localhost:5432/flipkart_recon"


def main() -> int:
    parser = argparse.ArgumentParser(description="Flipkart ETL Data Integrity Audit")
    parser.add_argument("--db", default=None, help="PostgreSQL DSN (default: from .env)")
    parser.add_argument("--inputs", default=str(_DEFAULT_INPUTS), help="Directory with April Excel files")
    parser.add_argument("--only", choices=["orders", "fees", "settlements"], default=None)
    parser.add_argument("--sample", type=int, default=None, help="Row sample size for Rule 5 (default: all)")
    args = parser.parse_args()

    dsn = args.db or _load_db_url_from_env()
    inputs_dir = Path(args.inputs)

    print(f"\nFlipkart ETL Data Integrity Audit")
    print(f"  DB:     {dsn}")
    print(f"  Files:  {inputs_dir}")
    print(f"  Report: {_REPORTS_DIR}\n")

    # -- Import audit module ----------------------------------------------------
    sys.path.insert(0, str(_HERE))
    from audit import (
        AuditReport, DbClient, ExcelReader,
        FEES_COL_MAP, FEES_DATE_COLS, FEES_KEYWORDS, FEES_NUMERIC_COLS, FEES_SHEET_HINTS,
        ORDERS_COL_MAP, ORDERS_DATE_COLS, ORDERS_KEYWORDS, ORDERS_SHEET_HINTS,
        SETTLEMENTS_COL_MAP, SETTLEMENTS_DATE_COLS, SETTLEMENTS_KEYWORDS,
        SETTLEMENTS_NUMERIC_COLS, SETTLEMENTS_SHEET_HINTS,
        generate_reports,
        validate_column_names, validate_column_values, validate_date_integrity,
        validate_file_metadata, validate_null_integrity, validate_numeric_precision,
        validate_row_count, validate_row_integrity,
    )

    # -- Connect to DB ---------------------------------------------------------
    try:
        db = DbClient(dsn)
        print("  [OK] Connected to database")
    except Exception as e:
        print(f"  [FAIL] Cannot connect to database: {e}")
        return 2

    reader = ExcelReader()
    report = AuditReport()

    # -------------------------------------------------------------------------
    # FILE DEFINITIONS
    # -------------------------------------------------------------------------
    file_defs = [
        {
            "type": "orders",
            "file": inputs_dir / "FulfilmentReports_Orders.xlsx",
            "sheet_hints": ORDERS_SHEET_HINTS,
            "keywords": ORDERS_KEYWORDS,
            "col_map": ORDERS_COL_MAP,
            "raw_table": "orders_raw",
            "etl_table": "orders_etl",
            "key_col": "order_item_id",
            "date_cols": ORDERS_DATE_COLS,
            "numeric_cols": [],
            "optional_numeric_cols": [],
            "required_etl_cols": ["order_item_id"],
            "nullable_etl_cols": ["order_id", "sku", "product_title", "order_date"],
        },
        {
            "type": "fees",
            "file": inputs_dir / "Invoices_CommissionInvoiceTransactionDetails.xlsx",
            "sheet_hints": FEES_SHEET_HINTS,
            "keywords": FEES_KEYWORDS,
            "col_map": FEES_COL_MAP,
            "raw_table": "fees_raw",
            "etl_table": "fees_etl",
            "key_col": "order_item_id",
            "date_cols": FEES_DATE_COLS,
            "numeric_cols": FEES_NUMERIC_COLS,
            "optional_numeric_cols": [],
            "required_etl_cols": ["order_item_id", "fee_name"],
            "nullable_etl_cols": ["fee_date"],
        },
        {
            "type": "settlements",
            "file": inputs_dir / "PaymentReports_SettledTransactions.xlsx",
            "sheet_hints": SETTLEMENTS_SHEET_HINTS,
            "keywords": SETTLEMENTS_KEYWORDS,
            "col_map": SETTLEMENTS_COL_MAP,
            "raw_table": "settlements_raw",
            "etl_table": "settlements_etl",
            "key_col": "order_item_id",
            "date_cols": SETTLEMENTS_DATE_COLS,
            "numeric_cols": SETTLEMENTS_NUMERIC_COLS,
            "optional_numeric_cols": ["settlement_amount", "sale_amount"],
            "required_etl_cols": ["order_item_id", "settlement_amount"],
            "nullable_etl_cols": ["sale_amount", "neft_id"],
        },
    ]

    if args.only:
        file_defs = [f for f in file_defs if f["type"] == args.only]

    # -------------------------------------------------------------------------
    # RUN AUDIT PER FILE TYPE
    # -------------------------------------------------------------------------
    for fdef in file_defs:
        ftype = fdef["type"]
        fpath: Path = fdef["file"]

        print(f"\n{'-' * 60}")
        print(f"  Auditing: {ftype.upper()} ({fpath.name})")
        print(f"{'-' * 60}")

        # -- R1: File Metadata -------------------------------------------------
        r1 = validate_file_metadata(fpath, ftype)
        report.add(r1)
        print(f"  R1 [{r1.status}] File Metadata     -- {r1.summary}")

        if not r1.passed:
            print(f"      Skipping remaining rules for {ftype} (file issue)")
            continue

        # -- Read Excel (shared for R2-R5) -------------------------------------
        try:
            exc = reader.read(fpath, fdef["sheet_hints"], fdef["keywords"], fdef["col_map"])
        except Exception as e:
            print(f"  [ERROR] Failed to read Excel: {e}")
            continue

        # -- R2: Column Names --------------------------------------------------
        r2 = validate_column_names(exc, fdef["col_map"], ftype)
        report.add(r2)
        print(f"  R2 [{r2.status}] Column Names      -- {r2.summary}")

        # -- Find DB batch -- match by row count so April Excel -> April batch -----
        excel_row_count = len(exc.df)
        batch_info = db.best_matching_batch(fdef["raw_table"], excel_row_count)
        if not batch_info:
            print(f"  [SKIP] No data found in {fdef['raw_table']} -- was this file ingested?")
            continue

        batch_id = str(batch_info["batch_id"])
        db_filename = batch_info["file_name"]
        print(f"  [DB]   Using batch {batch_id[:8]}... "
              f"(rows: {batch_info['row_count']}, uploaded: {batch_info['uploaded_at']})")

        # -- R3: Row Count -----------------------------------------------------
        r3 = validate_row_count(exc, db, fdef["raw_table"], batch_id, ftype)
        report.add(r3)
        print(f"  R3 [{r3.status}] Row Count         -- {r3.summary}")

        # -- R4: Row Integrity -------------------------------------------------
        r4 = validate_row_integrity(exc, db, fdef["raw_table"], batch_id, ftype, fdef["key_col"])
        report.add(r4)
        print(f"  R4 [{r4.status}] Row Integrity     -- {r4.summary}")

        # -- R5: Column Values -------------------------------------------------
        r5 = validate_column_values(exc, db, fdef["raw_table"], batch_id, ftype, sample_size=args.sample)
        report.add(r5)
        print(f"  R5 [{r5.status}] Column Values     -- {r5.summary}")

        # -- R6: NULL Integrity ------------------------------------------------
        r6 = validate_null_integrity(
            exc, db,
            fdef["raw_table"], fdef["etl_table"],
            batch_id, ftype,
            non_null_cols=fdef["required_etl_cols"],
            nullable_cols=fdef["nullable_etl_cols"],
        )
        report.add(r6)
        print(f"  R6 [{r6.status}] NULL Integrity    -- {r6.summary}")

        # -- R7: Numeric Precision ---------------------------------------------
        if fdef["numeric_cols"]:
            r7 = validate_numeric_precision(
                db, fdef["raw_table"], fdef["etl_table"],
                batch_id, ftype,
                numeric_cols=fdef["numeric_cols"],
                optional_cols=fdef["optional_numeric_cols"],
            )
            report.add(r7)
            print(f"  R7 [{r7.status}] Numeric Precision -- {r7.summary}")
        else:
            print(f"  R7 [SKIP] Numeric Precision -- no numeric cols for {ftype}")

        # -- R8: Date Integrity ------------------------------------------------
        if fdef["date_cols"]:
            r8 = validate_date_integrity(
                db, fdef["raw_table"], fdef["etl_table"],
                batch_id, ftype,
                date_cols=fdef["date_cols"],
            )
            report.add(r8)
            print(f"  R8 [{r8.status}] Date Integrity    -- {r8.summary}")
        else:
            print(f"  R8 [SKIP] Date Integrity -- no date cols for {ftype}")

    # -------------------------------------------------------------------------
    # PRINT SUMMARY
    # -------------------------------------------------------------------------
    report.print_summary()

    # -------------------------------------------------------------------------
    # GENERATE REPORTS
    # -------------------------------------------------------------------------
    print("Generating Excel reports...")
    try:
        created = generate_reports(report, _REPORTS_DIR)
        for p in created:
            print(f"  -> {p}")
    except Exception as e:
        print(f"  [WARNING] Report generation failed: {e}")

    db.close()

    # Exit 0 if all passed, 1 if any failed
    return 0 if report.passed_all() else 1


if __name__ == "__main__":
    sys.exit(main())
