"""Pipeline router: auto-detection → parser routing → ledger ingestion."""
from app.services.pipeline.router import run_ingestion_pipeline, PipelineResult

__all__ = ["run_ingestion_pipeline", "PipelineResult"]
