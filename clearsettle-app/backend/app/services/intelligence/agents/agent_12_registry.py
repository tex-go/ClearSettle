"""
Agent 12: Report Schema Registry.

Checks if the detected schema version exists in the ReportSchemaVersion DB table.
If it is a new schema (drift detected), registers it.

This is an async agent — call run_async() instead of run().
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Optional

from app.services.intelligence.models import AgentStatus, RegistryResult


class AgentRegistry:
    AGENT_ID = 12
    AGENT_NAME = "Agent 12: Report Registry"

    async def run_async(self, context: dict) -> RegistryResult:
        start = time.time()
        try:
            result = await self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return RegistryResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                schema_registered=False,
                schema_version="unknown",
                is_new_schema=False,
                variants_known=0,
                registry_id=None,
            )

    # Synchronous fallback used by pipeline when DB is not injected
    def run(self, context: dict) -> RegistryResult:
        start = time.time()
        schema_result = context.get("schema")
        schema_version = (schema_result.schema_version if schema_result else "unknown") or "unknown"
        drift_detected = schema_result.drift_detected if schema_result else False

        return RegistryResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=AgentStatus.skipped,
            duration_ms=(time.time() - start) * 1000,
            messages=["Registry agent requires async DB context — running in stub mode."],
            schema_registered=False,
            schema_version=schema_version,
            is_new_schema=drift_detected,
            variants_known=0,
            registry_id=None,
        )

    async def _process(self, context: dict) -> RegistryResult:
        db = context.get("db")
        schema_result = context.get("schema")
        platform_result = context.get("platform")
        classification_result = context.get("classification")
        fp = context.get("fingerprint")

        schema_version = (schema_result.schema_version if schema_result else "unknown") or "unknown"
        drift_detected = schema_result.drift_detected if schema_result else False
        platform = (platform_result.platform if platform_result else "unknown")
        report_type = (classification_result.report_type if classification_result else "unknown")
        messages = []

        if db is None:
            return RegistryResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=["No DB session — registry check skipped."],
                schema_registered=False,
                schema_version=schema_version,
                is_new_schema=drift_detected,
                variants_known=0,
                registry_id=None,
            )

        try:
            from sqlalchemy import select, func
            from app.db.models.ingestion import ReportSchemaVersion

            # Count known variants for this platform+report_type
            variants_count_result = await db.execute(
                select(func.count()).where(
                    ReportSchemaVersion.platform == platform,
                    ReportSchemaVersion.report_type == report_type,
                )
            )
            variants_known = variants_count_result.scalar_one() or 0

            registry_id: Optional[str] = None
            is_new_schema = False

            if drift_detected and fp:
                # Check if this signature is already registered
                existing = (await db.execute(
                    select(ReportSchemaVersion).where(
                        ReportSchemaVersion.platform == platform,
                        ReportSchemaVersion.report_type == report_type,
                        ReportSchemaVersion.schema_signature == fp.schema_signature,
                    )
                )).scalar_one_or_none()

                if not existing:
                    is_new_schema = True
                    new_version = f"{platform}_{report_type}_v{variants_known + 1}_auto"
                    new_schema = ReportSchemaVersion(
                        id=uuid.uuid4(),
                        platform=platform,
                        report_type=report_type,
                        schema_version=new_version,
                        schema_signature=fp.schema_signature,
                        expected_columns=fp.all_column_names[:50],
                        optional_columns=[],
                        parser_name=None,
                        is_active=False,  # requires manual activation
                        first_seen_at=datetime.utcnow(),
                        created_at=datetime.utcnow(),
                    )
                    db.add(new_schema)
                    await db.commit()
                    await db.refresh(new_schema)
                    registry_id = str(new_schema.id)
                    messages.append(f"New schema registered as '{new_version}' (pending activation).")
                    variants_known += 1
                else:
                    registry_id = str(existing.id)
                    messages.append(f"Schema signature already registered as '{existing.schema_version}'.")
                    schema_version = existing.schema_version

            return RegistryResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.success,
                duration_ms=0.0,
                messages=messages,
                schema_registered=True,
                schema_version=schema_version,
                is_new_schema=is_new_schema,
                variants_known=variants_known,
                registry_id=registry_id,
            )

        except Exception as e:
            return RegistryResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.warning,
                duration_ms=0.0,
                messages=[f"Registry DB error (non-fatal): {e}"],
                schema_registered=False,
                schema_version=schema_version,
                is_new_schema=drift_detected,
                variants_known=0,
                registry_id=None,
            )
