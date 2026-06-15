"""Playback Position Service — two-level resume bookmarks (REQ-F-playback-resume).

Persists playback progress at two levels (data-model.md):

1. An audiobook-level bookmark (``playback_position``) recording the chapter
   the user was last listening to.
2. A per-chapter bookmark (``chapter_playback_position``) recording the
   timestamp within each individual chapter.

The application is single-user (CON-single-user), so there is at most one
audiobook-level row per audiobook and one per-chapter row per chapter.
Persistence uses SQLite (DEC-sqlite-metadata); each call opens its own
connection so the service is safe to use from any request handler.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from local_tts.db import get_connection
from local_tts.timeutils import utcnow_iso

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaybackPosition:
    """Two-level playback bookmark for an audiobook (REQ-F-playback-resume).

    ``last_chapter_number`` is the audiobook-level bookmark (the chapter the
    user was last listening to).  ``chapters`` maps chapter numbers (as strings,
    for JSON object keys) to the saved timestamp in seconds; only chapters that
    have been listened to appear.
    """

    last_chapter_number: int
    chapters: dict[str, float]


class PlaybackService:
    """Reads and writes two-level playback bookmarks."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def _audiobook_exists(self, conn: sqlite3.Connection, audiobook_id: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM audiobook WHERE id = ?", (audiobook_id,)
        ).fetchone()
        return row is not None

    def get_position(self, audiobook_id: str) -> PlaybackPosition | None:
        """Return the two-level bookmark for an audiobook.

        Returns ``None`` if the audiobook does not exist (the caller maps this
        to 404).  If the audiobook exists but has never been played, returns
        ``last_chapter_number = 1`` with an empty ``chapters`` map.
        """
        conn = get_connection(self._data_dir)
        try:
            if not self._audiobook_exists(conn, audiobook_id):
                return None

            book_row = conn.execute(
                "SELECT last_chapter_number FROM playback_position "
                "WHERE audiobook_id = ?",
                (audiobook_id,),
            ).fetchone()
            last_chapter_number = book_row[0] if book_row is not None else 1

            chapter_rows = conn.execute(
                "SELECT chapter_number, position_seconds "
                "FROM chapter_playback_position WHERE audiobook_id = ?",
                (audiobook_id,),
            ).fetchall()
        finally:
            conn.close()

        chapters = {str(row[0]): row[1] for row in chapter_rows}
        return PlaybackPosition(
            last_chapter_number=last_chapter_number,
            chapters=chapters,
        )

    def update_position(
        self, audiobook_id: str, chapter_number: int, position_seconds: float
    ) -> bool:
        """Save the audiobook-level bookmark and the per-chapter timestamp.

        Upserts both ``playback_position`` (setting ``last_chapter_number`` to
        the given chapter) and ``chapter_playback_position`` (setting the
        chapter's ``position_seconds``).  Returns ``True`` on success, or
        ``False`` if the audiobook does not exist (the caller maps this to 404).
        """
        # updated_at is set explicitly: the SQLite column default only fires on
        # INSERT, so the UPDATE branch of the upsert must refresh it.
        now = utcnow_iso()
        conn = get_connection(self._data_dir)
        try:
            if not self._audiobook_exists(conn, audiobook_id):
                return False

            conn.execute(
                "INSERT INTO playback_position "
                "(audiobook_id, last_chapter_number, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(audiobook_id) DO UPDATE SET "
                "last_chapter_number = excluded.last_chapter_number, "
                "updated_at = excluded.updated_at",
                (audiobook_id, chapter_number, now),
            )
            conn.execute(
                "INSERT INTO chapter_playback_position "
                "(audiobook_id, chapter_number, position_seconds, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(audiobook_id, chapter_number) DO UPDATE SET "
                "position_seconds = excluded.position_seconds, "
                "updated_at = excluded.updated_at",
                (audiobook_id, chapter_number, position_seconds, now),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception(
                "Failed to update playback position for audiobook %s",
                audiobook_id,
            )
            raise
        finally:
            conn.close()

        return True
