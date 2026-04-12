"""Tests for job progress SSE wiring (TASK-job-progress-sse).

Covers:
- _wire_job_callbacks connects all three JobService callbacks
- on_progress publishes job-progress event with correct payload
- on_completed publishes job-completed event with correct payload
- on_failed publishes job-failed event with correct payload
- Integration: background job processing publishes SSE events end-to-end

Acceptance criteria (REQ-F-synthesis-progress):
- Job status (queued, processing, completed, or failed) visible via SSE
- Progress indicator (percentage) visible via SSE during processing
- Error message visible via SSE when job fails
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from local_tts.api.sse import EventBus
from local_tts.app import _publish_from_thread, _wire_job_callbacks
from local_tts.db import init_db
from local_tts.services.job_service import JobService, SynthesisJobResult
from local_tts.tts.synthesizer import SynthesisResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture()
def tmp_data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture()
def db_conn(tmp_data_dir: Path):
    conn = init_db(tmp_data_dir)
    yield conn
    conn.close()


@pytest.fixture()
def mock_tts_engine() -> MagicMock:
    engine = MagicMock()
    engine.loaded_model_id = "hexgrad/Kokoro-82M"
    engine.synthesize.return_value = [
        SynthesisResult(chapter_number=1, title="Chapter 1", audio_filename="chapter-01.mp3", duration_seconds=60.0),
    ]
    return engine


@pytest.fixture()
def job_service(mock_tts_engine: MagicMock, db_conn, tmp_data_dir: Path):
    svc = JobService(mock_tts_engine, db_conn, tmp_data_dir)
    yield svc
    svc.shutdown()


@pytest.fixture()
def mock_library_service() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse_message(raw: str) -> tuple[str, dict]:
    """Parse a raw SSE message into (event_type, data_dict)."""
    lines = raw.strip().split("\n")
    event_type = lines[0].removeprefix("event: ")
    data = json.loads(lines[1].removeprefix("data: "))
    return event_type, data


async def _drain_queue(
    queue: asyncio.Queue[str | None],
    timeout: float = 5.0,
    stop_after: int | None = None,
) -> list[tuple[str, dict]]:
    """Collect SSE messages from a subscriber queue until timeout or count reached."""
    events = []
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            msg = await asyncio.wait_for(queue.get(), timeout=min(remaining, 0.5))
            if msg is None:
                break
            events.append(_parse_sse_message(msg))
            if stop_after and len(events) >= stop_after:
                break
        except asyncio.TimeoutError:
            if stop_after is None:
                break
            continue
    return events


def _wait_for_job_status(
    service: JobService,
    job_id: str,
    target_status: str,
    timeout: float = 5.0,
) -> None:
    """Poll until a job reaches the target status or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = service.get_job(job_id)
        if job and job.status == target_status:
            return
        time.sleep(0.05)
    job = service.get_job(job_id)
    raise TimeoutError(
        f"Job {job_id} did not reach status '{target_status}' within {timeout}s. "
        f"Current status: {job.status if job else 'not found'}"
    )


# ---------------------------------------------------------------------------
# Unit tests: _publish_from_thread
# ---------------------------------------------------------------------------


class TestPublishFromThread:
    @pytest.mark.anyio
    async def test_publishes_event_to_bus(self, event_bus: EventBus):
        queue = await event_bus.subscribe()
        loop = asyncio.get_running_loop()

        _publish_from_thread(event_bus, loop, "job-progress", {
            "job_id": "abc", "type": "synthesis", "status": "processing", "progress": 42,
        })

        # Allow coroutine to run
        await asyncio.sleep(0.1)

        msg = queue.get_nowait()
        event_type, data = _parse_sse_message(msg)
        assert event_type == "job-progress"
        assert data["job_id"] == "abc"
        assert data["progress"] == 42


# ---------------------------------------------------------------------------
# Unit tests: _wire_job_sse
# ---------------------------------------------------------------------------


class TestWireJobCallbacks:
    @pytest.mark.anyio
    async def test_wires_all_three_callbacks(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        assert job_service.on_progress is None
        assert job_service.on_completed is None
        assert job_service.on_failed is None

        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        assert job_service.on_progress is not None
        assert job_service.on_completed is not None
        assert job_service.on_failed is not None

    @pytest.mark.anyio
    async def test_on_progress_publishes_job_progress_event(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job_service.on_progress("job-123", "synthesis", 42)
        await asyncio.sleep(0.1)

        event_type, data = _parse_sse_message(queue.get_nowait())
        assert event_type == "job-progress"
        assert data == {
            "job_id": "job-123",
            "type": "synthesis",
            "status": "processing",
            "progress": 42,
        }

    @pytest.mark.anyio
    async def test_on_completed_publishes_job_completed_event(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        result = SynthesisJobResult(
            job_id="job-456",
            audiobook_id="book-789",
            source_filename="my-book.txt",
            model_id="hexgrad/Kokoro-82M",
            voice="af_heart",
            language="en",
            chapter_results=[
                SynthesisResult(chapter_number=1, title="Chapter 1", audio_filename="ch01.mp3", duration_seconds=60.0),
            ],
        )
        job_service.on_completed(result)
        await asyncio.sleep(0.1)

        event_type, data = _parse_sse_message(queue.get_nowait())
        assert event_type == "job-completed"
        assert data == {
            "job_id": "job-456",
            "type": "synthesis",
            "audiobook_id": "book-789",
        }

    @pytest.mark.anyio
    async def test_on_completed_calls_library_service(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        result = SynthesisJobResult(
            job_id="job-456",
            audiobook_id="book-789",
            source_filename="my-book.txt",
            model_id="hexgrad/Kokoro-82M",
            voice=None,
            language=None,
            chapter_results=[],
        )
        job_service.on_completed(result)

        mock_library_service.create_audiobook_from_job.assert_called_once_with(result)

    @pytest.mark.anyio
    async def test_on_failed_publishes_job_failed_event(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job_service.on_failed("job-err", "synthesis", "Out of VRAM")
        await asyncio.sleep(0.1)

        event_type, data = _parse_sse_message(queue.get_nowait())
        assert event_type == "job-failed"
        assert data == {
            "job_id": "job-err",
            "type": "synthesis",
            "error_message": "Out of VRAM",
        }


# ---------------------------------------------------------------------------
# Integration tests: end-to-end job → SSE
# ---------------------------------------------------------------------------


class TestJobProgressSSEIntegration:
    @pytest.mark.anyio
    async def test_processing_transition_emits_initial_progress_event(
        self,
        job_service: JobService,
        mock_tts_engine: MagicMock,
        mock_library_service: MagicMock,
        event_bus: EventBus,
    ):
        """The queued->processing transition emits a job-progress event with progress=0.

        Regression: without this initial event, the frontend (which relies
        exclusively on SSE per DEC-sse-progress) stays stuck at "queued" / 0%
        until the first chapter completes.
        """

        synthesize_started = threading.Event()
        synthesize_proceed = threading.Event()

        def slow_synthesize(text, output_dir, progress_callback=None):
            synthesize_started.set()
            synthesize_proceed.wait(timeout=5.0)
            if progress_callback:
                progress_callback(100)
            return [SynthesisResult(1, "Ch1", "chapter-01.mp3", 10.0)]

        mock_tts_engine.synthesize.side_effect = slow_synthesize

        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job = job_service.create_synthesis_job("book.txt", "Hello world")

        # Wait until synthesis has started (but not completed)
        assert synthesize_started.wait(timeout=5.0)
        await asyncio.sleep(0.2)

        # Drain events received so far — should include the initial progress=0
        events = await _drain_queue(queue, timeout=0.5)
        progress_events = [(t, d) for t, d in events if t == "job-progress"]
        assert len(progress_events) == 1
        assert progress_events[0][1]["progress"] == 0
        assert progress_events[0][1]["status"] == "processing"
        assert progress_events[0][1]["job_id"] == job.id

        # Let synthesis finish
        synthesize_proceed.set()
        _wait_for_job_status(job_service, job.id, "completed")

    @pytest.mark.anyio
    async def test_successful_job_emits_progress_and_completed(
        self,
        job_service: JobService,
        mock_tts_engine: MagicMock,
        mock_library_service: MagicMock,
        event_bus: EventBus,
    ):
        """A successful synthesis job publishes job-progress and job-completed events."""

        def fake_synthesize(text, output_dir, progress_callback=None):
            if progress_callback:
                progress_callback(33)
                progress_callback(66)
                progress_callback(100)
            return [SynthesisResult(1, "Chapter 1", "chapter-01.mp3", 30.0)]

        mock_tts_engine.synthesize.side_effect = fake_synthesize

        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job = job_service.create_synthesis_job("book.txt", "Hello world")

        # Wait for job to complete
        _wait_for_job_status(job_service, job.id, "completed")
        # Allow async events to propagate
        await asyncio.sleep(0.3)

        events = await _drain_queue(queue, timeout=1.0)

        # Should have 4 progress events (initial 0% + 3 from synthesis) + 1 completed
        progress_events = [(t, d) for t, d in events if t == "job-progress"]
        completed_events = [(t, d) for t, d in events if t == "job-completed"]

        assert len(progress_events) == 4
        assert [d["progress"] for _, d in progress_events] == [0, 33, 66, 100]
        for _, data in progress_events:
            assert data["job_id"] == job.id
            assert data["type"] == "synthesis"
            assert data["status"] == "processing"

        assert len(completed_events) == 1
        assert completed_events[0][1]["job_id"] == job.id
        assert completed_events[0][1]["type"] == "synthesis"
        assert completed_events[0][1]["audiobook_id"]  # non-empty UUID

    @pytest.mark.anyio
    async def test_failed_job_emits_job_failed_event(
        self,
        job_service: JobService,
        mock_tts_engine: MagicMock,
        mock_library_service: MagicMock,
        event_bus: EventBus,
    ):
        """A failed synthesis job publishes a job-failed event with error message."""
        mock_tts_engine.synthesize.side_effect = RuntimeError("GPU out of memory")

        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job = job_service.create_synthesis_job("book.txt", "Hello")

        _wait_for_job_status(job_service, job.id, "failed")
        await asyncio.sleep(0.3)

        events = await _drain_queue(queue, timeout=1.0)

        # Initial progress=0 event fires before synthesis attempt
        progress_events = [(t, d) for t, d in events if t == "job-progress"]
        assert len(progress_events) == 1
        assert progress_events[0][1]["progress"] == 0

        failed_events = [(t, d) for t, d in events if t == "job-failed"]
        assert len(failed_events) == 1
        assert failed_events[0][1]["job_id"] == job.id
        assert failed_events[0][1]["type"] == "synthesis"
        assert "GPU out of memory" in failed_events[0][1]["error_message"]

    @pytest.mark.anyio
    async def test_no_model_loaded_emits_job_failed_event(
        self,
        job_service: JobService,
        mock_tts_engine: MagicMock,
        mock_library_service: MagicMock,
        event_bus: EventBus,
    ):
        """When no model is loaded, job fails and publishes job-failed event."""
        mock_tts_engine.loaded_model_id = None

        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job = job_service.create_synthesis_job("book.txt", "Hello")

        _wait_for_job_status(job_service, job.id, "failed")
        await asyncio.sleep(0.3)

        events = await _drain_queue(queue, timeout=1.0)

        # Initial progress=0 event fires before model check
        progress_events = [(t, d) for t, d in events if t == "job-progress"]
        assert len(progress_events) == 1
        assert progress_events[0][1]["progress"] == 0

        failed_events = [(t, d) for t, d in events if t == "job-failed"]
        assert len(failed_events) == 1
        assert "No model loaded" in failed_events[0][1]["error_message"]


# ---------------------------------------------------------------------------
# SSE event payload conformance (api-design.md)
# ---------------------------------------------------------------------------


class TestEventPayloadConformance:
    @pytest.mark.anyio
    async def test_job_progress_payload_matches_api_design(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        """job-progress event has all fields from api-design.md."""
        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job_service.on_progress("j1", "synthesis", 42)
        await asyncio.sleep(0.1)

        _, data = _parse_sse_message(queue.get_nowait())
        assert set(data.keys()) == {"job_id", "type", "status", "progress"}

    @pytest.mark.anyio
    async def test_job_completed_payload_matches_api_design(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        """job-completed event has all fields from api-design.md."""
        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        result = SynthesisJobResult(
            job_id="j1", audiobook_id="b1", source_filename="f.txt",
            model_id="m1", voice=None, language=None, chapter_results=[],
        )
        job_service.on_completed(result)
        await asyncio.sleep(0.1)

        _, data = _parse_sse_message(queue.get_nowait())
        assert set(data.keys()) == {"job_id", "type", "audiobook_id"}

    @pytest.mark.anyio
    async def test_job_failed_payload_matches_api_design(
        self, job_service: JobService, mock_library_service: MagicMock, event_bus: EventBus,
    ):
        """job-failed event has all fields from api-design.md."""
        queue = await event_bus.subscribe()
        _wire_job_callbacks(job_service, mock_library_service, event_bus, asyncio.get_running_loop())

        job_service.on_failed("j1", "synthesis", "Error")
        await asyncio.sleep(0.1)

        _, data = _parse_sse_message(queue.get_nowait())
        assert set(data.keys()) == {"job_id", "type", "error_message"}
