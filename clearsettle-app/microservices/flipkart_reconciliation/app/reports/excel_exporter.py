from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ── Colour palette ─────────────────────────────────────────────────────────────
_HDR_FILL   = PatternFill("solid", fgColor="1F3864")   # dark navy
_HDR_FONT   = Font(bold=True, color="FFFFFF", size=10)
_TITLE_FONT = Font(bold=True, size=13, color="1F3864")

_STATUS_FILL = {
    "MATCHED":            PatternFill("solid", fgColor="C6EFCE"),
    "SHORT_PAID":         PatternFill("solid", fgColor="FFCCCC"),
    "OVER_PAID":          PatternFill("solid", fgColor="FFEB9C"),
    "MISSING_SETTLEMENT": PatternFill("solid", fgColor="F2DCDB"),
    "MISSING_ORDER":      PatternFill("solid", fgColor="DDDDDD"),
    "MISSING_FEE_RECORD": PatternFill("solid", fgColor="FFF2CC"),
}


def _fmt(val) -> str:
    if val is None:
        return ""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (date, datetime)):
        return str(val)
    return val


def generate_april_report(rows: list[dict], period_label: str = "April 2026") -> bytes:
    wb = Workbook()

    # ── Summary sheet ──────────────────────────────────────────────────────────
    ws_sum = wb.active
    ws_sum.title = "Summary"

    ws_sum["A1"] = f"Flipkart Reconciliation Report — {period_label}"
    ws_sum["A1"].font = _TITLE_FONT
    ws_sum["A2"] = f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    ws_sum["A2"].font = Font(italic=True, size=9, color="666666")

    status_counts: dict[str, int] = {}
    status_amounts: dict[str, Decimal] = {}
    for r in rows:
        s = r["reconciliation_status"]
        status_counts[s] = status_counts.get(s, 0) + 1
        diff = r.get("difference") or Decimal("0")
        status_amounts[s] = status_amounts.get(s, Decimal("0")) + diff

    summary_rows = [
        ("Status", "Count", "Net Amount (Rs.)"),
        ("MATCHED",            status_counts.get("MATCHED", 0),            float(status_amounts.get("MATCHED", 0))),
        ("SHORT_PAID",         status_counts.get("SHORT_PAID", 0),         float(status_amounts.get("SHORT_PAID", 0))),
        ("OVER_PAID",          status_counts.get("OVER_PAID", 0),          float(status_amounts.get("OVER_PAID", 0))),
        ("MISSING_SETTLEMENT", status_counts.get("MISSING_SETTLEMENT", 0), "—"),
        ("MISSING_FEE_RECORD", status_counts.get("MISSING_FEE_RECORD", 0), float(status_amounts.get("MISSING_FEE_RECORD", 0))),
        ("MISSING_ORDER",      status_counts.get("MISSING_ORDER", 0),      "—"),
        ("TOTAL",              len(rows),                                   ""),
    ]

    net_leakage = sum(
        float(r.get("difference") or 0)
        for r in rows
        if r["reconciliation_status"] == "SHORT_PAID"
    )
    summary_rows.append(("NET LEAKAGE (Short-paid only)", "", abs(net_leakage)))

    start_row = 4
    for i, (label, count, amount) in enumerate(summary_rows):
        row = start_row + i
        ws_sum.cell(row=row, column=1, value=label)
        ws_sum.cell(row=row, column=2, value=count)
        ws_sum.cell(row=row, column=3, value=amount)
        if i == 0:
            for col in range(1, 4):
                cell = ws_sum.cell(row=row, column=col)
                cell.fill = _HDR_FILL
                cell.font = _HDR_FONT
        elif label in _STATUS_FILL:
            for col in range(1, 4):
                ws_sum.cell(row=row, column=col).fill = _STATUS_FILL[label]
        if label in ("NET LEAKAGE (Short-paid only)", "TOTAL"):
            for col in range(1, 4):
                ws_sum.cell(row=row, column=col).font = Font(bold=True)

    ws_sum.column_dimensions["A"].width = 30
    ws_sum.column_dimensions["B"].width = 10
    ws_sum.column_dimensions["C"].width = 20

    # ── Detail sheet ───────────────────────────────────────────────────────────
    ws_det = wb.create_sheet("Detail")

    headers = [
        "Order Item ID", "Order ID", "SKU", "Product Title",
        "Order Date", "Delivery Date",
        "Selling Price", "Commission Fee", "Shipping Fee",
        "Tax Amount", "Other Fee",
        "Expected Settlement", "Actual Settlement", "Difference",
        "Status", "Settlement Date", "NEFT ID",
    ]
    field_keys = [
        "order_item_id", "order_id", "sku", "product_title",
        "order_date", "delivery_date",
        "selling_price", "commission_fee", "shipping_fee",
        "tax_amount", "other_fee",
        "expected_settlement", "settlement_amount", "difference",
        "reconciliation_status", "settlement_date", "neft_id",
    ]

    for col, hdr in enumerate(headers, 1):
        cell = ws_det.cell(row=1, column=col, value=hdr)
        cell.fill = _HDR_FILL
        cell.font = _HDR_FONT
        cell.alignment = Alignment(horizontal="center")

    for r_idx, row in enumerate(rows, 2):
        status = row.get("reconciliation_status", "")
        fill = _STATUS_FILL.get(status)
        for c_idx, key in enumerate(field_keys, 1):
            val = _fmt(row.get(key))
            cell = ws_det.cell(row=r_idx, column=c_idx, value=val)
            if fill and c_idx == len(field_keys):  # colour status column
                cell.fill = fill

    # Auto-width
    col_widths = [22, 22, 18, 45, 12, 12, 14, 15, 13, 12, 10, 18, 17, 12, 20, 15, 22]
    for col, width in enumerate(col_widths, 1):
        ws_det.column_dimensions[get_column_letter(col)].width = width

    ws_det.freeze_panes = "A2"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
