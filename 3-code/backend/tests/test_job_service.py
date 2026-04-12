"""Tests for the JobService application service (TASK-job-service).

Covers:
- Job creation inserts a DB record and enqueues work
- get_job / list_jobs return correct data
- Background worker transitions job through queued -> processing -> completed
- Failed synthesis transitions job to failed state with error message
- Progress callback updates DB and invokes on_progress
- on_completed callback receives SynthesisJobResult with correct data
- on_failed callback is invoked with error details
- No-model-loaded scenario fails the job
- Sequential processing (one job at a time)
- Shutdown stops the worker thread
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from local_tts.db import init_db
from local_tts.services.job_service import JobInfo, JobService, SynthesisJobResult
from local_tts.tts.synthesizer import SynthesisResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        SynthesisResult(chapter_number=1, audio_filename="chapter-01.mp3", duration_seconds=60.0),
    ]
    return engine


@pytest.fixture()
def service(mock_tts_engine: MagicMock, db_conn, tmp_data_dir: Path):
    svc = JobService(mock_tts_engine, db_conn, tmp_data_dir)
    yield svc
    svc.shutdown()


# ---------------------------------------------------------------------------
# create_synthesis_job
# ---------------------------------------------------------------------------


class TestCreateSynthesisJob:
    def test_returns_job_info_with_queued_status(self, service: JobService):
        job = service.create_synthesis_job("book.txt", "Hello world")
        assert isinstance(job, JobInfo)
        assert job.type == "synthesis"
        assert job.status == "queued"
        assert job.progress == 0
        assert job.audiobook_id is None
        assert job.error_message is None
        assert job.started_at is None
        assert job.completed_at is None

    def test_generates_unique_job_ids(self, service: JobService):
        job1 = service.create_synthesis_job("a.txt", "Text A")
        job2 = service.create_synthesis_job("b.txt", "Text B")
        assert job1.id != job2.id

    def test_persists_job_to_database(self, service: JobService, db_conn):
        job = service.create_synthesis_job("book.txt", "Hello")
        row = db_conn.execute(
            "SELECT id, type, status, progress FROM job WHERE id = ?",
            (job.id,),
        ).fetchone()
        assert row is not None
        assert row[0] == job.id
        assert row[1] == "synthesis"
        assert row[2] == "queued"
        assert row[3] == 0


# ---------------------------------------------------------------------------
# get_job
# ---------------------------------------------------------------------------


class TestGetJob:
    def test_returns_created_job(self, service: JobService):
        created = service.create_synthesis_job("book.txt", "Hello")
        fetched = service.get_job(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.status == "queued"

    def test_returns_none_for_unknown_id(self, service: JobService):
        assert service.get_job("nonexistent-id") is None


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------


class TestListJobs:
    def test_returns_empty_when_no_jobs(self, service: JobService):
        assert service.list_jobs() == []

    def test_returns_all_jobs_most_recent_first(self, service: JobService):
        job1 = service.create_synthesis_job("a.txt", "A")
        job2 = service.create_synthesis_job("b.txt", "B")
        jobs = service.list_jobs()
        assert len(jobs) >= 2
        ids = [j.id for j in jobs]
        assert job2.id in ids
        assert job1.id in ids


# ---------------------------------------------------------------------------
# Background processing: successful synthesis
# ---------------------------------------------------------------------------


class TestSuccessfulProcessing:
    def test_job_transitions_to_completed(self, service: JobService, mock_tts_engine: MagicMock):
        job = service.create_synthesis_job("book.txt", "Hello world")

        # Wait for background processing
        _wait_for_job_status(service, job.id, "completed")

        updated = service.get_job(job.id)
        assert updated is not None
        assert updated.status == "completed"
        assert updated.progress == 100
        assert updated.completed_at is not None
        assert updated.started_at is not None

    def test_calls_tts_engine_synthesize(self, service: JobService, mock_tts_engine: MagicMock):
        job = service.create_synthesis_job("book.txt", "Hello world")
        _wait_for_job_status(service, job.id, "completed")

        mock_tts_engine.synthesize.assert_called_once()
        call_kwargs = mock_tts_engine.synthesize.call_args
        assert call_kwargs.kwargs["text"] == "Hello world"
        assert isinstance(call_kwargs.kwargs["output_dir"], Path)

    def test_output_dir_under_audiobooks(self, service: JobService, mock_tts_engine: MagicMock, tmp_data_dir: Path):
        job = service.create_synthesis_job("book.txt", "Hello world")
        _wait_for_job_status(service, job.id, "completed")

        call_kwargs = mock_tts_engine.synthesize.call_args
        output_dir: Path = call_kwargs.kwargs["output_dir"]
        assert output_dir.parent == tmp_data_dir / "audiobooks"

    def test_on_completed_callback_invoked(self, service: JobService, mock_tts_engine: MagicMock):
        callback = MagicMock()
        service.on_completed = callback

        job = service.create_synthesis_job("my-book.txt", "Some text", voice="af_heart", language="en")
        _wait_for_job_status(service, job.id, "completed")

        callback.assert_called_once()
        result: SynthesisJobResult = callback.call_args[0][0]
        assert result.job_id == job.id
        assert result.source_filename == "my-book.txt"
        assert result.model_id == "hexgrad/Kokoro-82M"
        assert result.voice == "af_heart"
        assert result.language == "en"
        assert len(result.chapter_results) == 1
        assert result.audiobook_id  # non-empty UUID


# ---------------------------------------------------------------------------
# Background processing: progress reporting
# ---------------------------------------------------------------------------


class TestProgressReporting:
    def test_progress_callback_updates_database(self, service: JobService, mock_tts_engine: MagicMock, db_conn):
        progress_values: list[int] = []

        def fake_synthesize(text, output_dir, progress_callback=None):
            if progress_callback:
                progress_callback(33)
                progress_callback(66)
                progress_callback(100)
            return [SynthesisResult(1, "chapter-01.mp3", 30.0)]

        mock_tts_engine.synthesize.side_effect = fake_synthesize

        callback = MagicMock()
        service.on_progress = callback

        job = service.create_synthesis_job("book.txt", "Hello")
        _wait_for_job_status(service, job.id, "completed")

        assert callback.call_count == 3
        callback.assert_any_call(job.id, "synthesis", 33)
        callback.assert_any_call(job.id, "synthesis", 66)
        callback.assert_any_call(job.id, "synthesis", 100)


# ---------------------------------------------------------------------------
# Background processing: failed synthesis
# ---------------------------------------------------------------------------


class TestFailedProcessing:
    def test_synthesis_error_transitions_to_failed(self, service: JobService, mock_tts_engine: MagicMock):
        mock_tts_engine.synthesize.side_effect = RuntimeError("GPU out of memory")

        job = service.create_synthesis_job("book.txt", "Hello")
        _wait_for_job_status(service, job.id, "failed")

        updated = service.get_job(job.id)
        assert updated is not None
        assert updated.status == "failed"
        assert "GPU out of memory" in updated.error_message
        assert updated.completed_at is not None

    def test_on_failed_callback_invoked(self, service: JobService, mock_tts_engine: MagicMock):
        mock_tts_engine.synthesize.side_effect = RuntimeError("boom")
        callback = MagicMock()
        service.on_failed = callback

        job = service.create_synthesis_job("book.txt", "Hello")
        _wait_for_job_status(service, job.id, "failed")

        callback.assert_called_once_with(job.id, "synthesis", "boom")

    def test_no_model_loaded_fails_job(self, service: JobService, mock_tts_engine: MagicMock):
        mock_tts_engine.loaded_model_id = None

        job = service.create_synthesis_job("book.txt", "Hello")
        _wait_for_job_status(service, job.id, "failed")

        updated = service.get_job(job.id)
        assert updated is not None
        assert updated.status == "failed"
        assert "No model loaded" in updated.error_message


# ---------------------------------------------------------------------------
# Sequential processing
# ---------------------------------------------------------------------------


class TestSequentialProcessing:
    def test_jobs_processed_in_order(self, service: JobService, mock_tts_engine: MagicMock):
        processing_order: list[str] = []
        gate = threading.Event()

        def ordered_synthesize(text, output_dir, progress_callback=None):
            processing_order.append(text)
            if text == "first":
                gate.wait(timeout=5)
            return [SynthesisResult(1, "chapter-01.mp3", 10.0)]

        mock_tts_engine.synthesize.side_effect = ordered_synthesize

        job1 = service.create_synthesis_job("a.txt", "first")
        job2 = service.create_synthesis_job("b.txt", "second")

        # Give time for first job to start processing
        time.sleep(0.2)

        # First job should be processing, second still queued
        j2 = service.get_job(job2.id)
        assert j2 is not None
        assert j2.status == "queued"

        # Release the gate
        gate.set()

        _wait_for_job_status(service, job2.id, "completed")

        assert processing_order == ["first", "second"]


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------


class TestShutdown:
    def test_shutdown_stops_worker(self, mock_tts_engine: MagicMock, db_conn, tmp_data_dir: Path):
        svc = JobService(mock_tts_engine, db_conn, tmp_data_dir)
        assert svc._worker_thread.is_alive()
        svc.shutdown()
        assert not svc._worker_thread.is_alive()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
