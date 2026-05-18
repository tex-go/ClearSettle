"""
India GST/TCS calculation primitives.

All arithmetic uses Decimal — never float — to avoid rounding errors.

India context
-------------
E-commerce operators (Amazon, Flipkart, …) are required under Section 52
of the CGST Act to collect TCS at 1% of the net taxable value of goods
supplied through them.

Marketplace fees (referral fee, FBA, subscription, advertising) are treated
as a B2B service supplied by the marketplace to the seller.  Since the
marketplace is typically registered in a different state, this is an
inter-state supply → IGST at 18%.

Amazon settlement reports include GST-inclusive fee amounts, so the GST
component must be reverse-calculated:
    gst_amount    = fee_amount × 18 / 118
    taxable_base  = fee_amount × 100 / 118

The seller can claim Input Tax Credit (ITC) on gst_on_fee entries.
TCS (tcs_deducted entries) is claimable via GSTR-2A reconciliation.
"""
from __future__ import annotations

from decimal import Decimal

# ── Constants ─────────────────────────────────────────────────────────────────

GST_RATE_ON_FEES: Decimal = Decimal("18")   # 18% GST (IGST) on marketplace fees
TCS_RATE: Decimal         = Decimal("1")    # 1% TCS under Section 52 CGST Act

# TCS fee_type names as they appear in Amazon/Flipkart settlement reports
_TCS_KEYWORDS: frozenset[str] = frozenset({
    "tax collected at source",
    "tax collection at source",
    "tcs",
    "tcs (igst)",
    "tcs (cgst)",
    "tcs (sgst)",
    "marketplace tcs",
    "marketplace facilitator tcs",
    "marketplace facilitator tax",
})


# ── Fee classification ────────────────────────────────────────────────────────

def is_tcs_fee(fee_type: str) -> bool:
    """
    Return True if the fee represents a TCS deduction by the marketplace.

    Checks both exact matches and substring matches to handle variations
    in how different platforms label TCS in their settlement reports.
    """
    if not fee_type:
        return False
    normalized = fee_type.lower().strip()
    return normalized in _TCS_KEYWORDS or "tax collected" in normalized


# ── Tax arithmetic ────────────────────────────────────────────────────────────

def gst_from_inclusive(
    inclusive_amount: Decimal,
    rate: Decimal = GST_RATE_ON_FEES,
) -> tuple[Decimal, Decimal]:
    """
    Reverse-calculate GST from a GST-inclusive amount.

    Returns (taxable_base, gst_amount), both rounded to 4 decimal places.

    Formula: gst = amount × rate / (100 + rate)
    """
    q = Decimal("0.0001")
    gst  = (inclusive_amount * rate / (Decimal("100") + rate)).quantize(q)
    base = (inclusive_amount - gst).quantize(q)
    return base, gst


def split_igst(
    total_gst: Decimal,
    supply_type: str = "inter_state",
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Split a total GST/TCS amount into (IGST, CGST, SGST).

    inter_state → all IGST (zero CGST/SGST).
    intra_state → equal CGST+SGST split (zero IGST).
    """
    q = Decimal("0.0001")
    if supply_type == "intra_state":
        half = (total_gst / 2).quantize(q)
        return Decimal("0"), half, half
    return total_gst.quantize(q), Decimal("0"), Decimal("0")


def compute_tcs_taxable_base(tcs_amount: Decimal) -> Decimal:
    """
    Back-calculate the taxable sale value from a known TCS deduction.

    taxable_value = tcs_amount / TCS_RATE × 100
    """
    if tcs_amount == Decimal("0"):
        return Decimal("0")
    return (tcs_amount / TCS_RATE * Decimal("100")).quantize(Decimal("0.0001"))
