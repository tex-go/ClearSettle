"""
Settlement query service.

Entry points:
  queries.list_settlements(db, ...)       → (items, total, summary)
  queries.get_settlement_by_id(db, ...)   → detail dict | None
  queries.get_fee_breakdown(db, ...)      → FeeBreakdownOut
  queries.list_transactions(db, ...)      → (items, total, by_type)
  queries.list_payouts(db, ...)           → (items, total, stats)
"""
