"""
10 leakage detectors for the Vendor Reconciliation Engine.

Each detector operates on staged data already loaded into the DB for a given
recon_job and returns a list of LeakageCandidate dataclasses.

Detectors are pure functions — no DB writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Sequence

_ZERO = Decimal("0")


@dataclass
class LeakageCandidate:
    leakage_type:           str
    severity:               str         # critical / warning / info
    description:            str
    amount:                 Decimal | None = None
    reference_type:         str | None = None
    reference_id:           str | None = None
    po_number:              str | None = None
    invoice_number:         str | None = None
    sku:                    str | None = None
    deduction_code:         str | None = None
    root_cause:             str | None = None
    is_disputable:          bool = False
    recovery_potential:     Decimal | None = None
    recovery_recommendation:str | None = None
    evidence:               list[str] = field(default_factory=list)


# ── 1. SHORTAGE ───────────────────────────────────────────────────────────────
def detect_shortage(
    settlement_lines: Sequence[Any],
    operational_lines: Sequence[Any],
) -> list[LeakageCandidate]:
    """
    Shortage = Amazon claims fewer received units than ASN shipped.
    Logic: for each PO, shipped_qty (ASN) > received_qty (receiving/POD) → flag.
    """
    asn: dict[str, Decimal] = {}
    received: dict[str, Decimal] = {}

    for op in operational_lines:
        key = (op.po_number or "") + "|" + (op.sku or "")
        if op.line_category == "asn" and op.shipped_qty:
            asn[key] = asn.get(key, _ZERO) + Decimal(str(op.shipped_qty))
        if op.line_category in ("receiving", "pod") and op.received_qty:
            received[key] = received.get(key, _ZERO) + Decimal(str(op.received_qty))

    events: list[LeakageCandidate] = []
    for key, shipped in asn.items():
        recv = received.get(key, _ZERO)
        if shipped > recv:
            gap = shipped - recv
            po, sku = key.split("|", 1)
            events.append(LeakageCandidate(
                leakage_type="SHORT",
                severity="critical",
                description=(
                    f"PO {po} / SKU {sku}: ASN shows {shipped} units shipped "
                    f"but only {recv} received. Shortage of {gap} units."
                ),
                amount=gap,
                reference_type="po",
                reference_id=po,
                po_number=po or None,
                sku=sku or None,
                root_cause="Receiving count < ASN shipment count — check POD vs warehouse receiving report.",
                is_disputable=True,
                recovery_recommendation="Raise shortage claim with ASN and POD as evidence. File within 30 days.",
                evidence=["ASN shipment record", "Warehouse receiving report", "POD"],
            ))
    return events


# ── 2. DUPLICATE DEDUCTIONS ───────────────────────────────────────────────────
def detect_duplicates(
    settlement_lines: Sequence[Any],
) -> list[LeakageCandidate]:
    """
    Same deduction_code + reference_number + deduction_amount appearing > once.
    """
    seen: dict[tuple, list[Any]] = {}
    for line in settlement_lines:
        code = line.deduction_code or ""
        ref  = line.reference_number or line.invoice_number or ""
        amt  = str(line.deduction_amount or "")
        if not code or not ref or not amt or amt == "0":
            continue
        key = (code, ref, amt)
        seen.setdefault(key, []).append(line)

    events: list[LeakageCandidate] = []
    flagged: set[tuple] = set()
    for (code, ref, amt_str), lines in seen.items():
        if len(lines) <= 1:
            continue
        if (code, ref) in flagged:
            continue
        flagged.add((code, ref))
        amount = Decimal(amt_str) if amt_str else _ZERO
        excess = amount * (len(lines) - 1)
        events.append(LeakageCandidate(
            leakage_type="DUPLICATE",
            severity="critical",
            description=(
                f"Deduction '{code}' of ₹{amount} appears {len(lines)} times "
                f"for reference '{ref}'. Excess charged: ₹{excess}."
            ),
            amount=excess,
            reference_type="settlement",
            reference_id=ref,
            deduction_code=code,
            root_cause="Same deduction applied multiple times — possible system error or manual duplicate entry.",
            is_disputable=True,
            recovery_potential=excess,
            recovery_recommendation=f"Raise dispute for ₹{excess} duplicate deduction. Attach settlement line extract.",
            evidence=["Settlement report lines", "Deduction reference numbers"],
        ))
    return events


# ── 3. INVALID OTIF PENALTY ───────────────────────────────────────────────────
def detect_otif(
    operational_lines: Sequence[Any],
) -> list[LeakageCandidate]:
    """
    OTIF penalty invalid when actual_delivery_date <= requested_delivery_date.
    """
    events: list[LeakageCandidate] = []
    for op in operational_lines:
        if op.line_category != "otif":
            continue
        if not op.penalty_amount or Decimal(str(op.penalty_amount)) <= _ZERO:
            continue
        if op.actual_date and op.expected_date:
            if op.actual_date <= op.expected_date:
                amt = Decimal(str(op.penalty_amount))
                events.append(LeakageCandidate(
                    leakage_type="OTIF",
                    severity="warning",
                    description=(
                        f"PO {op.po_number}: OTIF penalty ₹{amt} charged but delivery "
                        f"was on time ({op.actual_date} ≤ {op.expected_date})."
                    ),
                    amount=amt,
                    reference_type="po",
                    reference_id=op.po_number,
                    po_number=op.po_number,
                    root_cause="Penalty applied despite on-time / early delivery. Data mismatch or system error.",
                    is_disputable=True,
                    recovery_potential=amt,
                    recovery_recommendation="Dispute OTIF penalty with POD and delivery confirmation as evidence.",
                    evidence=["OTIF compliance report", "Proof of Delivery", "ASN dispatch timestamp"],
                ))
    return events


# ── 4. ACCRUAL WITHOUT REVERSAL ───────────────────────────────────────────────
def detect_accrual_mismatch(
    settlement_lines: Sequence[Any],
) -> list[LeakageCandidate]:
    """
    Accrual deducted but no matching reversal within the same settlement.
    """
    accruals: dict[str, Decimal] = {}
    reversals: dict[str, Decimal] = {}

    for line in settlement_lines:
        code = line.deduction_code or line.reference_number or ""
        if not code:
            continue
        if line.accrual_amount and Decimal(str(line.accrual_amount)) > _ZERO:
            accruals[code] = accruals.get(code, _ZERO) + Decimal(str(line.accrual_amount))
        if line.reversal_amount and Decimal(str(line.reversal_amount)) > _ZERO:
            reversals[code] = reversals.get(code, _ZERO) + Decimal(str(line.reversal_amount))

    events: list[LeakageCandidate] = []
    for code, accrued in accruals.items():
        reversed_amt = reversals.get(code, _ZERO)
        if accrued > reversed_amt:
            gap = accrued - reversed_amt
            events.append(LeakageCandidate(
                leakage_type="ACCRUAL",
                severity="warning",
                description=(
                    f"Accrual '{code}': ₹{accrued} deducted but only ₹{reversed_amt} "
                    f"reversed. Net unreversed accrual: ₹{gap}."
                ),
                amount=gap,
                reference_type="settlement",
                reference_id=code,
                deduction_code=code,
                root_cause="Temporary accrual deduction never reversed in subsequent settlement period.",
                is_disputable=True,
                recovery_potential=gap,
                recovery_recommendation="Contact platform finance to issue reversal credit. Check next 2 settlement cycles.",
                evidence=["Settlement accrual line", "Prior settlement reversal records"],
            ))
    return events


# ── 5. UNAUTHORIZED CO-OP ─────────────────────────────────────────────────────
def detect_coop(
    settlement_lines: Sequence[Any],
    chargeback_lines: Sequence[Any],
) -> list[LeakageCandidate]:
    """
    Co-op deduction without a matching approved chargeback record.
    """
    coop_keywords = {"coop", "co-op", "marketing", "promo", "promotional", "mdf", "fund"}
    approved_refs: set[str] = {
        cb.invoice_number or cb.po_number or cb.chargeback_id or ""
        for cb in chargeback_lines
        if cb.dispute_status and cb.dispute_status.lower() in ("approved", "agreed", "recovered")
    }

    events: list[LeakageCandidate] = []
    for line in settlement_lines:
        reason = (line.deduction_reason or "").lower()
        code   = (line.deduction_code   or "").lower()
        if not any(kw in reason or kw in code for kw in coop_keywords):
            continue
        ref = line.reference_number or line.invoice_number or ""
        if ref in approved_refs:
            continue
        amt = line.deduction_amount
        if not amt or Decimal(str(amt)) <= _ZERO:
            continue
        events.append(LeakageCandidate(
            leakage_type="COOP",
            severity="warning",
            description=(
                f"Co-op/marketing deduction ₹{amt} (code: {line.deduction_code}) "
                f"has no matching approved funding agreement."
            ),
            amount=Decimal(str(amt)),
            reference_type="settlement",
            reference_id=ref or line.deduction_code,
            deduction_code=line.deduction_code,
            root_cause="Marketing/co-op fund deducted without vendor approval or signed funding agreement.",
            is_disputable=True,
            recovery_potential=Decimal(str(amt)),
            recovery_recommendation="Request funding agreement from platform. If none exists, dispute the deduction.",
            evidence=["Settlement deduction line", "Funding agreement (if available)", "Chargeback records"],
        ))
    return events


# ── 6. RETURN LEAKAGE ─────────────────────────────────────────────────────────
def detect_return_leakage(
    settlement_lines: Sequence[Any],
    operational_lines: Sequence[Any],
) -> list[LeakageCandidate]:
    """
    Refund/return deduction in settlement with no matching return record.
    """
    return_keywords = {"return", "refund", "rto", "rts"}
    valid_returns: set[str] = set()
    for op in operational_lines:
        if op.line_category == "return" and op.sku:
            valid_returns.add(op.sku)

    events: list[LeakageCandidate] = []
    for line in settlement_lines:
        reason = (line.deduction_reason or "").lower()
        code   = (line.deduction_code   or "").lower()
        if not any(kw in reason or kw in code for kw in return_keywords):
            continue
        sku = line.sku
        if sku and sku in valid_returns:
            continue
        amt = line.deduction_amount
        if not amt or Decimal(str(amt)) <= _ZERO:
            continue
        events.append(LeakageCandidate(
            leakage_type="RETURN",
            severity="warning",
            description=(
                f"Return deduction ₹{amt} (SKU: {sku}, code: {line.deduction_code}) "
                f"has no matching return record in the return report."
            ),
            amount=Decimal(str(amt)),
            reference_type="settlement",
            reference_id=line.reference_number or sku or "",
            sku=sku,
            deduction_code=line.deduction_code,
            root_cause="Refund deducted from settlement but no corresponding return event exists.",
            is_disputable=True,
            recovery_potential=Decimal(str(amt)),
            recovery_recommendation="Cross-verify with returns report and platform portal. Dispute if no valid return found.",
            evidence=["Settlement return deduction", "Returns report", "Platform order history"],
        ))
    return events


# ── 7. DAMAGE CLAIM LEAKAGE ───────────────────────────────────────────────────
def detect_damage(
    settlement_lines: Sequence[Any],
    operational_lines: Sequence[Any],
) -> list[LeakageCandidate]:
    """
    Damage deduction in settlement exceeds reported damage quantity × price.
    """
    damage_by_sku: dict[str, Decimal] = {}
    for op in operational_lines:
        if op.line_category == "damage" and op.sku and op.amount:
            sku = op.sku
            damage_by_sku[sku] = damage_by_sku.get(sku, _ZERO) + Decimal(str(op.amount))

    damage_keywords = {"damage", "unsellable", "defect"}
    events: list[LeakageCandidate] = []
    charged_by_sku: dict[str, Decimal] = {}
    for line in settlement_lines:
        reason = (line.deduction_reason or "").lower()
        code   = (line.deduction_code   or "").lower()
        if not any(kw in reason or kw in code for kw in damage_keywords):
            continue
        amt = line.deduction_amount
        if not amt or Decimal(str(amt)) <= _ZERO:
            continue
        sku = line.sku or "__all__"
        charged_by_sku[sku] = charged_by_sku.get(sku, _ZERO) + Decimal(str(amt))

    for sku, charged in charged_by_sku.items():
        valid = damage_by_sku.get(sku, _ZERO)
        if charged > valid:
            excess = charged - valid
            events.append(LeakageCandidate(
                leakage_type="DAMAGE",
                severity="warning",
                description=(
                    f"Damage deduction ₹{charged} for SKU {sku} exceeds "
                    f"reported damage value ₹{valid}. Excess: ₹{excess}."
                ),
                amount=excess,
                reference_type="settlement",
                reference_id=sku,
                sku=sku if sku != "__all__" else None,
                root_cause="Settlement damage charge exceeds warehouse damage report. Possible overstatement.",
                is_disputable=True,
                recovery_potential=excess,
                recovery_recommendation="Compare damage report with settlement deduction. Raise dispute for excess amount.",
                evidence=["Damage/unsellable report", "Settlement damage line", "Warehouse inspection record"],
            ))
    return events


# ── 8. PAYMENT TIMING LEAKAGE ────────────────────────────────────────────────
def detect_timing(
    invoice_lines: Sequence[Any],
    payment_lines: Sequence[Any],
    payment_terms_days: int = 30,
) -> list[LeakageCandidate]:
    """
    Invoice aged beyond payment terms → delayed cash flow leakage.
    Match invoice_number across invoices and payments.
    """
    invoice_dates: dict[str, date] = {}
    for inv in invoice_lines:
        if inv.invoice_number and inv.invoice_date:
            invoice_dates[inv.invoice_number] = inv.invoice_date

    paid_dates: dict[str, date] = {}
    for pay in payment_lines:
        if pay.settlement_id and pay.transfer_date:
            paid_dates[pay.settlement_id] = pay.transfer_date

    # For invoices not matched to a payment — check if past terms
    today = date.today()
    events: list[LeakageCandidate] = []
    for inv_no, inv_date in invoice_dates.items():
        due_date = inv_date
        from datetime import timedelta
        due_date_dt = inv_date.replace(month=inv_date.month) if hasattr(inv_date, 'replace') else inv_date
        try:
            from datetime import timedelta
            due = date(inv_date.year, inv_date.month, inv_date.day)
            # Python date arithmetic
            days_old = (today - due).days
        except Exception:
            continue
        if days_old > payment_terms_days:
            events.append(LeakageCandidate(
                leakage_type="TIMING",
                severity="warning",
                description=(
                    f"Invoice {inv_no} dated {inv_date} is {days_old} days old "
                    f"(terms: {payment_terms_days} days). Unpaid or delayed payment detected."
                ),
                amount=None,
                reference_type="invoice",
                reference_id=inv_no,
                invoice_number=inv_no,
                root_cause=f"Invoice aged {days_old} days beyond {payment_terms_days}-day payment terms.",
                is_disputable=True,
                recovery_recommendation="Send payment reminder. Escalate to platform vendor payments team if > 45 days.",
                evidence=["Invoice record", "Payment advice", "Vendor agreement payment terms"],
            ))
    return events


# ── 9. TAX MISMATCH ───────────────────────────────────────────────────────────
def detect_tax_mismatch(
    settlement_lines: Sequence[Any],
    invoice_lines: Sequence[Any],
    tolerance: Decimal = Decimal("1.0"),
) -> list[LeakageCandidate]:
    """
    Settlement tax_amount differs from invoice tax_amount for same invoice_number.
    """
    invoice_tax: dict[str, Decimal] = {}
    for inv in invoice_lines:
        if inv.invoice_number and inv.tax_amount:
            invoice_tax[inv.invoice_number] = (
                invoice_tax.get(inv.invoice_number, _ZERO) + Decimal(str(inv.tax_amount))
            )

    settlement_tax: dict[str, Decimal] = {}
    for line in settlement_lines:
        if line.invoice_number and line.tax_amount:
            settlement_tax[line.invoice_number] = (
                settlement_tax.get(line.invoice_number, _ZERO) + Decimal(str(line.tax_amount))
            )

    events: list[LeakageCandidate] = []
    for inv_no, inv_tax in invoice_tax.items():
        stl_tax = settlement_tax.get(inv_no)
        if stl_tax is None:
            continue
        variance = abs(inv_tax - stl_tax)
        if variance > tolerance:
            events.append(LeakageCandidate(
                leakage_type="TAX",
                severity="warning",
                description=(
                    f"Invoice {inv_no}: invoice tax ₹{inv_tax} vs settlement tax ₹{stl_tax}. "
                    f"Variance ₹{variance}."
                ),
                amount=variance,
                reference_type="invoice",
                reference_id=inv_no,
                invoice_number=inv_no,
                root_cause="Tax computed in settlement differs from tax on invoice. GST/TCS rate mismatch or rounding issue.",
                is_disputable=True,
                recovery_potential=variance,
                recovery_recommendation="Verify GST rates applied. File GSTR-2A reconciliation. Raise credit note if overcharged.",
                evidence=["Invoice copy", "Settlement tax breakdown", "GSTR-2A extract"],
            ))
    return events


# ── 10. DISPUTE RECOVERY FAILURE ─────────────────────────────────────────────
def detect_dispute_recovery_failure(
    chargeback_lines: Sequence[Any],
    operational_lines: Sequence[Any],
    recovery_deadline_days: int = 90,
) -> list[LeakageCandidate]:
    """
    Deduction disputed but no recovery recorded after recovery_deadline_days.
    """
    recovered_disputes: set[str] = set()
    for op in operational_lines:
        if op.line_category == "dispute_recovery" and op.recovered_amount:
            if Decimal(str(op.recovered_amount)) > _ZERO:
                if op.dispute_id:
                    recovered_disputes.add(op.dispute_id)
                if op.claim_id:
                    recovered_disputes.add(op.claim_id)

    today = date.today()
    events: list[LeakageCandidate] = []
    for cb in chargeback_lines:
        if cb.dispute_status and cb.dispute_status.lower() in ("disputed", "raised", "pending"):
            cb_id = cb.chargeback_id or ""
            if cb_id in recovered_disputes:
                continue
            if cb.created_date:
                from datetime import timedelta
                days_open = (today - cb.created_date).days
                if days_open > recovery_deadline_days:
                    amt = Decimal(str(cb.deduction_amount)) if cb.deduction_amount else None
                    events.append(LeakageCandidate(
                        leakage_type="DISPUTE_RECOVERY",
                        severity="critical",
                        description=(
                            f"Chargeback {cb_id} (code: {cb.deduction_code}) of ₹{amt} "
                            f"disputed {days_open} days ago with no recovery recorded."
                        ),
                        amount=amt,
                        reference_type="chargeback",
                        reference_id=cb_id,
                        po_number=cb.po_number,
                        invoice_number=cb.invoice_number,
                        deduction_code=cb.deduction_code,
                        root_cause=f"Dispute open for {days_open} days without recovery — case may be stalled or closed unfavorably.",
                        is_disputable=True,
                        recovery_potential=amt,
                        recovery_recommendation="Escalate to senior account manager. Re-submit dispute with updated evidence.",
                        evidence=["Original chargeback notice", "Dispute submission record", "Evidence submitted"],
                    ))
    return events
