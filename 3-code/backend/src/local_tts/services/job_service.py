"""Job Service — application service for synthesis job management.

Manages the lifecycle of synthesis jobs: queued -> processing -> completed/failed.
Jobs run sequentially in a single background daemon thread (DEC-single-process,
CON-single-user). State is persisted to SQLite (DEC-sqlite-metadata).

Downstream tasks wire in additional behavior via callbacks:
- TASK-job-progress-sse: publishes progress to SSE EventBus
- TASK-library-service-create: creates audiobook + chapter records on completion
"""

from __future__ import annotations

import logging
import queue
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from local_tts.db import get_connection
from local_tts.tts.engine import TTSEngine
from local_tts.tts.synthesizer import SynthesisResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobInfo:
    """Read-only snapshot of a job's current state."""

    id: str
    audiobook_id: str | None
    type: str
    status: str
    progress: int
    error_message: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None


@dataclass(frozen=True)
class SynthesisJobResult:
    """Data produced by a completed synthesis job.

    Passed to the on_completed callback so downstream tasks (e.g.,
    TASK-library-service-create) have everything they need to create
    audiobook and chapter records.
    """

    job_id: str
    audiobook_id: str
    source_filename: str
    model_id: str
    voice: str | None
    language: str | None
    chapter_results: list[SynthesisResult]


# Type aliases for callbacks
ProgressCallback = Callable[[str, str, int], None]
"""(job_id, job_type, progress_percent) -> None"""

CompletedCallback = Callable[[SynthesisJobResult], None]
"""(result) -> None"""

FailedCallback = Callable[[str, str, str], None]
"""(job_id, job_type, error_message) -> None"""


@dataclass
class _SynthesisWork:
    """Internal work item enqueued for background processing."""

    job_id: str
    source_filename: str
    text: str
    voice: str | None
    language: str | None


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_job_info(row: tuple) -> JobInfo:
    return JobInfo(
        id=row[0],
        audiobook_id=row[1],
        type=row[2],
        status=row[3],
        progress=row[4],
        error_message=row[5],
        created_at=row[6],
        started_at=row[7],
        completed_at=row[8],
    )


_JOB_SELECT_COLS = (
    "id, audiobook_id, type, status, progress, error_message, "
    "created_at, started_at, completed_at"
)


class JobService:
    """Manages synthesis job lifecycle with sequential background processing.

    Jobs are enqueued via :meth:`create_synthesis_job` and processed one at a
    time by a daemon thread. The service persists job state transitions to
    SQLite and invokes optional callbacks for progress reporting and
    completion handling.
    """

    def __init__(
        self,
        tts_engine: TTSEngine,
        db_conn: sqlite3.Connection,
        data_dir: Path,
    ) -> None:
        self._tts_engine = tts_engine
        self._db_conn = db_conn
        self._data_dir = data_dir
        self._queue: queue.Queue[_SynthesisWork | None] = queue.Queue()

        self.on_progress: ProgressCallback | None = None
        self.on_completed: CompletedCallback | None = None
        self.on_failed: FailedCallback | None = None

        self._worker_thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="job-worker",
        )
        self._worker_thread.start()

    # ------------------------------------------------------------------
    # Public API (called from main / request threads)
    # ------------------------------------------------------------------

    def create_synthesis_job(
        self,
        source_filename: str,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> JobInfo:
        """Create a synthesis job and enqueue it for background processing.

        The job is inserted into the database with status ``queued`` and
        immediately placed on the work queue.

        Args:
            source_filename: Original .txt filename (used for title derivation).
            text: Full text content to synthesize.
            voice: Voice selection (model default if None).
            language: Language selection (model default if None).

        Returns:
            A snapshot of the newly created job.
        """
        job_id = str(uuid.uuid4())
        now = _utcnow_iso()

        self._db_conn.execute(
            "INSERT INTO job (id, type, status, progress, created_at) "
            "VALUES (?, 'synthesis', 'queued', 0, ?)",
            (job_id, now),
        )
        self._db_conn.commit()

        self._queue.put(
            _SynthesisWork(
                job_id=job_id,
                source_filename=source_filename,
                text=text,
                voice=voice,
                language=language,
            )
        )

        logger.info("Synthesis job %s created and queued", job_id)

        return JobInfo(
            id=job_id,
            audiobook_id=None,
            type="synthesis",
            status="queued",
            progress=0,
            error_message=None,
            created_at=now,
            started_at=None,
            completed_at=None,
        )

    def get_job(self, job_id: str) -> JobInfo | None:
        """Retrieve a job by ID, or None if not found."""
        row = self._db_conn.execute(
            f"SELECT {_JOB_SELECT_COLS} FROM job WHERE id = ?",
            (job_id,),
        ).fetchone()
        return _row_to_job_info(row) if row else None

    def list_jobs(self) -> list[JobInfo]:
        """List all jobs, most recent first."""
        rows = self._db_conn.execute(
            f"SELECT {_JOB_SELECT_COLS} FROM job ORDER BY created_at DESC",
        ).fetchall()
        return [_row_to_job_info(r) for r in rows]

    def shutdown(self) -> None:
        """Signal the background worker to stop and wait for it to finish."""
        self._queue.put(None)
        self._worker_thread.join(timeout=30)

    # ------------------------------------------------------------------
    # Background worker (runs in daemon thread)
    # ------------------------------------------------------------------

    def _worker(self) -> None:
        """Process jobs sequentially from the queue."""
        worker_conn = get_connection(self._data_dir)
        logger.info("Job worker started")
        try:
            while True:
                work = self._queue.get()
                if work is None:
                    logger.info("Job worker shutting down")
                    break
                try:
                    self._process_synthesis_job(work, worker_conn)
                except Exception:
                    logger.exception(
                        "Unexpected error processing job %s", work.job_id
                    )
        finally:
            worker_conn.close()

    def _process_synthesis_job(
        self,
        work: _SynthesisWork,
        conn: sqlite3.Connection,
    ) -> None:
        """Execute a single synthesis job end-to-end."""
        job_id = work.job_id
        now = _utcnow_iso()

        # Transition: queued -> processing
        conn.execute(
            "UPDATE job SET status = 'processing', started_at = ? WHERE id = ?",
            (now, job_id),
        )
        conn.commit()

        if self.on_progress:
            self.on_progress(job_id, "synthesis", 0)

        # Check that a model is loaded
        model_id = self._tts_engine.loaded_model_id
        if model_id is None:
            self._fail_job(
                conn, job_id, "No model loaded — cannot synthesize"
            )
            return

        # Prepare output directory: data/audiobooks/<audiobook_id>/
        audiobook_id = str(uuid.uuid4())
        output_dir = self._data_dir / "audiobooks" / audiobook_id

        try:

            def progress_callback(progress: int) -> None:
                conn.execute(
                    "UPDATE job SET progress = ? WHERE id = ?",
                    (progress, job_id),
                )
                conn.commit()
                if self.on_progress:
                    self.on_progress(job_id, "synthesis", progress)

            results = self._tts_engine.synthesize(
                text=work.text,
                output_dir=output_dir,
                progress_callback=progress_callback,
                voice=work.voice,
                language=work.language,
            )

            # Transition: processing -> completed
            completed_at = _utcnow_iso()
            conn.execute(
                "UPDATE job SET status = 'completed', progress = 100, "
                "completed_at = ? WHERE id = ?",
                (completed_at, job_id),
            )
            conn.commit()

            logger.info(
                "Synthesis job %s completed (%d chapters, audiobook %s)",
                job_id,
                len(results),
                audiobook_id,
            )

            if self.on_completed:
                self.on_completed(
                    SynthesisJobResult(
                        job_id=job_id,
                        audiobook_id=audiobook_id,
                        source_filename=work.source_filename,
                        model_id=model_id,
                        voice=work.voice,
                        language=work.language,
                        chapter_results=results,
                    )
                )

        except Exception as exc:
            logger.error("Synthesis job %s failed: %s", job_id, exc)
            self._fail_job(conn, job_id, str(exc))

    def _fail_job(
        self,
        conn: sqlite3.Connection,
        job_id: str,
        error_message: str,
    ) -> None:
        """Transition a job to the failed state."""
        completed_at = _utcnow_iso()
        conn.execute(
            "UPDATE job SET status = 'failed', error_message = ?, "
            "completed_at = ? WHERE id = ?",
            (error_message, completed_at, job_id),
        )
        conn.commit()

        if self.on_failed:
            self.on_failed(job_id, "synthesis", error_message)
