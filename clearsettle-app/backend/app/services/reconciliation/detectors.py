"""
Reconciliation detectors — one function per discrepancy type.

All detectors share the same signature:
    detect_X(settlement, transactions, payout, params, rule_id) -> list[DiscrepancyCandidate]

Detectors are pure functions: they read ORM objects but never write to the DB.
The engine calls them and collects the results.
"""
from decimal import Decimal
from uuid import UUID

from app.services.reconciliation.models import DiscrepancyCandidate

# Fee types considered standard for Amazon marketplace
KNOWN_FEE_TYPES: frozenset[str] = frozenset({
    "ReferralFee",
    "FBAPerUnitFulfillmentFee",
    "FBAWeightBasedFee",
    "VariableClosingFee",
    "PerItemFee",
    "Commission",
    "Shipping",
    "GiftwrapCharge",
    "GiftwrapCommission",
    "ShippingCharge",
    "ShippingHBFee",
    "ShippingTax",
    "Goodwill",
    "RestockingFee",
    "ReturnShipping",
    "DigitalServiceFee",
    "LowValueGoodsCharge",
    "LowValueGoodsTax",
    "StorageFee",
    "LongTermStorageFee",
    "RemovalFee",
    "DisposalFee",
    "InboundTransportationFee",
    "FBAInboundConvenienceFee",
    "RunLightningDealFee",
    "SubscriptionFee",
    "MarketplaceFacilitatorTax-Principal",
    "MarketplaceFacilitatorTax-Shipping",
})

_ZERO = Decimal("0")


# ── 1. Missing payout ─────────────────────────────────────────────────────────

def detect_missing_payout(
    settlement, transactions, payout, params: dict, rule_id: UUID | None
) -> list[DiscrepancyCandidate]:
    if settlement.status != "closed":
        return []

    if payout is None:
        expected = settlement.fund_transfer_amount or settlement.total_amount or _ZERO
        return [DiscrepancyCandidate(
            discrepancy_type="MISSING_PAYOUT",
            severity="critical",
            description=(
                f"Closed settlement {settlement.external_id} has no payout event. "
                f"Expected transfer of {expected}."
            ),
            rule_id=rule_id,
            expected_amount=Decimal(str(expected)),
            actual_amount=_ZERO,
            variance_amount=Decimal(str(expected)),
        )]

    if payout.status == "failed":
        return [DiscrepancyCandidate(
            discrepancy_type="MISSING_PAYOUT",
            severity="critical",
            description=(
                f"Payout for settlement {settlement.external_id} has status 'failed'. "
                f"Amount {payout.amount} was not transferred."
            ),
            rule_id=rule_id,
            expected_amount=Decimal(str(payout.amount)),
            actual_amount=_ZERO,
            variance_amount=Decimal(str(payout.amount)),
        )]

    return []


# ── 2. Payout amount mismatch ─────────────────────────────────────────────────

def detect_payout_mismatch(
    settlement, transactions, payout, params: dict, rule_id: UUID | None
) -> list[DiscrepancyCandidate]:
    if payout is None or settlement.fund_transfer_amount is None:
        return []

    tolerance_pct = Decimal(str(params.get("tolerance_pct", "0.01")))
    expected = Decimal(str(settlement.fund_transfer_amount))
    actual   = Decimal(str(payout.amount))
    variance = abs(expected - actual)

    if expected == _ZERO:
        return []

    if variance / expected > tolerance_pct:
        return [DiscrepancyCandidate(
            discrepancy_type="PAYOUT_AMOUNT_MISMATCH",
            severity="critical",
            description=(
                f"Payout amount {actual} differs from expected fund transfer "
                f"{expected} by {variance} ({variance / expected:.1%})."
            ),
            rule_id=rule_id,
            expected_amount=expected,
            actual_amount=actual,
            variance_amount=variance,
        )]

    return []


# ── 3. Referral fee overcharge ────────────────────────────────────────────────

_REFERRAL_FEE_TYPES = frozenset({"ReferralFee", "Commission"})

def detect_referral_fee_overcharge(
    settlement, transactions, payout, params: dict, rule_id: UUID | None
) -> list[DiscrepancyCandidate]:
    max_rate = Decimal(str(params.get("max_rate", "0.30")))
    events: list[DiscrepancyCandidate] = []

    for txn in transactions:
        if txn.transaction_type != "shipment":
            continue
        principal = Decimal(str(txn.principal_amount or 0))
        if principal <= _ZERO:
            continue

        referral_fees = sum(
            abs(Decimal(str(fee.amount)))
            for fee in txn.fees
            if fee.fee_type in _REFERRAL_FEE_TYPES
        )
        if referral_fees == _ZERO:
            continue

        rate = referral_fees / principal
        if rate > max_rate:
            expected_fee = principal * max_rate
            events.append(DiscrepancyCandidate(
                discrepancy_type="OVERCHARGE_REFERRAL_FEE",
                severity="warning",
                description=(
                    f"Referral fee {referral_fees:.2f} is {rate:.1%} of principal {principal:.2f}, "
                    f"exceeding the {max_rate:.0%} threshold for order {txn.order_id}."
                ),
                rule_id=rule_id,
                transaction_id=txn.id,
                order_id=txn.order_id,
                fee_type="ReferralFee",
                expected_amount=expected_fee,
                actual_amount=referral_fees,
                variance_amount=referral_fees - expected_fee,
                metadata={"rate": float(rate), "max_rate": float(max_rate)},
            ))

    return events


# ── 4. FBA fee overcharge ─────────────────────────────────────────────────────

_FBA_FEE_TYPES = frozenset({"FBAPerUnitFulfillmentFee", "FBAWeightBasedFee"})

def detect_fba_fee_overcharge(
    settlement, transactions, payout, params: dict, rule_id: UUID | None
) -> list[DiscrepancyCandidate]:
    max_per_unit = Decimal(str(params.get("max_per_unit", "150.0")))
    events: list[DiscrepancyCandidate] = []

    for txn in transactions:
        if txn.transaction_type != "shipment":
            continue

        fba_fees = sum(
            abs(Decimal(str(fee.amount)))
            for fee in txn.fees
            if fee.fee_type in _FBA_FEE_TYPES
        )
        if fba_fees == _ZERO:
            continue

        quantity = Decimal(str(txn.quantity or 1))
        fba_per_unit = fba_fees / quantity

        if fba_per_unit > max_per_unit:
            expected_total = max_per_unit * quantity
            events.append(DiscrepancyCandidate(
                discrepancy_type="OVERCHARGE_FBA_FEE",
                severity="warning",
                description=(
                    f"FBA fee per unit {fba_per_unit:.2f} exceeds threshold {max_per_unit:.2f} "
                    f"for order {txn.order_id} (qty={int(quantity)})."
                ),
                rule_id=rule_id,
                transaction_id=txn.id,
                order_id=txn.order_id,
                fee_type="FBAPerUnitFulfillmentFee",
                expected_amount=expected_total,
                actual_amount=fba_fees,
                variance_amount=fba_fees - expected_total,
                metadata={"fba_per_unit": float(fba_per_unit), "max_per_unit": float(max_per_unit)},
            ))

    return events


# ── 5. Duplicate deductions ───────────────────────────────────────────────────

def detect_duplicate_deductions(
    settlement, transactions, payout, params: dict, rule_id: UUID | None
) -> list[DiscrepancyCandidate]:
    """
    Flag when the same fee (order_id, order_item_id, fee_type, amount) appears
    more than once across shipment transactions in the same settlement.
    """
    seen: dict[tuple, list] = {}

    for txn in transactions:
        if txn.transaction_type != "shipment":
            continue
        for fee in txn.fees:
            amount = Decimal(str(fee.amount))
            if amount >= _ZERO:
                continue   # only check deductions (negative amounts)

            key = (
                txn.order_id or "",
                txn.order_item_id or "",
                fee.fee_type,
                round(float(abs(amount)), 2),
            )
            seen.setdefault(key, []).append(txn.id)

    events: list[DiscrepancyCandidate] = []
    flagged_keys: set[tuple] = set()

    for (order_id, order_item_id, fee_type, amount_f), txn_ids in seen.items():
        if len(txn_ids) <= 1:
            continue

        dedup_key = (order_id, order_item_id, fee_type)
        if dedup_key in flagged_keys:
            continue
        flagged_keys.add(dedup_key)

        amount     = Decimal(str(amount_f))
        total_charged = amount * len(txn_ids)
        variance   = amount * (len(txn_ids) - 1)

        label = f"{order_id}/{order_item_id}" if order_item_id else order_id
        events.append(DiscrepancyCandidate(
            discrepancy_type="DUPLICATE_DEDUCTION",
            severity="critical",
            description=(
                f"Fee '{fee_type}' of {amount:.2f} charged {len(txn_ids)} times "
                f"for order item {label}. Expected once, excess: {variance:.2f}."
            ),
            rule_id=rule_id,
            transaction_id=txn_ids[0],
            order_id=order_id,
            fee_type=fee_type,
            expected_amount=amount,
            actual_amount=total_charged,
            variance_amount=variance,
            metadata={
                "count": len(txn_ids),
                "transaction_ids": [str(t) for t in txn_ids],
            },
        ))

    return events


# ── 6. Unexpected fees ────────────────────────────────────────────────────────

def detect_unexpected_fees(
    settlement, transactions, payout, params: dict, rule_id: UUID | None
) -> list[DiscrepancyCandidate]:
    allowed_extra: set[str] = set(params.get("allowed_fee_types", []))
    all_allowed = KNOWN_FEE_TYPES | allowed_extra

    flagged_types: set[str] = set()
    events: list[DiscrepancyCandidate] = []

    for txn in transactions:
        for fee in txn.fees:
            if fee.fee_type in all_allowed or fee.fee_type in flagged_types:
                continue
            flagged_types.add(fee.fee_type)
            events.append(DiscrepancyCandidate(
                discrepancy_type="UNEXPECTED_FEE",
                severity="info",
                description=(
                    f"Unexpected fee type '{fee.fee_type}' in settlement "
                    f"{settlement.external_id}. Verify this charge is legitimate."
                ),
                rule_id=rule_id,
                transaction_id=txn.id,
                order_id=txn.order_id,
                fee_type=fee.fee_type,
                actual_amount=Decimal(str(fee.amount)),
                metadata={"fee_type": fee.fee_type},
            ))

    return events


# ── 7. Penalty / service-fee mismatch ─────────────────────────────────────────

def detect_penalty_mismatches(
    settlement, transactions, payout, params: dict, rule_id: UUID | None
) -> list[DiscrepancyCandidate]:
    max_service_fee = Decimal(str(params.get("max_service_fee", "5000.0")))
    events: list[DiscrepancyCandidate] = []

    for txn in transactions:
        if txn.transaction_type != "service_fee":
            continue

        fee_amount = abs(Decimal(str(txn.total_amount or 0)))
        if fee_amount <= max_service_fee:
            continue

        events.append(DiscrepancyCandidate(
            discrepancy_type="PENALTY_MISMATCH",
            severity="warning",
            description=(
                f"Service fee {fee_amount:.2f} exceeds expected maximum {max_service_fee:.2f}. "
                f"Possible excessive penalty in settlement {settlement.external_id}."
            ),
            rule_id=rule_id,
            transaction_id=txn.id,
            expected_amount=max_service_fee,
            actual_amount=fee_amount,
            variance_amount=fee_amount - max_service_fee,
            metadata={"service_fee_amount": float(fee_amount)},
        ))

    return events
