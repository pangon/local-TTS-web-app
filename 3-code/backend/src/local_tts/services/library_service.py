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
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

from local_tts.db import get_connection
from local_tts.services.job_service import SynthesisJobResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudiobookSummary:
    """Audiobook metadata for the library list view (REQ-F-library-listing)."""

    id: str
    title: str
    source_filename: str
    model_id: str
    voice: str | None
    language: str | None
    created_at: str
    chapter_count: int


@dataclass(frozen=True)
class ChapterInfo:
    """Chapter metadata returned with audiobook details."""

    chapter_number: int
    title: str
    duration_seconds: float | None


@dataclass(frozen=True)
class AudiobookDetail:
    """Full audiobook details including the chapter list."""

    id: str
    title: str
    source_filename: str
    model_id: str
    voice: str | None
    language: str | None
    created_at: str
    chapters: list[ChapterInfo]


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

    def list_audiobooks(self) -> list[AudiobookSummary]:
        """Return all audiobooks with their chapter counts (REQ-F-library-listing).

        Ordered newest-first.  Returns an empty list when no audiobooks exist.
        """
        conn = get_connection(self._data_dir)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT a.id, a.title, a.source_filename, a.model_id, "
                "a.voice, a.language, a.created_at, "
                "COUNT(c.id) AS chapter_count "
                "FROM audiobook a "
                "LEFT JOIN chapter c ON c.audiobook_id = a.id "
                "GROUP BY a.id "
                "ORDER BY a.created_at DESC, a.id"
            ).fetchall()
        finally:
            conn.close()

        return [
            AudiobookSummary(
                id=row["id"],
                title=row["title"],
                source_filename=row["source_filename"],
                model_id=row["model_id"],
                voice=row["voice"],
                language=row["language"],
                created_at=row["created_at"],
                chapter_count=row["chapter_count"],
            )
            for row in rows
        ]

    def get_audiobook(self, audiobook_id: str) -> AudiobookDetail | None:
        """Return audiobook details with its chapter list, or ``None`` if absent."""
        conn = get_connection(self._data_dir)
        conn.row_factory = sqlite3.Row
        try:
            book = conn.execute(
                "SELECT id, title, source_filename, model_id, voice, language, "
                "created_at FROM audiobook WHERE id = ?",
                (audiobook_id,),
            ).fetchone()
            if book is None:
                return None

            chapter_rows = conn.execute(
                "SELECT chapter_number, title, duration_seconds "
                "FROM chapter WHERE audiobook_id = ? ORDER BY chapter_number",
                (audiobook_id,),
            ).fetchall()
        finally:
            conn.close()

        return AudiobookDetail(
            id=book["id"],
            title=book["title"],
            source_filename=book["source_filename"],
            model_id=book["model_id"],
            voice=book["voice"],
            language=book["language"],
            created_at=book["created_at"],
            chapters=[
                ChapterInfo(
                    chapter_number=ch["chapter_number"],
                    title=ch["title"],
                    duration_seconds=ch["duration_seconds"],
                )
                for ch in chapter_rows
            ],
        )

    def delete_audiobook(self, audiobook_id: str) -> bool:
        """Delete an audiobook, its DB records, and its audio files.

        Chapter and playback-position rows are removed automatically by the
        ``ON DELETE CASCADE`` foreign keys (DEC-sqlite-metadata); the linked
        job rows have their ``audiobook_id`` set to NULL.  The on-disk audio
        directory (``audiobooks/<id>/``) is removed after the database row is
        committed.

        Returns ``True`` if the audiobook existed and was deleted, ``False``
        if no audiobook with the given id was found.
        """
        conn = get_connection(self._data_dir)
        try:
            cursor = conn.execute(
                "DELETE FROM audiobook WHERE id = ?", (audiobook_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
        except Exception:
            conn.rollback()
            logger.exception("Failed to delete audiobook %s", audiobook_id)
            raise
        finally:
            conn.close()

        if not deleted:
            return False

        audio_dir = self._data_dir / "audiobooks" / audiobook_id
        if audio_dir.exists():
            shutil.rmtree(audio_dir, ignore_errors=True)

        logger.info("Audiobook %s deleted", audiobook_id)
        return True
