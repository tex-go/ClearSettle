"""
Settlement ingestion pipeline.

Architecture
------------
Raw layer    → fetcher.py fetches raw API dicts (no transformation)
Parse layer  → parser.py converts raw dicts → NormalizedSettlement dataclasses
Storage layer → storage.py persists with UPSERT duplicate protection
Pipeline     → pipeline.py orchestrates all three layers

Extensibility
-------------
Each platform gets its own sub-package (amazon/, flipkart/, meesho/).
The sub-package exposes:
  fetcher.fetch_settlements(client, ...) → list[dict]
  parser.parse(raw_group, raw_events)   → NormalizedSettlement

storage.py and pipeline.py are platform-agnostic.
"""

from app.services.ingestion.models import (   # noqa: F401 — public API
    IngestionResult,
    NormalizedFee,
    NormalizedSettlement,
    NormalizedTransaction,
)
