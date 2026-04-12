"""Library Service — creates audiobook and chapter records on synthesis completion.

When a synthesis job completes successfully, the JobService invokes
:meth:`LibraryService.create_audiobook_from_job` via the ``on_completed``
callback.  This method persists the audiobook and its chapters to SQLite
(DEC-sqlite-metadata) and links the job record to the new audiobook.

The callback runs on the job-worker thread, so the service opens its own
database connection per call to stay thread-safe.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from local_tts.db import get_connection
from local_tts.services.job_service import SynthesisJobResult

logger = logging.getLogger(__name__)


def _derive_title(source_filename: str) -> str:
    """Derive an audiobook title from the source filename.

    Strips the ``.txt`` extension and replaces hyphens/underscores with spaces.
    """
    stem = Path(source_filename).stem
    return stem.replace("-", " ").replace("_", " ")


class LibraryService:
    """Manages audiobook persistence triggered by synthesis completion."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def create_audiobook_from_job(self, result: SynthesisJobResult) -> None:
        """Persist audiobook + chapter records and link the job.

        Called from the job-worker thread when a synthesis job completes.

        Steps:
            1. INSERT audiobook record (REQ-F-synthesize-audiobook).
            2. INSERT one chapter record per synthesized chapter
               (REQ-F-chapter-split-output).
            3. UPDATE the job row to set ``audiobook_id``.
        """
        conn = get_connection(self._data_dir)
        try:
            title = _derive_title(result.source_filename)

            # 1. Create audiobook record
            conn.execute(
                "INSERT INTO audiobook "
                "(id, title, source_filename, model_id, voice, language) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    result.audiobook_id,
                    title,
                    result.source_filename,
                    result.model_id,
                    result.voice,
                    result.language,
                ),
            )

            # 2. Create chapter records
            for ch in result.chapter_results:
                chapter_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO chapter "
                    "(id, audiobook_id, chapter_number, title, "
                    "audio_filename, duration_seconds) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        chapter_id,
                        result.audiobook_id,
                        ch.chapter_number,
                        ch.title,
                        ch.audio_filename,
                        ch.duration_seconds,
                    ),
                )

            # 3. Link job to audiobook
            conn.execute(
                "UPDATE job SET audiobook_id = ? WHERE id = ?",
                (result.audiobook_id, result.job_id),
            )

            conn.commit()

            logger.info(
                "Audiobook %s created (%d chapters) for job %s",
                result.audiobook_id,
                len(result.chapter_results),
                result.job_id,
            )

        except Exception:
            conn.rollback()
            logger.exception(
                "Failed to create audiobook records for job %s",
                result.job_id,
            )
            raise
        finally:
            conn.close()
