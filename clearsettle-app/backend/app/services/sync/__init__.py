"""
Sync job system.

Modules
-------
job_manager   → CRUD for SyncJob + SyncLog (pure DB, no HTTP)
orchestrator  → Per-job-type async handlers (calls SP API, updates job state)
registry      → Maps job_type string → orchestrator handler

Architecture notes
------------------
- All orchestrator functions manage their own AsyncSession (they run in background,
  outside the HTTP request-response cycle).
- job_manager functions accept an open session and never open their own.
- registry.dispatch() is the single entry point for background_tasks.add_task().
- Future Celery migration: replace background_tasks.add_task(...) with
  celery_task.delay(...); keep registry.dispatch as the Celery task body.
"""
