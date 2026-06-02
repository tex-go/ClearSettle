# Financial Quality Standards
**Version:** 1.0 | **Owner:** `data-quality-agent`

ClearSettle handles real money. Financial accuracy is non-negotiable. These standards define the precision requirements, validation rules, and testing obligations for all financial calculations in the system.

---

## Precision Standards

### Currency Handling
- All monetary values stored as `NUMERIC(15, 2)` in PostgreSQL (never FLOAT, never VARCHAR)
- All calculations use Python `Decimal` type — never `float` for money
- Rounding uses ROUND_HALF_UP for all paisa calculations
- Final rounding only at display time — never round intermediates

```python
# CORRECT
from decimal import Decimal, ROUND_HALF_UP
commission = Decimal('1000.00') * Decimal('0.18')
commission = commission.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

# WRONG — never do this
commission = 1000.0 * 0.18  # floating point error
commission = round(1000 * 0.18, 2)  # still float
```

### Tolerance Rules

| Comparison | Tolerance | Action |
|---|---|---|
| Settlement discrepancy | ±₹0.01 | Within tolerance — no flag |
| Settlement discrepancy | ₹0.01–₹1.00 | Flag for review |
| Settlement discrepancy | > ₹1.00 | Flag + queue for dispute evaluation |
| Settlement discrepancy | > ₹100.00 | Auto-dispute trigger |
| Tax calculation | ±₹0.01 | Within tolerance |
| Commission overcharge | > ₹5.00 per order | Flag |
| Commission overcharge aggregate | > ₹500.00 per cycle | Auto-dispute |

---

## Settlement Validation Rules

### Rule 1 — Arithmetic Integrity
```
Gross Order Value
- Marketplace Commission
- Platform Fee
- Shipping Charge
- GST on Commission
- TDS/TCS
- Returns Amount
+ Promotional Credits
+ Adjustments
= Net Settlement

ASSERTION: |Calculated Net - Reported Net| ≤ ₹0.01
```

### Rule 2 — Date Integrity
```
Order Date ≤ Settlement Date ≤ Today
Settlement Period Start ≤ Order Date ≤ Settlement Period End (within marketplace SLA)
No settlement date in future
No order date more than 2 years in past (flag for review)
```

### Rule 3 — Completeness
```
Count(line_items) == Count(orders_in_period)
Sum(line_item_amounts) == Total Settlement Amount (within ₹0.01)
All returned orders have a corresponding original order ID
```

### Rule 4 — Uniqueness
```
Settlement reference number is unique per marketplace per company
No duplicate order_id within same settlement period
No order_id appearing in two settlement periods
```

### Rule 5 — Range Validation
```
Commission rate in [0%, 30%] — marketplace max
Shipping charge in [₹0, ₹5000] — flag above
GST rate in [0%, 28%] — validate against GSTIN category
TDS rate in [0%, 2%] — current rates
TCS rate in [0%, 1%] — Amazon TCS rate
```

---

## Marketplace-Specific Rules

### Flipkart
```python
COMMISSION_RANGES = {
    "electronics": (0.01, 0.05),
    "fashion": (0.10, 0.25),
    "beauty": (0.08, 0.18),
    "default": (0.01, 0.25)
}

# TDS calculation
tds = gross_order_value * Decimal('0.01')

# Wallet redemption: amounts > ₹10,000 require manual review
if wallet_redemption > 10000:
    flag_for_review("wallet_redemption_large_amount")

# Return commission: should equal original commission × return_percentage
expected_return_commission = original_commission * (return_qty / original_qty)
```

### Amazon
```python
# TCS (Tax Collected at Source)
tcs = gross_order_value * Decimal('0.01')

# SAFE-T claim: reduces settlement by exact claim amount
net_after_safe_t = settlement - safe_t_amount

# Commission validation
assert commission_rate <= Decimal('0.25'), "Commission rate exceeds 25%"
```

### Meesho
```python
# No TDS, No TCS on Meesho
assert tds == Decimal('0'), "Meesho should have no TDS"
assert tcs == Decimal('0'), "Meesho should have no TCS"

# Return commission: zero (Meesho policy)
assert return_commission == Decimal('0'), "Meesho return commission must be zero"
```

---

## Financial Test Requirements

### Unit Test Coverage for Financial Code: 95% minimum

Every financial function must have tests for:
1. Standard calculation (normal case)
2. Zero amount
3. Maximum rate
4. Minimum rate
5. Rounding edge cases (₹0.005 → ₹0.01)
6. Return/refund calculations
7. Marketplace-specific edge cases
8. Invalid input rejection

### Fixture-Based Regression Tests

Maintain in `tests/fixtures/financial/`:

```json
// flipkart_settlement_fixture.json
{
  "input": {
    "gross_order_value": "1000.00",
    "commission_rate": "0.15",
    "shipping": "40.00",
    "gst_on_commission": "27.00",
    "tds": "10.00"
  },
  "expected": {
    "commission": "150.00",
    "net_settlement": "773.00",
    "discrepancy_from_reported_900": "-127.00"
  }
}
```

Every calculation change must:
1. Not break any existing fixture
2. Add a new fixture for the new behavior

---

## Double-Entry Validation

For any multi-step financial operation (settlement import → reconciliation → dispute):
```
Total Input Amount = Total Output Amount + Unexplained Difference
Unexplained Difference must be ≤ ₹0.01 after all processing
```

If unexplained difference > ₹0.01, raise `FinancialIntegrityError` and halt processing.

---

## Auditability Requirements

Every financial calculation must store:
1. Input values used (immutable record)
2. Formula applied (rate version + marketplace rules version)
3. Output value produced
4. Timestamp of calculation
5. Version of calculation engine that produced this result

This allows reproduction of any historical calculation for audit purposes.
