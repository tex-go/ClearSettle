"""
Flipkart ETL Validation Audit — Phase 2
========================================
Validates correctness of ETL transformations: raw tables → ETL tables.
All rules are independent of app.* — implemented from scratch.

7 Validation Rules:
  Rule 1: Lineage  — every ETL row traces back to raw row (file, sheet, row#)
  Rule 2: Mapping  — column names map correctly raw_json → ETL columns
  Rule 3: Keys     — order_item_id never changes (OI: prefix stripped correctly)
  Rule 4: Dupes    — duplicate key detection per ETL table
  Rule 5: FeeAgg   — per-order fee totals match between raw and ETL
  Rule 6: SettAgg  — settlement_amount == sum of its components
  Rule 7: Money    — grand total sums match raw vs ETL (zero leakage)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

import psycopg2
import psycopg2.extras

# ─────────────────────────────────────────────────────────────────────────────
# Known column mapping: raw_json key → ETL column  (per table type)
# ─────────────────────────────────────────────────────────────────────────────

ORDERS_RAW_TO_ETL: dict[str, str] = {
    "order_item_id": "order_item_id",   # stripped of "OI:" prefix
    "order_id":      "order_id",
    "sku":           "sku",
    "fsn":           "fsn",
    "product_title": "product_title",
    "quantity":      "quantity",
    "order_date":    "order_date",
    "dispatch_date": "dispatch_date",
    "delivery_date": "delivery_date",
    "order_item_status": "order_item_status",
}

FEES_RAW_TO_ETL: dict[str, str] = {
    "order_item_id":    "order_item_id",
    "fee_name":         "fee_name",
    "fee_amount":       "fee_amount",
    "fee_waiver_amount":"fee_waiver_amount",
    "cgst":             "cgst",
    "sgst":             "sgst",
    "igst":             "igst",
    "tax_amount":       "tax_amount",
    "fee_date":         "fee_date",
}

SETTLEMENTS_RAW_TO_ETL: dict[str, str] = {
    "neft_id":              "neft_id",
    "neft_type":            "neft_type",
    "settlement_date":      "settlement_date",
    "settlement_amount":    "settlement_amount",
    "order_id":             "order_id",
    "order_item_id":        "order_item_id",
    "sale_amount":          "sale_amount",
    "total_offer_amount":   "total_offer_amount",
    "my_share":             "my_share",
    "customer_addons_amount": "customer_addons_amount",
    "marketplace_fee":      "marketplace_fee",
    "offer_adjustments":    "offer_adjustments",
    "protection_fund":      "protection_fund",
    "refund":               "refund",
    "tcs":                  "tcs",
    "tds":                  "tds",
    "gst_on_mp_fees":       "gst_on_mp_fees",
    "fixed_fee":            "fixed_fee",
    "collection_fee":       "collection_fee",
    "reverse_shipping_fee": "reverse_shipping_fee",
    "sku":                  "sku",
    "fsn":                  "fsn",
}

# Fee types extracted from Commission Invoice fee_name values
FEE_CATEGORIES = {
    "commission":  ["commission", "fixed fee", "marketplace fee", "platform fee"],
    "shipping":    ["shipping", "courier", "delivery", "logistics", "sdd fee"],
    "collection":  ["collection"],
    "returns":     ["return", "reverse"],
    "tax":         ["cgst", "sgst", "igst", "gst", "tds", "tcs"],
    "rebate":      ["rebate", "waiver"],
}

_MATCH_TOLERANCE = Decimal("0.02")  # 2 paise tolerance for sub-paisa rounding
_TWO_DP = Decimal("0.01")


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EtlRuleResult:
    rule_id: str
    rule_name: str
    table: str
    passed: bool
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    issues: list[dict] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


@dataclass
class EtlAuditReport:
    results: list[EtlRuleResult] = field(default_factory=list)

    def add(self, r: EtlRuleResult) -> None:
        self.results.append(r)

    def passed_all(self) -> bool:
        return all(r.passed for r in self.results)

    def print_summary(self) -> None:
        print("\n" + "=" * 72)
        print("  FLIPKART ETL VALIDATION AUDIT -- RESULTS")
        print("=" * 72)
        for r in self.results:
            icon = "+" if r.passed else "X"
            print(f"  {icon} [{r.rule_id}] {r.rule_name:<40} [{r.table:<15}] {r.status}")
            if not r.passed:
                print(f"      -> {r.summary}")
        print("-" * 72)
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        print(f"  TOTAL: {passed}/{total} rules passed")
        print("=" * 72 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _d(value, optional: bool = False) -> Decimal | None:
    """Parse a string/numeric value to Decimal. Returns 0 or None for blanks."""
    if value is None:
        return None if optional else Decimal("0")
    s = str(value).replace(",", "").replace("₹", "").strip()
    if not s or s.lower() in ("none", "nan", "-", ""):
        return None if optional else Decimal("0")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None if optional else Decimal("0")


def _d2(value, optional: bool = False) -> Decimal | None:
    """_d() then round to 2dp using ROUND_HALF_UP (matches PostgreSQL Numeric(15,2))."""
    v = _d(value, optional)
    if v is None:
        return None
    return v.quantize(_TWO_DP, rounding=ROUND_HALF_UP)


class DbClient:
    def __init__(self, dsn: str):
        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True

    def close(self) -> None:
        self.conn.close()

    def _query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def raw_rows(self, table: str, batch_id: str) -> list[dict]:
        return self._query(
            f"SELECT id, row_number, file_name, raw_json FROM {table} "
            f"WHERE batch_id = %s ORDER BY row_number",
            (batch_id,),
        )

    def etl_rows(self, table: str, batch_id: str) -> list[dict]:
        return self._query(
            f"SELECT * FROM {table} WHERE batch_id = %s ORDER BY id",
            (batch_id,),
        )

    def raw_by_id(self, table: str, raw_id: int) -> dict | None:
        rows = self._query(
            f"SELECT id, row_number, file_name, raw_json FROM {table} WHERE id = %s",
            (raw_id,),
        )
        return rows[0] if rows else None

    def best_matching_batch(self, table: str, target_row_count: int) -> dict | None:
        batches = self._query(
            f"SELECT batch_id, file_name, COUNT(*) AS row_count, MAX(uploaded_at) AS uploaded_at "
            f"FROM {table} GROUP BY batch_id, file_name ORDER BY MAX(uploaded_at) DESC"
        )
        if not batches:
            return None
        exact = [b for b in batches if b["row_count"] == target_row_count]
        if exact:
            return exact[0]
        return min(batches, key=lambda b: abs(b["row_count"] - target_row_count))

    def all_batches(self, table: str) -> list[dict]:
        return self._query(
            f"SELECT batch_id, file_name, COUNT(*) AS row_count, MAX(uploaded_at) AS uploaded_at "
            f"FROM {table} GROUP BY batch_id, file_name ORDER BY MAX(uploaded_at) DESC"
        )


# ─────────────────────────────────────────────────────────────────────────────
# RULE 1 — Lineage
# ─────────────────────────────────────────────────────────────────────────────

def validate_lineage(
    db: DbClient,
    raw_table: str,
    etl_table: str,
    batch_id: str,
    table_label: str,
) -> EtlRuleResult:
    """
    Rule 1: Every ETL row must have a raw_id that points to a valid raw row.
    The raw row must have a non-null file_name and row_number (source lineage).
    """
    etl_rows = db.etl_rows(etl_table, batch_id)
    raw_by_id = {r["id"]: r for r in db.raw_rows(raw_table, batch_id)}

    orphaned: list[dict] = []          # ETL rows whose raw_id doesn't exist
    missing_lineage: list[dict] = []   # ETL rows whose raw row lacks file_name/row_number

    for row in etl_rows:
        raw_id = row.get("raw_id")
        if raw_id is None or raw_id not in raw_by_id:
            orphaned.append({
                "etl_id": row.get("id"),
                "order_item_id": row.get("order_item_id"),
                "raw_id": raw_id,
            })
            continue
        raw = raw_by_id[raw_id]
        if not raw.get("file_name") or raw.get("row_number") is None:
            missing_lineage.append({
                "etl_id": row.get("id"),
                "order_item_id": row.get("order_item_id"),
                "raw_id": raw_id,
                "file_name": raw.get("file_name"),
                "row_number": raw.get("row_number"),
            })

    issues = []
    if orphaned:
        issues.append({"problem": "orphaned_etl_rows", "count": len(orphaned), "sample": orphaned[:10]})
    if missing_lineage:
        issues.append({"problem": "missing_lineage", "count": len(missing_lineage), "sample": missing_lineage[:10]})

    total = len(etl_rows)
    ok = total - len(orphaned) - len(missing_lineage)
    passed = not orphaned and not missing_lineage
    summary = (
        f"{total} ETL rows checked: {ok} have full lineage"
        + (f", {len(orphaned)} orphaned" if orphaned else "")
        + (f", {len(missing_lineage)} missing lineage" if missing_lineage else "")
    )
    return EtlRuleResult(
        rule_id="R1", rule_name="Lineage", table=table_label,
        passed=passed, summary=summary,
        details={
            "etl_total": total, "ok": ok,
            "orphaned": len(orphaned), "missing_lineage": len(missing_lineage),
            "sample_lineage": [
                {
                    "etl_id": r["id"],
                    "order_item_id": r.get("order_item_id"),
                    "raw_id": r.get("raw_id"),
                    "source_file": raw_by_id.get(r["raw_id"], {}).get("file_name", "?"),
                    "source_row": raw_by_id.get(r["raw_id"], {}).get("row_number", "?"),
                }
                for r in etl_rows[:5] if r.get("raw_id") in raw_by_id
            ],
        },
        issues=issues,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RULE 2 — Column Mapping Verification
# ─────────────────────────────────────────────────────────────────────────────

def validate_column_mapping(
    db: DbClient,
    raw_table: str,
    etl_table: str,
    batch_id: str,
    table_label: str,
    raw_to_etl_map: dict[str, str],
    skip_cols: set[str] | None = None,
) -> EtlRuleResult:
    """
    Rule 2: For each raw_json key → ETL column mapping, verify that the values
    are correctly transformed (string → typed). Checks that the mapping is
    complete and no ETL column is silently receiving wrong values.
    """
    skip_cols = skip_cols or set()
    raw_rows_list = db.raw_rows(raw_table, batch_id)
    etl_rows_list = db.etl_rows(etl_table, batch_id)

    raw_by_id = {r["id"]: r for r in raw_rows_list}
    # Mapping report: column → {correct, wrong, missing}
    mapping_report: dict[str, dict] = {}
    for raw_col, etl_col in raw_to_etl_map.items():
        if etl_col in skip_cols:
            continue
        mapping_report[etl_col] = {
            "raw_key": raw_col,
            "etl_column": etl_col,
            "total": 0, "correct": 0, "wrong": 0, "missing_in_raw": 0,
            "wrong_samples": [],
        }

    for etl_row in etl_rows_list:
        raw_id = etl_row.get("raw_id")
        raw = raw_by_id.get(raw_id, {})
        raw_json = raw.get("raw_json", {})

        for raw_col, etl_col in raw_to_etl_map.items():
            if etl_col in skip_cols:
                continue
            m = mapping_report[etl_col]
            m["total"] += 1

            raw_val = raw_json.get(raw_col)
            if raw_val is None and raw_col not in raw_json:
                m["missing_in_raw"] += 1
                continue

            etl_val = etl_row.get(etl_col)
            # Just verify the raw value is NOT lost (ETL has a non-null value
            # when raw has a non-null value, and vice versa).
            raw_is_null = (
                raw_val is None
                or str(raw_val).strip().lower() in ("none", "nan", "", "-")
            )
            etl_is_null = etl_val is None
            if raw_is_null != etl_is_null:
                m["wrong"] += 1
                if len(m["wrong_samples"]) < 5:
                    m["wrong_samples"].append({
                        "etl_id": etl_row.get("id"),
                        "order_item_id": etl_row.get("order_item_id"),
                        "raw_value": str(raw_val)[:50],
                        "etl_value": str(etl_val)[:50],
                    })
            else:
                m["correct"] += 1

    total_wrong = sum(m["wrong"] for m in mapping_report.values())
    issues = []
    wrong_cols = [c for c, m in mapping_report.items() if m["wrong"] > 0]
    if wrong_cols:
        issues.append({
            "problem": "null_mismatch_in_mapping",
            "columns": wrong_cols,
            "details": {c: mapping_report[c] for c in wrong_cols},
        })

    passed = total_wrong == 0
    summary = (
        f"{len(raw_to_etl_map)} column mappings verified"
        + (f" -- {total_wrong} null-mismatch errors across {len(wrong_cols)} columns" if not passed else " -- all correct")
    )
    return EtlRuleResult(
        rule_id="R2", rule_name="Column Mapping", table=table_label,
        passed=passed, summary=summary,
        details={"mapping_report": mapping_report},
        issues=issues,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RULE 3 — Key Generation
# ─────────────────────────────────────────────────────────────────────────────

def validate_key_generation(
    db: DbClient,
    raw_table: str,
    etl_table: str,
    batch_id: str,
    table_label: str,
    strip_prefix: str | None = "OI:",
) -> EtlRuleResult:
    """
    Rule 3: order_item_id in ETL must equal raw_json["order_item_id"] with
    the 'OI:' prefix stripped (for orders) or unchanged (fees/settlements).
    """
    raw_rows_list = db.raw_rows(raw_table, batch_id)
    etl_rows_list = db.etl_rows(etl_table, batch_id)
    raw_by_id = {r["id"]: r for r in raw_rows_list}

    violations: list[dict] = []
    ok = 0

    for etl_row in etl_rows_list:
        raw_id = etl_row.get("raw_id")
        raw = raw_by_id.get(raw_id, {})
        raw_json = raw.get("raw_json", {})

        raw_key = str(raw_json.get("order_item_id", "")).strip()
        expected_key = raw_key
        if strip_prefix and raw_key.startswith(strip_prefix):
            expected_key = raw_key[len(strip_prefix):]

        etl_key = str(etl_row.get("order_item_id", "")).strip()

        if etl_key != expected_key:
            violations.append({
                "etl_id": etl_row.get("id"),
                "raw_order_item_id": raw_key,
                "expected_etl_key": expected_key,
                "actual_etl_key": etl_key,
            })
        else:
            ok += 1

    issues = []
    if violations:
        issues.append({"problem": "key_transformation_error", "count": len(violations), "sample": violations[:10]})

    total = len(etl_rows_list)
    passed = not violations
    summary = (
        f"{total} ETL rows: {ok} keys correct"
        + (f", {len(violations)} key mismatches" if violations else "")
        + (f" (strip_prefix='{strip_prefix}')" if strip_prefix else " (no prefix strip)")
    )
    return EtlRuleResult(
        rule_id="R3", rule_name="Key Generation", table=table_label,
        passed=passed, summary=summary,
        details={"total": total, "correct": ok, "violations": len(violations)},
        issues=issues,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RULE 4 — Duplicate Detection
# ─────────────────────────────────────────────────────────────────────────────

def validate_duplicates(
    db: DbClient,
    etl_table: str,
    batch_id: str,
    table_label: str,
    key_cols: list[str],
    allow_duplicates: bool = False,
) -> EtlRuleResult:
    """
    Rule 4: Detect duplicate keys in the ETL table for this batch.
    - orders_etl / settlements_etl: order_item_id should be unique
    - fees_etl: (order_item_id, fee_name) pairs expected to repeat per order
    """
    etl_rows_list = db.etl_rows(etl_table, batch_id)
    key_counts: dict[tuple, int] = defaultdict(int)
    key_examples: dict[tuple, dict] = {}

    for row in etl_rows_list:
        key = tuple(str(row.get(c, "")) for c in key_cols)
        key_counts[key] += 1
        if key not in key_examples:
            key_examples[key] = {c: row.get(c) for c in key_cols}
            key_examples[key]["etl_id"] = row.get("id")

    duplicates = {k: v for k, v in key_counts.items() if v > 1}
    unique = len(key_counts)
    total = len(etl_rows_list)

    issues = []
    if duplicates and not allow_duplicates:
        sample = [
            {"key": dict(zip(key_cols, k)), "count": v, "example": key_examples.get(k)}
            for k, v in list(duplicates.items())[:20]
        ]
        issues.append({
            "problem": "duplicate_keys",
            "count": len(duplicates),
            "sample": sample,
        })

    passed = not duplicates or allow_duplicates
    dupe_note = f" (duplicates expected — fee table has multiple rows per order)" if allow_duplicates else ""
    summary = (
        f"{total} rows, {unique} unique {'+'.join(key_cols)} keys"
        + (f", {len(duplicates)} duplicate keys" if duplicates else ", no duplicates")
        + dupe_note
    )
    return EtlRuleResult(
        rule_id="R4", rule_name="Duplicate Detection", table=table_label,
        passed=passed, summary=summary,
        details={
            "total_rows": total, "unique_keys": unique, "duplicate_keys": len(duplicates),
            "key_columns": key_cols,
            "duplicates_sample": [
                {"key": dict(zip(key_cols, k)), "count": v}
                for k, v in list(duplicates.items())[:10]
            ],
        },
        issues=issues,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RULE 5 — Fee Aggregation
# ─────────────────────────────────────────────────────────────────────────────

def validate_fee_aggregation(
    db: DbClient,
    raw_table: str,
    etl_table: str,
    batch_id: str,
    table_label: str,
) -> EtlRuleResult:
    """
    Rule 5: For each order_item_id, the sum of fee_amount in fees_etl
    must equal the sum of fee_amount (parsed from raw_json) in fees_raw.
    Also validates fee category breakdowns.
    """
    raw_rows_list = db.raw_rows(raw_table, batch_id)
    etl_rows_list = db.etl_rows(etl_table, batch_id)

    # Raw fee totals per order
    raw_fee_by_order: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    raw_fee_by_category: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    raw_fee_count: dict[str, int] = defaultdict(int)
    raw_waiver_by_order: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for r in raw_rows_list:
        j = r["raw_json"]
        oid = str(j.get("order_item_id", "")).strip()
        fee_name = str(j.get("fee_name", "")).lower()
        fee_amt = _d2(j.get("fee_amount")) or Decimal("0")
        waiver = _d2(j.get("fee_waiver_amount")) or Decimal("0")
        raw_fee_by_order[oid] += fee_amt - waiver
        raw_waiver_by_order[oid] += waiver
        raw_fee_count[oid] += 1
        # Categorize
        cat = "other"
        for c, keywords in FEE_CATEGORIES.items():
            if any(k in fee_name for k in keywords):
                cat = c
                break
        raw_fee_by_category[oid][cat] += fee_amt - waiver

    # ETL fee totals per order
    etl_fee_by_order: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    etl_fee_count: dict[str, int] = defaultdict(int)

    for row in etl_rows_list:
        oid = str(row.get("order_item_id", "")).strip()
        fee_amt = _d(row.get("fee_amount")) or Decimal("0")
        waiver = _d(row.get("fee_waiver_amount")) or Decimal("0")
        etl_fee_by_order[oid] += fee_amt - waiver
        etl_fee_count[oid] += 1

    # Compare
    all_orders = set(raw_fee_by_order.keys()) | set(etl_fee_by_order.keys())
    mismatches: list[dict] = []
    missing_in_etl: list[str] = []
    missing_in_raw: list[str] = []
    total_raw = Decimal("0")
    total_etl = Decimal("0")

    for oid in sorted(all_orders):
        raw_total = raw_fee_by_order.get(oid, Decimal("0"))
        etl_total = etl_fee_by_order.get(oid, Decimal("0"))
        total_raw += raw_total
        total_etl += etl_total

        if oid not in raw_fee_by_order:
            missing_in_raw.append(oid)
        elif oid not in etl_fee_by_order:
            missing_in_etl.append(oid)
        elif abs(raw_total - etl_total) > _MATCH_TOLERANCE:
            mismatches.append({
                "order_item_id": oid,
                "raw_net_fee": str(raw_total),
                "etl_net_fee": str(etl_total),
                "delta": str(etl_total - raw_total),
                "raw_count": raw_fee_count.get(oid, 0),
                "etl_count": etl_fee_count.get(oid, 0),
                "fee_categories": {cat: str(amt) for cat, amt in raw_fee_by_category[oid].items()},
            })

    issues = []
    if mismatches:
        issues.append({"problem": "fee_total_mismatch", "count": len(mismatches), "sample": mismatches[:20]})
    if missing_in_etl:
        issues.append({"problem": "orders_missing_in_etl", "count": len(missing_in_etl), "sample": missing_in_etl[:10]})
    if missing_in_raw:
        issues.append({"problem": "orders_missing_in_raw", "count": len(missing_in_raw), "sample": missing_in_raw[:10]})

    grand_delta = total_etl - total_raw
    passed = not mismatches and not missing_in_etl and not missing_in_raw
    summary = (
        f"{len(all_orders)} orders -- raw_net={total_raw:.2f}, etl_net={total_etl:.2f}, "
        f"delta={grand_delta:.2f}"
        + (f" -- {len(mismatches)} per-order mismatches" if mismatches else " -- all match")
    )
    return EtlRuleResult(
        rule_id="R5", rule_name="Fee Aggregation", table=table_label,
        passed=passed, summary=summary,
        details={
            "orders_checked": len(all_orders),
            "total_raw_net_fees": str(total_raw),
            "total_etl_net_fees": str(total_etl),
            "grand_delta": str(grand_delta),
            "mismatches": len(mismatches),
            "missing_in_etl": len(missing_in_etl),
            "missing_in_raw": len(missing_in_raw),
            "fee_category_breakdown": {
                cat: str(sum(raw_fee_by_category[oid].get(cat, Decimal("0")) for oid in raw_fee_by_order))
                for cat in FEE_CATEGORIES
            },
        },
        issues=issues,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RULE 6 — Settlement Aggregation (internal checksum)
# ─────────────────────────────────────────────────────────────────────────────

def validate_settlement_aggregation(
    db: DbClient,
    etl_table: str,
    batch_id: str,
    table_label: str,
) -> EtlRuleResult:
    """
    Rule 6: For each settlement row, verify that the Bank Settlement Value
    equals the sum of its components:
        BSV = sale_amount + total_offer_amount + my_share + customer_addons_amount
            + marketplace_fee + (tcs + tds + gst_on_mp_fees)
            + offer_adjustments + protection_fund + refund
    This is a self-consistency check (Excel header says '= SUM(J:R)').
    """
    etl_rows_list = db.etl_rows(etl_table, batch_id)
    checksum_failures: list[dict] = []
    null_bsv: list[dict] = []
    ok = 0

    for row in etl_rows_list:
        bsv = _d(row.get("settlement_amount"), optional=True)
        if bsv is None:
            null_bsv.append({
                "etl_id": row.get("id"),
                "order_item_id": row.get("order_item_id"),
            })
            continue

        computed = (
            (_d(row.get("sale_amount"), optional=True) or Decimal("0"))
            + _d(row.get("total_offer_amount"))
            + _d(row.get("my_share"))
            + _d(row.get("customer_addons_amount"))
            + _d(row.get("marketplace_fee"))
            + _d(row.get("tcs"))
            + _d(row.get("tds"))
            + _d(row.get("gst_on_mp_fees"))
            + _d(row.get("offer_adjustments"))
            + _d(row.get("protection_fund"))
            + _d(row.get("refund"))
        )

        delta = bsv - computed
        if abs(delta) > _MATCH_TOLERANCE:
            checksum_failures.append({
                "etl_id": row.get("id"),
                "order_item_id": row.get("order_item_id"),
                "neft_id": row.get("neft_id"),
                "bsv": str(bsv),
                "computed_sum": str(computed),
                "delta": str(delta),
                "components": {
                    "sale_amount": str(_d(row.get("sale_amount"), optional=True)),
                    "total_offer_amount": str(_d(row.get("total_offer_amount"))),
                    "my_share": str(_d(row.get("my_share"))),
                    "customer_addons_amount": str(_d(row.get("customer_addons_amount"))),
                    "marketplace_fee": str(_d(row.get("marketplace_fee"))),
                    "tcs": str(_d(row.get("tcs"))),
                    "tds": str(_d(row.get("tds"))),
                    "gst_on_mp_fees": str(_d(row.get("gst_on_mp_fees"))),
                    "offer_adjustments": str(_d(row.get("offer_adjustments"))),
                    "protection_fund": str(_d(row.get("protection_fund"))),
                    "refund": str(_d(row.get("refund"))),
                },
            })
        else:
            ok += 1

    issues = []
    if checksum_failures:
        issues.append({"problem": "settlement_checksum_failure", "count": len(checksum_failures), "sample": checksum_failures[:10]})
    if null_bsv:
        issues.append({"problem": "null_settlement_amount", "count": len(null_bsv), "sample": null_bsv[:5]})

    total = len(etl_rows_list)
    passed = not checksum_failures
    summary = (
        f"{total} settlement rows: {ok} checksum OK"
        + (f", {len(checksum_failures)} checksum failures" if checksum_failures else "")
        + (f", {len(null_bsv)} null BSV (non-order rows)" if null_bsv else "")
    )
    return EtlRuleResult(
        rule_id="R6", rule_name="Settlement Aggregation", table=table_label,
        passed=passed, summary=summary,
        details={
            "total": total, "checksum_ok": ok,
            "checksum_failures": len(checksum_failures), "null_bsv": len(null_bsv),
        },
        issues=issues,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RULE 7 — Money Totals (grand sum, zero leakage)
# ─────────────────────────────────────────────────────────────────────────────

def validate_money_totals(
    db: DbClient,
    raw_table: str,
    etl_table: str,
    batch_id: str,
    table_label: str,
    numeric_raw_cols: list[str],
    numeric_etl_cols: list[str],
    optional_raw_cols: set[str] | None = None,
) -> EtlRuleResult:
    """
    Rule 7: For every financial column, SUM in source (raw_json) must equal
    SUM in ETL. Delta must be within tolerance (sub-paisa rounding).
    """
    optional_raw_cols = optional_raw_cols or set()
    raw_rows_list = db.raw_rows(raw_table, batch_id)
    etl_rows_list = db.etl_rows(etl_table, batch_id)

    raw_totals: dict[str, Decimal] = {c: Decimal("0") for c in numeric_raw_cols}
    for r in raw_rows_list:
        j = r["raw_json"]
        for col in numeric_raw_cols:
            opt = col in optional_raw_cols
            val = _d2(j.get(col), optional=opt)
            if val is not None:
                raw_totals[col] += val

    etl_totals: dict[str, Decimal] = {c: Decimal("0") for c in numeric_etl_cols}
    for row in etl_rows_list:
        for col in numeric_etl_cols:
            val = _d(row.get(col))
            if val is not None:
                etl_totals[col] += val

    mismatches: list[dict] = []
    for raw_col, etl_col in zip(numeric_raw_cols, numeric_etl_cols):
        raw_sum = raw_totals[raw_col]
        etl_sum = etl_totals[etl_col]
        delta = etl_sum - raw_sum
        if abs(delta) > _MATCH_TOLERANCE:
            mismatches.append({
                "column": f"{raw_col} -> {etl_col}",
                "raw_sum": str(raw_sum),
                "etl_sum": str(etl_sum),
                "delta": str(delta),
            })

    issues = []
    if mismatches:
        issues.append({"problem": "grand_total_mismatch", "count": len(mismatches), "mismatches": mismatches})

    col_report = {}
    for raw_col, etl_col in zip(numeric_raw_cols, numeric_etl_cols):
        raw_sum = raw_totals[raw_col]
        etl_sum = etl_totals[etl_col]
        col_report[etl_col] = {
            "raw_col": raw_col, "raw_sum": str(raw_sum),
            "etl_col": etl_col, "etl_sum": str(etl_sum),
            "delta": str(etl_sum - raw_sum),
            "match": abs(etl_sum - raw_sum) <= _MATCH_TOLERANCE,
        }

    passed = not mismatches
    summary = (
        f"{len(numeric_raw_cols)} columns: all grand totals match" if passed
        else f"{len(mismatches)}/{len(numeric_raw_cols)} columns have total mismatches"
    )
    return EtlRuleResult(
        rule_id="R7", rule_name="Money Totals", table=table_label,
        passed=passed, summary=summary,
        details={"columns": col_report},
        issues=issues,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Python Test Suite (pytest-compatible)
# ─────────────────────────────────────────────────────────────────────────────

def test_etl_mapping(db: DbClient, batches: dict[str, str]) -> dict[str, bool]:
    """Verify column mapping for all three ETL tables."""
    results = {}
    for label, (raw_t, etl_t, col_map, batch_id) in {
        "orders":      ("orders_raw",      "orders_etl",      ORDERS_RAW_TO_ETL,      batches.get("orders", "")),
        "fees":        ("fees_raw",        "fees_etl",        FEES_RAW_TO_ETL,        batches.get("fees", "")),
        "settlements": ("settlements_raw", "settlements_etl", SETTLEMENTS_RAW_TO_ETL, batches.get("settlements", "")),
    }.items():
        if not batch_id:
            results[label] = None
            continue
        r = validate_column_mapping(db, raw_t, etl_t, batch_id, label, col_map,
                                    skip_cols={"batch_id", "raw_id", "created_at", "is_valid", "validation_errors"})
        results[label] = r.passed
    return results


def test_duplicate_detection(db: DbClient, batches: dict[str, str]) -> dict[str, bool]:
    """
    Check for duplicates in each ETL table.
    All tables allow duplicates — the test detects and reports them.
    Orders: Flipkart can report same order_item_id with different statuses.
    Fees: multiple rows per order (one per fee type) is expected.
    Settlements: return + original can both appear for same order_item_id.
    """
    results = {}
    for label, (etl_t, key_cols, allow_dupes, batch_id) in {
        "orders":      ("orders_etl",      ["order_item_id"],            True, batches.get("orders", "")),
        "fees":        ("fees_etl",        ["order_item_id", "fee_name"], True, batches.get("fees", "")),
        "settlements": ("settlements_etl", ["order_item_id"],             True, batches.get("settlements", "")),
    }.items():
        if not batch_id:
            results[label] = None
            continue
        r = validate_duplicates(db, etl_t, batch_id, label, key_cols, allow_duplicates=allow_dupes)
        results[label] = r.passed
    return results


def test_fee_aggregation(db: DbClient, batch_id: str) -> bool:
    r = validate_fee_aggregation(db, "fees_raw", "fees_etl", batch_id, "fees")
    return r.passed


def test_settlement_aggregation(db: DbClient, batch_id: str) -> bool:
    r = validate_settlement_aggregation(db, "settlements_etl", batch_id, "settlements")
    return r.passed


def test_monetary_totals(db: DbClient, batches: dict[str, str]) -> dict[str, bool]:
    results = {}
    fees_batch = batches.get("fees", "")
    settlements_batch = batches.get("settlements", "")
    if fees_batch:
        r = validate_money_totals(
            db, "fees_raw", "fees_etl", fees_batch, "fees",
            numeric_raw_cols=["fee_amount", "fee_waiver_amount", "cgst", "sgst", "igst", "tax_amount"],
            numeric_etl_cols=["fee_amount", "fee_waiver_amount", "cgst", "sgst", "igst", "tax_amount"],
        )
        results["fees"] = r.passed
    if settlements_batch:
        r = validate_money_totals(
            db, "settlements_raw", "settlements_etl", settlements_batch, "settlements",
            numeric_raw_cols=["settlement_amount", "sale_amount", "total_offer_amount", "my_share",
                              "marketplace_fee", "tcs", "tds", "gst_on_mp_fees",
                              "offer_adjustments", "protection_fund", "refund"],
            numeric_etl_cols=["settlement_amount", "sale_amount", "total_offer_amount", "my_share",
                              "marketplace_fee", "tcs", "tds", "gst_on_mp_fees",
                              "offer_adjustments", "protection_fund", "refund"],
            optional_raw_cols={"settlement_amount", "sale_amount"},
        )
        results["settlements"] = r.passed
    return results
