"""
Persist reconciliation results and discrepancy events to the database.

All functions accept an open AsyncSession and do NOT commit — the caller decides.
"""
import json
import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.discrepancy_event import DiscrepancyEvent
from app.db.models.reconciliation_result import ReconciliationResult
from app.services.reconciliation.models import ReconciliationRunResult

_ZERO = Decimal("0")


async def save_result(
    db: AsyncSession,
    run: ReconciliationRunResult,
) -> ReconciliationResult:
    """
    Persist a ReconciliationRunResult to the DB.

    Creates one ReconciliationResult row and N DiscrepancyEvent rows.
    Does NOT commit.
    """
    warning_count  = sum(1 for d in run.discrepancies if d.severity == "warning")
    critical_count = sum(1 for d in run.discrepancies if d.severity == "critical")
    info_count     = sum(1 for d in run.discrepancies if d.severity == "info")

    metadata = {
        "execution_log": [
            {
                "rule_type":  log.rule_type,
                "rule_name":  log.rule_name,
                "fired":      log.fired,
                "elapsed_ms": log.elapsed_ms,
                "error":      log.error,
            }
            for log in run.execution_log
        ],
        "loaded_transactions": run.loaded_transactions,
        "loaded_fees":         run.loaded_fees,
    }

    result = ReconciliationResult(
        id=uuid.uuid4(),
        settlement_id=run.settlement_id,
        company_id=run.company_id,
        platform=run.platform,
        status=run.status,
        total_discrepancies=len(run.discrepancies),
        warning_count=warning_count,
        critical_count=critical_count,
        info_count=info_count,
        total_variance_amount=run.total_variance_amount,
        rules_evaluated=run.rules_evaluated,
        processing_time_ms=run.processing_time_ms,
        error_message=run.error_message,
        metadata_json=json.dumps(metadata),
    )
    db.add(result)
    await db.flush()   # assign result.id before inserting discrepancies

    for d in run.discrepancies:
        event = DiscrepancyEvent(
            id=uuid.uuid4(),
            result_id=result.id,
            settlement_id=run.settlement_id,
            transaction_id=d.transaction_id,
            company_id=run.company_id,
            rule_id=d.rule_id,
            platform=run.platform,
            discrepancy_type=d.discrepancy_type,
            severity=d.severity,
            expected_amount=d.expected_amount,
            actual_amount=d.actual_amount,
            variance_amount=d.variance_amount,
            description=d.description,
            order_id=d.order_id,
            fee_type=d.fee_type,
            metadata_json=json.dumps(d.metadata) if d.metadata else None,
            is_resolved=False,
            created_at=datetime.utcnow(),
        )
        db.add(event)

    return result


async def load_result_with_discrepancies(
    db: AsyncSession,
    result_id: UUID,
) -> ReconciliationResult | None:
    res = await db.execute(
        select(ReconciliationResult)
        .options(selectinload(ReconciliationResult.discrepancies))
        .where(ReconciliationResult.id == result_id)
    )
    return res.scalar_one_or_none()
