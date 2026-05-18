"""In-process async event bus for reconciliation job progress events.

Architecture
------------
Each job has a list of subscriber asyncio.Queue objects.
The engine calls `emit()` at every meaningful stage transition.
SSE endpoints subscribe via `subscribe()`, replay history on connect,
then stream live events until the client disconnects.

History buffer (maxlen=200) lets clients that connect mid-run catch up
without replaying events from previous runs.

Platform portability
--------------------
This module has zero browser/HTTP dependencies.  The event contract
(plain dicts) is identical to the JSON payloads the SSE endpoint
serialises — so the same schema can be used for WebSocket,
gRPC streaming, or mobile push once those transports are added.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Any

# job_id (str) → list of subscriber queues
_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

# job_id → deque of recent events (replay buffer for late clients)
_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

# sentinel placed in queue when the job finishes
_DONE = object()


async def emit(job_id: Any, event: dict) -> None:
    """Broadcast an event to all subscribers of a job.

    Also appends to the history buffer so clients that connect after
    the event was fired can still receive it.
    """
    key = str(job_id)
    _history[key].append(event)
    for q in list(_subscribers[key]):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
    # Yield to allow SSE sender coroutines to flush their buffers.
    await asyncio.sleep(0)


async def close(job_id: Any) -> None:
    """Signal all subscribers that the job stream has ended."""
    key = str(job_id)
    for q in list(_subscribers[key]):
        try:
            q.put_nowait(_DONE)
        except asyncio.QueueFull:
            pass
    await asyncio.sleep(0)


def subscribe(job_id: Any) -> tuple[asyncio.Queue, list[dict]]:
    """Register a new SSE subscriber.

    Returns:
        (queue, history): The subscriber queue and all events emitted
        so far for this job (for replay on connect).
    """
    key = str(job_id)
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers[key].append(q)
    history = list(_history[key])
    return q, history


def unsubscribe(job_id: Any, q: asyncio.Queue) -> None:
    """Remove a subscriber queue (called when SSE client disconnects)."""
    key = str(job_id)
    subs = _subscribers[key]
    try:
        subs.remove(q)
    except ValueError:
        pass
    if not subs:
        _subscribers.pop(key, None)


def is_done(item: Any) -> bool:
    return item is _DONE
