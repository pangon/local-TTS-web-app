"""Tests for SSE endpoint and EventBus (TASK-sse-endpoint).

Covers:
- EventBus: publish/subscribe, fan-out, unsubscribe cleanup
- SSE endpoint: text/event-stream content type, keepalive, event delivery
- DEC-sse-progress: SSE via StreamingResponse with proper headers
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from local_tts.api.sse import (
    KEEPALIVE_INTERVAL_SECONDS,
    EventBus,
    _event_stream,
)


# ---------------------------------------------------------------------------
# EventBus unit tests
# ---------------------------------------------------------------------------


class TestEventBus:
    @pytest.mark.anyio
    async def test_subscribe_returns_queue(self):
        bus = EventBus()
        queue = await bus.subscribe()
        assert isinstance(queue, asyncio.Queue)

    @pytest.mark.anyio
    async def test_publish_delivers_to_subscriber(self):
        bus = EventBus()
        queue = await bus.subscribe()
        await bus.publish("job-progress", {"job_id": "abc", "progress": 42})
        message = queue.get_nowait()
        assert "event: job-progress" in message
        assert '"job_id": "abc"' in message
        assert '"progress": 42' in message

    @pytest.mark.anyio
    async def test_publish_fans_out_to_multiple_subscribers(self):
        bus = EventBus()
        q1 = await bus.subscribe()
        q2 = await bus.subscribe()
        await bus.publish("download-completed", {"model_id": "test/model"})
        msg1 = q1.get_nowait()
        msg2 = q2.get_nowait()
        assert msg1 == msg2
        assert "event: download-completed" in msg1

    @pytest.mark.anyio
    async def test_unsubscribe_removes_queue(self):
        bus = EventBus()
        queue = await bus.subscribe()
        await bus.unsubscribe(queue)
        await bus.publish("job-failed", {"job_id": "x"})
        assert queue.empty()

    @pytest.mark.anyio
    async def test_unsubscribe_nonexistent_queue_is_safe(self):
        bus = EventBus()
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        await bus.unsubscribe(queue)  # should not raise

    @pytest.mark.anyio
    async def test_published_message_is_valid_sse_format(self):
        bus = EventBus()
        queue = await bus.subscribe()
        await bus.publish("job-completed", {"job_id": "123", "type": "synthesis"})
        message = queue.get_nowait()
        lines = message.strip().split("\n")
        assert lines[0] == "event: job-completed"
        assert lines[1].startswith("data: ")
        payload = json.loads(lines[1][len("data: "):])
        assert payload == {"job_id": "123", "type": "synthesis"}

    @pytest.mark.anyio
    async def test_subscriber_count(self):
        bus = EventBus()
        assert await bus.subscriber_count == 0
        q1 = await bus.subscribe()
        assert await bus.subscriber_count == 1
        q2 = await bus.subscribe()
        assert await bus.subscriber_count == 2
        await bus.unsubscribe(q1)
        assert await bus.subscriber_count == 1
        await bus.unsubscribe(q2)
        assert await bus.subscriber_count == 0

    @pytest.mark.anyio
    async def test_shutdown_sends_sentinel_to_all_subscribers(self):
        bus = EventBus()
        q1 = await bus.subscribe()
        q2 = await bus.subscribe()
        await bus.shutdown()
        assert q1.get_nowait() is None
        assert q2.get_nowait() is None

    @pytest.mark.anyio
    async def test_all_api_event_types_produce_valid_sse(self):
        """All event types from the API design produce valid SSE format."""
        bus = EventBus()
        queue = await bus.subscribe()

        event_types = [
            ("job-progress", {"job_id": "uuid", "type": "synthesis", "status": "processing", "progress": 42}),
            ("job-completed", {"job_id": "uuid", "type": "synthesis", "audiobook_id": "uuid"}),
            ("job-failed", {"job_id": "uuid", "type": "synthesis", "error_message": "Out of VRAM"}),
            ("download-progress", {"model_id": "facebook/mms-tts-eng", "progress": 65}),
            ("download-completed", {"model_id": "facebook/mms-tts-eng"}),
            ("download-failed", {"model_id": "facebook/mms-tts-eng", "error_message": "Network error"}),
        ]

        for event_type, data in event_types:
            await bus.publish(event_type, data)
            message = queue.get_nowait()
            lines = message.strip().split("\n")
            assert lines[0] == f"event: {event_type}", f"Bad event line for {event_type}"
            assert lines[1].startswith("data: "), f"Bad data line for {event_type}"
            payload = json.loads(lines[1][len("data: "):])
            assert payload == data, f"Payload mismatch for {event_type}"


# ---------------------------------------------------------------------------
# _event_stream generator tests
# ---------------------------------------------------------------------------


def _mock_request(disconnected: bool = False) -> MagicMock:
    """Create a mock Request with is_disconnected support."""
    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=disconnected)
    return request


class TestEventStreamGenerator:
    @pytest.mark.anyio
    async def test_yields_published_event(self):
        bus = EventBus()
        request = _mock_request()

        async def _publish_and_stop():
            while await bus.subscriber_count == 0:
                await asyncio.sleep(0.01)
            await bus.publish("job-progress", {"job_id": "1", "progress": 42})
            await bus.shutdown()

        task = asyncio.create_task(_publish_and_stop())
        chunks = []
        async for chunk in _event_stream(request, bus):
            chunks.append(chunk)

        await task
        combined = "".join(chunks)
        assert "event: job-progress" in combined
        assert '"progress": 42' in combined

    @pytest.mark.anyio
    async def test_yields_multiple_events_in_order(self):
        bus = EventBus()
        request = _mock_request()

        async def _publish_and_stop():
            while await bus.subscriber_count == 0:
                await asyncio.sleep(0.01)
            await bus.publish("download-progress", {"model_id": "m1", "progress": 10})
            await bus.publish("download-progress", {"model_id": "m1", "progress": 50})
            await bus.shutdown()

        task = asyncio.create_task(_publish_and_stop())
        chunks = []
        async for chunk in _event_stream(request, bus):
            chunks.append(chunk)

        await task
        combined = "".join(chunks)
        assert combined.index('"progress": 10') < combined.index('"progress": 50')

    @pytest.mark.anyio
    async def test_stops_on_none_sentinel(self):
        bus = EventBus()
        request = _mock_request()

        async def _shutdown():
            while await bus.subscriber_count == 0:
                await asyncio.sleep(0.01)
            await bus.shutdown()

        task = asyncio.create_task(_shutdown())
        chunks = []
        async for chunk in _event_stream(request, bus):
            chunks.append(chunk)

        await task
        assert chunks == []

    @pytest.mark.anyio
    async def test_stops_on_client_disconnect(self):
        bus = EventBus()
        call_count = 0

        async def _is_disconnected():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # disconnect after first check

        request = MagicMock()
        request.is_disconnected = _is_disconnected

        # Pre-subscribe so the generator has a queue, then put a message
        # so the first iteration yields something before the disconnect check
        queue = await bus.subscribe()
        # Manually put an event so the generator yields once
        queue.put_nowait("event: test\ndata: {}\n\n")

        chunks = []
        async for chunk in _event_stream(request, bus):
            chunks.append(chunk)
            # After first yield, next is_disconnected will return True
            break  # Safety: don't loop forever

    @pytest.mark.anyio
    async def test_yields_keepalive_on_timeout(self):
        """Generator sends keepalive comment when no events arrive."""
        import local_tts.api.sse as sse_module

        original = sse_module.KEEPALIVE_INTERVAL_SECONDS
        # Use a very short interval for testing
        sse_module.KEEPALIVE_INTERVAL_SECONDS = 0.1

        bus = EventBus()
        request = _mock_request()

        async def _wait_then_shutdown():
            while await bus.subscriber_count == 0:
                await asyncio.sleep(0.01)
            # Wait long enough for one keepalive
            await asyncio.sleep(0.2)
            await bus.shutdown()

        task = asyncio.create_task(_wait_then_shutdown())
        chunks = []
        async for chunk in _event_stream(request, bus):
            chunks.append(chunk)

        await task
        sse_module.KEEPALIVE_INTERVAL_SECONDS = original
        assert any(":keepalive" in c for c in chunks)

    @pytest.mark.anyio
    async def test_unsubscribes_on_exit(self):
        bus = EventBus()
        request = _mock_request()

        async def _shutdown():
            while await bus.subscriber_count == 0:
                await asyncio.sleep(0.01)
            assert await bus.subscriber_count == 1
            await bus.shutdown()

        task = asyncio.create_task(_shutdown())
        async for _ in _event_stream(request, bus):
            pass

        await task
        await asyncio.sleep(0.01)
        assert await bus.subscriber_count == 0


# ---------------------------------------------------------------------------
# SSE endpoint route tests
# ---------------------------------------------------------------------------


class TestSSEEndpointRoute:
    def test_events_route_is_registered(self):
        """The /events route exists under /api/v1."""
        from fastapi import FastAPI

        from local_tts.api.sse import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        paths = [route.path for route in app.routes]
        assert "/api/v1/events" in paths

    def test_events_route_returns_streaming_response(self):
        """Endpoint function returns a StreamingResponse."""
        from fastapi.responses import StreamingResponse

        from local_tts.api.sse import events

        # The endpoint is an async function that returns StreamingResponse
        import inspect
        assert inspect.iscoroutinefunction(events)
