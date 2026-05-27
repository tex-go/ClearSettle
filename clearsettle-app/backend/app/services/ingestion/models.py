"""
Platform-agnostic normalised data models for the ingestion pipeline.

These dataclasses are the contract between platform-specific parsers and
the platform-agnostic storage layer.  Adding Flipkart/Meesho means writing
a new parser that produces these same dataclasses.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class NormalizedFee:
    fee_type:        str
    currency:        str
    amount:          Decimal           # negative for marketplace deductions
    fee_description: str | None = None


@dataclass
class NormalizedTransaction:
    transaction_type: str              # shipment | refund | service_fee | adjustment | …
    source_hash:      str              # platform-derived dedup key (SHA-256 hex)
    currency:         str
    total_amount:     Decimal          # sum of charges (principal + shipping + …)
    fees_total:       Decimal          # sum of all fee amounts (usually negative)
    net_amount:       Decimal          # total_amount + fees_total
    fees:             list[NormalizedFee]
    raw_data_json:    str

    order_id:         str | None = None
    order_item_id:    str | None = None
    sku:              str | None = None
    marketplace:      str | None = None
    posted_date:      datetime | None = None
    quantity:         int = 1
    principal_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    shipping_amount:  Decimal = field(default_factory=lambda: Decimal("0"))
    gift_wrap_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    promotion_amount: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass
class NormalizedSettlement:
    external_id:  str              # platform settlement ID (e.g. FinancialEventGroupId)
    status:       str              # open | closed
    currency:     str
    total_amount: Decimal          # gross settlement amount
    transactions: list[NormalizedTransaction]
    raw_data_json: str             # full raw group API response (for audit)

    converted_amount:     Decimal | None = None
    fund_transfer_amount: Decimal | None = None
    beginning_balance:    Decimal | None = None
    period_start:         datetime | None = None
    period_end:           datetime | None = None
    fund_transfer_date:   datetime | None = None
    account_tail:         str | None = None


@dataclass
class IngestionResult:
    settlements_created:  int = 0
    settlements_updated:  int = 0
    transactions_created: int = 0
    fees_created:         int = 0
    payouts_created:      int = 0
    skipped:              int = 0   # settlement already up-to-date (closed, not re-fetched)

    @property
    def total_records(self) -> int:
        return (
            self.settlements_created
            + self.settlements_updated
            + self.transactions_created
            + self.fees_created
            + self.payouts_created
        )
