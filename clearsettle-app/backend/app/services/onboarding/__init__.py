"""
Platform onboarding service — manages the 8-step seller activation flow.

Entry points:
    manager.create_session(db, company_id, platform)
    manager.get_progress(db, session_id)
    orchestrator.advance_onboarding(db, session_id)
    validators.validate_step(db, session_id, step_name)
"""
