"""
Flipkart Payment Report (Settlement) Parser.

Handles the quarterly Flipkart Seller Hub Payment Reports which use a
3-level header structure with merged cells:

  Row 0: Section headers — "Payment Details", "Transaction Summary",
         "Marketplace Fees", "Taxes", "Order Details", etc.
  Row 1: Column names (actual field names)
  Row 2: Sometimes a sub-header row (e.g., "Total (Rs.)")
  Row 3+: Data rows

Also parses:
  - GST_Details sheet (per-fee-type breakdown)
  - Summary of report sheet (KPI totals)
  - Ads sheet
  - TCS_Recovery / TDS sheets

Key financial columns extracted per order:
  neft_id, payment_date, bank_settlement, order_id, order_item_id,
  sale_amount, commission_rate, commission, fixed_fee, collection_fee,
  pick_pack_fee, shipping_fee, reverse_shipping_fee, tcs, tds,
  gst_on_fees, marketplace_fee, offer_amount, tier, seller_sku,
  product_sub_category, shipping_zone, item_gst_rate, fulfilment_type,
  invoice_id, invoice_date, return_type, shopsy_order, item_return_status
"""
from __future__ import annotations

import io
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)

# ── Canonical column name → known raw header variations ──────────────────────
PAYMENT_COL_ALIASES: Dict[str, List[str]] = {
    "neft_id":               ["neft id", "neft_id", "neft reference", "neft ref"],
    "neft_type":             ["neft type", "neft_type", "payment type"],
    "payment_date":          ["payment date", "payment_date", "neft date"],
    "bank_settlement":       ["bank settlement value", "bank_settlement_value", "bank settlement (rs.)"],
    "gst_tcs_credit":        ["input gst + tcs credits", "gst+tcs", "input gst"],
    "tds_credit":            ["income tax credits", "tds credit", "[tds]"],
    "order_id":              ["order id", "order_id"],
    "order_item_id":         ["order item id", "order item id", "order_item_id"],
    "sale_amount":           ["sale amount (rs.)", "sale amount", "sale_amount"],
    "offer_amount":          ["total offer amount (rs.)", "total offer amount", "offer amount"],
    "my_share":              ["my share (rs.)", "my share"],
    "customer_addons":       ["customer add-ons amount (rs.)", "customer add-ons"],
    "marketplace_fee":       ["marketplace fee (rs.)", "marketplace fee"],
    "taxes":                 ["taxes (rs.)", "taxes"],
    "offer_adjustments":     ["offer adjustments (rs.)", "offer adjustments"],
    "protection_fund":       ["protection fund (rs.)", "protection fund"],
    "refund":                ["refund (rs.)", "refund"],
    "tier":                  ["tier"],
    "commission_rate":       ["commission rate (%)", "commission rate"],
    "commission":            ["commission (rs.)", "commission"],
    "fixed_fee":             ["fixed fee  (rs.)", "fixed fee (rs.)", "fixed fee"],
    "collection_fee":        ["collection fee (rs.)", "collection fee"],
    "pick_pack_fee":         ["pick and pack fee (rs.)", "pick and pack fee", "pick & pack"],
    "shipping_fee":          ["shipping fee (rs.)", "shipping fee"],
    "reverse_shipping_fee":  ["reverse shipping fee (rs.)", "reverse shipping"],
    "no_cost_emi_fee":       ["no cost emi fee reimbursement(rs.)", "no cost emi"],
    "installation_fee":      ["installation fee (rs.)", "installation fee"],
    "tech_visit_fee":        ["tech visit fee (rs.)", "tech visit fee"],
    "cancel_fee":            ["product cancellation fee (rs.)", "product cancellation fee"],
    "shopsy_marketing_fee":  ["shopsy marketing fee (rs.)", "shopsy marketing fee"],
    "franchise_fee":         ["franchise fee (rs.)", "franchise fee"],
    "tcs":                   ["tcs (rs.)", "tcs"],
    "tds":                   ["tds (rs.)", "tds"],
    "gst_on_fees":           ["gst on mp fees (rs.)", "gst on mp fees", "gst on marketplace fees"],
    "offer_discount":        ["offer amount settled as discount in mp fee (rs.)"],
    "item_gst_rate":         ["item gst rate (%)", "item gst rate"],
    "discount_in_mp_fee":    ["discount in mp fees (rs.)", "discount in mp fees"],
    "gst_on_discount":       ["gst on discount (rs.)", "gst on discount"],
    "total_discount_mp":     ["total discount in mp fee (rs.)", "total discount in mp fee"],
    "length_breadth_height": ["length*breadth*height"],
    "volumetric_weight":     ["volumetric weight (kgs)", "volumetric weight"],
    "chargeable_wt_slab":    ["chargeable wt. slab (in kgs)", "chargeable wt slab", "weight slab"],
    "shipping_zone":         ["shipping zone"],
    "order_date":            ["order date"],
    "dispatch_date":         ["dispatch date"],
    "fulfilment_type":       ["fulfilment type"],
    "seller_sku":            ["seller sku"],
    "quantity":              ["quantity"],
    "product_sub_category":  ["product sub category"],
    "additional_information":["additional information"],
    "return_type":           ["return type"],
    "shopsy_order":          ["shopsy order"],
    "item_return_status":    ["item return status"],
    "invoice_id":            ["invoice id"],
    "invoice_date":          ["invoice date"],
}

# ── Fee types that need anomaly detection ─────────────────────────────────────
# Known valid Flipkart fee names (from GST_Details analysis)
KNOWN_FEE_TYPES = frozenset([
    "fixed fee", "commission", "reverse shipping fee", "shipping fee",
    "collection fee", "sdd fee", "pick and pack fee", "tech visit fee",
    "installation fee", "product cancellation fee", "shopsy marketing fee",
    "franchise fee", "no cost emi fee reimbursement",
    "customer add-ons amount recovery",
])

SUSPECT_FEE_TYPES = frozenset([
    "wallet redeem",  # Not a standard seller deduction — raise dispute
])


# ── Helper utilities ──────────────────────────────────────────────────────────

def _d(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    try:
        s = str(v).replace(",", "").strip()
        if s in ("", "-", "nan", "None", "N/A", "#N/A"):
            return Decimal("0")
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")


def _s(v: Any) -> str:
    if v is None:
        return ""
    sv = str(v).strip()
    return "" if sv.lower() in ("nan", "none") else sv


def _to_date(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        return pd.to_datetime(str(v)[:20], dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return None


def _clean_col(c: str) -> str:
    return (
        str(c).strip().lower()
        .replace("\n", " ")
        .replace("  ", " ")
        .strip()
    )


def _find_col(df: DataFrame, candidates: List[str]) -> Optional[str]:
    """Return first DataFrame column matching any candidate (case-insensitive, partial)."""
    clean_map = {_clean_col(c): c for c in df.columns}
    for cand in candidates:
        cand_c = cand.lower().strip()
        for clean, real in clean_map.items():
            if cand_c == clean or cand_c in clean or clean in cand_c:
                return real
    return None


def _build_col_map(df: DataFrame) -> Dict[str, Optional[str]]:
    return {
        canonical: _find_col(df, candidates)
        for canonical, candidates in PAYMENT_COL_ALIASES.items()
    }


# ── Multi-header flattener ────────────────────────────────────────────────────

def _flatten_multiheader(raw: DataFrame) -> DataFrame:
    """
    Flatten the 2-row merged-cell header used in Flipkart Payment Reports.
    Rows 0-1 are headers; rows 2+ are data (sometimes row 2 is sub-header).
    """
    if len(raw) < 3:
        return raw

    # Detect which row contains "Payment Details" (section header row)
    r_sec, r_col = 0, 1
    for i in range(min(5, len(raw))):
        row_str = " ".join(_s(v).lower() for v in raw.iloc[i])
        if "payment details" in row_str or "neft id" in row_str.lower():
            r_sec = i
            r_col = i + 1
            break

    sec_headers = list(raw.iloc[r_sec])
    col_names   = list(raw.iloc[r_col])

    # Forward-fill section headers (merged cells appear blank after first cell)
    flat: List[str] = []
    curr_sec = ""
    seen: Dict[str, int] = {}
    for i, (sec, col) in enumerate(zip(sec_headers, col_names)):
        sec_s = _s(sec)
        col_s = _s(col)
        if sec_s and not sec_s.lower().startswith("unnamed"):
            curr_sec = sec_s
        nm = col_s if (col_s and not col_s.lower().startswith("unnamed")) else f"{curr_sec}_{i}"
        # Deduplicate
        cnt = seen.get(nm, 0)
        seen[nm] = cnt + 1
        flat.append(f"{nm}_{cnt}" if cnt else nm)

    # Data starts after r_col; check if r_col+1 is a sub-header (contains "Total")
    data_start = r_col + 1
    if data_start < len(raw):
        next_row = [_s(v) for v in raw.iloc[data_start]]
        if any("total" in v.lower() or "sum" in v.lower() for v in next_row if v):
            data_start += 1

    df = raw.iloc[data_start:].copy()
    df.columns = flat[: len(df.columns)]
    df = df.dropna(how="all").reset_index(drop=True)

    # Remove any repeated header rows in data
    id_col = _find_col(df, ["order item id", "order id"])
    if id_col:
        df = df[
            ~df[id_col].str.lower().str.strip().isin(["order item id", "order id", "nan", ""])
        ].copy()

    return df


# ── Sheet parsers ─────────────────────────────────────────────────────────────

def _parse_orders_sheet(df_raw: DataFrame) -> List[Dict[str, Any]]:
    """Parse the multi-header Orders sheet into per-order records."""
    df = _flatten_multiheader(df_raw)
    cm = _build_col_map(df)
    rows: List[Dict[str, Any]] = []

    def g(field: str, idx: Any) -> Any:
        col = cm.get(field)
        if not col or col not in df.columns:
            return None
        try:
            return df.at[idx, col]
        except (KeyError, TypeError):
            return None

    for idx in df.index:
        oi = _s(g("order_item_id", idx))
        if not oi or oi.lower() in ("nan", "order item id"):
            continue

        sale   = _d(g("sale_amount", idx))
        comm   = _d(g("commission", idx))
        fixed  = _d(g("fixed_fee", idx))
        coll   = _d(g("collection_fee", idx))
        ship   = _d(g("shipping_fee", idx))
        rship  = _d(g("reverse_shipping_fee", idx))
        pp     = _d(g("pick_pack_fee", idx))
        tcs    = _d(g("tcs", idx))
        tds    = _d(g("tds", idx))
        gst_f  = _d(g("gst_on_fees", idx))
        mp_tot = _d(g("marketplace_fee", idx))
        bank   = _d(g("bank_settlement", idx))

        # Total platform fees (abs sum of individual lines)
        total_fees = abs(comm) + abs(fixed) + abs(coll) + abs(ship) + abs(rship) + abs(pp)

        # Effective commission rate validation
        comm_rate = _d(g("commission_rate", idx))
        expected_comm = -(sale * comm_rate / Decimal("100")) if (sale > 0 and comm_rate > 0) else None
        comm_variance = None
        if expected_comm is not None and abs(comm) > 0:
            comm_variance = abs(comm - expected_comm)

        rows.append({
            "neft_id":              _s(g("neft_id", idx)) or None,
            "neft_type":            _s(g("neft_type", idx)) or None,
            "payment_date":         _to_date(g("payment_date", idx)),
            "bank_settlement":      float(bank),
            "order_id":             _s(g("order_id", idx)) or None,
            "order_item_id":        oi,
            "order_date":           _to_date(g("order_date", idx)),
            "invoice_id":           _s(g("invoice_id", idx)) or None,
            "invoice_date":         _to_date(g("invoice_date", idx)),
            "seller_sku":           _s(g("seller_sku", idx)) or None,
            "product_sub_category": _s(g("product_sub_category", idx)) or None,
            "tier":                 _s(g("tier", idx)) or None,
            "fulfilment_type":      _s(g("fulfilment_type", idx)) or None,
            "shipping_zone":        _s(g("shipping_zone", idx)) or None,
            "quantity":             int(_d(g("quantity", idx))) or None,
            "shopsy_order":         _s(g("shopsy_order", idx)).lower() in ("yes", "true", "1"),
            "item_return_status":   _s(g("item_return_status", idx)) or None,
            "return_type":          _s(g("return_type", idx)) or None,
            # Financials
            "sale_amount":          float(sale),
            "offer_amount":         float(_d(g("offer_amount", idx))),
            "commission_rate_pct":  float(comm_rate),
            "commission":           float(comm),
            "fixed_fee":            float(fixed),
            "collection_fee":       float(coll),
            "shipping_fee":         float(ship),
            "reverse_shipping_fee": float(rship),
            "pick_pack_fee":        float(pp),
            "tcs":                  float(tcs),
            "tds":                  float(tds),
            "gst_on_fees":          float(gst_f),
            "marketplace_fee_total":float(mp_tot),
            "total_platform_fees":  float(total_fees),
            "item_gst_rate":        float(_d(g("item_gst_rate", idx))),
            # Derived
            "expected_commission":   float(expected_comm) if expected_comm is not None else None,
            "commission_variance":   float(comm_variance) if comm_variance is not None else None,
        })

    return rows


def _parse_gst_details_sheet(df_raw: DataFrame) -> List[Dict[str, Any]]:
    """
    Parse GST_Details sheet — per-fee-line breakdown with fee names.
    Also detects suspect fee types like 'Wallet Redeem'.
    """
    df = _flatten_multiheader(df_raw)
    rows = []

    fee_name_col = _find_col(df, ["fee name"])
    fee_amt_col  = _find_col(df, ["fee amount (rs.)", "fee amount"])
    neft_col     = _find_col(df, ["neft id", "neft_id"])
    oi_col       = _find_col(df, ["order item id", "order_item_id"])
    svc_col      = _find_col(df, ["service type"])
    igst_col     = _find_col(df, ["igst rate", "igst amount"])
    wh_col       = _find_col(df, ["warehouse state code"])

    if not fee_name_col:
        return rows

    for idx in df.index:
        fee_name = _s(df.at[idx, fee_name_col]) if fee_name_col else ""
        if not fee_name or fee_name.lower() in ("fee name", "nan"):
            continue

        fee_amt  = float(_d(df.at[idx, fee_amt_col])) if fee_amt_col else 0.0
        neft_id  = _s(df.at[idx, neft_col]) if neft_col else None
        oi       = _s(df.at[idx, oi_col]) if oi_col else None
        svc_type = _s(df.at[idx, svc_col]) if svc_col else None
        wh_state = _s(df.at[idx, wh_col]) if wh_col else None
        igst_rate = float(_d(df.at[idx, igst_col])) if igst_col else 18.0

        is_suspect = fee_name.lower().strip() in SUSPECT_FEE_TYPES
        gst_amount  = abs(fee_amt) * igst_rate / 100
        total_incl_gst = fee_amt - gst_amount if fee_amt < 0 else fee_amt + gst_amount

        rows.append({
            "service_type":    svc_type or None,
            "neft_id":         neft_id or None,
            "order_item_id":   oi or None,
            "warehouse_state": wh_state or None,
            "fee_name":        fee_name,
            "fee_amount":      fee_amt,
            "gst_amount":      -gst_amount if fee_amt < 0 else gst_amount,
            "total_incl_gst":  total_incl_gst,
            "igst_rate":       igst_rate,
            "is_suspect_fee":  is_suspect,
        })

    return rows


def _parse_summary_kv(df_raw: DataFrame) -> Dict[str, Any]:
    """Parse the 'Summary of report' / 'Last Transactions Report Summary' KV sheet."""
    result: Dict[str, Any] = {}
    if df_raw.shape[1] < 2:
        return result

    for _, row in df_raw.iterrows():
        key = _s(row.iloc[0])
        val_raw = row.iloc[1]
        if not key or key.lower() in ("nan", ""):
            continue
        val = _d(val_raw)
        result[key] = float(val) if val != Decimal("0") else _s(val_raw)

    return result


# ── Anomaly detectors ─────────────────────────────────────────────────────────

def detect_payment_anomalies(
    order_rows: List[Dict[str, Any]],
    gst_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Run anomaly checks on parsed payment report data.
    Returns list of issue dicts.
    """
    issues: List[Dict[str, Any]] = []

    # ── 1. Wallet Redeem detection ────────────────────────────────────────────
    wallet_rows = [r for r in gst_rows if "wallet redeem" in (r.get("fee_name") or "").lower()]
    if wallet_rows:
        total_wallet = sum(abs(r["fee_amount"]) for r in wallet_rows)
        total_gst    = sum(abs(r["gst_amount"]) for r in wallet_rows)
        affected_ois = [r["order_item_id"] for r in wallet_rows if r.get("order_item_id")]
        issues.append({
            "issue_type":      "wallet_redeem_deduction",
            "severity":        "critical",
            "description":     (
                f"'Wallet Redeem' deduction of Rs.{total_wallet:,.2f} (+ Rs.{total_gst:,.2f} GST) "
                f"in {len(wallet_rows)} transaction(s). "
                f"This is NOT a standard Flipkart seller fee. Raise seller support dispute."
            ),
            "expected_amount": 0.0,
            "actual_amount":   -total_wallet,
            "variance":        total_wallet,
            "order_ids":       affected_ois,
            "fee_name":        "Wallet Redeem",
            "policy_ref":      "No published Flipkart seller fee policy",
            "action_required": "File seller support ticket for Wallet Redeem reversal",
        })

    # ── 2. Unexplained / suspect fee types ────────────────────────────────────
    for r in gst_rows:
        fn = (r.get("fee_name") or "").lower().strip()
        if fn and fn not in KNOWN_FEE_TYPES and fn not in SUSPECT_FEE_TYPES and fn != "":
            issues.append({
                "issue_type":      "unknown_fee_type",
                "severity":        "warning",
                "description":     (
                    f"Unknown fee type '{r['fee_name']}' = Rs.{r['fee_amount']:,.2f}. "
                    f"Verify against Flipkart fee policy."
                ),
                "expected_amount": 0.0,
                "actual_amount":   r["fee_amount"],
                "variance":        abs(r["fee_amount"]),
                "order_ids":       [r.get("order_item_id")] if r.get("order_item_id") else [],
                "fee_name":        r["fee_name"],
                "policy_ref":      "Requires verification at seller.flipkart.com/s/payments/fee-structure",
                "action_required": "Verify fee type legitimacy with Flipkart",
            })

    # ── 3. High reverse shipping (potential overcharge) ───────────────────────
    REVERSE_SHIP_THRESHOLD = Decimal("200")
    high_reverse = [
        r for r in order_rows
        if abs(Decimal(str(r.get("reverse_shipping_fee", 0)))) > REVERSE_SHIP_THRESHOLD
    ]
    if high_reverse:
        issues.append({
            "issue_type":      "high_reverse_shipping",
            "severity":        "warning",
            "description":     (
                f"{len(high_reverse)} orders with reverse shipping fee > Rs.{float(REVERSE_SHIP_THRESHOLD):,.0f}. "
                f"Validate against return type (misshipment/platform error → not seller liability)."
            ),
            "expected_amount": float(REVERSE_SHIP_THRESHOLD) * len(high_reverse),
            "actual_amount":   sum(abs(r.get("reverse_shipping_fee", 0)) for r in high_reverse),
            "variance":        sum(
                max(0, abs(r.get("reverse_shipping_fee", 0)) - float(REVERSE_SHIP_THRESHOLD))
                for r in high_reverse
            ),
            "order_ids":       [r["order_item_id"] for r in high_reverse if r.get("order_item_id")],
            "fee_name":        "Reverse Shipping Fee",
            "policy_ref":      "Flipkart Reverse Logistics Policy",
            "action_required": "Validate each return type; claim for misshipment/platform-error returns",
        })

    # ── 4. Commission rate mismatch ───────────────────────────────────────────
    for r in order_rows:
        variance = r.get("commission_variance")
        if variance is not None and variance > 1.0:  # > Rs.1 tolerance
            issues.append({
                "issue_type":      "commission_calculation_error",
                "severity":        "warning",
                "description":     (
                    f"Order {r.get('order_item_id')}: commission Rs.{r['commission']:,.2f} "
                    f"vs expected Rs.{r.get('expected_commission', 0):,.2f} "
                    f"(rate {r.get('commission_rate_pct', 0):.2f}%). "
                    f"Variance Rs.{variance:,.2f}."
                ),
                "expected_amount": r.get("expected_commission", 0),
                "actual_amount":   r.get("commission", 0),
                "variance":        variance,
                "order_ids":       [r["order_item_id"]] if r.get("order_item_id") else [],
                "fee_name":        "Commission",
                "policy_ref":      "Flipkart commission rate per category tier",
                "action_required": "Dispute commission overcharge with Flipkart",
            })

    # ── 5. Missing settlement (positive bank_settlement but 0 payment) ────────
    missing_settle = [
        r for r in order_rows
        if r.get("sale_amount", 0) > 0
        and r.get("bank_settlement", 0) == 0
        and not r.get("item_return_status", "")
    ]
    if missing_settle:
        est_recovery = sum(r.get("sale_amount", 0) * 0.80 for r in missing_settle)  # 80% est
        issues.append({
            "issue_type":      "missing_settlement",
            "severity":        "warning",
            "description":     (
                f"{len(missing_settle)} orders with sale amount but zero bank settlement. "
                f"Estimated recovery Rs.{est_recovery:,.2f}."
            ),
            "expected_amount": est_recovery,
            "actual_amount":   0.0,
            "variance":        est_recovery,
            "order_ids":       [r["order_item_id"] for r in missing_settle[:20] if r.get("order_item_id")],
            "fee_name":        "Settlement",
            "policy_ref":      "Flipkart payment cycle 7-15 days post delivery",
            "action_required": "Follow up on overdue settlements in Seller Hub",
        })

    return issues


# ── Summary builder ───────────────────────────────────────────────────────────

def compute_payment_summary(
    order_rows: List[Dict[str, Any]],
    gst_rows: List[Dict[str, Any]],
    kv_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Aggregate all quarterly payment metrics into a single summary dict."""
    gross_sales        = sum(r.get("sale_amount", 0) for r in order_rows)
    total_commission   = sum(r.get("commission", 0) for r in order_rows)
    total_fixed        = sum(r.get("fixed_fee", 0) for r in order_rows)
    total_collection   = sum(r.get("collection_fee", 0) for r in order_rows)
    total_shipping     = sum(r.get("shipping_fee", 0) for r in order_rows)
    total_reverse      = sum(r.get("reverse_shipping_fee", 0) for r in order_rows)
    total_pick_pack    = sum(r.get("pick_pack_fee", 0) for r in order_rows)
    total_tcs          = sum(r.get("tcs", 0) for r in order_rows)
    total_tds          = sum(r.get("tds", 0) for r in order_rows)
    total_gst_on_fees  = sum(r.get("gst_on_fees", 0) for r in order_rows)
    total_mp_fee       = sum(r.get("marketplace_fee_total", 0) for r in order_rows)
    net_settlement     = sum(r.get("bank_settlement", 0) for r in order_rows)

    # GST detail aggregations
    fee_by_type: Dict[str, float] = {}
    suspect_total = 0.0
    for r in gst_rows:
        fn = (r.get("fee_name") or "").strip()
        if fn:
            fee_by_type[fn] = fee_by_type.get(fn, 0.0) + r.get("fee_amount", 0)
        if r.get("is_suspect_fee"):
            suspect_total += abs(r.get("fee_amount", 0))

    # Effective rate
    eff_fee_pct = abs(total_mp_fee) / gross_sales * 100 if gross_sales else 0
    payout_rate = net_settlement / gross_sales * 100 if gross_sales else 0

    # Return rate
    return_orders = len([r for r in order_rows if r.get("reverse_shipping_fee", 0) < 0])
    return_rate   = return_orders / len(order_rows) * 100 if order_rows else 0

    return {
        "total_orders":             len(order_rows),
        "gross_sales":              round(gross_sales, 2),
        "total_commission":         round(total_commission, 2),
        "total_fixed_fee":          round(total_fixed, 2),
        "total_collection_fee":     round(total_collection, 2),
        "total_shipping_fee":       round(total_shipping, 2),
        "total_reverse_shipping":   round(total_reverse, 2),
        "total_pick_pack_fee":      round(total_pick_pack, 2),
        "total_tcs":                round(total_tcs, 2),
        "total_tds":                round(total_tds, 2),
        "total_gst_on_fees":        round(total_gst_on_fees, 2),
        "total_marketplace_fee":    round(total_mp_fee, 2),
        "net_bank_settlement":      round(net_settlement, 2),
        "effective_fee_pct":        round(eff_fee_pct, 2),
        "payout_rate_pct":          round(payout_rate, 2),
        "return_order_count":       return_orders,
        "return_rate_pct":          round(return_rate, 2),
        "suspect_fee_total":        round(suspect_total, 2),
        "fee_breakdown_by_type":    fee_by_type,
        "kv_summary":               kv_summary,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def parse_flipkart_payment_report(file_bytes: bytes, quarter_label: str = "") -> Dict[str, Any]:
    """
    Parse a Flipkart Payment Report Excel file.

    Returns:
        {
          "quarter":        str,
          "sheets_found":   [str, ...],
          "order_rows":     [{...}, ...],    # per-order financial data
          "gst_rows":       [{...}, ...],    # per-fee-line GST detail
          "summary":        {...},           # KV summary from report
          "computed":       {...},           # aggregated metrics
          "anomalies":      [{...}, ...],    # detected issues
          "errors":         [str, ...],
        }
    """
    out: Dict[str, Any] = {
        "quarter":      quarter_label,
        "sheets_found": [],
        "order_rows":   [],
        "gst_rows":     [],
        "summary":      {},
        "computed":     {},
        "anomalies":    [],
        "errors":       [],
    }

    try:
        xf = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as exc:
        out["errors"].append(f"Cannot open Excel: {exc}")
        return out

    out["sheets_found"] = list(xf.sheet_names)

    for sheet_name in xf.sheet_names:
        sn = sheet_name.lower().strip()
        try:
            df_raw = xf.parse(sheet_name, header=None, dtype=str)
        except Exception as exc:
            out["errors"].append(f"Cannot read sheet '{sheet_name}': {exc}")
            continue

        if "orders" == sn:
            rows = _parse_orders_sheet(df_raw)
            out["order_rows"].extend(rows)
            logger.info("Payment report '%s' Orders: %d rows", quarter_label, len(rows))

        elif "gst_details" == sn:
            rows = _parse_gst_details_sheet(df_raw)
            out["gst_rows"].extend(rows)
            logger.info("Payment report '%s' GST_Details: %d rows", quarter_label, len(rows))

        elif any(k in sn for k in ["summary", "report summary", "last transactions"]):
            try:
                df_kv = xf.parse(sheet_name, header=None, dtype=str)
                out["summary"] = _parse_summary_kv(df_kv)
            except Exception as exc:
                out["errors"].append(f"Cannot parse summary sheet '{sheet_name}': {exc}")

    # Compute aggregated metrics
    out["computed"] = compute_payment_summary(
        out["order_rows"], out["gst_rows"], out["summary"]
    )

    # Run anomaly detection
    out["anomalies"] = detect_payment_anomalies(out["order_rows"], out["gst_rows"])

    if out["anomalies"]:
        logger.warning(
            "Payment report '%s': %d anomalies detected", quarter_label, len(out["anomalies"])
        )

    return out
