"""
Dynamic rule engine — evaluate configurable rules against settlement contexts.

Entry points:
    engine.evaluate_rules_for_settlement(db, settlement_id, company_id)
    engine.evaluate_rule(db, rule_id, company_id, context, dry_run=True)
"""
