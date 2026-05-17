"""
Settlement ingestion pipeline — orchestrates fetcher → parser → storage.

Entry point: ingest_settlements()

The pipeline is platform-aware at the fetching+parsing stage (each platform
has its own sub-package) and platform-agnostic at the storage stage.
"""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.platform_connection import PlatformConnection
from app.db.models.sync_job import SyncJob
from app.services.amazon.sp_api_client import SPAPIClient
from app.services.ingestion.amazon import fetcher, parser
from app.services.ingestion.models import IngestionResult
from app.services.ingestion import storage
from app.services.sync import job_manager

logger = logging.getLogger(__name__)


async def ingest_settlements(
    client:        SPAPIClient,
    connection:    PlatformConnection,
    company_id:    UUID,
    db:            AsyncSession,
    *,
    days_back:     int = 30,
    job:           SyncJob | None = None,
) -> IngestionResult:
    """
    Full settlement ingestion pipeline.

    Steps per group:
      1. Fetch raw financial event group metadata
      2. Fetch individual financial events for that group
      3. Parse raw data → NormalizedSettlement
      4. Upsert settlement row (duplicate protection)
      5. Upsert transactions (bulk ON CONFLICT DO UPDATE)
      6. Replace fees (delete-then-insert)
      7. Update settlement summary counts
      8. Upsert payout event (for closed settlements)

    Returns an IngestionResult with counts of created/updated rows.
    """
    result = IngestionResult()
    platform = connection.platform or "amazon"

    if job:
        await job_manager.add_log(
            db, job, "info",
            f"Fetching settlement groups (last {days_back} days)",
        )

    # ── Step 1: Fetch settlement groups ──────────────────────────────────────
    raw_groups = fetcher.fetch_settlement_groups(client, days_back=days_back)

    if job:
        await job_manager.add_log(
            db, job, "info",
            f"Found {len(raw_groups)} settlement groups",
            context={"count": len(raw_groups)},
        )

    for raw_group in raw_groups:
        group_id = raw_group.get("FinancialEventGroupId", "unknown")

        try:
            await _ingest_one_group(
                db=db,
                client=client,
                raw_group=raw_group,
                company_id=company_id,
                connection_id=connection.id,
                platform=platform,
                result=result,
                job=job,
            )
        except Exception as exc:
            logger.error("Failed to ingest group %s: %s", group_id, exc)
            result.skipped += 1
            if job:
                await job_manager.add_log(
                    db, job, "error",
                    f"Failed to ingest group {group_id}: {exc}",
                )

    if job:
        await job_manager.add_log(
            db, job, "info",
            "Ingestion complete",
            context={
                "settlements_created":  result.settlements_created,
                "settlements_updated":  result.settlements_updated,
                "transactions_created": result.transactions_created,
                "fees_created":         result.fees_created,
                "payouts_created":      result.payouts_created,
                "skipped":              result.skipped,
            },
        )

    return result


async def _ingest_one_group(
    *,
    db:            AsyncSession,
    client:        SPAPIClient,
    raw_group:     dict,
    company_id:    UUID,
    connection_id: UUID,
    platform:      str,
    result:        IngestionResult,
    job:           SyncJob | None,
) -> None:
    group_id    = raw_group.get("FinancialEventGroupId", "")
    proc_status = (raw_group.get("ProcessingStatus") or "").lower()

    # ── Step 2: Fetch events ──────────────────────────────────────────────────
    raw_events = fetcher.fetch_events_for_group(client, group_id)

    # ── Step 3: Parse ─────────────────────────────────────────────────────────
    normalized = parser.parse_settlement(raw_group, raw_events)

    if job:
        await job_manager.add_log(
            db, job, "info",
            f"Parsed group {group_id[:12]}… ({proc_status}): "
            f"{len(normalized.transactions)} transactions",
            context={"group_id": group_id, "transaction_count": len(normalized.transactions)},
        )

    # ── Step 4: Upsert settlement ──────────────────────────────────────────────
    settlement, created = await storage.upsert_settlement(
        db,
        company_id=company_id,
        connection_id=connection_id,
        platform=platform,
        normalized=normalized,
    )
    if created:
        result.settlements_created += 1
    else:
        result.settlements_updated += 1

    # ── Step 5: Upsert transactions ────────────────────────────────────────────
    n_txns = await storage.upsert_transactions(
        db,
        settlement=settlement,
        company_id=company_id,
        platform=platform,
        transactions=normalized.transactions,
    )
    result.transactions_created += n_txns

    # ── Step 6: Replace fees ──────────────────────────────────────────────────
    n_fees = await storage.replace_fees(
        db,
        settlement=settlement,
        company_id=company_id,
        platform=platform,
        transactions=normalized.transactions,
    )
    result.fees_created += n_fees

    # ── Step 7: Update settlement summary ──────────────────────────────────────
    await storage.update_settlement_summaries(db, settlement)

    # ── Step 8: Upsert payout (closed settlements only) ────────────────────────
    if normalized.status == "closed":
        _, payout_created = await storage.upsert_payout(
            db,
            settlement=settlement,
            company_id=company_id,
            connection_id=connection_id,
            platform=platform,
            normalized=normalized,
        )
        if payout_created:
            result.payouts_created += 1

    # Commit the entire group atomically
    await db.commit()
