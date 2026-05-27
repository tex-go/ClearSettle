"""
GST/TCS tax engine for Indian e-commerce sellers.

Entry points:
  engine.process_settlement(db, settlement_id, company_id) -> TaxExtractionResult
  engine.process_all_for_period(db, company_id, platform, period) -> list[TaxExtractionResult]
  summary.build_monthly_summary(db, company_id, platform, period) -> MonthlyTaxSummary
  summary.generate_ledger_csv(entries) -> str
  calculator.is_tcs_fee(fee_type) -> bool
  calculator.gst_from_inclusive(amount, rate) -> (taxable, gst)
"""
