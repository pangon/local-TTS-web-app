"""Server-Sent Events endpoint and in-memory event bus (DEC-sse-progress).

Provides a single SSE endpoint at /events that streams all real-time
server-to-client updates. Application services publish events via the
EventBus; connected clients receive them as SSE messages.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

KEEPALIVE_INTERVAL_SECONDS = 15

router = APIRouter()


class EventBus:
    """In-memory pub/sub event bus for SSE broadcasting (DEC-single-process).

    Services publish typed events via :meth:`publish`. Each connected SSE
    client gets its own asyncio.Queue; events are fanned out to all queues.
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[str | None]] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str | None]:
        """Register a new subscriber and return its queue.

        The queue yields formatted SSE strings ready for writing to the
        response stream. A ``None`` sentinel signals the subscriber to
        disconnect.
        """
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[str | None]) -> None:
        """Remove a subscriber queue."""
        async with self._lock:
            try:
                self._subscribers.remove(queue)
            except ValueError:
                pass

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast a typed event to all connected clients.

        Parameters
        ----------
        event_type:
            SSE event name (e.g. ``job-progress``, ``download-completed``).
        data:
            JSON-serialisable payload.
        """
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        async with self._lock:
            count = len(self._subscribers)
            if count == 0:
                logger.warning(
                    "SSE event '%s' published but no subscribers connected",
                    event_type,
                )
            for queue in self._subscribers:
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("Dropping SSE event for slow subscriber")

    async def shutdown(self) -> None:
        """Send a stop sentinel to all subscribers, causing their generators to exit."""
        async with self._lock:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass

    @property
    async def subscriber_count(self) -> int:
        async with self._lock:
            return len(self._subscribers)


async def _event_stream(
    request: Request,
    event_bus: EventBus,
) -> Any:
    """Async generator that yields SSE messages with keepalive."""
    queue = await event_bus.subscribe()
    subscriber_count = len(event_bus._subscribers)
    logger.info("SSE client connected (total subscribers: %d)", subscriber_count)
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(
                    queue.get(), timeout=KEEPALIVE_INTERVAL_SECONDS
                )
                if message is None:
                    break
                yield message
            except asyncio.TimeoutError:
                yield ":keepalive\n\n"
    finally:
        await event_bus.unsubscribe(queue)
        logger.info("SSE client disconnected")


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    """SSE endpoint for all real-time server-to-client updates.

    The client connects once and filters events by type. Automatic
    reconnection is handled by the browser EventSource API.
    """
    event_bus: EventBus = request.app.state.event_bus
    return StreamingResponse(
        _event_stream(request, event_bus),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
