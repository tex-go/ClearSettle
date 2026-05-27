"""
Sync orchestrators — one async function per job type.

Each function:
  1. Opens its own DB session (runs in a background task, outside request context).
  2. Marks the job running via job_manager.
  3. Refreshes the SP API access token.
  4. Calls the relevant SP API function.
  5. Updates job state and connection metadata via job_manager.
  6. Logs progress at each step.

Error classification
--------------------
  AuthError          → terminal failure (retryable=False) — re-auth needed
  TransientError     → retryable (retryable=True) — network / 5xx
  SpApiError (other) → retryable by default
  Exception          → terminal (unexpected, don't retry blindly)
"""
import logging
from datetime import datetime
from uuid import UUID

from app.db.database import AsyncSessionLocal
from app.db.models.platform_connection import PlatformConnection
from app.services.amazon.auth import get_valid_access_token
from app.services.amazon.finances import get_financial_event_groups
from app.services.amazon.orders import get_orders
from app.services.amazon.sp_api_client import AuthError, SPAPIClient, SpApiError, TransientError
from app.services.ingestion import pipeline as ingestion_pipeline
from app.services.sync import job_manager

logger = logging.getLogger(__name__)


async def run_orders_sync(job_id: str) -> None:
    """Fetch orders from Amazon SP API and update job state."""
    if not AsyncSessionLocal:
        return

    async with AsyncSessionLocal() as db:
        job = await job_manager.get_job(db, UUID(job_id))
        if not job:
            logger.error("run_orders_sync: job %s not found", job_id)
            return

        conn: PlatformConnection | None = await db.get(PlatformConnection, job.connection_id)
        if not conn:
            await job_manager.fail_job(db, job, error="Connection not found", retryable=False)
            return

        options   = job_manager.parse_options(job)
        days_back = options.get("days_back", 30)

        await job_manager.start_job(db, job)
        await job_manager.add_log(db, job, "info", f"Starting orders sync (last {days_back} days)")

        try:
            get_valid_access_token(conn)   # mutates conn; commit below persists the token
            db.add(conn)
            await db.commit()

            await job_manager.add_log(db, job, "info", "Access token refreshed; calling Orders API")

            orders = get_orders(SPAPIClient(conn), days_back=days_back)

            await job_manager.add_log(
                db, job, "info",
                f"Fetched {len(orders)} orders from Amazon",
                context={"count": len(orders), "days_back": days_back},
            )

            conn.last_sync_at        = datetime.utcnow()
            conn.last_sync_error     = None
            conn.total_orders_synced = (conn.total_orders_synced or 0) + len(orders)
            db.add(conn)

            # complete_job commits both job completion and conn update in one shot
            await job_manager.complete_job(db, job, records_created=len(orders))

        except AuthError as exc:
            conn.last_sync_error = str(exc)
            db.add(conn)
            await job_manager.add_log(db, job, "error", f"Auth failure: {exc}")
            await job_manager.fail_job(db, job, error=str(exc), retryable=False)

        except (TransientError, SpApiError) as exc:
            conn.last_sync_error = str(exc)
            db.add(conn)
            await job_manager.add_log(db, job, "error", f"SP API error: {exc}")
            await job_manager.fail_job(db, job, error=str(exc), retryable=True)

        except Exception as exc:
            logger.exception("Unexpected error in orders sync job %s", job_id)
            conn.last_sync_error = str(exc)
            db.add(conn)
            await job_manager.add_log(db, job, "error", f"Unexpected error: {exc}")
            await job_manager.fail_job(db, job, error=str(exc), retryable=False)


async def run_settlements_sync(job_id: str) -> None:
    """
    Full settlement ingestion pipeline for Amazon SP API.

    Calls ingestion_pipeline.ingest_settlements() which handles:
    fetch → parse → normalize → upsert settlements/transactions/fees/payouts.
    """
    if not AsyncSessionLocal:
        return

    async with AsyncSessionLocal() as db:
        job = await job_manager.get_job(db, UUID(job_id))
        if not job:
            logger.error("run_settlements_sync: job %s not found", job_id)
            return

        conn: PlatformConnection | None = await db.get(PlatformConnection, job.connection_id)
        if not conn:
            await job_manager.fail_job(db, job, error="Connection not found", retryable=False)
            return

        options   = job_manager.parse_options(job)
        days_back = options.get("days_back", 30)

        await job_manager.start_job(db, job)
        await job_manager.add_log(db, job, "info", f"Starting settlement ingestion (last {days_back} days)")

        try:
            get_valid_access_token(conn)   # refresh token; commit persists it
            db.add(conn)
            await db.commit()

            await job_manager.add_log(db, job, "info", "Access token refreshed; running ingestion pipeline")

            ingest_result = await ingestion_pipeline.ingest_settlements(
                client=SPAPIClient(conn),
                connection=conn,
                company_id=job.company_id,
                db=db,
                days_back=days_back,
                job=job,
            )

            conn.last_sync_at    = datetime.utcnow()
            conn.last_sync_error = None
            db.add(conn)

            await job_manager.complete_job(
                db, job,
                records_created=ingest_result.settlements_created + ingest_result.transactions_created,
                records_updated=ingest_result.settlements_updated,
            )
            logger.info(
                "Settlement ingestion done: %d settlements, %d transactions, %d fees — job %s",
                ingest_result.settlements_created + ingest_result.settlements_updated,
                ingest_result.transactions_created,
                ingest_result.fees_created,
                job_id,
            )

        except AuthError as exc:
            conn.last_sync_error = str(exc)
            db.add(conn)
            await job_manager.add_log(db, job, "error", f"Auth failure: {exc}")
            await job_manager.fail_job(db, job, error=str(exc), retryable=False)

        except (TransientError, SpApiError) as exc:
            conn.last_sync_error = str(exc)
            db.add(conn)
            await job_manager.add_log(db, job, "error", f"SP API error: {exc}")
            await job_manager.fail_job(db, job, error=str(exc), retryable=True)

        except Exception as exc:
            logger.exception("Unexpected error in settlements sync job %s", job_id)
            conn.last_sync_error = str(exc)
            db.add(conn)
            await job_manager.add_log(db, job, "error", f"Unexpected error: {exc}")
            await job_manager.fail_job(db, job, error=str(exc), retryable=False)
