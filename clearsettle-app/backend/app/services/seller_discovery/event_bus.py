"""
In-process async event bus for discovery job progress events.

Identical architecture to app.services.vendor_recon.event_bus.
One bus instance per process; keyed by job_id string.

Event schema (all fields are strings or primitives):
  {"type": "job_started",    "job_id": str, "keyword": str, "strategy": str}
  {"type": "profile_found",  "username": str, "followers": int|None}
  {"type": "lead_created",   "username": str, "lead_id": str}
  {"type": "lead_duplicate", "username": str}
  {"type": "lead_skipped",   "username": str, "reason": str}
  {"type": "progress",       "leads_found": int, "leads_created": int, "leads_dupes": int}
  {"type": "blocked",        "message": str}
  {"type": "job_completed",  "leads_found": int, "leads_created": int}
  {"type": "job_failed",     "error": str}
  {"type": "stream_end"}
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Any

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
_history:     dict[str, deque]               = defaultdict(lambda: deque(maxlen=300))
_DONE = object()


async def emit(job_id: Any, event: dict) -> None:
    key = str(job_id)
    _history[key].append(event)
    for q in list(_subscribers[key]):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
    await asyncio.sleep(0)   # yield so SSE senders can flush


async def close(job_id: Any) -> None:
    key = str(job_id)
    for q in list(_subscribers[key]):
        try:
            q.put_nowait(_DONE)
        except asyncio.QueueFull:
            pass
    await asyncio.sleep(0)


def subscribe(job_id: Any) -> tuple[asyncio.Queue, list[dict]]:
    key = str(job_id)
    q: asyncio.Queue = asyncio.Queue(maxsize=300)
    _subscribers[key].append(q)
    history = list(_history[key])
    return q, history


def unsubscribe(job_id: Any, q: asyncio.Queue) -> None:
    key  = str(job_id)
    subs = _subscribers[key]
    try:
        subs.remove(q)
    except ValueError:
        pass
    if not subs:
        _subscribers.pop(key, None)


def is_done(item: Any) -> bool:
    return item is _DONE
