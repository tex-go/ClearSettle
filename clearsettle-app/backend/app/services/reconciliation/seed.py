"""
Test data seed for the reconciliation engine.

generate_test_settlement(db, company_id) → Settlement

Creates one Settlement with hand-crafted transactions and fees designed to
trigger all 7 detectors when reconciliation is run:

  1. MISSING_PAYOUT         — payout.status = "failed"
  2. PAYOUT_AMOUNT_MISMATCH — payout.amount 20% below fund_transfer_amount (> 1% tolerance)
  3. OVERCHARGE_REFERRAL_FEE — referral fee is 40% of principal (threshold 30%)
  4. OVERCHARGE_FBA_FEE      — FBA fee per unit is 200 INR (threshold 150)
  5. DUPLICATE_DEDUCTION     — same referral fee charged twice on the same order item
  6. UNEXPECTED_FEE          — fee_type "CustomAuditFee" not in KNOWN_FEE_TYPES
  7. PENALTY_MISMATCH        — service_fee transaction for 8 000 INR (threshold 5 000)
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fee import Fee
from app.db.models.payout_event import PayoutEvent
from app.db.models.settlement import Settlement
from app.db.models.settlement_transaction import SettlementTransaction


def _sha256(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


async def generate_test_settlement(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    external_id: str | None = None,
    platform: str = "amazon",
) -> Settlement:
    """
    Insert a synthetic settlement + related records into the DB.

    Does NOT commit — caller decides when to commit.
    Returns the Settlement ORM object (id is assigned after flush).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ext_id = external_id or f"TEST-RECON-{uuid.uuid4().hex[:8].upper()}"

    # ── Settlement ────────────────────────────────────────────────────────────
    settlement = Settlement(
        id=uuid.uuid4(),
        company_id=company_id,
        platform=platform,
        external_id=ext_id,
        status="closed",
        currency="INR",
        total_amount=Decimal("100000.00"),
        fund_transfer_amount=Decimal("80000.00"),
        period_start=datetime(2026, 1, 1),
        period_end=datetime(2026, 1, 14),
        transactions_count=0,
    )
    db.add(settlement)
    await db.flush()

    # ── Payout: failed + wrong amount ─────────────────────────────────────────
    # → Triggers MISSING_PAYOUT (status="failed")
    # → Triggers PAYOUT_AMOUNT_MISMATCH (64000 vs expected 80000, 20% off)
    payout = PayoutEvent(
        id=uuid.uuid4(),
        settlement_id=settlement.id,
        company_id=company_id,
        platform=platform,
        status="failed",
        currency="INR",
        amount=Decimal("64000.00"),
        transfer_date=None,
    )
    db.add(payout)

    # ── Shipment 1: referral overcharge + FBA overcharge + unexpected fee ─────
    # → Triggers OVERCHARGE_REFERRAL_FEE: 2000/5000 = 40% > 30% threshold
    # → Triggers OVERCHARGE_FBA_FEE: 400/2 = 200 per unit > 150 threshold
    # → Triggers UNEXPECTED_FEE: "CustomAuditFee" is not a known fee type
    txn1 = SettlementTransaction(
        id=uuid.uuid4(),
        settlement_id=settlement.id,
        company_id=company_id,
        platform=platform,
        source_hash=_sha256("amazon", "shipment", ext_id, "ORDER-001", "ITEM-001"),
        transaction_type="shipment",
        order_id="ORDER-001",
        order_item_id="ITEM-001",
        sku="SKU-TEST-001",
        currency="INR",
        quantity=2,
        principal_amount=Decimal("5000.00"),
        total_amount=Decimal("5000.00"),
        fees_total=Decimal("-2700.00"),
        net_amount=Decimal("2300.00"),
        posted_date=now,
        created_at=now,
    )
    db.add(txn1)
    await db.flush()

    db.add(Fee(
        id=uuid.uuid4(), transaction_id=txn1.id, settlement_id=settlement.id,
        company_id=company_id, platform=platform,
        fee_type="ReferralFee", currency="INR",
        amount=Decimal("-2000.00"), created_at=now,
    ))
    db.add(Fee(
        id=uuid.uuid4(), transaction_id=txn1.id, settlement_id=settlement.id,
        company_id=company_id, platform=platform,
        fee_type="FBAPerUnitFulfillmentFee", currency="INR",
        amount=Decimal("-400.00"), created_at=now,
    ))
    db.add(Fee(
        id=uuid.uuid4(), transaction_id=txn1.id, settlement_id=settlement.id,
        company_id=company_id, platform=platform,
        fee_type="CustomAuditFee", currency="INR",
        amount=Decimal("-300.00"), created_at=now,
    ))

    # ── Shipment 2: duplicate referral fee on the same order item ─────────────
    # → Triggers DUPLICATE_DEDUCTION: ReferralFee -2000 on ORDER-001/ITEM-001 twice
    txn2 = SettlementTransaction(
        id=uuid.uuid4(),
        settlement_id=settlement.id,
        company_id=company_id,
        platform=platform,
        source_hash=_sha256("amazon", "shipment", ext_id, "ORDER-001", "ITEM-001-DUP"),
        transaction_type="shipment",
        order_id="ORDER-001",
        order_item_id="ITEM-001",
        sku="SKU-TEST-001",
        currency="INR",
        quantity=1,
        principal_amount=Decimal("0.00"),
        total_amount=Decimal("0.00"),
        fees_total=Decimal("-2000.00"),
        net_amount=Decimal("-2000.00"),
        posted_date=now,
        created_at=now,
    )
    db.add(txn2)
    await db.flush()

    db.add(Fee(
        id=uuid.uuid4(), transaction_id=txn2.id, settlement_id=settlement.id,
        company_id=company_id, platform=platform,
        fee_type="ReferralFee", currency="INR",
        amount=Decimal("-2000.00"), created_at=now,
    ))

    # ── Service fee: 8 000 INR ────────────────────────────────────────────────
    # → Triggers PENALTY_MISMATCH: 8000 > 5000 threshold
    txn3 = SettlementTransaction(
        id=uuid.uuid4(),
        settlement_id=settlement.id,
        company_id=company_id,
        platform=platform,
        source_hash=_sha256("amazon", "service_fee", ext_id, "SVC-TEST-001", ""),
        transaction_type="service_fee",
        order_id=None,
        currency="INR",
        quantity=1,
        principal_amount=Decimal("0.00"),
        total_amount=Decimal("-8000.00"),
        fees_total=Decimal("0.00"),
        net_amount=Decimal("-8000.00"),
        posted_date=now,
        created_at=now,
    )
    db.add(txn3)

    settlement.transactions_count = 3

    return settlement
