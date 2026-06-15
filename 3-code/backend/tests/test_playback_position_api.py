"""Tests for the playback position API (TASK-playback-position-api).

Covers REQ-F-playback-resume acceptance criteria:
- GET /api/v1/audiobooks/{id}/position — returns the two-level bookmark.
- A never-played audiobook returns {"last_chapter_number": 1, "chapters": {}}.
- PUT /api/v1/audiobooks/{id}/position — saves the audiobook-level bookmark
  and the per-chapter timestamp; repeated PUTs update in place.
- Resume reads back the last active chapter and per-chapter positions.
- Unknown audiobook returns 404 on both GET and PUT.
- Invalid chapter number / position is rejected with 422.

These are integration tests: they run against a real SQLite database and a
real PlaybackService, exercising the actual upsert behavior.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from local_tts.api.playback import router
from local_tts.db import get_connection, init_db
from local_tts.services.playback_service import PlaybackService


# ---------------------------------------------------------------------------
# Fixtures & helpers
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
def app(tmp_data_dir: Path, db_conn) -> FastAPI:
    """Minimal app exposing the playback router backed by a real service."""
    application = FastAPI()
    application.include_router(router, prefix="/api/v1")
    application.state.playback_service = PlaybackService(tmp_data_dir)
    return application


def _seed_audiobook(conn, *, audiobook_id: str = "book-001") -> None:
    """Insert a minimal audiobook record (no chapters needed for positions)."""
    conn.execute(
        "INSERT INTO audiobook (id, title, source_filename, model_id) "
        "VALUES (?, 'My Book', 'my-book.txt', 'hexgrad/Kokoro-82M')",
        (audiobook_id,),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# GET /audiobooks/{id}/position
# ---------------------------------------------------------------------------


class TestGetPlaybackPosition:
    @pytest.mark.anyio
    async def test_never_played_returns_defaults(
        self, app: FastAPI, db_conn
    ):
        """Acceptance: never played -> starts from chapter 1, no saved chapters."""
        _seed_audiobook(db_conn)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks/book-001/position")

        assert response.status_code == 200
        assert response.json() == {"last_chapter_number": 1, "chapters": {}}

    @pytest.mark.anyio
    async def test_returns_saved_two_level_bookmark(
        self, app: FastAPI, db_conn
    ):
        _seed_audiobook(db_conn)
        db_conn.execute(
            "INSERT INTO playback_position (audiobook_id, last_chapter_number) "
            "VALUES ('book-001', 3)"
        )
        db_conn.executemany(
            "INSERT INTO chapter_playback_position "
            "(audiobook_id, chapter_number, position_seconds) VALUES (?, ?, ?)",
            [
                ("book-001", 1, 120.5),
                ("book-001", 2, 300.0),
                ("book-001", 3, 45.2),
            ],
        )
        db_conn.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks/book-001/position")

        assert response.status_code == 200
        assert response.json() == {
            "last_chapter_number": 3,
            "chapters": {"1": 120.5, "2": 300.0, "3": 45.2},
        }

    @pytest.mark.anyio
    async def test_unknown_audiobook_returns_404(self, app: FastAPI):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks/missing/position")

        assert response.status_code == 404
        assert response.json()["detail"] == "Audiobook not found"


# ---------------------------------------------------------------------------
# PUT /audiobooks/{id}/position
# ---------------------------------------------------------------------------


class TestUpdatePlaybackPosition:
    @pytest.mark.anyio
    async def test_saves_position_and_echoes_payload(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        """Acceptance: on stop, the chapter and timestamp are recorded."""
        _seed_audiobook(db_conn)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 3, "position_seconds": 45.2},
            )

        assert response.status_code == 200
        assert response.json() == {"chapter_number": 3, "position_seconds": 45.2}

        check = get_connection(tmp_data_dir)
        try:
            book_row = check.execute(
                "SELECT last_chapter_number FROM playback_position "
                "WHERE audiobook_id = 'book-001'"
            ).fetchone()
            ch_row = check.execute(
                "SELECT position_seconds FROM chapter_playback_position "
                "WHERE audiobook_id = 'book-001' AND chapter_number = 3"
            ).fetchone()
        finally:
            check.close()

        assert book_row[0] == 3
        assert ch_row[0] == 45.2

    @pytest.mark.anyio
    async def test_resume_after_save_reads_back_position(
        self, app: FastAPI, db_conn
    ):
        """Acceptance: returning to the audiobook loads the last active chapter
        and resumes from that chapter's saved position."""
        _seed_audiobook(db_conn)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 2, "position_seconds": 88.0},
            )
            response = await client.get("/api/v1/audiobooks/book-001/position")

        assert response.json() == {
            "last_chapter_number": 2,
            "chapters": {"2": 88.0},
        }

    @pytest.mark.anyio
    async def test_repeated_put_updates_in_place(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        """Per-chapter and audiobook bookmarks upsert (one row each)."""
        _seed_audiobook(db_conn)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 2, "position_seconds": 10.0},
            )
            await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 2, "position_seconds": 55.5},
            )
            response = await client.get("/api/v1/audiobooks/book-001/position")

        assert response.json() == {
            "last_chapter_number": 2,
            "chapters": {"2": 55.5},
        }

        check = get_connection(tmp_data_dir)
        try:
            book_count = check.execute(
                "SELECT COUNT(*) FROM playback_position "
                "WHERE audiobook_id = 'book-001'"
            ).fetchone()[0]
            ch_count = check.execute(
                "SELECT COUNT(*) FROM chapter_playback_position "
                "WHERE audiobook_id = 'book-001'"
            ).fetchone()[0]
        finally:
            check.close()

        assert book_count == 1
        assert ch_count == 1

    @pytest.mark.anyio
    async def test_navigating_chapters_keeps_per_chapter_positions(
        self, app: FastAPI, db_conn
    ):
        """Acceptance: a previously listened chapter keeps its own position;
        a chapter never listened to has no saved position."""
        _seed_audiobook(db_conn)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 1, "position_seconds": 200.0},
            )
            await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 3, "position_seconds": 12.0},
            )
            response = await client.get("/api/v1/audiobooks/book-001/position")

        body = response.json()
        # Last active chapter is the most recent one written.
        assert body["last_chapter_number"] == 3
        # Chapter 1 retains its position; chapter 2 (never played) is absent.
        assert body["chapters"] == {"1": 200.0, "3": 12.0}
        assert "2" not in body["chapters"]

    @pytest.mark.anyio
    async def test_updated_at_is_refreshed_on_update(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        """The UPDATE branch of the upsert must set updated_at (the DB default
        only fires on INSERT) and it must be ISO 8601 UTC with a trailing Z."""
        _seed_audiobook(db_conn)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 1, "position_seconds": 1.0},
            )
            await client.put(
                "/api/v1/audiobooks/book-001/position",
                json={"chapter_number": 1, "position_seconds": 2.0},
            )

        check = get_connection(tmp_data_dir)
        try:
            updated_at = check.execute(
                "SELECT updated_at FROM chapter_playback_position "
                "WHERE audiobook_id = 'book-001' AND chapter_number = 1"
            ).fetchone()[0]
        finally:
            check.close()

        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", updated_at)

    @pytest.mark.anyio
    async def test_unknown_audiobook_returns_404(self, app: FastAPI):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                "/api/v1/audiobooks/missing/position",
                json={"chapter_number": 1, "position_seconds": 0.0},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Audiobook not found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "payload",
        [
            {"chapter_number": 0, "position_seconds": 5.0},
            {"chapter_number": -1, "position_seconds": 5.0},
            {"chapter_number": 1, "position_seconds": -1.0},
            {"position_seconds": 5.0},
            {"chapter_number": 1},
        ],
    )
    async def test_invalid_payload_returns_422(
        self, app: FastAPI, db_conn, payload: dict
    ):
        _seed_audiobook(db_conn)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                "/api/v1/audiobooks/book-001/position", json=payload
            )

        assert response.status_code == 422
