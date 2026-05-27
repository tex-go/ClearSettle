"""
Amazon SP API → NormalizedSettlement parser.

Converts raw Amazon Finances API dicts into the platform-agnostic
NormalizedSettlement / NormalizedTransaction / NormalizedFee dataclasses.

Event types handled
-------------------
ShipmentEventList        → transaction_type = "shipment"
RefundEventList          → transaction_type = "refund"
ServiceFeeEventList      → transaction_type = "service_fee"
AdjustmentEventList      → transaction_type = "adjustment"
GuaranteeClaimEventList  → transaction_type = "guarantee_claim"
ProductAdsPaymentEventList → transaction_type = "ads_payment"
All others               → transaction_type = "other"
"""
import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.services.ingestion.models import (
    NormalizedFee,
    NormalizedSettlement,
    NormalizedTransaction,
)

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _money(d: dict | None) -> Decimal:
    if not d:
        return Decimal("0")
    try:
        return Decimal(str(d.get("CurrencyAmount") or 0))
    except InvalidOperation:
        return Decimal("0")


def _currency(d: dict | None, default: str = "INR") -> str:
    if not d:
        return default
    return d.get("CurrencyCode") or default


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _hash(*parts: str) -> str:
    """Deterministic 64-char hex dedup key from arbitrary string parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Group-level parsing ────────────────────────────────────────────────────────

def parse_settlement(raw_group: dict, raw_events: dict) -> NormalizedSettlement:
    """
    Convert one raw FinancialEventGroup + its FinancialEvents into a
    NormalizedSettlement.
    """
    group_id = raw_group.get("FinancialEventGroupId", "")
    proc_status = (raw_group.get("ProcessingStatus") or "").lower()
    # Amazon returns "Open" or "Closed"
    status = "closed" if proc_status == "closed" else "open"

    orig   = raw_group.get("OriginalTotal", {})
    conv   = raw_group.get("ConvertedTotal", {})
    fund   = raw_group.get("FundTransferAmount", {})
    begin  = raw_group.get("BeginningBalance", {})

    currency     = _currency(orig)
    total_amount = _money(orig)

    transactions = _parse_all_events(raw_events, group_id=group_id)

    return NormalizedSettlement(
        external_id=group_id,
        status=status,
        currency=currency,
        total_amount=total_amount,
        converted_amount=_money(conv) if conv else None,
        fund_transfer_amount=_money(fund) if fund else None,
        beginning_balance=_money(begin) if begin else None,
        period_start=_parse_dt(raw_group.get("FinancialEventGroupStart")),
        period_end=_parse_dt(raw_group.get("FinancialEventGroupEnd")),
        fund_transfer_date=_parse_dt(raw_group.get("FundTransferDate")),
        account_tail=raw_group.get("AccountTail"),
        transactions=transactions,
        raw_data_json=json.dumps(raw_group),
    )


# ── Event-list dispatchers ────────────────────────────────────────────────────

def _parse_all_events(raw_events: dict, *, group_id: str) -> list[NormalizedTransaction]:
    txns: list[NormalizedTransaction] = []

    for item in raw_events.get("ShipmentEventList", []):
        txns.extend(_parse_shipment_event(item, group_id=group_id, txn_type="shipment"))

    for item in raw_events.get("RefundEventList", []):
        txns.extend(_parse_shipment_event(item, group_id=group_id, txn_type="refund"))

    for item in raw_events.get("ServiceFeeEventList", []):
        t = _parse_service_fee_event(item, group_id=group_id)
        if t:
            txns.append(t)

    for item in raw_events.get("AdjustmentEventList", []):
        txns.extend(_parse_adjustment_event(item, group_id=group_id))

    for item in raw_events.get("GuaranteeClaimEventList", []):
        txns.extend(_parse_shipment_event(item, group_id=group_id, txn_type="guarantee_claim"))

    for item in raw_events.get("ProductAdsPaymentEventList", []):
        t = _parse_ads_payment_event(item, group_id=group_id)
        if t:
            txns.append(t)

    # Any unrecognised lists are silently ignored (audit trail in raw_data_json)
    return txns


# ── Shipment / refund / guarantee_claim (shared structure) ────────────────────

def _parse_shipment_event(
    event: dict,
    *,
    group_id: str,
    txn_type: str,
) -> list[NormalizedTransaction]:
    """One ShipmentEvent may contain multiple ShipmentItems — one txn per item."""
    order_id    = event.get("AmazonOrderId", "")
    marketplace = event.get("MarketplaceName", "")
    posted_date = _parse_dt(event.get("PostedDate"))
    txns: list[NormalizedTransaction] = []

    for item in event.get("ShipmentItemList", []):
        sku           = item.get("SellerSKU", "")
        order_item_id = item.get("OrderItemId", "")
        qty           = item.get("QuantityShipped") or 1

        charges = {
            c["ChargeType"]: c.get("ChargeAmount")
            for c in item.get("ItemChargeList", [])
            if "ChargeType" in c
        }
        principal = _money(charges.get("Principal"))
        shipping  = _money(charges.get("Shipping"))
        gift_wrap = _money(charges.get("GiftWrap"))
        promotion = sum(
            _money(p.get("PromotionAmount"))
            for p in item.get("PromotionList", [])
        )
        total    = principal + shipping + gift_wrap + promotion
        currency = _currency(charges.get("Principal"))

        fees: list[NormalizedFee] = []
        fees_total = Decimal("0")
        for fee_dict in item.get("ItemFeeList", []):
            f_amt = fee_dict.get("FeeAmount")
            f = NormalizedFee(
                fee_type=fee_dict.get("FeeType", "UnknownFee"),
                fee_description=fee_dict.get("FeeType"),
                currency=_currency(f_amt, currency),
                amount=_money(f_amt),
            )
            fees.append(f)
            fees_total += f.amount

        # Tax-withheld items treated as negative fees
        for tw in item.get("ItemTaxWithheldList", []):
            for c in tw.get("TaxesWithheld", []):
                f_amt = c.get("ChargeAmount")
                f = NormalizedFee(
                    fee_type="TaxWithheld_" + c.get("ChargeType", ""),
                    currency=_currency(f_amt, currency),
                    amount=_money(f_amt),
                )
                fees.append(f)
                fees_total += f.amount

        net = total + fees_total
        src = _hash("amazon", txn_type, group_id, order_id, order_item_id)

        txns.append(NormalizedTransaction(
            transaction_type=txn_type,
            source_hash=src,
            order_id=order_id,
            order_item_id=order_item_id,
            sku=sku,
            marketplace=marketplace,
            posted_date=posted_date,
            quantity=int(qty),
            currency=currency,
            principal_amount=principal,
            shipping_amount=shipping,
            gift_wrap_amount=gift_wrap,
            promotion_amount=promotion,
            total_amount=total,
            fees=fees,
            fees_total=fees_total,
            net_amount=net,
            raw_data_json=json.dumps(item),
        ))

    return txns


# ── Service fees ──────────────────────────────────────────────────────────────

def _parse_service_fee_event(event: dict, *, group_id: str) -> NormalizedTransaction | None:
    fee_type    = event.get("FeeType", "UnknownFee")
    posted_date = _parse_dt(event.get("PostedDate"))
    f_amt       = event.get("FeeAmount")
    amount      = _money(f_amt)
    currency    = _currency(f_amt)

    src = _hash("amazon", "service_fee", group_id, fee_type,
                (posted_date or datetime.utcnow()).isoformat())

    fee = NormalizedFee(fee_type=fee_type, currency=currency, amount=amount)

    return NormalizedTransaction(
        transaction_type="service_fee",
        source_hash=src,
        order_id=event.get("AmazonOrderId"),
        currency=currency,
        total_amount=Decimal("0"),
        fees=[fee],
        fees_total=amount,
        net_amount=amount,
        posted_date=posted_date,
        raw_data_json=json.dumps(event),
    )


# ── Adjustments ───────────────────────────────────────────────────────────────

def _parse_adjustment_event(event: dict, *, group_id: str) -> list[NormalizedTransaction]:
    adj_type    = event.get("AdjustmentType", "Adjustment")
    posted_date = _parse_dt(event.get("PostedDate"))
    txns: list[NormalizedTransaction] = []

    for idx, item in enumerate(event.get("AdjustmentItemList", [])):
        sku      = item.get("SellerSKU", "")
        qty      = item.get("Quantity") or 1
        amt_dict = item.get("PerUnitAmount") or item.get("TotalAmount")
        amount   = _money(amt_dict)
        currency = _currency(amt_dict)

        src = _hash("amazon", "adjustment", group_id, adj_type, sku, str(idx))

        txns.append(NormalizedTransaction(
            transaction_type="adjustment",
            source_hash=src,
            sku=sku,
            posted_date=posted_date,
            quantity=int(qty),
            currency=currency,
            total_amount=amount,
            fees=[],
            fees_total=Decimal("0"),
            net_amount=amount,
            raw_data_json=json.dumps(item),
        ))

    return txns


# ── Product Ads payments ───────────────────────────────────────────────────────

def _parse_ads_payment_event(event: dict, *, group_id: str) -> NormalizedTransaction | None:
    posted_date = _parse_dt(event.get("PostedDate"))
    amt_dict    = event.get("TransactionAmount")
    amount      = _money(amt_dict)
    currency    = _currency(amt_dict)
    inv_id      = event.get("InvoiceId", "")

    src = _hash("amazon", "ads_payment", group_id, inv_id,
                (posted_date or datetime.utcnow()).isoformat())

    return NormalizedTransaction(
        transaction_type="ads_payment",
        source_hash=src,
        posted_date=posted_date,
        currency=currency,
        total_amount=amount,
        fees=[],
        fees_total=Decimal("0"),
        net_amount=amount,
        raw_data_json=json.dumps(event),
    )
